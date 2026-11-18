"""Pilot runner: minimal-prompt, single-call LLM verifier over pilot/cases.jsonl.

Modes
  e2e     the model decomposes the answer itself and judges each claim
  oracle  the model receives the gold claims (text only) and judges each one

Usage: DASHSCOPE_API_KEY=... python3 run.py MODEL [MODEL ...] [--modes e2e,oracle] [--workers 6] [--cases cases.jsonl] [--runs-dir runs]
Writes one JSON line per (case) to runs/<model>/<mode>.jsonl, including the raw
model output, latency and token usage. Nothing here repairs model output: parse
failures are recorded as such, because this is the minimal baseline.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

SYSTEM_E2E = """You check whether an answer is grounded in the given source passages.
Split the answer into atomic factual claims. For each claim give a verdict:
- SUPPORTED: fully entailed by the passages
- CONTRADICTED: refuted by the passages
- UNSUPPORTED: not stated in the passages (even if true in the real world)
For SUPPORTED and CONTRADICTED claims, cite exact verbatim quotes from the passages together with the passage index. UNSUPPORTED claims have an empty citations list.
Return only JSON of the form:
{"claims": [{"claim_text": "...", "verdict": "SUPPORTED|CONTRADICTED|UNSUPPORTED", "reasoning": "...", "citations": [{"index": 0, "quote": "..."}]}]}"""

SYSTEM_ORACLE = """You check whether claims are grounded in the given source passages.
For each claim give a verdict:
- SUPPORTED: fully entailed by the passages
- CONTRADICTED: refuted by the passages
- UNSUPPORTED: not stated in the passages (even if true in the real world)
For SUPPORTED and CONTRADICTED claims, cite exact verbatim quotes from the passages together with the passage index. UNSUPPORTED claims have an empty citations list.
Return only JSON of the form:
{"claims": [{"claim_id": "c1", "verdict": "SUPPORTED|CONTRADICTED|UNSUPPORTED", "reasoning": "...", "citations": [{"index": 0, "quote": "..."}]}]}"""


def render_passages(passages: list) -> str:
    if not passages:
        return "(no passages)"
    return "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages))


def build_messages(case: dict, mode: str) -> list:
    ctx = render_passages(case["context_passages"])
    if mode == "e2e":
        user = f"Passages:\n{ctx}\n\nAnswer:\n{case['generated_answer']}"
        return [{"role": "system", "content": SYSTEM_E2E}, {"role": "user", "content": user}]
    claims = "\n".join(f"[{c['claim_id']}] {c['claim_text']}" for c in case["gold_claims"])
    user = f"Passages:\n{ctx}\n\nClaims:\n{claims or '(none)'}"
    return [{"role": "system", "content": SYSTEM_ORACLE}, {"role": "user", "content": user}]


def parse_model_spec(spec: str) -> tuple:
    """'qwen3.8-flash@think' -> ('qwen3.8-flash', True); '@nothink' -> False; no suffix -> None (provider default,
    except Qwen where the minimal baseline turns thinking off)."""
    name, _, flag = spec.partition("@")
    return name, {"think": True, "nothink": False}.get(flag)


def call(model: str, messages: list, key: str, json_mode: bool = True, timeout: int = 180, thinking=None) -> dict:
    body = {"model": model, "messages": messages, "temperature": 0}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if thinking is None and model.startswith("qwen"):
        thinking = False
    if thinking is not None:
        body["enable_thinking"] = thinking
    if thinking:  # DashScope only returns thinking output in streaming mode
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if not thinking:
            return json.loads(r.read())
        content, reasoning, usage = [], [], None
        for line in r:
            line = line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[5:])
            usage = chunk.get("usage") or usage
            for ch in chunk.get("choices") or []:
                delta = ch.get("delta") or {}
                content.append(delta.get("content") or "")
                reasoning.append(delta.get("reasoning_content") or "")
        return {"choices": [{"message": {"content": "".join(content), "reasoning_content": "".join(reasoning)}}], "usage": usage}


def call_with_retry(model: str, messages: list, key: str, timeout=None) -> tuple:
    model, thinking = parse_model_spec(model)
    timeout = timeout or (600 if thinking else 180)
    json_mode = True
    last_err = None
    for attempt in range(4):
        try:
            return call(model, messages, key, json_mode=json_mode, timeout=timeout, thinking=thinking), None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            last_err = f"HTTP {e.code}: {detail}"
            if e.code == 400 and "response_format" in detail and json_mode:
                json_mode = False
                continue
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt * 2)
                continue
            break
        except Exception as e:  # timeouts, connection resets
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt * 2)
    return None, last_err


def parse_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1]), None
            except json.JSONDecodeError:
                pass
        return None, f"JSONDecodeError: {e}"


def run_one(model: str, mode: str, case: dict, key: str, timeout=None) -> dict:
    messages = build_messages(case, mode)
    t0 = time.time()
    resp, err = call_with_retry(model, messages, key, timeout)
    latency = time.time() - t0
    row = {"case_id": case["id"], "model": model, "mode": mode, "latency_s": round(latency, 3), "error": err}
    if resp:
        msg = resp["choices"][0]["message"]
        content = msg.get("content") or ""
        row["raw"] = content
        row["usage"] = resp.get("usage")
        if msg.get("reasoning_content"):
            row["reasoning_chars"] = len(msg["reasoning_content"])
        parsed, perr = parse_json(content)
        row["parsed"] = parsed
        row["parse_error"] = perr
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--modes", default="e2e,oracle")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cases", default="cases.jsonl")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--timeout", type=int, default=None, help="per-request timeout in seconds")
    ap.add_argument("--retry-errors", action="store_true", help="only rerun rows that errored or failed to parse, merging into existing files")
    args = ap.parse_args()
    key = os.environ["DASHSCOPE_API_KEY"]
    cases = [json.loads(l) for l in (ROOT / args.cases).read_text(encoding="utf-8").splitlines() if l.strip()]
    jobs = [(m, mode, c) for m in args.models for mode in args.modes.split(",") for c in cases]
    results: dict = {}
    if args.retry_errors:
        keep = []
        for m, mode, c in jobs:
            f = ROOT / args.runs_dir / m.replace("/", "_") / f"{mode}.jsonl"
            old = {r["case_id"]: r for r in (json.loads(l) for l in f.read_text().splitlines() if l.strip())} if f.exists() else {}
            r = old.get(c["id"])
            if r is None or r.get("error") or r.get("parse_error"):
                keep.append((m, mode, c))
            else:
                results.setdefault((m, mode), []).append(r)
        jobs = keep
        print(f"retrying {len(jobs)} rows", flush=True)
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(run_one, m, mode, c, key, args.timeout): (m, mode) for m, mode, c in jobs}
        for f in cf.as_completed(futs):
            row = f.result()
            results.setdefault((row["model"], row["mode"]), []).append(row)
            flag = "ERR " + row["error"][:80] if row["error"] else ("PARSE_FAIL" if row.get("parse_error") else "ok")
            print(f"{row['model']:<22} {row['mode']:<6} {row['case_id']:<40} {row['latency_s']:>6.1f}s {flag}", flush=True)
    for (m, mode), rows in results.items():
        d = ROOT / args.runs_dir / m.replace("/", "_")
        d.mkdir(parents=True, exist_ok=True)
        rows.sort(key=lambda r: r["case_id"])
        with open(d / f"{mode}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
