import json

import pytest
from fastapi.testclient import TestClient

from verifier.api import create_app
from verifier.llm import FakeLLM, UpstreamError
from verifier.parsing import ParseError
from verifier.pipelines import LexicalVerifier, MinimalVerifier, PivotVerifier
from verifier.schemas import Verdict

PASSAGES = ["The WAL file grows until a checkpoint. A checkpoint runs at 1000 pages by default.",
            "The default page size is 4096 bytes."]
ANSWER = "Checkpoints run at 1000 pages. So the WAL reaches about 8 MB. WAL was added in 2010."


def stage1(claims):
    return json.dumps({"claims": claims})


C_DIRECT = {"anchor": "Checkpoints run at 1000 pages", "claim_text": "A checkpoint runs at 1000 pages by default.",
            "kind": "direct", "sure": True, "evidence": [{"sid": "P0.S1", "rel": "entails"}], "reasoning": "stated"}
C_ARITH = {"anchor": "the WAL reaches about 8 MB", "claim_text": "The WAL reaches about 8 MB before a checkpoint.",
           "kind": "arith", "sure": True, "evidence": [{"sid": "P0.S1", "rel": "entails"}, {"sid": "P1.S0", "rel": "entails"}],
           "check": {"kind": "arith", "expr": "1000*4096/1e6", "op": "==", "value": "8"}, "reasoning": "1000 pages x 4KB"}
C_EXTR = {"anchor": "WAL was added in 2010", "claim_text": "WAL was added in 2010.", "kind": "direct", "sure": True,
          "evidence": [], "reasoning": "not in passages"}


def test_pivot_end_to_end_with_escalation():
    refuting = [dict(e, rel="refutes") for e in C_ARITH["evidence"]]  # the escalated model read the computed value
    esc = json.dumps({"claims": [{"id": "c1", "evidence": refuting, "check": C_ARITH["check"],
                                  "reasoning": "1000 * 4096 B = 4.1 MB, not 8"}]})
    llm = FakeLLM([stage1([C_DIRECT, C_ARITH, C_EXTR]), esc])
    r = PivotVerifier(llm).verify(PASSAGES, ANSWER)
    assert [c.verdict for c in r.claims] == [Verdict.SUPPORTED, Verdict.CONTRADICTED, Verdict.UNSUPPORTED]
    assert r.claims[1].citations[1].quote == PASSAGES[1]
    assert r.claims[0].answer_span == [0, 29]
    assert r.meta.llm_calls == 2 and r.meta.escalated_claims == 1 and r.meta.computed_checks == 1
    assert llm.calls[0]["thinking"] is False and llm.calls[1]["thinking"] is True
    assert "[c1]" in llm.calls[1]["messages"][1]["content"]  # only the hard claim is escalated
    assert "[c0]" not in llm.calls[1]["messages"][1]["content"]


def test_pivot_no_escalation_when_all_direct():
    llm = FakeLLM([stage1([C_DIRECT, C_EXTR])])
    r = PivotVerifier(llm).verify(PASSAGES, ANSWER)
    assert r.meta.llm_calls == 1 and r.meta.escalated_claims == 0


def test_escalation_failure_returns_partial():
    llm = FakeLLM([stage1([C_DIRECT, C_ARITH]), UpstreamError("timeout", "slow")])
    r = PivotVerifier(llm).verify(PASSAGES, ANSWER)
    assert r.meta.status == "partial" and r.claims[1].verdict is Verdict.CONTRADICTED  # first-pass check still computed


def test_fault_injection_reask_recovers():
    """Broken output first, valid output second: PiVoT recovers, minimal fails."""
    for bad in ["not json at all", '{"claims": "oops"}']:
        r = PivotVerifier(FakeLLM([bad, stage1([C_DIRECT])])).verify(PASSAGES, ANSWER)
        assert r.meta.parse_repairs == ["reask"] and r.claims[0].verdict is Verdict.SUPPORTED
        with pytest.raises(ParseError):
            MinimalVerifier(FakeLLM([bad])).verify(PASSAGES, ANSWER)


