"""Score stored runs against gold labels.

    python -m bench.score [--runs bench/runs/<model>] [--datasets ...] [--ref minimal --cmp pivot]

Alignment (gold claim -> predicted claims), in order:
  1. span: every predicted claim whose answer_span overlaps the gold answer_span by at least
     SPAN_OVERLAP of the shorter span. Many-to-one is allowed both ways: a prediction that merges
     two gold claims is matched to both, a gold claim split into parts is matched to all parts.
  2. text fallback, only for predictions without a span (e.g. paraphrased claim_text that cannot
     be located in the answer): greedy one-to-one token-Dice matching above TEXT_SIMILARITY.
The verdict assigned to a gold claim is the most severe among its matches (C > U > S): one wrong
part is enough to make the claim wrong. A gold claim with no match is MISSING (counted wrong).

Metrics are over gold claims (contestable ones excluded unless --include-contestable).
"""
import argparse
import collections
import json
import pathlib
import random
import re
import statistics
from typing import Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
V = ["SUPPORTED", "CONTRADICTED", "UNSUPPORTED"]
SEVERITY = {"SUPPORTED": 0, "UNSUPPORTED": 1, "CONTRADICTED": 2}
PLAIN_TYPES = {"paraphrase", "near_verbatim"}
SPAN_OVERLAP = 0.5
TEXT_SIMILARITY = 0.45
_STOP = set("a an the of to in on for and or is are be by with as at it its this that from can will was were has have".split())


# ------------------------------------------------------------------ alignment

