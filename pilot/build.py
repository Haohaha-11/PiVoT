"""Build a cases JSONL from a spec (default: spec.json -> cases.jsonl).

Usage: python3 build.py [SPEC] [OUT]

Resolves passage references verbatim from pilot/sources/*.json, then validates the
gold annotations with the same invariants the service must enforce:
  * every evidence quote is an exact substring of its passage (offsets computed here)
  * every claim anchor is an exact substring of the answer (answer_span computed here)
  * SUPPORTED / CONTRADICTED claims have evidence, UNSUPPORTED claims have none
Fails loudly on any violation.
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
VERDICTS = {"SUPPORTED", "CONTRADICTED", "UNSUPPORTED"}


def main() -> None:
    spec_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "spec.json"
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "cases.jsonl"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    sources = {
        name: json.loads((ROOT / "sources" / fname).read_text(encoding="utf-8"))
        for name, fname in spec["sources"].items()
    }
    errors: list[str] = []
    out = []
    verdicts = collections.Counter()
    for case in spec["cases"]:
        cid = case["id"]
        passages, provenance = [], []
        for ref in case["passages"]:
            src, _, key = ref.partition(":")
            if src == "inline":
                passages.append(key)
                provenance.append("inline")
            else:
                passages.append(sources[src]["paragraphs"][int(key)])
                provenance.append(f"{sources[src]['url']}#para{key}")
        answer = case["answer"]
        gold = []
        for i, c in enumerate(case["claims"]):
            tag = f"{cid}/c{i + 1}"
            if c["verdict"] not in VERDICTS:
                errors.append(f"{tag}: bad verdict {c['verdict']}")
            a = answer.find(c["anchor"])
            if a < 0:
                errors.append(f"{tag}: anchor not in answer: {c['anchor']!r}")
            ev = []
            for e in c["evidence"]:
                p = e["p"]
                if not 0 <= p < len(passages):
                    errors.append(f"{tag}: passage index {p} out of range")
                    continue
                s = passages[p].find(e["quote"])
                if s < 0:
                    errors.append(f"{tag}: quote not verbatim in passage {p}: {e['quote']!r}")
                    continue
                ev.append({"index": p, "quote": e["quote"], "start_char": s, "end_char": s + len(e["quote"])})
            if c["verdict"] == "UNSUPPORTED" and c["evidence"]:
                errors.append(f"{tag}: UNSUPPORTED claim must have no evidence")
            if c["verdict"] != "UNSUPPORTED" and not c["evidence"]:
                errors.append(f"{tag}: {c['verdict']} claim needs evidence")
            verdicts[c["verdict"]] += 1
            gold.append({
                "claim_id": f"c{i + 1}",
                "claim_text": c["text"],
                "answer_span": [a, a + len(c["anchor"])] if a >= 0 else None,
                "verdict": c["verdict"],
                "type": c["type"],
                "evidence": ev,
                "evidence_mode": c.get("evidence_mode", "any"),
                **({"note": c["note"]} if "note" in c else {}),
                **({"contestable": True} if c.get("contestable") else {}),
            })
        out.append({
            "id": cid,
            "categories": case["categories"],
            **({"question": case["question"], "generator": case["generator"]} if "question" in case else {}),
            "context_passages": passages,
            "passage_sources": provenance,
            "generated_answer": answer,
            "gold_claims": gold,
        })
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n = sum(verdicts.values())
    print(f"{len(out)} cases, {n} gold claims: " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in sorted(verdicts.items())))


if __name__ == "__main__":
    main()
