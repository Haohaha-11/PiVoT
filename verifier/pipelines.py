"""Three verifiers behind one interface: verify(passages, answer) -> VerifyResponse.

  LexicalVerifier   non-LLM baseline (token overlap + number / negation conflicts)
  MinimalVerifier   one call, free-text quotes, exact-match enforcement only
  PivotVerifier   PiVoT: sentence-pointer output + derived verdicts + computed checks + re-split + escalation
"""
import json
import re
import time
from typing import Dict, List, Optional

from . import prompts
from .compute import eval_number, is_hedged, run_check
from .derive import ENTAILS, REFUTES, assert_invariants, derive, enforce_free_text, resolve_edges
from .llm import LLM, Completion
from .parsing import ParseError, parse_object
from .schemas import Citation, Claim, Meta, Verdict, VerifyResponse
from .text import PassageIndex, locate, split_sentences


class Verifier:
    name = "base"
    prompt_version: Optional[str] = None

    def verify(self, passages: List[str], answer: str) -> VerifyResponse:
        t0 = time.time()
        meta = Meta(pipeline=self.name, prompt_version=self.prompt_version)
        if not answer.strip():
            claims: List[Claim] = []
        elif not any(p.strip() for p in passages):
            # Nothing can be supported or contradicted: no model call needed.
            claims = [Claim(claim_text=answer[s:e], verdict=Verdict.UNSUPPORTED, citations=[], answer_span=[s, e],
                            reasoning="No context passages were provided.") for s, e in split_sentences(answer)]
            meta.warnings.append("empty_context")
        else:
            claims = self._run(passages, answer, meta)
        assert_invariants(passages, claims)
        meta.latency_ms = int((time.time() - t0) * 1000)
        return VerifyResponse(claims=claims, meta=meta)

    def _run(self, passages: List[str], answer: str, meta: Meta) -> List[Claim]:
        raise NotImplementedError


def _account(meta: Meta, c: Completion) -> None:
    meta.llm_calls += 1
    meta.prompt_tokens += c.prompt_tokens
    meta.completion_tokens += c.completion_tokens
    meta.llm_latency_ms += c.latency_ms
    meta.cached_llm_calls += int(c.cached)


def _call_json(llm: LLM, messages: List[dict], meta: Meta, *, retries: int, thinking=None, model=None, list_key="claims"):
    """Call, parse; on a parse failure re-ask with the error as feedback."""
    for attempt in range(retries + 1):
        c = llm.complete(messages, thinking=thinking, model=model)
        _account(meta, c)
        try:
            obj, repairs = parse_object(c.text, list_key)
            meta.parse_repairs.extend(repairs)
            return obj
        except ParseError as e:
            if attempt == retries:
                raise
            meta.parse_repairs.append("reask")
            messages = messages + [{"role": "assistant", "content": c.text[:4000]},
                                   {"role": "user", "content": f"That was not valid: {e}. Return only the JSON object."}]


# --------------------------------------------------------------------------- lexical

_WORD = re.compile(r"[a-z0-9]+(?:[.'][a-z0-9]+)*")
_NUM = re.compile(r"\d+(?:\.\d+)*")
_NEG = re.compile(r"\b(?:not|no|never|cannot|can't|doesn't|isn't|aren't|won't|without|none)\b", re.I)
_STOP = set("a an the of to in on for and or is are was were be by with as at it its this that these those from "
            "can will which when if than then into also has have had do does".split())


def _toks(s: str) -> set:
    return {t for t in _WORD.findall(s.lower()) if t not in _STOP}


class LexicalVerifier(Verifier):
    name = "lexical"

    def __init__(self, support_threshold: float = 0.6, topic_threshold: float = 0.4):
        self.support_threshold, self.topic_threshold = support_threshold, topic_threshold

    def _run(self, passages, answer, meta):
        index = PassageIndex(passages)
        claims = []
        for s, e in split_sentences(answer):
            text = answer[s:e]
            ct = _toks(text)
            best, score = None, 0.0
            for sent in index.order:
                sc = len(ct & _toks(sent.text)) / max(len(ct), 1)
                if sc > score:
                    best, score = sent, sc
            verdict, why = Verdict.UNSUPPORTED, f"Best lexical overlap {score:.2f} below threshold."
            if best is not None and score >= self.topic_threshold:
                cn, pn = set(_NUM.findall(text)), set(_NUM.findall(best.text))
                if cn and pn and not cn <= pn:
                    verdict, why = Verdict.CONTRADICTED, f"Numbers {sorted(cn - pn)} differ from the best-matching sentence."
                elif bool(_NEG.search(text)) != bool(_NEG.search(best.text)):
                    verdict, why = Verdict.CONTRADICTED, "Negation differs from the best-matching sentence."
                elif score >= self.support_threshold:
                    verdict, why = Verdict.SUPPORTED, f"Lexical overlap {score:.2f} with {best.sid}."
            cits = [] if verdict is Verdict.UNSUPPORTED else [
                Citation(index=best.passage, quote=best.text, start_char=best.start, end_char=best.end)]
            claims.append(Claim(claim_text=text, verdict=verdict, reasoning=why, citations=cits, answer_span=[s, e]))
        return claims


