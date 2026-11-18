"""One table for the current model lineup across the three pilot sets.

Usage: python3 lineup_report.py > lineup_report.md
"""
import json
import pathlib
import statistics

from score import pred_claims_of, score_run

ROOT = pathlib.Path(__file__).resolve().parent
PLAIN = {"paraphrase", "near_verbatim"}
SETS = [("v1 (53 claims)", "cases.jsonl", "runs"), ("hard (130)", "cases_hard.jsonl", "runs_hard"), ("reasoning (116)", "cases_reason.jsonl", "runs_reason")]
LINEUP = [  # label, thinking
    ("deepseek-v4.1-flash", "on (default)"), ("deepseek-v4.1-flash@nothink", "off"),
    ("kimi-k3", "on (default)"), ("kimi-k3@nothink", "off"),
    ("glm-5.3", "on (cannot disable)"),
    ("qwen3.8-flash", "off"), ("qwen3.8-flash@think", "on"),
    ("qwen3.8-max", "off"), ("qwen3.8-max@think", "on"),
]


def load(path: pathlib.Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    for set_name, cases_file, runs_dir in SETS:
        cases = {c["id"]: c for c in load(ROOT / cases_file)}
        gold = {(cid, g["claim_id"]): g for cid, c in cases.items() for g in c["gold_claims"]}
        is_reason = "reason" in cases_file
        print(f"\n### {set_name}\n")
        hdr = "| model | thinking | oracle acc | oracle macro-F1 | S-vs-nonS | " + ("reasoning acc* | plain acc | " if is_reason else "") + "e2e acc | quote valid | unwrapped / unusable | p50 s | avg out tokens |"
        print(hdr)
        print("|" + "---|" * (hdr.count("|") - 1))
        for label, thinking in LINEUP:
            d = ROOT / runs_dir / label
            if not (d / "oracle.jsonl").exists():
                continue
            o_rows, e_rows = load(d / "oracle.jsonl"), load(d / "e2e.jsonl") if (d / "e2e.jsonl").exists() else []
            o = score_run(o_rows, cases, "oracle")
            e = score_run(e_rows, cases, "e2e") if e_rows else None
            det = o["detail"]
            nc = [x for x in det if not gold[(x["case"], x["claim"])].get("contestable")]
            s2 = sum((x["gold"] == "SUPPORTED") == (x["pred"] == "SUPPORTED") and x["pred"] != "MISSING" for x in nc) / len(nc)
            cols = [label.split("@")[0], thinking, f"{o['acc']:.2f}", f"{o['macro_f1']:.2f}", f"{s2:.2f}"]
            if is_reason:
                r = [x for x in nc if x["type"] not in PLAIN]
                p = [x for x in det if x["type"] in PLAIN]
                cols += [f"{sum(x['pred'] == x['gold'] for x in r) / len(r):.2f}", f"{sum(x['pred'] == x['gold'] for x in p) / len(p):.2f}"]
            rows = o_rows + e_rows
            unwrapped = sum(pred_claims_of(x)[1] for x in rows)
            unusable = sum(pred_claims_of(x)[0] is None for x in rows)
            toks = [(x.get("usage") or {}).get("completion_tokens", 0) for x in rows]
            cols += [f"{e['acc']:.2f}" if e else "-",
                     f"{(o['cit_valid_rate'] * o['cit_total'] + (e['cit_valid_rate'] * e['cit_total'] if e else 0)) / max(1, o['cit_total'] + (e['cit_total'] if e else 0)):.2f}",
                     f"{unwrapped} / {unusable}", f"{statistics.median(x['latency_s'] for x in rows):.1f}", f"{statistics.mean(toks):.0f}"]
            print("| " + " | ".join(cols) + " |")
        if is_reason:
            print("\n\\* reasoning-type claims only, contestable excluded. S-vs-nonS also excludes contestable.")
    print("\nNote: glm-5.3 generated the two natural answers in the hard set (natural-01/02), so its hard-set numbers include self-verification on those two cases.")


if __name__ == "__main__":
    main()
