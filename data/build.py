"""Build data/dev.jsonl and data/test.jsonl and write data/MANIFEST.json.

    python -m data.build                  # build + validate (refuses to change a frozen test split)
    python -m data.build --freeze test2   # also mark a test split as frozen

dev  = the three pilot sets (pilot/cases*.jsonl), used to design and tune the verifier.
test  = data/spec_test.py, four documentation families the dev split never uses, labelled before any
        system was run on it (frozen, evaluated once with pivot-v3).
test2 = data/spec_test2.py, two further families (git gc, HTTP caching RFC 9111), built after test was
        evaluated and frozen before pivot-v4 was run on it.

Every gold claim is validated with the invariants the service enforces: quotes are exact substrings of
their passage (offsets computed here), anchors are exact substrings of the answer, SUPPORTED and
CONTRADICTED claims have evidence, UNSUPPORTED claims have none.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import sys

from . import spec_test, spec_test2

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
VERDICTS = {"SUPPORTED", "CONTRADICTED", "UNSUPPORTED"}
PLAIN_TYPES = {"paraphrase", "near_verbatim"}
DEV_SOURCES = ["pilot/cases.jsonl", "pilot/cases_hard.jsonl", "pilot/cases_reason.jsonl"]


def _sources() -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "sources").glob("*.json")}


TEST_SPLITS = {"test": (spec_test, "natural_answers.json"), "test2": (spec_test2, "natural_answers_test2.json")}


def build_test(errors: list, split: str = "test") -> list:
    spec, natural_file = TEST_SPLITS[split]
    sources = _sources()
    natural = {n["id"]: n for n in json.loads((ROOT / natural_file).read_text(encoding="utf-8"))}
    out = []
    for case in spec.CASES:
        cid = case["id"]
        meta = {}
        if case.get("natural"):
            n = natural[cid]
            refs, answer = n["refs"], n["answer"]
            meta = {"question": n["q"], "generator": n["generator"]}
        else:
            refs, answer = case["passages"], case["answer"]
        passages, provenance = [], []
        for ref in refs:
            src, _, key = ref.partition(":")
            if src == "inline":
                passages.append(key)
                provenance.append("inline")
            else:
                passages.append(sources[src]["paragraphs"][int(key)])
                provenance.append(f"{sources[src]['url']}#para{key}")
        gold = []
        for i, c in enumerate(case["claims"]):
            tag = f"{cid}/c{i + 1}"
            if c["verdict"] not in VERDICTS:
                errors.append(f"{tag}: bad verdict {c['verdict']}")
            a = answer.find(c["anchor"])
            if a < 0:
                errors.append(f"{tag}: anchor not in answer: {c['anchor']!r}")
            if c["verdict"] == "UNSUPPORTED" and c["evidence"]:
                errors.append(f"{tag}: UNSUPPORTED claim must have no evidence")
            if c["verdict"] != "UNSUPPORTED" and not c["evidence"]:
                errors.append(f"{tag}: {c['verdict']} claim needs evidence")
            ev = []
            for e in c["evidence"]:
                p = e["p"]
                if not 0 <= p < len(passages):
                    errors.append(f"{tag}: passage index {p} out of range")
                    continue
                s = passages[p].find(e["quote"])
                if s < 0:
                    errors.append(f"{tag}: quote not verbatim in passage {p}: {e['quote'][:90]!r}")
                    continue
                ev.append({"index": p, "quote": e["quote"], "start_char": s, "end_char": s + len(e["quote"])})
            gold.append({"claim_id": f"c{i + 1}", "claim_text": c["text"],
                         "answer_span": [a, a + len(c["anchor"])] if a >= 0 else None,
                         "verdict": c["verdict"], "type": c["type"], "evidence": ev,
                         "evidence_mode": c.get("evidence_mode", "any"),
                         **({"note": c["note"]} if c.get("note") else {}),
                         **({"contestable": True} if c.get("contestable") else {})})
        out.append({"id": cid, "split": split, "family": case["family"], "categories": case["categories"],
                    "answer_origin": "natural" if case.get("natural") else "crafted", **meta,
                    "context_passages": passages, "passage_sources": provenance,
                    "generated_answer": answer, "gold_claims": gold})
    return out


def build_dev() -> list:
    out = []
    for f in DEV_SOURCES:
        for line in (REPO / f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                fam = {"sqlite": "sqlite_wal", "redis": "redis_persistence", "pg": "pg_vacuum"}
                family = next((v for k, v in fam.items() if k in c["id"]), "mixed")
                out.append({"split": "dev", "family": family, "answer_origin": "natural" if "natural" in c["id"] else "crafted",
                            "pilot_set": pathlib.Path(f).stem, **c})
    return out


def stats(cases: list) -> dict:
    claims = [g for c in cases for g in c["gold_claims"]]
    return {
        "cases": len(cases), "claims": len(claims),
        "verdicts": dict(collections.Counter(g["verdict"] for g in claims)),
        "reasoning_claims": sum(g["type"] not in PLAIN_TYPES for g in claims),
        "contestable_claims": sum(bool(g.get("contestable")) for g in claims),
        "categories": dict(collections.Counter(cat for c in cases for cat in c["categories"])),
        "families": dict(collections.Counter(c["family"] for c in cases)),
        "answer_origin": dict(collections.Counter(c.get("answer_origin", "crafted") for c in cases)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", choices=sorted(TEST_SPLITS), action="append", default=[], help="mark a test split as frozen")
    ap.add_argument("--allow-test-change", default=None, metavar="REASON",
                    help="rebuild a frozen test split anyway; REASON is logged in MANIFEST.json")
    args = ap.parse_args()
    errors: list = []
    splits = {name: build_test(errors, name) for name in TEST_SPLITS}
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    rows = {"dev": build_dev(), **splits}
    blobs = {name: "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in r) for name, r in rows.items()}
    sha = {name: hashlib.sha256(b.encode()).hexdigest() for name, b in blobs.items()}
    mpath = ROOT / "MANIFEST.json"
    old = json.loads(mpath.read_text()) if mpath.exists() else {}
    log = old.get("test_change_log", [])
    frozen = {name: bool(old.get(f"{name}_frozen")) or name in args.freeze for name in TEST_SPLITS}
    for name in TEST_SPLITS:
        if old.get(f"{name}_frozen") and old.get("sha256", {}).get(name) != sha[name]:
            if not args.allow_test_change:
                sys.exit(f"{name} split is frozen and would change; rerun with --allow-test-change REASON if this is intended")
            log.append({"split": name, "from": old["sha256"][name], "to": sha[name], "reason": args.allow_test_change})
    for name, b in blobs.items():
        (ROOT / f"{name}.jsonl").write_text(b, encoding="utf-8")
    manifest = {"sha256": sha, **{f"{n}_frozen": f for n, f in frozen.items()},
                **{name: stats(r) for name, r in rows.items()}, "test_change_log": log, "guideline": "data/guideline.md"}
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name in rows:
        st = manifest[name]
        print(f"{name}: {st['cases']} cases, {st['claims']} claims {st['verdicts']}, reasoning {st['reasoning_claims']}, "
              f"contestable {st['contestable_claims']}, origin {st['answer_origin']}"
              + (f"  sha256 {sha[name][:16]} frozen={frozen[name]}" if name in frozen else ""))


if __name__ == "__main__":
    main()
