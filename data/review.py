"""Human review of the gold labels.

    python -m data.review export [SPLIT]             # writes data/review/{test_review.md, blind_cases.md, blind_labels.tsv}
    python -m data.review agreement [FILE] [SPLIT]   # compares a filled-in labels file (default data/review/blind_labels.tsv) with gold

SPLIT defaults to test; the files of any other test split go to data/review/<split>/.

test_review.md   every test case with its gold claims, for a line-by-line check.
blind_*          a stratified sample of claims WITHOUT gold labels: label them independently first
                 (fill the `label` column with S / C / U), then run `agreement` for raw agreement and
                 Cohen's kappa. Disagreements are adjudicated by data/guideline.md.
"""
import collections
import csv
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "review"
SAMPLE_SIZE = 40
SHORT = {"SUPPORTED": "S", "CONTRADICTED": "C", "UNSUPPORTED": "U"}


def out_dir(split: str) -> pathlib.Path:
    return OUT if split == "test" else OUT / split


def load(split: str = "test") -> list:
    return [json.loads(l) for l in (ROOT / f"{split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def _passages_md(case: dict) -> list:
    if not case["context_passages"]:
        return ["*(no passages)*", ""]
    return [f"**[{i}]** {p}\n" for i, p in enumerate(case["context_passages"])]


def export(split: str = "test") -> None:
    OUT = out_dir(split)
    OUT.mkdir(parents=True, exist_ok=True)
    cases = load(split)
    lines = [f"# {split} split: gold review", "",
             "For every claim, check the verdict and evidence against data/guideline.md. Mark disagreements by editing",
             "`[ ]` to `[x]` and writing the label you would give plus a short reason.", ""]
    for c in cases:
        lines += [f"## {c['id']}", "", f"family `{c['family']}` · categories {', '.join(c['categories'])} · {c['answer_origin']}", ""]
        if c.get("question"):
            lines += [f"**Question:** {c['question']}", ""]
        lines += ["### Passages", ""] + _passages_md(c) + ["### Answer", "", f"> {c['generated_answer']}", "", "### Gold claims", ""]
        if not c["gold_claims"]:
            lines += ["*(no factual claims)*", ""]
        for g in c["gold_claims"]:
            flag = " · **contestable**" if g.get("contestable") else ""
            lines.append(f"- [ ] **{g['claim_id']} {SHORT[g['verdict']]}** `{g['type']}`{flag}: {g['claim_text']}")
            for e in g["evidence"]:
                lines.append(f"    - [{e['index']}] \"{e['quote']}\"" + (" (all)" if g['evidence_mode'] == "all" else ""))
            if g.get("note"):
                lines.append(f"    - note: {g['note']}")
        lines.append("")
    (OUT / "test_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if (OUT / "blind_labels.tsv").exists():
        print(f"wrote {OUT/'test_review.md'} (blind sample already exists, kept unchanged so finished labels stay valid)")
        return
    # stratified blind sample: all contestable excluded, then proportional by verdict with a floor for C and U
    rng = random.Random(7)
    pool = [(c, g) for c in cases for g in c["gold_claims"] if not g.get("contestable")]
    by_v = collections.defaultdict(list)
    for item in pool:
        by_v[item[1]["verdict"]].append(item)
    quota = {"CONTRADICTED": 12, "UNSUPPORTED": 10}
    quota = {v: min(k, len(by_v[v])) for v, k in quota.items()}
    quota["SUPPORTED"] = SAMPLE_SIZE - sum(quota.values())
    sample = [x for v, k in quota.items() for x in rng.sample(by_v[v], min(k, len(by_v[v])))]
    rng.shuffle(sample)
    with open(OUT / "blind_labels.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["case_id", "claim_id", "claim_text", "label"])
        for c, g in sample:
            w.writerow([c["id"], g["claim_id"], g["claim_text"], ""])
    used = sorted({c["id"] for c, _ in sample})
    md = ["# Blind labelling", "", "Label each claim in blind_labels.tsv with S / C / U using only the passages below and data/guideline.md.",
          "Do not open test_review.md before you are done.", ""]
    for c in cases:
        if c["id"] in used:
            md += [f"## {c['id']}", "", "### Passages", ""] + _passages_md(c) + ["### Answer", "", f"> {c['generated_answer']}", ""]
    (OUT / "blind_cases.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT/'test_review.md'}, {OUT/'blind_cases.md'}, {OUT/'blind_labels.tsv'} ({len(sample)} claims from {len(used)} cases)")


def agreement(path: str = "", split: str = "test") -> None:
    gold = {(c["id"], g["claim_id"]): SHORT[g["verdict"]] for c in load(split) for g in c["gold_claims"]}
    f = pathlib.Path(path) if path else out_dir(split) / "blind_labels.tsv"
    rows = list(csv.DictReader(open(f, encoding="utf-8"), delimiter="\t"))
    pairs = [(gold[(r["case_id"], r["claim_id"])], r["label"].strip().upper()[:1]) for r in rows if r["label"].strip()]
    if not pairs:
        sys.exit("no labels filled in yet")
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in "SCU") / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"{n} claims labelled: raw agreement {po:.3f}, Cohen's kappa {kappa:.3f}")
    print("confusion (gold->you):", dict(collections.Counter(f"{a}->{b}" for a, b in pairs)))
    for r in rows:
        lab = r["label"].strip().upper()[:1]
        if lab and lab != gold[(r["case_id"], r["claim_id"])]:
            print(f"  disagree {r['case_id']} {r['claim_id']}: gold {gold[(r['case_id'], r['claim_id'])]} you {lab} | {r['claim_text']}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "export"
    if cmd == "export":
        export(argv[1] if len(argv) > 1 else "test")
    else:
        agreement(argv[1] if len(argv) > 1 else "", argv[2] if len(argv) > 2 else "test")