def test_pivot_tolerates_array_wrapping_and_bad_pointers():
    wrapped = json.dumps([{"claims": [dict(C_DIRECT, evidence=[{"sid": "P9.S9", "rel": "entails"}])]}])
    r = PivotVerifier(FakeLLM([wrapped]), escalate="never").verify(PASSAGES, ANSWER)
    assert r.meta.parse_repairs == ["unwrap_array"] and r.meta.dropped_pointers == 1 and r.meta.status == "ok"
    assert r.claims[0].verdict is Verdict.UNSUPPORTED and r.claims[0].citations == []


def test_minimal_enforces_verbatim():
    out = json.dumps({"claims": [
        {"claim_text": "a", "verdict": "SUPPORTED", "reasoning": "", "citations": [{"index": 0, "quote": "1000 pages by default"}]},
        {"claim_text": "b", "verdict": "SUPPORTED", "reasoning": "", "citations": [{"index": 0, "quote": "1000 pages ... default"}]}]})
    r = MinimalVerifier(FakeLLM([out])).verify(PASSAGES, ANSWER)
    assert [c.verdict for c in r.claims] == [Verdict.SUPPORTED, Verdict.UNSUPPORTED] and r.meta.dropped_pointers == 1


def test_edge_cases_skip_the_model():
    llm = FakeLLM([])  # any call would raise
    assert PivotVerifier(llm).verify(PASSAGES, "   ").claims == []
    r = PivotVerifier(llm).verify([], "Fact one. Fact two.")
    assert [c.verdict for c in r.claims] == [Verdict.UNSUPPORTED] * 2 and r.meta.llm_calls == 0


def test_lexical_baseline():
    r = LexicalVerifier().verify(PASSAGES, "A checkpoint runs at 1000 pages by default. A checkpoint runs at 2000 pages by default. Rust is memory safe.")
    assert [c.verdict for c in r.claims] == [Verdict.SUPPORTED, Verdict.CONTRADICTED, Verdict.UNSUPPORTED]


# ------------------------------------------------------------------ HTTP

def client(script):
    return TestClient(create_app(llm_factory=lambda: FakeLLM(script)))


def test_http_ok_and_shape():
    c = client([stage1([C_DIRECT])])
    r = c.post("/verify", json={"context_passages": PASSAGES, "generated_answer": ANSWER})
    assert r.status_code == 200
    claim = r.json()["claims"][0]
    assert set(claim) >= {"claim_text", "verdict", "reasoning", "citations"}
    assert set(claim["citations"][0]) == {"index", "quote", "start_char", "end_char"}
    assert c.get("/health").json()["status"] == "ok"


@pytest.mark.parametrize("body,status,code", [
    ({"context_passages": "x", "generated_answer": "y"}, 422, "invalid_request"),
    ({"generated_answer": "y"}, 422, "invalid_request"),
    ({"context_passages": ["x"] * 65, "generated_answer": "y"}, 413, "too_large"),
    ({"context_passages": ["x" * 200_001], "generated_answer": "y"}, 413, "too_large"),
])
def test_http_input_errors(body, status, code):
    r = client([]).post("/verify", json=body)
    assert r.status_code == status and r.json()["error"]["code"] == code


@pytest.mark.parametrize("exc,status", [(UpstreamError("rate_limited", "429"), 503),
                                        (UpstreamError("timeout", "t"), 504), (UpstreamError("upstream", "500"), 502)])
def test_http_upstream_errors(exc, status):
    r = client([exc]).post("/verify", json={"context_passages": PASSAGES, "generated_answer": ANSWER})
    assert r.status_code == status and r.json()["error"]["code"].startswith("upstream_")


def test_http_unparseable_and_pipeline_param():
    body = {"context_passages": PASSAGES, "generated_answer": ANSWER}
    assert client(["no", "still no"]).post("/verify", json=body).status_code == 502
    r = client([]).post("/verify?pipeline=lexical", json=body)
    assert r.status_code == 200 and r.json()["meta"]["pipeline"] == "lexical"
    assert client([]).post("/verify?pipeline=nope", json=body).status_code == 422
