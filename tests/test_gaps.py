"""Tests for the four design gaps found in the pilot:
1. escalation must not rely only on the model's self-report,
2. arithmetic checks: tolerance follows the claim's hedging, KB/MB ambiguity, dates,
3. compound claims are re-split,
4. mixed evidence is re-split / escalated instead of silently becoming CONTRADICTED.
"""
import json

from verifier.compute import is_hedged, run_check
from verifier.llm import FakeLLM, UpstreamError
from verifier.pipelines import MinimalVerifier, PivotVerifier
from verifier.schemas import Verdict

P = ["Since Redis 2.4 it can trigger log rewriting automatically. Redis 2.2 users must run BGREWRITEAOF themselves.",
     "With appendfsync always, Redis is very slow but very safe. The default policy is to fsync every second."]


def out(claims):
    return json.dumps({"claims": claims})


def claim(anchor, text=None, evidence=(), kind="direct", sure=True, check=None):
    return {"anchor": anchor, "claim_text": text or anchor, "kind": kind, "sure": sure,
            "evidence": [{"sid": s, "rel": r} for s, r in evidence], "check": check, "reasoning": "r"}


# ------------------------------------------------------------------ gap 2: computed checks

def test_tolerance_follows_hedging_not_the_model():
    c = {"kind": "arith", "expr": "190 / 2000 * 100", "op": "==", "value": "10"}  # 9.5 vs 10
    assert run_check(c) is False and run_check(c, hedged=True) is True
    assert run_check({"expr": "4096", "op": "==", "value": "8192", "tolerance": 0.9}) is False  # model tolerance ignored
    assert is_hedged("about 10%") and is_hedged("roughly 4 MB") and is_hedged("~4MB") and not is_hedged("10%")


def test_byte_units_accept_either_convention():
    assert run_check({"expr": "1000 * 4KB", "op": "==", "value": "4MB"}) is True       # 4,096,000 vs 4,000,000 / 4,194,304
    assert run_check({"expr": "1000 * 4KB", "op": "==", "value": "8MB"}) is False
    assert run_check({"expr": "32KiB / 4MB * 100", "op": "<", "value": "1"}) is True   # holds under both conventions
    assert run_check({"expr": "1000KB", "op": ">", "value": "1000000"}) is None        # depends on the convention


def test_date_checks():
    days = {"kind": "date", "from": "2026-03-03", "to": "2026-03-13", "unit": "days", "op": "==", "value": "10"}
    assert run_check(days) is True and run_check(dict(days, value="30")) is False
    years = {"kind": "date", "from": "2010-07-21", "to": "2026-03-03", "unit": "years", "op": ">", "value": "15"}
    assert run_check(years) is True and run_check(dict(years, op="==", value="20")) is False
    assert run_check(dict(days, to="March 13")) is None and run_check(dict(days, unit="fortnights")) is None


# ------------------------------------------------------------------ gap 1: deterministic escalation

def test_confident_direct_claim_with_unstated_version_is_escalated():
    c = claim("Redis 2.6 can trigger log rewriting automatically", evidence=[("P0.S0", "entails")])
    esc = out([{"id": "c0", "evidence": [{"sid": "P0.S0", "rel": "entails"}],
                "check": {"kind": "version", "left": "2.6", "op": ">=", "right": "2.4"}, "reasoning": "2.6 >= 2.4"}])
    llm = FakeLLM([out([c]), esc])
    r = PivotVerifier(llm).verify(P, "Redis 2.6 can trigger log rewriting automatically.")
    assert r.meta.escalation_reasons == {"number_not_in_evidence": 1} and r.meta.escalated_claims == 1
    assert r.claims[0].verdict is Verdict.SUPPORTED and r.meta.computed_checks == 1
    assert llm.calls[1]["thinking"] is True


