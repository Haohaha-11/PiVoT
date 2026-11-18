import random

from verifier.compute import eval_number, run_check
from verifier.derive import assert_invariants, derive, enforce_free_text, resolve_edges
from verifier.parsing import ParseError, parse_object
from verifier.schemas import Verdict
from verifier.text import PassageIndex, locate, split_sentences

P = ["SQLite uses WAL mode when configured. The default page size is 4096 bytes, e.g. on Linux.",
     "Checkpoints run automatically.\n\nThey happen at 1000 pages by default!"]


def test_sentences_have_exact_offsets():
    for text in P:
        for s, e in split_sentences(text):
            assert text[s:e] == text[s:e].strip() and text[s:e]
    assert len(split_sentences(P[0])) == 2  # "e.g." does not split
    assert len(split_sentences(P[1])) == 2
    assert len(split_sentences("The default policy is no. Linux flushes every 30 seconds.")) == 2
    assert len(split_sentences("See item No. 5 for details. Done.")) == 2


def test_index_render_and_sid_variants():
    idx = PassageIndex(P)
    assert "[P1.S1] They happen at 1000 pages by default!" in idx.render()
    for v in ("P1.S1", "p1.s1", "[P1.S1]", "P1 S1"):
        assert idx.get(v).text.startswith("They happen")
    assert idx.get("P9.S0") is None


def test_derive_rules():
    idx = PassageIndex(P)
    edges, dropped = resolve_edges(idx, [{"sid": "P0.S1", "rel": "supports", "sub": "4096 bytes"},
                                         {"sid": "P7.S0", "rel": "entails"}, "junk", {"sid": "P0.S0", "rel": "?"}])
    assert dropped == 3 and len(edges) == 1 and edges[0][1].quote == "4096 bytes"
    assert derive(edges)[0] is Verdict.SUPPORTED
    assert derive([])[:2] == (Verdict.UNSUPPORTED, [])
    both = resolve_edges(idx, [{"sid": "P0.S0", "rel": "entails"}, {"sid": "P1.S1", "rel": "refutes"}])[0]
    v, cits, _ = derive(both)
    assert v is Verdict.CONTRADICTED and [c.index for c in cits] == [1]


def test_check_overrides_model_mental_math():
    idx = PassageIndex(P)
    edges, _ = resolve_edges(idx, [{"sid": "P1.S1", "rel": "entails"}])
    assert derive(edges, {"kind": "arith", "expr": "1000 * 4096", "op": "==", "value": "8MB"})[0] is Verdict.CONTRADICTED
    assert derive(edges, {"kind": "arith", "expr": "1000 * 4096 / 1e6", "op": "==", "value": "4.096"})[0] is Verdict.SUPPORTED
    assert derive([], {"kind": "arith", "expr": "1", "op": "==", "value": "1"})[0] is Verdict.UNSUPPORTED


def test_compute():
    assert eval_number("200M / 2B * 100") == 10
    assert eval_number("4 KB") == 4096 and eval_number("10%") == 10
    assert eval_number("__import__('os')") is None and eval_number("9**999") is None
    assert run_check({"kind": "version", "left": "2.6", "op": ">=", "right": "2.4.1"}) is True
    assert run_check({"kind": "version", "left": "6.0", "op": ">=", "right": "7.0.0"}) is False
    assert run_check({"kind": "arith", "expr": "0.1+0.2", "op": "==", "value": "0.3"}) is True
    assert run_check({"op": "~~"}) is None and run_check("nope") is None


def test_parse_repairs():
    assert parse_object('{"claims": []}') == ({"claims": []}, [])
    assert parse_object('```json\n{"claims": [{"a":1}]}\n```')[1] == ["code_fence"]
    assert parse_object('[{"claims": []}]')[1] == ["unwrap_array"]
    assert parse_object('Sure! {"claims": []} hope it helps')[1] == ["surrounding_text"]
    assert parse_object('[{"x": 1}]') == ({"claims": [{"x": 1}]}, ["bare_list"])
    for bad in ("", "nope", '{"claims": 3}'):
        try:
            parse_object(bad)
            raise AssertionError(bad)
        except ParseError:
            pass


def test_free_text_enforcement_downgrades():
    claim, dropped = enforce_free_text(P, {"claim_text": "x", "verdict": "SUPPORTED",
                                           "citations": [{"index": 0, "quote": "made up"}, {"index": 5, "quote": "a"}]})
    assert dropped == 2 and claim.verdict is Verdict.UNSUPPORTED and claim.citations == []
    claim, _ = enforce_free_text(P, {"verdict": "unsupported", "citations": [{"index": 0, "quote": "SQLite"}]})
    assert claim.citations == []
    claim, _ = enforce_free_text(P, {"verdict": "CONTRADICTED", "citations": [{"index": 1, "quote": "1000 pages"}]})
    assert claim.verdict is Verdict.CONTRADICTED and claim.citations[0].start_char == P[1].find("1000 pages")


def test_invariants_hold_for_random_pointer_garbage():
    """Property: whatever pointers the model emits, derived claims satisfy the invariants."""
    rng = random.Random(0)
    idx = PassageIndex(P)
    sids = [s.sid for s in idx.order] + ["P3.S0", "P0.S9", "", None, 7]
    rels = ["entails", "refutes", "supports", "maybe", None]
    from verifier.schemas import Claim
    for _ in range(500):
        ev = [{"sid": rng.choice(sids), "rel": rng.choice(rels), "sub": rng.choice([None, "page", "zzz", ""])}
              for _ in range(rng.randint(0, 4))]
        check = rng.choice([None, {"expr": "2*2", "op": "==", "value": str(rng.randint(3, 5))}, {"kind": "version"}])
        v, cits, _ = derive(resolve_edges(idx, ev)[0], check)
        assert_invariants(P, [Claim(claim_text="c", verdict=v, reasoning="", citations=cits)])


def test_locate():
    a = "WAL is  the default.\nIt is fast."
    assert locate(a, "WAL is the default") == [0, 19]
    assert locate(a, "missing") is None and locate(a, "") is None
