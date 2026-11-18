"""Thinking on/off comparison on the reasoning set (runs_reason/). Prints a markdown table.

Usage: python3 compare_thinking.py   (run `python3 score.py --cases cases_reason.jsonl --runs-dir runs_reason --out results_reason.md --detail` first)
"""
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent
PLAIN = {"paraphrase", "near_verbatim"}
PAIRS = [  # (thinking off, thinking on)
    ("qwen3.6-35b-a3b", "qwen3.6-35b-a3b@think"),
    ("qwen3.8-flash", "qwen3.8-flash@think"),
    ("qwen3.7-plus", "qwen3.7-plus@think"),
    ("qwen3.8-max", "qwen3.8-max@think"),
    ("deepseek-v4-flash-0731@nothink", "deepseek-v4-flash-0731"),
]


def main() -> None:
    det = json.loads((ROOT / "results_reason_detail.json").read_text())
    cases = {c["id"]: c for c in (json.loads(l) for l in (ROOT / "cases_reason.jsonl").read_text().splitlines() if l.strip())}
    gold = {(cid, g["claim_id"]): g for cid, c in cases.items() for g in c["gold_claims"]}

    def stats(label: str) -> dict:
        o = det.get(f"{label}|oracle")
        e = det.get(f"{label}|e2e")
        if o is None:
            return {}
        r = [d for d in o if d["type"] not in PLAIN and not gold[(d["case"], d["claim"])].get("contestable")]
        p = [d for d in o if d["type"] in PLAIN]
        runs = [json.loads(l) for f in ("oracle", "e2e") for l in (ROOT / "runs_reason" / label / f"{f}.jsonl").read_text().splitlines() if l.strip()]
        comp = [(x.get("usage") or {}).get("completion_tokens", 0) for x in runs]
        reas = [((x.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0 for x in runs]
        lat = [x["latency_s"] for x in runs]
        unusable = sum(1 for x in runs if not (isinstance(x.get("parsed"), dict) and isinstance(x["parsed"].get("claims"), list)))
        return {
            "reason3": sum(d["pred"] == d["gold"] for d in r) / len(r),
            "reason2": sum((d["gold"] == "SUPPORTED") == (d["pred"] == "SUPPORTED") and d["pred"] != "MISSING" for d in r) / len(r),
            "plain": sum(d["pred"] == d["gold"] for d in p) / len(p),
            "e2e": sum(d["pred"] == d["gold"] for d in e) / len(e) if e else float("nan"),
            "p50": statistics.median(lat),
            "comp_tok": statistics.mean(comp),
            "reas_tok": statistics.mean(reas),
            "unusable": unusable,
        }

    print("| model | thinking | reasoning acc (3-way) | reasoning S-vs-nonS | plain acc | e2e strict acc | p50 latency s | avg completion tokens | of which reasoning | unusable outputs (/22) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for off, on in PAIRS:
        for label, th in ((off, "off"), (on, "on")):
            s = stats(label)
            if not s:
                print(f"| {label} | {th} | (missing) |||||||")
                continue
            print(f"| {label.split('@')[0]} | {th} | {s['reason3']:.2f} | {s['reason2']:.2f} | {s['plain']:.2f} | {s['e2e']:.2f} | {s['p50']:.1f} | {s['comp_tok']:.0f} | {s['reas_tok']:.0f} | {s['unusable']} |")


if __name__ == "__main__":
    main()
