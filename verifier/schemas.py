"""Public request/response types.

The response deliberately has no field the model can fill with free text that must
match the passages: every citation is produced by `derive.cite()` from a sentence
pointer, so the verbatim invariant holds by construction.
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"


class VerifyRequest(BaseModel):
    context_passages: List[str]
    generated_answer: str


class Citation(BaseModel):
    index: int = Field(ge=0)
    quote: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)


class Claim(BaseModel):
    claim_text: str
    verdict: Verdict
    reasoning: str
    citations: List[Citation]
    answer_span: Optional[List[int]] = None  # [start, end) in generated_answer


class Meta(BaseModel):
    pipeline: str
    prompt_version: Optional[str] = None
    status: str = "ok"  # "ok" | "partial"
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0         # wall clock of this request (cache hits make it small)
    llm_latency_ms: int = 0     # sum of the model calls' original latencies (preserved through the cache)
    cached_llm_calls: int = 0
    escalated_claims: int = 0
    escalation_reasons: Dict[str, int] = Field(default_factory=dict)  # why claims were escalated (a claim can have several)
    resplit_claims: int = 0     # compound claims replaced by their atomic parts
    mixed_evidence: int = 0     # claims still citing both entailing and refuting sentences at the end
    dropped_pointers: int = 0   # model pointed at a sentence that does not exist
    computed_checks: int = 0    # arithmetic / version / date checks evaluated by code
    check_conflicts: int = 0    # check result disagreed with the cited evidence even after escalation; evidence kept
    parse_repairs: List[str] = []
    warnings: List[str] = []


class VerifyResponse(BaseModel):
    claims: List[Claim]
    meta: Meta


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