def span_overlap(a: List[int], b: List[int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / max(1, min(a[1] - a[0], b[1] - b[0]))


def _toks(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+(?:[.\-_][a-z0-9]+)*", s.lower()) if t not in _STOP}


def dice(a: str, b: str) -> float:
    x, y = _toks(a), _toks(b)
    return 2 * len(x & y) / (len(x) + len(y)) if x and y else 0.0


def align(gold: List[dict], preds: List[dict]) -> Tuple[List[List[int]], List[str]]:
    """-> (matched prediction indices per gold claim, how each was matched: span | text | none)."""
    matches: List[List[int]] = []
    via: List[str] = []
    for g in gold:
        m = [i for i, p in enumerate(preds)
             if p.get("answer_span") and g.get("answer_span") and span_overlap(g["answer_span"], p["answer_span"]) >= SPAN_OVERLAP]
        matches.append(m)
        via.append("span" if m else "none")
    spanless = [i for i, p in enumerate(preds) if not p.get("answer_span")]
    pairs = sorted(((dice(g["claim_text"], preds[pi]["claim_text"]), gi, pi)
                    for gi, g in enumerate(gold) if not matches[gi] for pi in spanless), reverse=True)
    used = set()
    for sim, gi, pi in pairs:
        if sim < TEXT_SIMILARITY:
            break
        if matches[gi] or pi in used:
            continue
        matches[gi], via[gi] = [pi], "text"
        used.add(pi)
    return matches, via


def most_severe(preds: List[dict], idx: List[int]) -> str:
    if not idx:
        return "MISSING"
    return max((preds[i]["verdict"] for i in idx), key=lambda v: SEVERITY.get(v, -1))


def evidence_hit(preds: List[dict], idx: List[int], g: dict) -> bool:
    """Do the matched predictions' citations cover the gold evidence (every piece when evidence_mode == 'all')?"""
    cits = [c for i in idx for c in preds[i].get("citations") or []]
    hits = [any(c["index"] == e["index"] and c["start_char"] < e["end_char"] and e["start_char"] < c["end_char"] for c in cits)
            for e in g["evidence"]]
    return all(hits) if g.get("evidence_mode") == "all" else any(hits)


# ------------------------------------------------------------------ per-case scoring

def score_case(case: dict, row: Optional[dict]) -> dict:
    gold = case["gold_claims"]
    resp = (row or {}).get("response")
    preds = resp["claims"] if resp else []
    matches, via = align(gold, preds)
    claims = []
    for g, m, how in zip(gold, matches, via):
        pv = most_severe(preds, m)
        claims.append({"claim_id": g["claim_id"], "gold": g["verdict"], "pred": pv, "type": g["type"], "via": how,
                       "contestable": bool(g.get("contestable")),
                       "evidence_ok": evidence_hit(preds, m, g) if pv == g["verdict"] and g["verdict"] != "UNSUPPORTED" else None})
    matched_preds = {i for m in matches for i in m}
    meta = (resp or {}).get("meta") or {}
    return {
        "case_id": case["id"], "categories": case.get("categories", []), "claims": claims,
        "error": (row or {}).get("error") if row else "missing run",
        "n_pred": len(preds), "n_pred_matched": len(matched_preds),
        "answer_gold_flag": any(g["verdict"] != "SUPPORTED" for g in gold),
        "answer_pred_flag": any(p["verdict"] != "SUPPORTED" for p in preds) if resp else None,
        "llm_calls": meta.get("llm_calls", 0), "prompt_tokens": meta.get("prompt_tokens", 0),
        "completion_tokens": meta.get("completion_tokens", 0),
        "latency_ms": meta.get("llm_latency_ms") or meta.get("latency_ms") or (row or {}).get("wall_ms", 0),
        "status": meta.get("status"), "escalated": meta.get("escalated_claims", 0), "resplit": meta.get("resplit_claims", 0),
        "dropped_pointers": meta.get("dropped_pointers", 0), "parse_repairs": meta.get("parse_repairs", []),
    }


# ------------------------------------------------------------------ aggregate metrics

def _macro_f1(pairs) -> float:
    f1 = []
    for c in V:
        tp = sum(g == c and p == c for g, p in pairs)
        fp = sum(g != c and p == c for g, p in pairs)
        fn = sum(g == c and p != c for g, p in pairs)
        pr, rc = (tp / (tp + fp) if tp + fp else 0.0), (tp / (tp + fn) if tp + fn else 0.0)
        f1.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return sum(f1) / 3


def aggregate(cases: List[dict], include_contestable: bool = False) -> dict:
    cl = [c for k in cases for c in k["claims"] if include_contestable or not c["contestable"]]
    pairs = [(c["gold"], c["pred"]) for c in cl]
    n = len(pairs) or 1
    non_s = [c for c in cl if c["gold"] != "SUPPORTED"]
    s_gold = [c for c in cl if c["gold"] == "SUPPORTED"]
    flagged = [c for c in cl if c["pred"] in ("CONTRADICTED", "UNSUPPORTED")]
    reasoning = [c for c in cl if c["type"] not in PLAIN_TYPES]
    plain = [c for c in cl if c["type"] in PLAIN_TYPES]
    ev = [c["evidence_ok"] for c in cl if c["evidence_ok"] is not None]
    lat = [k["latency_ms"] for k in cases if not k["error"]]
    answer = [k for k in cases if k["answer_pred_flag"] is not None]
    no_claim = [k for k in cases if not k["claims"]]
    return {
        "n_cases": len(cases), "n_claims": len(pairs),
        "accuracy": sum(g == p for g, p in pairs) / n,
        "macro_f1": _macro_f1(pairs),
        "recall": {v[0]: (sum(c["pred"] == v for c in cl if c["gold"] == v) / max(1, sum(c["gold"] == v for c in cl))) for v in V},
        "hallucination_recall": sum(c["pred"] in ("CONTRADICTED", "UNSUPPORTED") for c in non_s) / max(1, len(non_s)),
        "hallucination_precision": sum(c["gold"] != "SUPPORTED" for c in flagged) / max(1, len(flagged)),
        "false_support": sum(c["pred"] == "SUPPORTED" for c in non_s) / max(1, len(non_s)),
        "false_alarm": sum(c["pred"] in ("CONTRADICTED", "UNSUPPORTED") for c in s_gold) / max(1, len(s_gold)),
        "reasoning_accuracy": sum(c["gold"] == c["pred"] for c in reasoning) / max(1, len(reasoning)),
        "plain_accuracy": sum(c["gold"] == c["pred"] for c in plain) / max(1, len(plain)),
        "evidence_hit": sum(ev) / max(1, len(ev)),
        "claim_recall": sum(c["pred"] != "MISSING" for c in cl) / n,
        "matched_accuracy": sum(c["gold"] == c["pred"] for c in cl if c["pred"] != "MISSING") / max(1, sum(c["pred"] != "MISSING" for c in cl)),
        "claim_precision": sum(k["n_pred_matched"] for k in cases) / max(1, sum(k["n_pred"] for k in cases)),
        "text_aligned": sum(c["via"] == "text" for c in cl) / n,
        "answer_accuracy": sum(k["answer_gold_flag"] == k["answer_pred_flag"] for k in answer) / max(1, len(answer)),
        "spurious_on_no_claim": sum(k["n_pred"] for k in no_claim),
        "errors": sum(bool(k["error"]) for k in cases), "partial": sum(k["status"] == "partial" for k in cases),
        "llm_calls": statistics.mean(k["llm_calls"] for k in cases) if cases else 0,
        "tokens": statistics.mean(k["prompt_tokens"] + k["completion_tokens"] for k in cases) if cases else 0,
        "completion_tokens": statistics.mean(k["completion_tokens"] for k in cases) if cases else 0,
        "latency_p50_s": statistics.median(lat) / 1000 if lat else 0,
        "latency_p95_s": sorted(lat)[max(0, round(0.95 * len(lat)) - 1)] / 1000 if lat else 0,
        "escalated_per_case": statistics.mean(k["escalated"] for k in cases) if cases else 0,
        "confusion": dict(collections.Counter(f"{g[0]}->{p[0]}" for g, p in pairs)),
    }


def bootstrap_ci(cases: List[dict], metric=lambda a: a["accuracy"], n: int = 1000, seed: int = 0,
                 include_contestable: bool = False) -> Tuple[float, float]:
    """95% percentile interval, resampling whole cases (claims within a case are not independent)."""
    rng = random.Random(seed)
    vals = sorted(metric(aggregate([rng.choice(cases) for _ in cases], include_contestable)) for _ in range(n))
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def paired_diff(a: List[dict], b: List[dict], n: int = 1000, seed: int = 0, include_contestable: bool = False):
    """accuracy(b) - accuracy(a) on the same cases, with a paired case-level bootstrap interval."""
    by_a, by_b = {k["case_id"]: k for k in a}, {k["case_id"]: k for k in b}
    ids = sorted(set(by_a) & set(by_b))
    rng = random.Random(seed)

    def diff(sample):
        return aggregate([by_b[i] for i in sample], include_contestable)["accuracy"] - aggregate([by_a[i] for i in sample], include_contestable)["accuracy"]
    point = diff(ids)
    vals = sorted(diff([rng.choice(ids) for _ in ids]) for _ in range(n))
    return point, vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


# ------------------------------------------------------------------ CLI / report

def load_jsonl(p: pathlib.Path) -> List[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def verify_frozen(ds: str) -> None:
    """Refuse to score a test split whose bytes differ from the frozen hash in data/MANIFEST.json."""
    manifest = ROOT / "data" / "MANIFEST.json"
    split = pathlib.Path(ds).stem
    if split.startswith("test") and manifest.exists():
        import hashlib
        m = json.loads(manifest.read_text())
        actual = hashlib.sha256((ROOT / ds).read_bytes()).hexdigest()
        if m.get(f"{split}_frozen") and actual != m["sha256"].get(split):
            raise SystemExit(f"{ds} does not match the frozen hash in data/MANIFEST.json")


def score_run_dir(runs: pathlib.Path, datasets: List[str]) -> Dict[str, Dict[str, List[dict]]]:
    """-> {config: {dataset_stem: [scored case]}}"""
    out: Dict[str, Dict[str, List[dict]]] = collections.defaultdict(dict)
    for ds in datasets:
        verify_frozen(ds)
        cases = load_jsonl(ROOT / ds)
        stem = pathlib.Path(ds).stem
        for cfg_dir in sorted(p for p in runs.iterdir() if p.is_dir()):
            f = cfg_dir / f"{stem}.jsonl"
            if f.exists():
                rows = {r["case_id"]: r for r in load_jsonl(f)}
                out[cfg_dir.name][stem] = [score_case(c, rows.get(c["id"])) for c in cases]
    return out


def table(scored: Dict[str, List[dict]], order: List[str], include_contestable: bool) -> List[str]:
    lines = ["| config | claim acc [95% CI] | acc on matched | macro-F1 | halluc. recall | false alarm | reasoning acc | plain acc | evidence hit | claim recall / precision | answer acc | errors / partial | calls | out tokens | p50 / p95 s |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cfg in order:
        if cfg not in scored:
            continue
        cs = scored[cfg]
        a = aggregate(cs, include_contestable)
        lo, hi = bootstrap_ci(cs, include_contestable=include_contestable)
        lines.append(f"| {cfg} | {a['accuracy']:.3f} [{lo:.2f}, {hi:.2f}] | {a['matched_accuracy']:.3f} | {a['macro_f1']:.3f} | {a['hallucination_recall']:.2f} | {a['false_alarm']:.2f} "
                     f"| {a['reasoning_accuracy']:.2f} | {a['plain_accuracy']:.2f} | {a['evidence_hit']:.2f} | {a['claim_recall']:.2f} / {a['claim_precision']:.2f} "
                     f"| {a['answer_accuracy']:.2f} | {a['errors']} / {a['partial']} | {a['llm_calls']:.1f} | {a['completion_tokens']:.0f} | {a['latency_p50_s']:.1f} / {a['latency_p95_s']:.1f} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "bench" / "runs" / "deepseek-v4.1-flash"))
    ap.add_argument("--datasets", default="data/dev.jsonl", help="comma list; the frozen test split must be named explicitly (data/test.jsonl)")
    ap.add_argument("--include-contestable", action="store_true")
    ap.add_argument("--ref", default="minimal", help="reference config for paired differences")
    ap.add_argument("--out", default=None, help="write the markdown report here")
    args = ap.parse_args()
    datasets = args.datasets.split(",")
    scored = score_run_dir(pathlib.Path(args.runs), datasets)
    from .configs import CONFIGS
    order = [c for c in CONFIGS if c in scored] + sorted(c for c in scored if c not in CONFIGS)
    ic = args.include_contestable
    lines = [f"# Benchmark report: {pathlib.Path(args.runs).name}", "",
             f"Contestable gold claims {'included' if ic else 'excluded'}. Claim accuracy CI: case-level bootstrap (1000 resamples).", ""]
    pooled = {cfg: [k for ds in scored[cfg].values() for k in ds] for cfg in scored}
    lines += ["## All datasets pooled", ""] + table(pooled, order, ic) + [""]
    for ds in datasets:
        stem = pathlib.Path(ds).stem
        lines += [f"## {stem}", ""] + table({c: scored[c][stem] for c in scored if stem in scored[c]}, order, ic) + [""]
    if args.ref in pooled:
        lines += [f"## Paired accuracy difference vs {args.ref} (pooled, case-level bootstrap)", "", "| config | delta | 95% CI |", "|---|---|---|"]
        for cfg in order:
            if cfg != args.ref:
                d, lo, hi = paired_diff(pooled[args.ref], pooled[cfg], include_contestable=ic)
                lines.append(f"| {cfg} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
        lines.append("")
    lines += ["## Confusion (pooled, gold->pred; M = missing)", ""]
    for cfg in order:
        lines.append(f"- **{cfg}**: " + ", ".join(f"{k}: {v}" for k, v in sorted(aggregate(pooled[cfg], ic)["confusion"].items())))
    report = "\n".join(lines) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
