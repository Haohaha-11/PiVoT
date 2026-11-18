"""Summarise repeated runs (independent caches) of the same configs on one dataset.

    python -m bench.repeats --runs-root bench/runs_test --dataset data/test.jsonl --out bench/results/test_report.md

Expects <runs-root>/rep*/<model>/<config>/<dataset stem>.jsonl. Reports mean +- std across repeats for the
headline metrics, the per-repeat paired difference between two configs (case-level bootstrap CI), and
accuracy by case category. Contestable gold claims are excluded unless stated.
"""
import argparse
import pathlib
import statistics

from .configs import CONFIGS
from .score import ROOT, aggregate, bootstrap_ci, paired_diff, score_run_dir, verify_frozen

METRICS = [("accuracy", "claim acc", "{:.3f}"), ("matched_accuracy", "acc on matched", "{:.3f}"), ("macro_f1", "macro-F1", "{:.3f}"),
           ("hallucination_recall", "halluc. recall", "{:.2f}"), ("false_alarm", "false alarm", "{:.3f}"),
           ("reasoning_accuracy", "reasoning acc", "{:.3f}"), ("plain_accuracy", "plain acc", "{:.3f}"),
           ("evidence_hit", "evidence hit", "{:.2f}"), ("claim_recall", "claim recall", "{:.2f}"), ("claim_precision", "claim precision", "{:.2f}"),
           ("errors", "errors", "{:.1f}"), ("llm_calls", "calls", "{:.1f}"), ("completion_tokens", "out tokens", "{:.0f}"),
           ("latency_p50_s", "p50 s", "{:.1f}"), ("latency_p95_s", "p95 s", "{:.1f}")]
CATEGORIES = ["fully_supported", "subtle_distortion", "extrinsic_hallucination", "multi_passage", "natural_answer"]


def fmt(vals, f):
    if len(vals) == 1:
        return f.format(vals[0])
    return f"{f.format(statistics.mean(vals))} ± {f.format(statistics.stdev(vals))}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=str(ROOT / "bench" / "runs_test"))
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--dataset", default="data/test.jsonl")
    ap.add_argument("--ref", default="minimal")
    ap.add_argument("--cmp", default="pivot,minimal-nothink")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    verify_frozen(args.dataset)
    stem = pathlib.Path(args.dataset).stem
    reps = sorted(p for p in pathlib.Path(args.runs_root).glob("rep*") if (p / args.model).is_dir())
    scored = [score_run_dir(r / args.model, [args.dataset]) for r in reps]
    configs = [c for c in CONFIGS if all(c in s for s in scored)]
    lines = [f"# {stem}: {len(reps)} independent repeats, model {args.model}", "",
             "Mean ± std across repeats (each repeat has its own LLM cache). Contestable gold claims excluded.", ""]
    hdr = [label for _, label, _ in METRICS]
    lines += ["| config | " + " | ".join(hdr) + " |", "|---|" + "---|" * len(hdr)]
    for cfg in configs:
        aggs = [aggregate(s[cfg][stem]) for s in scored]
        lines.append(f"| {cfg} | " + " | ".join(fmt([a[k] for a in aggs], f) for k, _, f in METRICS) + " |")
    lines += ["", "Claim accuracy with contestable claims included: " + ", ".join(
        f"{cfg} {fmt([aggregate(s[cfg][stem], include_contestable=True)['accuracy'] for s in scored], '{:.3f}')}" for cfg in configs), ""]
    lines += [f"## Repeat 1: claim accuracy with 95% case-level bootstrap CI", ""]
    for cfg in configs:
        lo, hi = bootstrap_ci(scored[0][cfg][stem])
        lines.append(f"- {cfg}: {aggregate(scored[0][cfg][stem])['accuracy']:.3f} [{lo:.3f}, {hi:.3f}]")
    lines += ["", f"## Paired accuracy difference vs {args.ref} (per repeat, case-level bootstrap)", "",
              "| config | " + " | ".join(f"repeat {i + 1}" for i in range(len(reps))) + " | mean delta |", "|---|" + "---|" * (len(reps) + 1)]
    for cmp in args.cmp.split(","):
        if cmp not in configs or args.ref not in configs:
            continue
        ds = [paired_diff(s[args.ref][stem], s[cmp][stem]) for s in scored]
        lines.append(f"| {cmp} | " + " | ".join(f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]" for d, lo, hi in ds) + f" | {statistics.mean(d for d, _, _ in ds):+.3f} |")
    lines += ["", "## Claim accuracy by case category (mean over repeats)", "", "| config | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    for cfg in configs:
        cells = []
        for cat in CATEGORIES:
            vals = [aggregate([k for k in s[cfg][stem] if cat in k["categories"]])["accuracy"] for s in scored]
            cells.append(f"{statistics.mean(vals):.3f}")
        lines.append(f"| {cfg} | " + " | ".join(cells) + " |")
    report = "\n".join(lines) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
