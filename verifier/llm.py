"""OpenAI-compatible chat client with bounded concurrency, retries and record/replay.

Record/replay: responses are stored under VERIFIER_CACHE_DIR keyed by the sha256 of
the request body (model + messages + params). mode "record" reads a hit or calls and
stores; "replay" never calls the network (a miss is an error). Re-scoring is free and
reproducible.
"""
import hashlib
import json
import os
import pathlib
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional, Union


class UpstreamError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind  # "rate_limited" | "timeout" | "upstream" | "cache_miss"


@dataclass
class Completion:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cached: bool = False


class LLM:
    def complete(self, messages: List[dict], *, model: Optional[str] = None, thinking: Optional[bool] = None) -> Completion:
        raise NotImplementedError


class OpenAICompatLLM(LLM):
    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 max_concurrency: int = 4, timeout_s: float = 120, max_retries: int = 3,
                 cache_dir: Optional[str] = None, cache_mode: str = "off", json_mode: bool = True):
        self.model = model
        self.json_mode = json_mode
        self.base_url = (base_url or os.environ.get("VERIFIER_BASE_URL")
                         or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("VERIFIER_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", "")
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self.timeout_s, self.max_retries = timeout_s, max_retries
        self.cache_mode = cache_mode
        self.cache_dir = pathlib.Path(cache_dir) if cache_dir else None

    def _body(self, messages, model, thinking) -> dict:
        model = model or self.model
        body = {"model": model, "messages": messages, "temperature": 0}
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}
        if thinking is None and model.startswith("qwen"):
            thinking = False
        if thinking is not None:
            body["enable_thinking"] = thinking
        if thinking:  # DashScope returns thinking models' output only when streaming
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}
        return body

    def complete(self, messages, *, model=None, thinking=None) -> Completion:
        body = self._body(messages, model, thinking)
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if path and self.cache_mode in ("record", "replay") and path.exists():
            c = Completion(**json.loads(path.read_text(encoding="utf-8")))
            c.cached = True
            return c
        if self.cache_mode == "replay":
            raise UpstreamError("cache_miss", f"no recorded response for {key[:12]}")
        c = self._call_with_retry(body)
        if path and self.cache_mode == "record":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(c.__dict__, ensure_ascii=False), encoding="utf-8")
        return c

    def _call_with_retry(self, body: dict) -> Completion:
        last: Optional[UpstreamError] = None
        for attempt in range(self.max_retries + 1):
            try:
                with self._sem:
                    return self._call(body)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code == 400 and "response_format" in detail and "response_format" in body:
                    body = {k: v for k, v in body.items() if k != "response_format"}
                    continue
                kind = "rate_limited" if e.code == 429 else "upstream"
                last = UpstreamError(kind, f"HTTP {e.code}: {detail}")
                if e.code not in (429, 500, 502, 503, 504):
                    raise last
            except (TimeoutError, OSError) as e:  # socket.timeout is an OSError subclass
                last = UpstreamError("timeout" if "timed out" in str(e).lower() else "upstream", f"{type(e).__name__}: {e}")
            if attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 8))
        raise last or UpstreamError("upstream", "unknown upstream failure")

    def _call(self, body: dict) -> Completion:
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        t0 = time.time()
        timeout = self.timeout_s * (4 if body.get("stream") else 1)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if body.get("stream"):
                parts, usage = [], {}
                for line in r:
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[5:])
                    usage = chunk.get("usage") or usage
                    for ch in chunk.get("choices") or []:
                        parts.append((ch.get("delta") or {}).get("content") or "")
                text = "".join(parts)
            else:
                data = json.loads(r.read())
                text, usage = data["choices"][0]["message"].get("content") or "", data.get("usage") or {}
        return Completion(text=text, prompt_tokens=usage.get("prompt_tokens", 0),
                          completion_tokens=usage.get("completion_tokens", 0),
                          latency_ms=int((time.time() - t0) * 1000))


class FakeLLM(LLM):
    """Scripted responses for tests and fault injection. Each item is a string, an
    exception to raise, or a callable(messages, thinking) -> str."""

    def __init__(self, script: List[Union[str, Exception, Callable]]):
        self.script = list(script)
        self.calls: List[dict] = []
        self._lock = threading.Lock()

    def complete(self, messages, *, model=None, thinking=None) -> Completion:
        with self._lock:
            self.calls.append({"messages": messages, "model": model, "thinking": thinking})
            if not self.script:
                raise AssertionError("FakeLLM script exhausted")
            item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        text = item(messages, thinking) if callable(item) else item
        return Completion(text=text, prompt_tokens=sum(len(m["content"]) for m in messages) // 4,
                          completion_tokens=len(text) // 4)
