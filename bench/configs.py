"""Named benchmark configurations. Every config is the same `verifier` code the HTTP service runs.

The first four are the three approaches the assignment asks for (minimal in two thinking
settings); the rest are single-change ablations of the optimized pipeline.

"pivot" (PiVoT) is the optimized pipeline as developed on dev and evaluated on test-1: pivot-v3 prompts and
triggers. "pivot-v3" is the same configuration under an explicit name (identical requests, so it replays the
same cache), and "pivot-v4" is the next version, developed on dev after the test-1 failure analysis. The
ablations are single changes to pivot-v3.
"""
from typing import Callable, Dict, Optional

from verifier.llm import LLM
from verifier.pipelines import LexicalVerifier, MinimalVerifier, PivotVerifier, Verifier

V3 = "pivot-v3"

CONFIGS: Dict[str, tuple] = {
    # name: (description, factory)
    "lexical": ("non-LLM baseline: sentence split + lexical overlap + number/negation conflicts",
                lambda llm: LexicalVerifier()),
    "minimal": ("one call, minimal prompt, provider-default thinking, model-written quotes",
                lambda llm: MinimalVerifier(llm)),
    "minimal-nothink": ("as minimal, thinking forced off",
                        lambda llm: MinimalVerifier(llm, thinking=False)),
    "pivot": ("optimized (PiVoT): sentence-pointer citations, derived verdicts, computed checks, re-split, escalation with thinking (pivot-v3)",
                lambda llm: PivotVerifier(llm, version=V3)),
    "pivot-v3": ("same as pivot, explicit version name", lambda llm: PivotVerifier(llm, version=V3)),
    "pivot-v4": ("pivot-v4: advice/evaluations are claims, premise and conclusion split, number trigger uses the fact sentence",
                   lambda llm: PivotVerifier(llm, version="pivot-v4")),
    # ablations of pivot-v3 (one change each)
    "pivot-noescalate": ("pivot without stage 3 (no escalation)", lambda llm: PivotVerifier(llm, version=V3, escalate="never")),
    "pivot-noresplit": ("pivot without stage 2 (no re-split)", lambda llm: PivotVerifier(llm, version=V3, resplit=False)),
    "pivot-escalate-nothink": ("pivot, escalation call without thinking",
                                 lambda llm: PivotVerifier(llm, version=V3, escalate_thinking=False)),
    "pivot-escalate-all": ("pivot, every claim escalated", lambda llm: PivotVerifier(llm, version=V3, escalate="always")),
    "pivot-selfflag-only": ("pivot, escalation only for claims the model flags itself (no deterministic triggers)",
                              lambda llm: PivotVerifier(llm, version=V3, escalate="self")),
    "pivot-nochecks": ("pivot, computed arithmetic/version/date checks ignored",
                         lambda llm: PivotVerifier(llm, version=V3, use_checks=False)),
}

MAIN = ["lexical", "minimal", "minimal-nothink", "pivot"]


def make(name: str, llm: Optional[LLM]) -> Verifier:
    if name not in CONFIGS:
        raise SystemExit(f"unknown config {name!r}; choose from {', '.join(CONFIGS)}")
    factory: Callable = CONFIGS[name][1]
    return factory(llm)
