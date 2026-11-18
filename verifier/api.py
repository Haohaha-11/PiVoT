"""HTTP layer. Run: uvicorn verifier.api:app

Env: VERIFIER_MODEL (default deepseek-v4.1-flash, the model every benchmark number is for),
VERIFIER_ESCALATE_MODEL, VERIFIER_PIVOT_VERSION (pivot-v4 | pivot-v3, default pivot-v4),
VERIFIER_MINIMAL_THINKING (default | on | off), VERIFIER_PIPELINE
(default pivot), VERIFIER_BASE_URL, VERIFIER_API_KEY / DASHSCOPE_API_KEY,
VERIFIER_CACHE_DIR + VERIFIER_CACHE_MODE (off | record | replay).
"""
import os
from typing import Callable, Dict, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .llm import LLM, OpenAICompatLLM, UpstreamError
from .parsing import ParseError
from .pipelines import Verifier, build
from .prompts import PIVOT_PROMPTS, PIVOT_VERSION
from .schemas import ErrorResponse, VerifyRequest, VerifyResponse

MAX_PASSAGES = 64
MAX_TOTAL_CHARS = 200_000
PIPELINES = ("pivot", "minimal", "lexical")
_UPSTREAM_STATUS = {"rate_limited": 503, "timeout": 504, "upstream": 502, "cache_miss": 502}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(llm_factory: Optional[Callable[[], LLM]] = None, verifier_kw: Optional[Dict[str, dict]] = None) -> FastAPI:
    app = FastAPI(title="Citation Grounding Verifier", version="0.1.0")
    state: Dict[str, Verifier] = {}
    default = os.environ.get("VERIFIER_PIPELINE", "pivot")
    pivot_version = os.environ.get("VERIFIER_PIVOT_VERSION", PIVOT_VERSION)
    if pivot_version not in PIVOT_PROMPTS:
        raise ValueError(f"VERIFIER_PIVOT_VERSION must be one of {sorted(PIVOT_PROMPTS)}, got {pivot_version!r}")

    def get(name: str) -> Verifier:
        if name not in state:
            llm = None
            if name != "lexical":
                llm = llm_factory() if llm_factory else OpenAICompatLLM(
                    model=os.environ.get("VERIFIER_MODEL", "deepseek-v4.1-flash"),
                    cache_dir=os.environ.get("VERIFIER_CACHE_DIR"),
                    cache_mode=os.environ.get("VERIFIER_CACHE_MODE", "off"))
            kw = dict((verifier_kw or {}).get(name, {}))
            if name == "pivot":
                kw.setdefault("version", pivot_version)
            if name == "pivot" and os.environ.get("VERIFIER_ESCALATE_MODEL"):
                kw.setdefault("escalate_model", os.environ["VERIFIER_ESCALATE_MODEL"])
            if name == "minimal" and os.environ.get("VERIFIER_MINIMAL_THINKING", "default") != "default":
                kw.setdefault("thinking", os.environ["VERIFIER_MINIMAL_THINKING"] == "on")
            state[name] = build(name, llm, **kw)
        return state[name]

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        return _error(422, "invalid_request", f"{loc}: {first.get('msg', 'invalid request')}")

    @app.get("/health")
    def health():
        return {"status": "ok", "default_pipeline": default, "pipelines": list(PIPELINES), "pivot_version": pivot_version}

    @app.post("/verify", response_model=VerifyResponse, responses={
        413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse},
        503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}})
    def verify(req: VerifyRequest, pipeline: str = Query(None, description="pivot | minimal | lexical")):
        name = pipeline or default
        if name not in PIPELINES:
            return _error(422, "invalid_request", f"unknown pipeline {name!r}")
        if len(req.context_passages) > MAX_PASSAGES:
            return _error(413, "too_large", f"at most {MAX_PASSAGES} passages")
        if sum(map(len, req.context_passages)) + len(req.generated_answer) > MAX_TOTAL_CHARS:
            return _error(413, "too_large", f"at most {MAX_TOTAL_CHARS} characters in total")
        try:
            return get(name).verify(req.context_passages, req.generated_answer)
        except UpstreamError as e:
            return _error(_UPSTREAM_STATUS.get(e.kind, 502), f"upstream_{e.kind}", str(e)[:300])
        except ParseError as e:
            return _error(502, "upstream_bad_output", f"model output could not be parsed: {e}")

    return app


app = create_app()