def test_strong_wording_and_silent_but_related_claims_are_escalated():
    always = claim("Redis always rewrites the log automatically", evidence=[("P0.S0", "entails")])
    silent = claim("Redis can trigger log rewriting automatically since 2.6")
    esc = out([{"id": "c0", "evidence": [], "reasoning": "'always' is stronger than the passage"},
               {"id": "c1", "evidence": [{"sid": "P0.S0", "rel": "entails"}],
                "check": {"kind": "version", "left": "2.6", "op": ">=", "right": "2.4"}, "reasoning": "range"}])
    answer = "Redis always rewrites the log automatically. Redis can trigger log rewriting automatically since 2.6."
    r = PivotVerifier(FakeLLM([out([always, silent]), esc])).verify(P, answer)
    assert r.meta.escalation_reasons == {"strong_wording": 1, "unsupported_but_related": 1}
    assert [c.verdict for c in r.claims] == [Verdict.UNSUPPORTED, Verdict.SUPPORTED]


def test_plain_restatement_is_not_escalated():
    c = claim("Since Redis 2.4 it can trigger log rewriting automatically", evidence=[("P0.S0", "entails")])
    extrinsic = claim("Redis is written in C")  # unrelated to every passage sentence
    llm = FakeLLM([out([c, extrinsic])])
    r = PivotVerifier(llm).verify(P, "Since Redis 2.4 it can trigger log rewriting automatically. Redis is written in C.")
    assert r.meta.llm_calls == 1 and r.meta.escalation_reasons == {}
    assert [x.verdict for x in r.claims] == [Verdict.SUPPORTED, Verdict.UNSUPPORTED]


# ------------------------------------------------------------------ gap 3: compound claims

ANS = "With appendfsync always, Redis calls fsync for every write, which is very safe but very slow."


def test_compound_claim_is_resplit_and_parts_are_judged_separately():
    compound = claim(ANS[:-1], evidence=[("P1.S0", "entails")])
    parts = out([{"id": "c0", "parts": [
        claim("Redis calls fsync for every write", "With appendfsync always, Redis calls fsync for every write.",
              evidence=[("P1.S0", "entails")]),
        claim("very safe but very slow", "appendfsync always is very safe but very slow.", evidence=[("P1.S0", "entails")])]}])
    llm = FakeLLM([out([compound]), parts])
    r = PivotVerifier(llm).verify(P, ANS)
    assert r.meta.resplit_claims == 1 and len(r.claims) == 2 and r.meta.llm_calls == 2
    assert r.claims[1].answer_span == [ANS.find("very safe"), ANS.find("very safe") + len("very safe but very slow")]
    assert llm.calls[1]["thinking"] is False


def test_anchor_across_sentences_is_compound_and_resplit_failure_is_partial():
    answer = "The default policy is no. Linux flushes every 30 seconds."
    c = claim(answer, evidence=[("P1.S1", "refutes")])
    r = PivotVerifier(FakeLLM([out([c]), UpstreamError("timeout", "slow")]), escalate="never").verify(P, answer)
    assert r.meta.status == "partial" and r.meta.warnings[0].startswith("resplit_failed")
    assert len(r.claims) == 1 and r.claims[0].verdict is Verdict.CONTRADICTED


# ------------------------------------------------------------------ gap 4: mixed evidence

def test_mixed_evidence_goes_to_resplit_first():
    mixed = claim("Redis 2.2 can rewrite the log automatically", evidence=[("P0.S0", "entails"), ("P0.S1", "refutes")])
    one_part = out([{"id": "c0", "parts": [mixed]}])  # model says it is a single fact
    esc = out([{"id": "c0", "evidence": [{"sid": "P0.S1", "rel": "refutes"}], "reasoning": "2.2 needs manual BGREWRITEAOF"}])
    llm = FakeLLM([out([mixed]), one_part, esc])
    r = PivotVerifier(llm).verify(P, "Redis 2.2 can rewrite the log automatically.")
    assert r.meta.resplit_claims == 0 and r.meta.escalation_reasons.get("mixed_evidence") == 1
    assert r.claims[0].verdict is Verdict.CONTRADICTED and r.meta.mixed_evidence == 0  # resolved by escalation
    assert [c.quote for c in r.claims[0].citations] == [P[0].split(". ")[1]]


def test_minimal_thinking_switch():
    ok = json.dumps({"claims": []})
    for setting in (None, False, True):
        llm = FakeLLM([ok])
        MinimalVerifier(llm, thinking=setting).verify(P, "Something.")
        assert llm.calls[0]["thinking"] is setting


# ------------------------------------------------------------------ found by the first benchmark run

