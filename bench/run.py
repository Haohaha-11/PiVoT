"""Run benchmark configs over datasets and store every response.

    python -m bench.run --configs lexical,minimal,minimal-nothink,pivot \
        --datasets pilot/cases.jsonl,pilot/cases_hard.jsonl,pilot/cases_reason.jsonl

Writes bench/runs/<model>/<config>/<dataset>.jsonl, one row per case:
    {"case_id", "config", "model", "response" (VerifyResponse JSON) | null, "error" | null, "wall_ms"}
LLM calls go through the record/replay cache (default bench/cache, mode "record"), so a rerun
with --cache-mode replay reproduces every number without an API key.
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import time

from verifier.llm import OpenAICompatLLM, UpstreamError
from verifier.parsing import ParseError

from .configs import CONFIGS, MAIN, make

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_cases(path: pathlib.Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_case(verifier, case: dict) -> dict:
    t0 = time.time()
    try:
        resp = verifier.verify(case["context_passages"], case["generated_answer"])
        return {"response": resp.model_dump(), "error": None, "wall_ms": int((time.time() - t0) * 1000)}
    except (UpstreamError, ParseError) as e:  # what the HTTP layer turns into 5xx
        return {"response": None, "error": f"{type(e).__name__}: {str(e)[:300]}", "wall_ms": int((time.time() - t0) * 1000)}


def _shown(path: pathlib.Path) -> str:
    """Path relative to the repo when it is inside it, absolute otherwise (--out may point anywhere)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=",".join(MAIN), help=f"comma list from: {', '.join(CONFIGS)}")
    ap.add_argument("--datasets", default="data/dev.jsonl", help="comma list; the frozen test split must be named explicitly (data/test.jsonl)")
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--cache-dir", default=str(ROOT / "bench" / "cache"))
    ap.add_argument("--cache-mode", default="record", choices=["record", "replay", "off"])
    ap.add_argument("--out", default=str(ROOT / "bench" / "runs"))
    ap.add_argument("--workers", type=int, default=6, help="cases in flight; also the LLM concurrency limit")
    ap.add_argument("--timeout", type=float, default=180, help="per-call timeout in seconds (x4 for thinking calls)")
    ap.add_argument("--retry-errors", action="store_true", help="only rerun cases that errored last time")
    args = ap.parse_args()
    out_root = pathlib.Path(args.out) if pathlib.Path(args.out).is_absolute() else ROOT / args.out
    cache_dir = pathlib.Path(args.cache_dir) if pathlib.Path(args.cache_dir).is_absolute() else ROOT / args.cache_dir

    llm = OpenAICompatLLM(model=args.model, cache_dir=str(cache_dir), cache_mode=args.cache_mode,
                          max_concurrency=args.workers, timeout_s=args.timeout)
    for config in args.configs.split(","):
        verifier = make(config, llm)
        for ds in args.datasets.split(","):
            ds_path = ROOT / ds
            cases = load_cases(ds_path)
            out = out_root / args.model / config / f"{ds_path.stem}.jsonl"
            done = {}
            if args.retry_errors and out.exists():
                done = {r["case_id"]: r for r in load_cases(out) if r["error"] is None}
            todo = [c for c in cases if c["id"] not in done]
            t0 = time.time()
            with cf.ThreadPoolExecutor(args.workers) as ex:
                results = dict(zip([c["id"] for c in todo], ex.map(lambda c: run_case(verifier, c), todo)))
            rows = []
            for c in cases:
                r = done.get(c["id"]) or {"case_id": c["id"], "config": config, "model": args.model, **results[c["id"]]}
                rows.append(r)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            errors = sum(r["error"] is not None for r in rows)
            print(f"{config:<26} {ds_path.stem:<14} {len(todo):>3} run, {errors} errors, {time.time() - t0:6.1f}s -> {_shown(out)}", flush=True)


if __name__ == "__main__":
    main()
