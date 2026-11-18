"""Independent-model audit of a draft test split: agreement of oracle-mode verdicts with the draft gold.

    (cd pilot && python run.py qwen3.8-max kimi-k3 --modes oracle --cases ../data/test2.jsonl --runs-dir runs_audit_test2)
    python -m data.audit test2 [--runs-dir runs_audit_test2] [--out data/review/test2/audit.md]

The audit models get passages and claim texts only (pilot/run.py oracle mode: no gold, no evidence, no notes).
Every claim on which any audit model disagrees with the draft is listed for adjudication under data/guideline.md.
"""
import argparse
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SHORT = {"SUPPORTED": "S", "CONTRADICTED": "C", "UNSUPPORTED": "U"}


def oracle_verdicts(path: pathlib.Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        p = row.get("parsed")
        if isinstance(p, list) and len(p) == 1 and isinstance(p[0], dict):
            p = p[0]  # kimi-k3 sometimes wraps the object in a list
        claims = p.get("claims") if isinstance(p, dict) else None
        for c in claims or []:
            if isinstance(c, dict):
                v = SHORT.get(str(c.get("verdict", "")).strip().upper(), "?")
                out[(row["case_id"], str(c.get("claim_id", "")).strip("[] "))] = (v, str(c.get("reasoning", ""))[:300])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("--models", default="qwen3.8-max,kimi-k3")
    ap.add_argument("--out", default=None)
    ap.add_argument("--runs-dir", default=None, help="under pilot/; default runs_audit_<split>")
    args = ap.parse_args()
    cases = [json.loads(l) for l in (ROOT / f"{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    models = args.models.split(",")
    preds = {m: oracle_verdicts(ROOT.parent / "pilot" / (args.runs_dir or f"runs_audit_{args.split}") / m / "oracle.jsonl") for m in models}
    lines = [f"# {args.split}: independent-model audit", "", "Oracle mode (passages + claim texts only). Agreement with the draft gold:", ""]
    for m in models:
        pairs = [(SHORT[g["verdict"]], preds[m].get((c["id"], g["claim_id"]), ("-", ""))[0]) for c in cases for g in c["gold_claims"]]
        agree = sum(a == b for a, b in pairs)
        conf = collections.Counter(f"{a}->{b}" for a, b in pairs if a != b)
        lines.append(f"- **{m}**: {agree}/{len(pairs)} = {agree / len(pairs):.3f}; disagreements {dict(conf)}")
    lines += ["", "## Disagreements", ""]
    n = 0
    for c in cases:
        for g in c["gold_claims"]:
            got = {m: preds[m].get((c["id"], g["claim_id"]), ("-", "missing")) for m in models}
            if all(v == SHORT[g["verdict"]] for v, _ in got.values()):
                continue
            n += 1
            flag = " (contestable)" if g.get("contestable") else ""
            lines.append(f"### {c['id']} {g['claim_id']}: gold {SHORT[g['verdict']]}{flag}")
            lines += [f"> {g['claim_text']}", ""]
            for m, (v, why) in got.items():
                lines.append(f"- {m}: **{v}** {why}")
            lines.append("")
    lines.insert(4 + len(models), f"\n{n} claims with at least one disagreement.")
    report = "\n".join(lines) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
