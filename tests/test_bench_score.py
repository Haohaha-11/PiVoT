from bench.score import aggregate, align, evidence_hit, most_severe, paired_diff, score_case


def g(cid, span, verdict, text="gold claim text", evidence=(), mode="any", typ="paraphrase", contestable=False):
    return {"claim_id": cid, "claim_text": text, "answer_span": list(span), "verdict": verdict, "type": typ,
            "evidence": list(evidence), "evidence_mode": mode, "contestable": contestable}


def p(span, verdict, text="pred", cits=()):
    return {"claim_text": text, "answer_span": list(span) if span else None, "verdict": verdict, "citations": list(cits)}


def ev(i, s, e):
    return {"index": i, "start_char": s, "end_char": e, "quote": "x"}


def test_split_prediction_takes_the_most_severe_part():
    gold = [g("c1", (0, 80), "UNSUPPORTED")]
    preds = [p((0, 30), "SUPPORTED"), p((32, 80), "CONTRADICTED")]
    m, via = align(gold, preds)
    assert m == [[0, 1]] and via == ["span"] and most_severe(preds, m[0]) == "CONTRADICTED"


def test_merged_prediction_matches_every_gold_it_covers():
    gold = [g("c1", (0, 20), "CONTRADICTED"), g("c2", (22, 50), "SUPPORTED")]
    m, _ = align(gold, [p((0, 50), "CONTRADICTED")])
    assert m == [[0], [0]]  # the S claim inherits the merged C: merging is penalised


def test_text_fallback_is_one_to_one_and_only_for_spanless_predictions():
    gold = [g("c1", (0, 10), "SUPPORTED", text="WAL works best with smaller transactions"),
            g("c2", (40, 60), "SUPPORTED", text="WAL works best with smaller transactions too")]
    preds = [p(None, "SUPPORTED", text="WAL works best with smaller transactions"), p((100, 120), "SUPPORTED", text="other")]
    m, via = align(gold, preds)
    assert m == [[0], []] and via == ["text", "none"]


def test_evidence_hit_any_vs_all():
    gold = g("c1", (0, 5), "SUPPORTED", evidence=[ev(0, 10, 20), ev(1, 0, 5)], mode="all")
    half = [p((0, 5), "SUPPORTED", cits=[ev(0, 15, 18)])]
    full = [p((0, 5), "SUPPORTED", cits=[ev(0, 15, 18), ev(1, 2, 3)])]
    assert not evidence_hit(half, [0], gold) and evidence_hit(full, [0], gold)
    assert evidence_hit(half, [0], dict(gold, evidence_mode="any"))


def test_score_and_aggregate_with_error_and_contestable():
    case = {"id": "k", "gold_claims": [g("c1", (0, 10), "SUPPORTED"), g("c2", (12, 20), "CONTRADICTED"),
                                       g("c3", (22, 30), "UNSUPPORTED", contestable=True)]}
    row = {"response": {"claims": [p((0, 10), "SUPPORTED"), p((12, 20), "SUPPORTED"), p((22, 30), "CONTRADICTED"),
                                   p((40, 50), "UNSUPPORTED")], "meta": {"llm_calls": 2}}, "error": None}
    k = score_case(case, row)
    a = aggregate([k])
    assert a["n_claims"] == 2 and a["accuracy"] == 0.5 and a["false_support"] == 1.0 and a["claim_precision"] == 0.75
    assert aggregate([k], include_contestable=True)["n_claims"] == 3
    failed = score_case(case, {"response": None, "error": "UpstreamError: x"})
    assert aggregate([failed])["accuracy"] == 0 and aggregate([failed])["errors"] == 1
    assert {c["pred"] for c in failed["claims"]} == {"MISSING"}
    assert paired_diff([k], [k])[0] == 0


def test_run_reports_an_out_dir_outside_the_repo(tmp_path):
    from bench.run import ROOT, _shown
    assert _shown(ROOT / "bench" / "runs" / "x.jsonl") == "bench/runs/x.jsonl"
    assert _shown(tmp_path / "x.jsonl") == str(tmp_path / "x.jsonl")
