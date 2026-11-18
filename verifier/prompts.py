"""Versioned prompts. A version string is immutable: change the text, bump the version.

pivot-v2 (from v1): every premise of a multi-sentence claim gets its own entails edge;
date checks; stricter one-fact-per-claim wording; a separate re-split prompt.
pivot-v3 (from v2): entails edges must jointly state the WHOLE claim (v2 said "part of", which let
partial support become SUPPORTED).
pivot-v4 (from v3; changes motivated by the test-1 failure analysis, developed on dev only): recommendations,
advice and evaluations are claims (guideline rev 2); a reason and its consequence ("Because X, Y", "X, so Y")
are two claims, in the first pass and in the re-split prompt. The escalation prompt is unchanged.
v3 stays available (PIVOT_PROMPTS["pivot-v3"]) so both versions can be compared on the same data.
"""

MINIMAL_VERSION = "minimal-v1"
MINIMAL_SYSTEM = """You check whether an answer is grounded in the given source passages.
Split the answer into atomic factual claims. For each claim give a verdict:
- SUPPORTED: fully entailed by the passages
- CONTRADICTED: refuted by the passages
- UNSUPPORTED: not stated in the passages (even if true in the real world)
For SUPPORTED and CONTRADICTED claims, cite exact verbatim quotes from the passages together with the passage index. UNSUPPORTED claims have an empty citations list.
Return only JSON of the form:
{"claims": [{"claim_text": "...", "verdict": "SUPPORTED|CONTRADICTED|UNSUPPORTED", "reasoning": "...", "citations": [{"index": 0, "quote": "..."}]}]}"""

_RULES = """Reading rules:
- A claim stronger than the passage (e.g. "typically" -> "always", "can" -> "must") is not entailed by it.
- "X only if Y" does not entail "Y is enough for X". Its contrapositive ("not Y -> not X") is entailed.
- A stated exception to a general rule refutes a claim that ignores the exception.
- If a later passage sentence updates or overrides an earlier one, the later one decides.
- Do not use outside knowledge, even if it is true."""

_CHECKS = """Do not do arithmetic, version or date comparisons in your head. Add a check instead and point at the sentences the numbers come from:
   {"kind": "arith", "expr": "<expression with numbers from the passages>", "op": "==", "value": "<number the claim states>"}
   {"kind": "version", "left": "<version in claim>", "op": ">=", "right": "<version in passage>"}
   {"kind": "date", "from": "YYYY-MM-DD", "to": "YYYY-MM-DD", "unit": "days|months|years", "op": "==", "value": "<number the claim states>"}
   op is one of == != < <= > >=. Use the comparison the claim makes ("more than 15 years" -> ">", "about 10%" -> "==")."""

_EDGES = """Evidence edges {"sid": "P0.S3", "rel": "entails" | "refutes"}:
   entails = the sentence is one of the premises that TOGETHER state the whole claim; if the claim combines facts
             from several sentences (numbers from two places, a rule plus an exception), give an entails edge to EVERY one
             of them. If the passages only partly support the claim (e.g. the claim is stronger than the passage), give NO
             entails edge;
   refutes = the sentence states something incompatible with the claim.
   Give no edge when the passages are silent: the claim is then unsupported.
   Optional "sub": an exact substring of that sentence, to cite only the relevant part."""

_SPLIT_V3 = """1. Split it into atomic factual claims: exactly one checkable fact each. Never join two facts with "and", "which",
   "while", "but" or ";" - make two claims. Resolve pronouns, keep conditions and qualifiers.
   "anchor" = the shortest exact substring of the answer that expresses the claim.
   Skip greetings, restated questions and text with no factual content."""

_SPLIT_V4 = """1. Split it into atomic claims: exactly one checkable statement each. Never join two facts with "and", "which",
   "while", "but" or ";" - make two claims. A reason and its consequence are two claims: "Because X, Y", "X, so Y",
   "X, which means Y" -> one claim for X and one for Y, each judged on its own. Resolve pronouns, keep conditions
   and qualifiers.
   Recommendations, advice and evaluations ("pin dependency versions in production", "this default is conservative") are
   claims too: check whether the passages make them. Skip only greetings, offers of further help and restated questions.
   "anchor" = the shortest exact substring of the answer that expresses the claim."""


def _pivot_system(split: str) -> str:
    return f"""You verify whether an answer is grounded in source passages.
Passages are split into sentences with IDs like [P0.S3]. Never copy passage text: point at sentence IDs.

For the answer:
{split}
2. For each claim give evidence. {_EDGES}
3. {_CHECKS}
4. "kind": "direct" (restatement or paraphrase) | "arith" | "version" | "date" | "logic" (conditions, only-if, exceptions,
   quantifiers, scope, multi-sentence inference). "sure": false when you are not confident.

{_RULES}

Return only JSON, reasoning at most 25 words:
{{"claims": [{{"anchor": "...", "claim_text": "...", "kind": "direct", "sure": true, "evidence": [{{"sid": "P0.S3", "rel": "entails"}}], "check": null, "reasoning": "..."}}]}}"""


ESCALATE_SYSTEM = f"""You verify claims against source passages. The claims were flagged as needing careful reasoning.
Passages are split into sentences with IDs like [P0.S3]. Never copy passage text: point at sentence IDs.

For each claim give evidence. {_EDGES}
{_CHECKS}
Give a reasoning of at most 40 words.

{_RULES}

Return only JSON:
{{"claims": [{{"id": "c1", "evidence": [{{"sid": "P0.S3", "rel": "entails"}}], "check": null, "reasoning": "..."}}]}}"""

_RESPLIT_HEAD_V3 = """Some claims extracted from an answer contain more than one fact. Split each into atomic claims:
exactly one checkable fact each, pronouns resolved, conditions and qualifiers kept, nothing added that the claim does not say."""

_RESPLIT_HEAD_V4 = """Some claims extracted from an answer contain more than one fact. Split each into atomic claims:
exactly one checkable fact each, pronouns resolved, conditions and qualifiers kept, nothing added that the claim does not say.
A reason and its consequence are two parts: "Because X, Y" or "X, so Y" -> one part for X and one for Y."""


def _resplit_system(head: str) -> str:
    return f"""{head}
Passages are split into sentences with IDs like [P0.S3]. Never copy passage text: point at sentence IDs.

For every part give "anchor" (the shortest exact substring of the ANSWER that expresses it), "claim_text", "kind"
("direct" | "arith" | "version" | "date" | "logic"), "sure", evidence and an optional check.
Evidence. {_EDGES}
{_CHECKS}

{_RULES}

If a claim really is a single fact, return it as one part.
Return only JSON, reasoning at most 25 words:
{{"claims": [{{"id": "c3", "parts": [{{"anchor": "...", "claim_text": "...", "kind": "direct", "sure": true, "evidence": [{{"sid": "P0.S3", "rel": "entails"}}], "check": null, "reasoning": "..."}}]}}]}}"""


PIVOT_PROMPTS = {
    "pivot-v3": {"system": _pivot_system(_SPLIT_V3), "resplit": _resplit_system(_RESPLIT_HEAD_V3)},
    "pivot-v4": {"system": _pivot_system(_SPLIT_V4), "resplit": _resplit_system(_RESPLIT_HEAD_V4)},
}
PIVOT_VERSION = "pivot-v4"  # the service default
PIVOT_SYSTEM = PIVOT_PROMPTS[PIVOT_VERSION]["system"]
RESPLIT_SYSTEM = PIVOT_PROMPTS[PIVOT_VERSION]["resplit"]
