"""From pointers to claims: the only place verdicts and citations are made.

    verdict = f(evidence edges, optional computed check)

  * a refuting edge                         -> CONTRADICTED, cite the refuting sentences
  * else an entailing edge                  -> SUPPORTED,    cite the entailing sentences
  * else                                    -> UNSUPPORTED,  cite nothing
  * a computed check overrides the model's edge labels (its mental arithmetic):
    evidence + check False -> CONTRADICTED, evidence + check True -> SUPPORTED.
    The check's tolerance depends on whether the claim is hedged (see compute.run_check).
  * mixed evidence (entails + refutes) still resolves to CONTRADICTED here, but the
    PiVoT pipeline first re-splits or escalates such claims, so this rule is the last resort.

Because citations are sliced from the passage index, and verdicts are a function of
which citations exist, the task invariants cannot be violated by the model.
`assert_invariants` still runs at the exit as a guard against our own bugs.
"""
from typing import Iterable, List, Optional, Tuple

from .compute import run_check
from .schemas import Citation, Claim, Verdict
from .text import PassageIndex

ENTAILS, REFUTES = "entails", "refutes"
_REL_ALIASES = {"entails": ENTAILS, "supports": ENTAILS, "support": ENTAILS, "entail": ENTAILS,
                "refutes": REFUTES, "contradicts": REFUTES, "refute": REFUTES, "contradict": REFUTES}


def cite(index: PassageIndex, sid: str, sub: Optional[str] = None) -> Optional[Citation]:
    """Slice a citation from a sentence pointer. `sub` may narrow it to an exact
    substring of that sentence; if it is not one, the whole sentence is cited."""
    s = index.get(sid)
    if s is None:
        return None
    start, end = s.start, s.end
    if sub and sub.strip():
        i = s.text.find(sub.strip())
        if i >= 0:
            start, end = s.start + i, s.start + i + len(sub.strip())
    return Citation(index=s.passage, quote=index.passages[s.passage][start:end], start_char=start, end_char=end)


def resolve_edges(index: PassageIndex, evidence: Iterable) -> Tuple[List[Tuple[str, Citation]], int]:
    """-> ([(rel, citation)], number of dropped pointers). Dedups identical spans."""
    out, dropped, seen = [], 0, set()
    for e in evidence or []:
        if not isinstance(e, dict):
            dropped += 1
            continue
        rel = _REL_ALIASES.get(str(e.get("rel", "")).lower().strip())
        c = cite(index, e.get("sid", ""), e.get("sub"))
        if c is None or rel is None:
            dropped += 1
            continue
        key = (rel, c.index, c.start_char, c.end_char)
        if key not in seen:
            seen.add(key)
            out.append((rel, c))
    return out, dropped


def derive(edges: List[Tuple[str, Citation]], check: Optional[dict] = None,
           hedged: bool = False) -> Tuple[Verdict, List[Citation], Optional[bool]]:
    checked = run_check(check, hedged) if check else None
    if checked is not None and edges:
        cits = [c for _, c in edges]
        return (Verdict.SUPPORTED if checked else Verdict.CONTRADICTED), cits, checked
    refuting = [c for r, c in edges if r == REFUTES]
    if refuting:
        return Verdict.CONTRADICTED, refuting, checked
    entailing = [c for r, c in edges if r == ENTAILS]
    if entailing:
        return Verdict.SUPPORTED, entailing, checked
    return Verdict.UNSUPPORTED, [], checked


def enforce_free_text(passages: List[str], claim: dict) -> Tuple[Claim, int]:
    """For the minimal baseline, whose model writes quotes itself: keep only citations
    that are exact substrings of an in-range passage, then downgrade if nothing is left.
    Returns (claim, number of dropped citations)."""
    verdict = _verdict(claim.get("verdict"))
    kept, dropped = [], 0
    for c in claim.get("citations") or []:
        try:
            idx, quote = int(c.get("index")), str(c.get("quote") or "")
        except (TypeError, ValueError, AttributeError):
            dropped += 1
            continue
        start = passages[idx].find(quote) if quote and 0 <= idx < len(passages) else -1
        if start < 0:
            dropped += 1
            continue
        kept.append(Citation(index=idx, quote=quote, start_char=start, end_char=start + len(quote)))
    reasoning = str(claim.get("reasoning") or "")
    if verdict is Verdict.UNSUPPORTED:
        kept = []
    elif not kept:
        reasoning = f"[downgraded from {verdict.value}: no valid citation] {reasoning}".strip()
        verdict = Verdict.UNSUPPORTED
    return Claim(claim_text=str(claim.get("claim_text") or ""), verdict=verdict, reasoning=reasoning, citations=kept), dropped


def _verdict(v) -> Verdict:
    try:
        return Verdict(str(v).strip().upper())
    except ValueError:
        return Verdict.UNSUPPORTED


def assert_invariants(passages: List[str], claims: List[Claim]) -> None:
    for i, c in enumerate(claims):
        if c.verdict is Verdict.UNSUPPORTED:
            assert not c.citations, f"claim {i}: UNSUPPORTED with citations"
        else:
            assert c.citations, f"claim {i}: {c.verdict.value} without citations"
        for cit in c.citations:
            assert 0 <= cit.index < len(passages), f"claim {i}: index out of range"
            assert passages[cit.index][cit.start_char:cit.end_char] == cit.quote, f"claim {i}: quote not verbatim"
