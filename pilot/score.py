"""Score pilot runs in runs/<model>/<mode>.jsonl against cases.jsonl.

oracle mode: gold claims were given, so verdicts are compared by claim_id.
e2e mode:    predicted claims are aligned to gold claims with greedy one-to-one
             matching on token Dice similarity (pilot-grade aligner, threshold 0.45).

Usage: python3 score.py [--cases cases.jsonl] [--runs-dir runs] [--out results.md] [--detail] [--exclude-contestable]
"""
import collections
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent
V = ["SUPPORTED", "CONTRADICTED", "UNSUPPORTED"]
SHORT = {"SUPPORTED": "S", "CONTRADICTED": "C", "UNSUPPORTED": "U"}
STOP = set("a an the of to in on for and or is are be by with as at it its this that from can will was were has have not no".split())
ALIGN_THRESHOLD = 0.45
EXCLUDE_CONTESTABLE = "--exclude-contestable" in sys.argv


def norm_verdict(v) -> str:
    v = str(v or "").strip().upper()
    return v if v in V else "INVALID"


def toks(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+(?:[.\-_][a-z0-9]+)*", s.lower()) if t not in STOP}


def dice(a: str, b: str) -> float:
    x, y = toks(a), toks(b)
    return 2 * len(x & y) / (len(x) + len(y)) if x and y else 0.0


def macro_f1(pairs: list) -> float:
    f1s = []
    for c in V:
        tp = sum(1 for g, p in pairs if g == c and p == c)
        fp = sum(1 for g, p in pairs if g != c and p == c)
        fn = sum(1 for g, p in pairs if g == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s)


def citation_stats(pred_claims: list, passages: list) -> dict:
    total = valid = sc_without = u_with = 0
    for pc in pred_claims:
        v = norm_verdict(pc.get("verdict"))
        cits = pc.get("citations") or []
        if v in ("SUPPORTED", "CONTRADICTED") and not cits:
            sc_without += 1
        if v == "UNSUPPORTED" and cits:
            u_with += 1
        for c in cits:
            total += 1
            idx, q = c.get("index"), c.get("quote")
            if isinstance(idx, int) and 0 <= idx < len(passages) and isinstance(q, str) and q and q in passages[idx]:
                valid += 1
    return {"cit_total": total, "cit_valid": valid, "sc_without_cit": sc_without, "u_with_cit": u_with}


def evidence_hit(pred_cits: list, gold: dict, passages: list) -> bool:
    """True if the valid predicted quotes overlap the gold evidence (all spans when evidence_mode == 'all')."""
    spans = []
    for c in pred_cits or []:
        idx, q = c.get("index"), c.get("quote")
        if isinstance(idx, int) and 0 <= idx < len(passages) and isinstance(q, str) and q:
            s = passages[idx].find(q)
            if s >= 0:
                spans.append((idx, s, s + len(q)))
    hits = [any(i == e["index"] and s < e["end_char"] and e["start_char"] < t for i, s, t in spans) for e in gold["evidence"]]
    return all(hits) if gold["evidence_mode"] == "all" else any(hits)


def pred_claims_of(row: dict):
    """Returns (claims or None, unwrapped). A single-element list wrapping the expected object
    (kimi-k3 does this in thinking mode) is unwrapped and counted separately."""
    p = row.get("parsed")
    unwrapped = False
    if isinstance(p, list) and len(p) == 1 and isinstance(p[0], dict):
        p, unwrapped = p[0], True
    if isinstance(p, dict) and isinstance(p.get("claims"), list):
        return [c for c in p["claims"] if isinstance(c, dict)], unwrapped
    return None, False


def score_run(rows: list, cases: dict, mode: str) -> dict:
    pairs, types, detail = [], collections.defaultdict(list), []
    ev_hits = ev_total = 0
    agg = collections.Counter()
    case_flag_ok = case_n = spurious_on_empty = 0
    pred_n = gold_n = matched_n = 0
    lat = [r["latency_s"] for r in rows]
    tokens = sum((r.get("usage") or {}).get("total_tokens", 0) for r in rows)
    for r in rows:
        case = cases[r["case_id"]]
        passages, gold = case["context_passages"], case["gold_claims"]
        preds, unwrapped = pred_claims_of(r)
        agg["unwrapped_outputs"] += unwrapped
        if r.get("error"):
            agg["call_errors"] += 1
        if preds is None:
            agg["unusable_outputs"] += 1
            preds = []
        for k, v in citation_stats(preds, passages).items():
            agg[k] += v
        if mode == "oracle":
            by_id = {str(p.get("claim_id", "")).strip("[] "): p for p in preds}
            matches = [(g, by_id.get(g["claim_id"])) for g in gold]
        else:
            cand = sorted(((dice(g["claim_text"], p.get("claim_text", "")), gi, pi) for gi, g in enumerate(gold) for pi, p in enumerate(preds)), reverse=True)
            used_g, used_p, m = set(), set(), {}
            for s, gi, pi in cand:
                if s < ALIGN_THRESHOLD or gi in used_g or pi in used_p:
                    continue
                used_g.add(gi); used_p.add(pi); m[gi] = preds[pi]
            matches = [(g, m.get(gi)) for gi, g in enumerate(gold)]
            pred_n += len(preds); gold_n += len(gold); matched_n += len(m)
            if not gold and preds:
                spurious_on_empty += len(preds)
        for g, p in matches:
            if EXCLUDE_CONTESTABLE and g.get("contestable"):
                continue
            pv = norm_verdict(p.get("verdict")) if p else "MISSING"
            pairs.append((g["verdict"], pv))
            types[g["type"]].append(pv == g["verdict"])
            if p and pv == g["verdict"] and g["verdict"] != "UNSUPPORTED":
                ev_total += 1
                ev_hits += evidence_hit(p.get("citations"), g, passages)
            detail.append({"case": r["case_id"], "claim": g["claim_id"], "gold": g["verdict"], "pred": pv, "type": g["type"],
                           "gold_text": g["claim_text"], "pred_text": (p or {}).get("claim_text"), "reasoning": (p or {}).get("reasoning")})
        gold_flag = any(g["verdict"] != "SUPPORTED" for g in gold)
        pred_flag = any(norm_verdict(p.get("verdict")) != "SUPPORTED" for p in preds)
        case_n += 1
        case_flag_ok += gold_flag == pred_flag
    n = len(pairs)
    non_s = [(g, p) for g, p in pairs if g != "SUPPORTED"]
    s_only = [(g, p) for g, p in pairs if g == "SUPPORTED"]
    res = {
        "n_claims": n,
        "acc": sum(g == p for g, p in pairs) / n if n else 0,
        "macro_f1": macro_f1(pairs),
        "recall": {SHORT[c]: (sum(1 for g, p in pairs if g == c and p == c) / max(1, sum(1 for g, _ in pairs if g == c))) for c in V},
        "false_support": sum(p == "SUPPORTED" for _, p in non_s) / max(1, len(non_s)),
        "false_alarm": sum(p not in ("SUPPORTED",) for _, p in s_only) / max(1, len(s_only)),
        "evidence_hit": ev_hits / ev_total if ev_total else 0,
        "cit_valid_rate": agg["cit_valid"] / agg["cit_total"] if agg["cit_total"] else 0,
        "cit_total": agg["cit_total"],
        "invariant_violations": agg["sc_without_cit"] + agg["u_with_cit"],
        "unusable_outputs": agg["unusable_outputs"],
        "unwrapped_outputs": agg["unwrapped_outputs"],
        "call_errors": agg["call_errors"],
        "answer_level_acc": case_flag_ok / case_n if case_n else 0,
        "p50_s": statistics.median(lat) if lat else 0,
        "p95_s": sorted(lat)[max(0, int(round(0.95 * len(lat))) - 1)] if lat else 0,
        "tokens": tokens,
        "confusion": collections.Counter(f"{SHORT.get(g, g)}->{SHORT.get(p, p)}" for g, p in pairs),
        "by_type": {t: f"{sum(v)}/{len(v)}" for t, v in sorted(types.items())},
        "detail": detail,
    }
    if mode == "e2e":
        res.update({"claim_recall": matched_n / gold_n if gold_n else 0, "claim_precision": matched_n / pred_n if pred_n else 0,
                    "pred_claims": pred_n, "gold_claims": gold_n, "spurious_on_empty": spurious_on_empty})
    return res


def arg(name: str, default: str) -> str:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main() -> None:
    cases_file, runs_dir, out_md = arg("--cases", "cases.jsonl"), arg("--runs-dir", "runs"), arg("--out", "results.md")
    cases = {c["id"]: c for c in (json.loads(l) for l in (ROOT / cases_file).read_text(encoding="utf-8").splitlines() if l.strip())}
    results = {}
    for f in sorted((ROOT / runs_dir).glob("*/*.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        results[(rows[0]["model"], f.stem)] = score_run(rows, cases, f.stem)
    order = sorted({m for m, _ in results})
    lines = []
    gold_all = [g["verdict"] for c in cases.values() for g in c["gold_claims"]]
    maj = collections.Counter(gold_all).most_common(1)[0]
    lines.append(f"Gold: {len(gold_all)} claims, " + ", ".join(f"{SHORT[k]} {v}" for k, v in collections.Counter(gold_all).items())
                 + f". Always-SUPPORTED reference: acc {maj[1] / len(gold_all):.2f}, macro-F1 {macro_f1([(g, 'SUPPORTED') for g in gold_all]):.2f}\n")
    lines.append("## Oracle mode (gold claims given; tests judgment only)\n")
    lines.append("| model | acc | macro-F1 | recall S/C/U | false-support | false-alarm | evidence hit | quote valid | unusable (unwrapped) | p50 s |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for m in order:
        r = results.get((m, "oracle"))
        if r:
            rc = r["recall"]
            lines.append(f"| {m} | {r['acc']:.2f} | {r['macro_f1']:.2f} | {rc['S']:.2f}/{rc['C']:.2f}/{rc['U']:.2f} | {r['false_support']:.2f} | {r['false_alarm']:.2f} | {r['evidence_hit']:.2f} | {r['cit_valid_rate']:.2f} ({r['cit_total']}) | {r['unusable_outputs']} ({r['unwrapped_outputs']}) | {r['p50_s']:.1f} |")
    lines.append("\n## End-to-end mode (model decomposes; greedy Dice alignment)\n")
    lines.append("| model | strict acc* | macro-F1* | claim recall | claim precision | #pred/#gold | false-support* | answer-level acc | quote valid | invariant viol. | spurious on no-claim case | p50 s | tokens |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in order:
        r = results.get((m, "e2e"))
        if r:
            lines.append(f"| {m} | {r['acc']:.2f} | {r['macro_f1']:.2f} | {r['claim_recall']:.2f} | {r['claim_precision']:.2f} | {r['pred_claims']}/{r['gold_claims']} | {r['false_support']:.2f} | {r['answer_level_acc']:.2f} | {r['cit_valid_rate']:.2f} ({r['cit_total']}) | {r['invariant_violations']} | {r['spurious_on_empty']} | {r['p50_s']:.1f} | {r['tokens']} |")
    lines.append("\n\\* over gold claims; an unmatched gold claim counts as wrong.\n")
    lines.append("## Oracle accuracy by perturbation type\n")
    types = sorted({t for r in results.values() for t in r["by_type"]})
    lines.append("| type | " + " | ".join(order) + " |")
    lines.append("|---|" + "---|" * len(order))
    for t in types:
        lines.append(f"| {t} | " + " | ".join(results.get((m, "oracle"), {}).get("by_type", {}).get(t, "-") for m in order) + " |")
    out = "\n".join(lines)
    (ROOT / out_md).write_text(out + "\n", encoding="utf-8")
    print(out)
    if "--detail" in sys.argv:
        wrong = collections.defaultdict(list)
        for (m, mode), r in results.items():
            for d in r["detail"]:
                if d["gold"] != d["pred"]:
                    wrong[(mode, d["case"], d["claim"])].append(f"{m}:{SHORT.get(d['pred'], d['pred'])}")
        print("\n## Misjudged claims (mode, case, claim -> model:pred)")
        for k in sorted(wrong):
            g = next(c for c in cases[k[1]]["gold_claims"] if c["claim_id"] == k[2])
            print(f"{k[0]:<6} {k[1]:<38} {k[2]:<3} gold={SHORT[g['verdict']]} [{g['type']}] {', '.join(wrong[k])}")
        (ROOT / out_md.replace(".md", "_detail.json")).write_text(json.dumps({f"{m}|{mode}": r["detail"] for (m, mode), r in results.items()}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