PG = ["The effective maximum for vacuum_freeze_table_age is 0.95 * autovacuum_freeze_max_age. The default is 200 million."]


def test_check_conflict_is_escalated_with_the_computed_value_and_evidence_wins():
    """Model refutes ('cap is 190M, not 180M') but writes a check that holds: the check must not overrule it."""
    bad_check = {"kind": "arith", "expr": "0.95 * 200M", "op": ">=", "value": "180M"}
    c = claim("vacuum_freeze_table_age can be at most 180 million", evidence=[("P0.S0", "refutes"), ("P0.S1", "refutes")],
              kind="arith", check=bad_check)
    esc = out([{"id": "c0", "evidence": [{"sid": "P0.S0", "rel": "refutes"}, {"sid": "P0.S1", "rel": "refutes"}],
                "check": bad_check, "reasoning": "cap is 190M"}])
    llm = FakeLLM([out([c]), esc])
    r = PivotVerifier(llm).verify(PG, "With the default, vacuum_freeze_table_age can be at most 180 million.")
    assert "check_conflict" in r.meta.escalation_reasons
    assert "= 1.9e+08" in llm.calls[1]["messages"][1]["content"]  # the model is shown what its check evaluates to
    assert r.claims[0].verdict is Verdict.CONTRADICTED and r.meta.check_conflicts == 1


def test_after_escalation_persistent_conflict_keeps_evidence():
    good = {"kind": "arith", "expr": "0.95 * 200M", "op": "==", "value": "180M"}
    c = claim("vacuum_freeze_table_age can be at most 180 million", evidence=[("P0.S0", "entails"), ("P0.S1", "entails")],
              kind="arith", check=good)  # model thought it was entailed; check fails -> conflict -> escalate
    esc = out([{"id": "c0", "evidence": [{"sid": "P0.S0", "rel": "entails"}, {"sid": "P0.S1", "rel": "entails"}],
                "check": {"kind": "arith", "expr": "0.95 * 200M", "op": "==", "value": "180M"}, "reasoning": "x"}])
    r = PivotVerifier(FakeLLM([out([c]), esc])).verify(PG, "vacuum_freeze_table_age can be at most 180 million.")
    assert r.claims[0].verdict is Verdict.SUPPORTED and r.meta.check_conflicts == 1  # evidence kept: documented trade-off


def test_prompt_requires_entails_edges_to_cover_the_whole_claim():
    from verifier import prompts
    for text in (prompts.PIVOT_SYSTEM, prompts.ESCALATE_SYSTEM, prompts.RESPLIT_SYSTEM):
        assert "(part of)" not in text and "TOGETHER state the whole claim" in text and "give NO" in text


def test_without_escalation_the_check_overrides_mental_math():
    c = claim("vacuum_freeze_table_age can be at most 180 million", evidence=[("P0.S0", "entails"), ("P0.S1", "entails")],
              kind="arith", check={"kind": "arith", "expr": "0.95 * 200M", "op": "==", "value": "180M"})
    r = PivotVerifier(FakeLLM([out([c])]), escalate="never").verify(PG, "vacuum_freeze_table_age can be at most 180 million.")
    assert r.claims[0].verdict is Verdict.CONTRADICTED and r.meta.check_conflicts == 0


def test_ablation_switches():
    c = claim("Redis 2.6 can trigger log rewriting automatically", evidence=[("P0.S0", "entails")])
    r = PivotVerifier(FakeLLM([out([c])]), escalate="self").verify(P, "Redis 2.6 can trigger log rewriting automatically.")
    assert r.meta.llm_calls == 1 and r.meta.escalation_reasons == {}  # deterministic trigger switched off
    wrong = claim("vacuum_freeze_table_age can be at most 180 million", evidence=[("P0.S0", "entails"), ("P0.S1", "entails")],
                  kind="arith", check={"kind": "arith", "expr": "0.95 * 200M", "op": "==", "value": "180M"})
    r = PivotVerifier(FakeLLM([out([wrong])]), escalate="never", use_checks=False).verify(PG, "vacuum_freeze_table_age can be at most 180 million.")
    assert r.claims[0].verdict is Verdict.SUPPORTED and r.meta.computed_checks == 0  # mental math kept