# --------------------------------------------------------------------------- minimal

class MinimalVerifier(Verifier):
    name = "minimal"
    prompt_version = prompts.MINIMAL_VERSION

    def __init__(self, llm: LLM, model: Optional[str] = None, thinking: Optional[bool] = None):
        """thinking: None = provider default, True / False = force on / off."""
        self.llm, self.model, self.thinking = llm, model, thinking

    def _run(self, passages, answer, meta):
        ctx = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages))
        messages = [{"role": "system", "content": prompts.MINIMAL_SYSTEM},
                    {"role": "user", "content": f"Passages:\n{ctx}\n\nAnswer:\n{answer}"}]
        obj = _call_json(self.llm, messages, meta, retries=0, model=self.model, thinking=self.thinking)
        claims = []
        for raw in obj["claims"]:
            if not isinstance(raw, dict):
                continue
            claim, dropped = enforce_free_text(passages, raw)
            meta.dropped_pointers += dropped
            claim.answer_span = locate(answer, claim.claim_text)
            claims.append(claim)
        return claims


# --------------------------------------------------------------------------- PiVoT

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_STRONG = re.compile(r"\b(?:only|always|never|must|every|all|any|unless|except|guarantee[sd]?|cannot|can't|required|"
                     r"requires|enough|sufficient|whenever|regardless|no longer|at most|at least)\b", re.I)
_CONNECTOR = re.compile(r";|,\s+(?:and|but|which|whereas|while|so)\s", re.I)
_CAUSAL = re.compile(r"\b(?:because|therefore|hence|thus)\b|,\s*so\s|\bwhich (?:is why|means)\b", re.I)  # v4
RELATED_OVERLAP = 0.5      # an unsupported claim this close to some passage sentence gets a second look
COMPOUND_MIN_WORDS = 15    # a clause connector only makes a claim compound when the claim is this long
CAUSAL_MIN_WORDS = 8       # v4: a premise + conclusion claim is compound from this length on


def _numbers(s: str) -> set:
    return {re.sub(r"(?<=\d),(?=\d)", "", n).rstrip(".") for n in _NUMBER.findall(s)}


def _strong(s: str) -> set:
    return {w.lower() for w in _STRONG.findall(s)}


def _content_toks(s: str) -> set:
    return {t for t in _toks(s) if not t[0].isdigit()}


def _fact_sentence(text: str, sentences: list):
    """v4: the cited sentence that states the claim's fact = most content-word overlap with the claim (numbers
    excluded, so that a number appearing elsewhere cannot pick the sentence); ties go to the first cited."""
    ct = _content_toks(text)
    return max(sentences, key=lambda s: len(ct & _content_toks(s.text)), default=None)


def _claim_hedged(c: dict) -> bool:
    return is_hedged(f"{c.get('claim_text') or ''} {c.get('anchor') or ''}")


def _check_conflict(c: dict, index: PassageIndex) -> bool:
    """The model's own check and its evidence point opposite ways (check holds but only refuting
    edges, or check fails but only entailing edges)."""
    check = c.get("check")
    if not isinstance(check, dict):
        return False
    edges, _ = resolve_edges(index, c.get("evidence"))
    rels = {r for r, _ in edges}
    result = run_check(check, _claim_hedged(c))
    return (result is True and rels == {REFUTES}) or (result is False and rels == {ENTAILS})


def _check_note(c: dict) -> str:
    """Show the model what its check actually evaluates to, so it can fix a mis-stated comparison."""
    check = c.get("check")
    if not isinstance(check, dict):
        return ""
    result = run_check(check, _claim_hedged(c))
    if result is None:
        return ""
    if check.get("kind", "arith") == "arith":
        left, right = eval_number(check.get("expr", "")), eval_number(check.get("value", ""))
        detail = f"{check.get('expr')} = {left:g}, claim value {check.get('value')} = {right:g}" if left is not None and right is not None else ""
    else:
        detail = json.dumps(check, ensure_ascii=False)
    return f"  (code evaluated your earlier check: {detail}; the comparison {check.get('op', '==')} {'holds' if result else 'fails'})"


