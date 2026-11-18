"""Blind second annotation of the agreement sample by an LLM annotator.

    python -m data.annotate --model deepseek-v4.1-flash [--split test2]
    python -m data.review agreement data/review/blind_labels_deepseek-v4.1-flash.tsv

The annotator gets the full guideline (data/guideline.md), the case's passages, the answer and the claim
texts to label. Gold labels, evidence and notes are never sent. Output: data/review/blind_labels_<model>.tsv.
"""
import argparse
import collections
import csv
import json
import pathlib

from verifier.llm import OpenAICompatLLM
from verifier.parsing import parse_object

ROOT = pathlib.Path(__file__).resolve().parent
REVIEW = ROOT / "review"

SYSTEM = """You are an annotator for a claim-verification benchmark. Label each claim against the given passages ONLY,
following this annotation guideline exactly:

{guideline}

Return only JSON: {{"labels": [{{"claim_id": "c3", "label": "S|C|U", "reason": "<at most 25 words, cite passage numbers>"}}]}}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--cache-dir", default=str(ROOT.parent / "bench" / "cache"))
    ap.add_argument("--split", default="test")
    args = ap.parse_args()
    review = REVIEW if args.split == "test" else REVIEW / args.split
    guideline = (ROOT / "guideline.md").read_text(encoding="utf-8")
    cases = {c["id"]: c for c in (json.loads(l) for l in (ROOT / f"{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    rows = list(csv.DictReader(open(review / "blind_labels.tsv", encoding="utf-8"), delimiter="\t"))
    by_case = collections.defaultdict(list)
    for r in rows:
        by_case[r["case_id"]].append(r)
    llm = OpenAICompatLLM(model=args.model, cache_dir=args.cache_dir, cache_mode="record", timeout_s=180)
    labels = {}
    for cid, items in by_case.items():
        case = cases[cid]  # only passages and answer are used; gold is never sent
        ctx = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(case["context_passages"])) or "(no passages)"
        claims = "\n".join(f"[{r['claim_id']}] {r['claim_text']}" for r in items)
        msg = [{"role": "system", "content": SYSTEM.format(guideline=guideline)},
               {"role": "user", "content": f"Passages:\n{ctx}\n\nAnswer:\n{case['generated_answer']}\n\nClaims to label:\n{claims}"}]
        obj, _ = parse_object(llm.complete(msg).text, "labels")
        for x in obj["labels"]:
            if isinstance(x, dict):
                labels[(cid, str(x.get("claim_id", "")).strip("[] "))] = (str(x.get("label", "")).strip().upper()[:1], str(x.get("reason", "")))
        print(f"{cid}: {len(items)} claims labelled", flush=True)
    out = review / f"blind_labels_{args.model.replace('/', '_')}.tsv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["case_id", "claim_id", "claim_text", "label", "reason"])
        for r in rows:
            lab, why = labels.get((r["case_id"], r["claim_id"]), ("", "missing"))
            w.writerow([r["case_id"], r["claim_id"], r["claim_text"], lab, why])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
