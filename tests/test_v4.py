"""pivot-v4: what changes relative to pivot-v3, and that v3 is kept exactly as it was evaluated."""
import hashlib
import json

from verifier import prompts
from verifier.llm import FakeLLM
from verifier.pipelines import PivotVerifier
from verifier.text import PassageIndex

P = ["SQLITE_LIMIT_SCHEMA can cap the number of schema objects beginning in version 3.54.0. "
     "The default maximum page count was raised in version 3.45.0."]


def claim(anchor, evidence, kind="direct", sure=True):
    return {"anchor": anchor, "claim_text": anchor, "kind": kind, "sure": sure,
            "evidence": [{"sid": s, "rel": r} for s, r in evidence], "check": None, "reasoning": "r"}


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def test_v3_prompts_are_byte_identical_to_the_evaluated_version():
    # hashes recorded before v4 was written; v3 runs replay the dev / test-1 caches only if these hold
    assert sha(prompts.PIVOT_PROMPTS["pivot-v3"]["system"]) == "f612284daf9ed362"
    assert sha(prompts.PIVOT_PROMPTS["pivot-v3"]["resplit"]) == "8b6feb55d58d2881"
    assert sha(prompts.ESCALATE_SYSTEM) == "4219c8265a963feb"


def test_v4_prompt_covers_advice_and_premise_conclusion():
    v4 = prompts.PIVOT_PROMPTS["pivot-v4"]
    assert "Recommendations, advice and evaluations" in v4["system"] and '"Because X, Y"' in v4["system"]
    assert '"Because X, Y"' in v4["resplit"]
    assert prompts.PIVOT_VERSION == "pivot-v4" and PivotVerifier(FakeLLM([])).prompt_version == "pivot-v4"


def test_number_must_be_in_the_fact_sentence_v4_only():
    # the version 3.45.0 occurs in a cited sentence, but not in the one that states the claimed fact
    c = claim("SQLITE_LIMIT_SCHEMA can cap the number of schema objects since 3.45.0",
              [("P0.S0", "entails"), ("P0.S1", "entails")])
    index = PassageIndex(P)
    assert "number_not_in_evidence" not in PivotVerifier(FakeLLM([]), version="pivot-v3")._escalation_reasons(c, index)
    assert "number_not_in_evidence" in PivotVerifier(FakeLLM([]), version="pivot-v4")._escalation_reasons(c, index)
    ok = claim("The default maximum page count was raised in 3.45.0", [("P0.S0", "entails"), ("P0.S1", "entails")])
    assert "number_not_in_evidence" not in PivotVerifier(FakeLLM([]), version="pivot-v4")._escalation_reasons(ok, index)


def test_premise_and_conclusion_claim_is_compound_in_v4_only():
    text = "Because predicate locks never block, Serializable never raises serialization errors"
    c = claim(text, [("P0.S0", "entails")])
    index = PassageIndex(P)
    assert not PivotVerifier(FakeLLM([]), version="pivot-v3")._is_compound(c, index, text)
    assert PivotVerifier(FakeLLM([]), version="pivot-v4")._is_compound(c, index, text)
    short = claim("It is slow, so avoid it", [("P0.S0", "entails")])  # below CAUSAL_MIN_WORDS
    assert not PivotVerifier(FakeLLM([]), version="pivot-v4")._is_compound(short, index, "It is slow, so avoid it")


def test_versions_send_their_own_prompts():
    answer = "SQLITE_LIMIT_SCHEMA caps schema objects."
    first = json.dumps({"claims": [claim("SQLITE_LIMIT_SCHEMA caps schema objects", [("P0.S0", "entails")])]})
    for v in ("pivot-v3", "pivot-v4"):
        llm = FakeLLM([first])
        r = PivotVerifier(llm, version=v).verify(P, answer)
        assert llm.calls[0]["messages"][0]["content"] == prompts.PIVOT_PROMPTS[v]["system"] and r.meta.prompt_version == v


def test_service_pivot_version_is_configurable(monkeypatch):
    from fastapi.testclient import TestClient
    from verifier.api import create_app
    answer = "SQLITE_LIMIT_SCHEMA caps schema objects."
    first = json.dumps({"claims": [claim("SQLITE_LIMIT_SCHEMA caps schema objects", [("P0.S0", "entails")])]})
    for env, expected in ((None, "pivot-v4"), ("pivot-v3", "pivot-v3")):
        if env:
            monkeypatch.setenv("VERIFIER_PIVOT_VERSION", env)
        client = TestClient(create_app(llm_factory=lambda: FakeLLM([first])))
        assert client.get("/health").json()["pivot_version"] == expected
        r = client.post("/verify", json={"context_passages": P, "generated_answer": answer}).json()
        assert r["meta"]["prompt_version"] == expected