class PivotVerifier(Verifier):
    """Stages: (1) one non-thinking call splits the answer and points at evidence; (2) compound
    claims are re-split; (3) claims that trip a deterministic trigger, or that the model itself
    flags, are escalated (thinking by default); (4) code derives verdicts and citations.

    escalate: "never" | "self" (only claims the model flags itself) | "auto" (self-flag + deterministic
    triggers) | "always".   resplit: re-split compound claims (stage 2).   use_checks: let computed
    arithmetic / version / date checks decide (ablation switch).
    version: "pivot-v4" (default) or "pivot-v3". v4 changes the first-pass and re-split prompts, treats
    "because / so / therefore" claims as compound, and requires a claim's numbers to occur in its fact
    sentence (v3: in any cited sentence) before it skips escalation.
    """
    name = "pivot"

    def __init__(self, llm: LLM, model: Optional[str] = None, escalate: str = "auto",
                 escalate_model: Optional[str] = None, escalate_thinking: Optional[bool] = True,
                 parse_retries: int = 1, resplit: bool = True, use_checks: bool = True,
                 version: str = prompts.PIVOT_VERSION):
        if version not in prompts.PIVOT_PROMPTS:
            raise ValueError(f"unknown PiVoT version {version!r}")
        self.prompt_version, self.v4 = version, version != "pivot-v3"
        self.system_prompt = prompts.PIVOT_PROMPTS[version]["system"]
        self.resplit_prompt = prompts.PIVOT_PROMPTS[version]["resplit"]
        self.llm, self.model = llm, model
        self.use_checks = use_checks
        self.escalate, self.escalate_model, self.escalate_thinking = escalate, escalate_model, escalate_thinking
        self.parse_retries, self.resplit = parse_retries, resplit

    def _run(self, passages, answer, meta):
        index = PassageIndex(passages)
        ctx = index.render()
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Passages:\n{ctx}\n\nAnswer:\n{answer}"}]
        obj = _call_json(self.llm, messages, meta, retries=self.parse_retries, thinking=False, model=self.model)
        raw = [c for c in obj["claims"] if isinstance(c, dict)]

        if self.resplit:
            compound = [i for i, c in enumerate(raw) if self._is_compound(c, index, answer)]
            if compound:
                try:
                    raw = self._resplit(ctx, raw, compound, meta)
                except Exception as e:  # keep the compound claims rather than fail the request
                    meta.status = "partial"
                    meta.warnings.append(f"resplit_failed: {type(e).__name__}: {str(e)[:120]}")

        hard = []
        for i, c in enumerate(raw):
            reasons = self._escalation_reasons(c, index)
            for r in reasons:
                meta.escalation_reasons[r] = meta.escalation_reasons.get(r, 0) + 1
            if reasons:
                hard.append(i)
        escalated_ok: set = set()
        if hard:
            try:
                escalated_ok = self._escalate(ctx, raw, hard, meta)
            except Exception as e:  # keep first-pass judgements rather than fail the request
                meta.status = "partial"
                meta.warnings.append(f"escalation_failed: {type(e).__name__}: {str(e)[:120]}")

        claims = []
        for i, c in enumerate(raw):
            edges, dropped = resolve_edges(index, c.get("evidence"))
            meta.dropped_pointers += dropped
            if {r for r, _ in edges} == {ENTAILS, REFUTES}:
                meta.mixed_evidence += 1
            text = str(c.get("claim_text") or c.get("anchor") or "")
            anchor = str(c.get("anchor") or "")
            check = c.get("check") if self.use_checks else None
            reasoning = str(c.get("reasoning") or "")
            if check is not None and i in escalated_ok and _check_conflict(c, index):
                # The model saw what its check evaluates to and still points the other way: the check most
                # likely encodes the wrong comparison, so the evidence decides. Without that second look
                # (not escalated) the check keeps overriding the model's mental arithmetic.
                meta.check_conflicts += 1
                check = None
                reasoning = f"{reasoning} [check conflicted with cited evidence; evidence kept]".strip()
            verdict, cits, checked = derive(edges, check, hedged=is_hedged(f"{text} {anchor}"))
            if checked is not None:
                meta.computed_checks += 1
                reasoning = f"{reasoning} [computed check: {'holds' if checked else 'fails'}]".strip()
            claims.append(Claim(claim_text=text, verdict=verdict, reasoning=reasoning, citations=cits,
                                answer_span=locate(answer, anchor) or locate(answer, text)))
        return claims

    # ------------------------------------------------------------------ stage 2: compound claims

    def _is_compound(self, c: dict, index: PassageIndex, answer: str) -> bool:
        text = str(c.get("claim_text") or c.get("anchor") or "")
        if len(text.split()) >= COMPOUND_MIN_WORDS and _CONNECTOR.search(text):
            return True
        if self.v4 and len(text.split()) >= CAUSAL_MIN_WORDS and _CAUSAL.search(text):
            return True  # premise and conclusion in one claim
        span = locate(answer, str(c.get("anchor") or ""))
        if span and any(span[0] < e and span[1] > s2 for (_, e), (s2, _) in zip(split_sentences(answer), split_sentences(answer)[1:])):
            return True  # the anchor runs across a sentence boundary
        edges, _ = resolve_edges(index, c.get("evidence"))
        return {r for r, _ in edges} == {ENTAILS, REFUTES}  # one part supported, another refuted

    def _resplit(self, ctx: str, raw: List[dict], compound: List[int], meta: Meta) -> List[dict]:
        listing = "\n".join(f"[c{i}] {raw[i].get('claim_text') or raw[i].get('anchor')} (anchor: {raw[i].get('anchor')})"
                             for i in compound)
        messages = [{"role": "system", "content": self.resplit_prompt},
                    {"role": "user", "content": f"Passages:\n{ctx}\n\nClaims:\n{listing}"}]
        obj = _call_json(self.llm, messages, meta, retries=self.parse_retries, thinking=False, model=self.model)
        parts: Dict[int, List[dict]] = {}
        for r in obj["claims"]:
            m = re.fullmatch(r"c?(\d+)", str(r.get("id", "")).strip()) if isinstance(r, dict) else None
            i = int(m.group(1)) if m else -1
            ps = [p for p in (r.get("parts") or []) if isinstance(p, dict) and (p.get("claim_text") or p.get("anchor"))]
            if i in compound and len(ps) >= 2:
                parts[i] = ps
        meta.resplit_claims += len(parts)
        out: List[dict] = []
        for i, c in enumerate(raw):
            out.extend(parts.get(i, [c]))
        return out

    # ------------------------------------------------------------------ stage 3: escalation

    def _escalation_reasons(self, c: dict, index: PassageIndex) -> List[str]:
        if self.escalate == "always":
            return ["forced"]
        if self.escalate == "never":
            return []
        reasons = []
        if str(c.get("kind", "direct")).lower() != "direct" or c.get("sure") is False:
            reasons.append("self_flag")
        if self.escalate == "self":
            return reasons
        edges, _ = resolve_edges(index, c.get("evidence"))
        rels = {r for r, _ in edges}
        text = f"{c.get('claim_text') or ''} {c.get('anchor') or ''}"
        if rels == {ENTAILS, REFUTES}:
            reasons.append("mixed_evidence")
        if _check_conflict(c, index):
            reasons.append("check_conflict")
        if edges:
            sents = [s for s in (index.get(e.get("sid", "")) for e in c.get("evidence") or [] if isinstance(e, dict)) if s is not None]
            cited = " ".join(s.text for s in sents)
            if self.v4:
                fact = _fact_sentence(text, sents)
                if _numbers(text) - _numbers(fact.text if fact else ""):
                    reasons.append("number_not_in_evidence")  # v4: not in the sentence that states the fact
            elif _numbers(text) - _numbers(cited):
                reasons.append("number_not_in_evidence")  # derived number, version range, unit conversion...
            if _strong(text) - _strong(cited):
                reasons.append("strong_wording")          # only / always / never / must ... not in the source
        else:
            ct = _toks(text)
            best = max((len(ct & _toks(s.text)) / max(len(ct), 1) for s in index.order), default=0.0)
            if best >= RELATED_OVERLAP:
                reasons.append("unsupported_but_related")  # silent evidence, yet clearly on topic
        return reasons

    def _escalate(self, ctx: str, raw: List[dict], hard: List[int], meta: Meta) -> set:
        """Re-judge the hard claims in one call; returns the indices actually updated."""
        listing = "\n".join(f"[c{i}] {raw[i].get('claim_text') or raw[i].get('anchor')}{_check_note(raw[i])}" for i in hard)
        messages = [{"role": "system", "content": prompts.ESCALATE_SYSTEM},
                    {"role": "user", "content": f"Passages:\n{ctx}\n\nClaims:\n{listing}"}]
        obj = _call_json(self.llm, messages, meta, retries=self.parse_retries,
                         thinking=self.escalate_thinking, model=self.escalate_model or self.model)
        meta.escalated_claims += len(hard)
        updated = set()
        for r in obj["claims"]:
            m = re.fullmatch(r"c?(\d+)", str(r.get("id", "")).strip()) if isinstance(r, dict) else None
            i = int(m.group(1)) if m else -1
            if i in hard:
                raw[i].update({k: r[k] for k in ("evidence", "check", "reasoning") if k in r})
                updated.add(i)
        return updated


def build(name: str, llm: Optional[LLM] = None, **kw) -> Verifier:
    if name == "lexical":
        return LexicalVerifier()
    if llm is None:
        raise ValueError(f"pipeline {name!r} needs an LLM")
    if name == "minimal":
        return MinimalVerifier(llm, **kw)
    if name == "pivot":
        return PivotVerifier(llm, **kw)
    raise ValueError(f"unknown pipeline {name!r}")
