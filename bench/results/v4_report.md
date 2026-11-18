# PiVoT v4: development on dev, evaluation on a new held-out split

PiVoT is the optimized pipeline. The model points at sentence IDs, and code slices the quotes, derives the verdicts
and evaluates arithmetic, version and date checks. Benchmark configs: `pivot-v3`, which is identical to `pivot`, the
version evaluated on test-1, and `pivot-v4`. Model: deepseek-v4.1-flash throughout. Every number is mean ± std over
3 independent repeats, each with its own LLM cache. Contestable gold claims are excluded unless stated.

## Summary

- **v4 changes three things**, each motivated by the [test-1 failure analysis](test_failure_analysis.md). It was
  developed on dev only, and v3's prompts are byte-identical to the evaluated version (pinned by a hash test).
- **Test-2 is a new held-out split**: 2 documentation families no other split uses, 141 claims, 125 of them
  non-contestable. Its labels were reviewed in four steps and frozen **before any system was run on it**
  ([review log](../../data/review/test2/REVIEW_LOG.md)).
- **On test-2, v4 ties v3:** −0.3 points (paired deltas +0.000, +0.008, −0.016), at **+44% output tokens**.
- **Both PiVoT versions beat minimal with thinking on test-2**, by +2.7 (v3) and +2.4 (v4) points, significant in 2 of
  3 repeats each. They use 31% (v3) and 44% (v4) of minimal's output tokens, and under half its median latency. On
  test-1 the same comparison was a tie.
- **On test-1, post hoc, v4 is +2.1 points over v3.** This is expected, because v4 was designed against those
  failures. It shows the fixes do what they were meant to do. It is **not** evidence that they generalise; test-2 is.
- **Both versions are kept.** Choose with `VERIFIER_PIVOT_VERSION` (`pivot-v4` by default) or the bench configs.

## What v4 changes

| # | Change | test-1 failure it targets |
|---|---|---|
| a | **Number trigger.** A claim's numbers must occur in its *fact sentence*, the cited sentence with the most content-word overlap (numbers excluded). In v3 they could occur in any cited sentence. Otherwise the claim is escalated. | "SQLITE_LIMIT_SCHEMA since 3.45.0": 3.45.0 occurs in another cited sentence, so the claim was never escalated (3/3 wrong). |
| b | **Premise and conclusion are separate claims.** The first-pass and re-split prompts both say so. Claims with because / so / therefore / which means / hence / thus, of 8+ words, are re-split. | "Because predicate locks never block, Serializable can never raise …" was kept as one C claim, so the S premise scored wrong. |
| c | **Advice, recommendations and evaluations are claims** (guideline rev 2). Only greetings, offers of help and restated questions are skipped. The prompt examples are domain-neutral and come from no split. | 5 advice or evaluation claims skipped (MISSING). |

The escalation prompt, derivation, checks and alignment are unchanged.

## Order of events

1. Test-1 was frozen and evaluated with v3, and the failure analysis was written. Nothing was tuned on test-1.
2. Guideline revision 2 added the claim-scope and "Because X, Y" rules. Test-1 labels were not changed.
3. Test-2 was written (spec `data/spec_test2.py`). The independent-model audit, the second review and the blind
   agreement checks followed.
4. v4 was implemented while test-2 was under review, and **run on dev only**.
5. Test-2 was frozen (sha256 `6b70c28df26b3174`). All five configs were then run on it, 3 repeats each. **Nothing was
   changed after these runs.**
6. v4 was run on test-1 (post hoc, below).

The same author wrote test-2 and v4, and knew v4's design when writing test-2. The spec-then-freeze order prevents
tuning on test-2. It cannot remove that author bias, in either direction.

## Dev (31 cases, 288 non-contestable claims)

| config | claim acc | out tokens | escalated claims / run |
|---|---|---|---|
| pivot-v3 | 0.978 ± 0.004 | 2040 ± 55 | 103 |
| pivot-v4 | 0.983 ± 0.003 | 2238 ± 244 | 109 |

Paired delta v4 − v3 per repeat: +0.003 [−0.011, +0.018], +0.000 [−0.011, +0.009], +0.010 [−0.008, +0.030].
v4 is not significant on dev, which is close to saturated.
The v3 repeat 1 replayed the original dev cache: 64 of 64 calls were cache hits, and the outputs are identical to the
run made during development. Full table: [dev_v4.md](dev_v4.md).

## Test-2 (11 cases, 125 non-contestable claims)

| config | claim acc | acc incl. contestable | out tokens | p50 / p95 latency |
|---|---|---|---|---|
| lexical | 0.256 | 0.284 | 0 | 0 s |
| minimal, thinking off | 0.875 ± 0.005 | 0.839 | 1.3k | 6 s / 10 s |
| minimal, provider-default thinking | 0.952 ± 0.016 | 0.894 | 6.8k | 32 s / 61 s |
| **pivot-v3** | **0.979 ± 0.005** | 0.929 | **2.1k** | 15 s / 20 s |
| pivot-v4 | 0.976 ± 0.008 | **0.939** | 3.0k | 16 s / 30 s |

Paired accuracy difference, case-level bootstrap, per repeat:

| comparison | repeat 1 | repeat 2 | repeat 3 | mean |
|---|---|---|---|---|
| pivot-v3 − minimal | +0.008 [−0.027, +0.052] | **+0.040 [+0.008, +0.077]** | **+0.032 [+0.007, +0.069]** | +0.027 |
| pivot-v4 − minimal | +0.008 [−0.027, +0.052] | **+0.048 [+0.017, +0.086]** | +0.016 [−0.029, +0.066] | +0.024 |
| pivot-v4 − pivot-v3 | +0.000 | +0.008 [+0.000, +0.027] | −0.016 [−0.043, +0.000] | −0.003 |
| minimal-nothink − minimal | **−0.096 [−0.173, −0.026]** | −0.056 [−0.122, +0.018] | −0.080 [−0.164, +0.016] | −0.077 |

Accuracy by case category, mean over repeats:

| config | fully supported | subtle distortion | extrinsic | multi-passage | natural answer |
|---|---|---|---|---|---|
| minimal | 0.960 | 0.922 | 0.986 | 0.952 | 0.954 |
| pivot-v3 | 0.983 | 0.961 | 1.000 | 0.968 | 0.972 |
| pivot-v4 | 0.972 | 0.969 | 1.000 | 0.984 | 0.954 |

Full table: [test2_report.md](test2_report.md).

### Why v4 does not move the test-2 headline

- **Fix (c) works, but mostly lands on contestable claims.** In the HTTP natural answer, the closing evaluation
  ("these directives give fine-grained control …") was MISSING in 3 of 3 v3 repeats and correctly UNSUPPORTED in 3 of
  3 v4 repeats. git-gc-natural c5 went from SSS to USU. Under the guideline, an evaluation or recommendation that
  plausibly follows from the passages is contestable, so these claims count only in the "incl. contestable" column.
  There v4 is ahead, 0.939 vs 0.929.
- **Test-2 has few headline errors left to fix.** v3 makes about 2.6 errors per repeat on the 125 headline claims.
  The persistent ones are below, and v4 shares all of them.

### Errors left on test-2 (every LLM config)

1. **Rule and exception in one sentence, split by the gold (2 claims, ~3/3 for both versions).** "If gc.log exists,
   git gc --auto prints its content and exits with status 1 …, unless the file is older than gc.logExpiry".
   "gc.bigPackThreshold keeps every non-cruft pack above the limit, but it is ignored when …". The gold splits rule
   and exception into separate S claims. PiVoT judges the rule claim on its own, so the exception rule ("a claim
   that ignores a stated exception is refuted") makes it C. The blind annotator deepseek-v4.1-flash flagged the first
   of these as well. This is a tension between the decomposition rule and the exception rule in the guideline, not a
   verification error. It is recorded and left unchanged, because test-2 is frozen.
2. **An evaluation folded into its neighbour (1 claim, 3/3 MISSING for both).** "It is deliberately conservative
   about deletion, keeping anything referenced by …": both versions emit only the "keeps …" claim.

### Cost of v4

v4 escalates 38 to 43 claims per test-2 run, against 32 for v3 (+25%). The stricter number trigger (a) accounts for
most of this: `number_not_in_evidence` fires 16 to 17 times instead of 10. Re-splits rise from 1 to 3–5. One thinking
escalation in repeat 3 used 20,162 output tokens on a single case, which explains the ±822 spread. Latency was
measured while repeats ran concurrently, so treat it as indicative. Output tokens are the reliable cost measure.

## Test-1, post hoc (23 cases, 255 non-contestable claims)

**These numbers are biased in v4's favour**, because v4's changes were chosen from these failures. v3 and minimal are
the original frozen test-1 runs, copied unchanged.

| config | claim acc | out tokens |
|---|---|---|
| minimal, provider-default thinking | 0.959 ± 0.011 | 6.5k |
| pivot-v3 | 0.953 ± 0.017 | 2.6k |
| pivot-v4 | 0.974 ± 0.009 | 3.3k |

- **v4 − v3:** +0.035 [+0.003, +0.074], +0.024 [+0.003, +0.051], +0.004 [−0.021, +0.030]; mean +0.021.
- **v4 − minimal:** +0.016, +0.031, −0.004; mean +0.014; not significant.

v4 was better on 15 claims and worse on 4:

- **Targets hit.**
  - The advice and evaluation claims that v3 skipped are now extracted and labelled U: "Transactions should be kept
    short", "a real health endpoint better reflects …". Several other claims that v3 dropped in the PostgreSQL natural
    answer are now extracted too.
  - The premise "predicate locks never block" is now its own claim (CCC to SSS).
  - The near-miss version 3.45.0 is now escalated, but still judged S in 2 of 3 repeats (SSS to SCS).
- **New errors.**
  - "In the exec example /tmp/healthy exists only for the first 30 seconds" went from SSS to UUU.
  - Three single-repeat flips.

None of this was used to change v4. Full table: [test1_posthoc_v4.md](test1_posthoc_v4.md).

## Which version to use

Both stay. On held-out data they are equally accurate on headline claims, so the choice is about scope and cost.

- **pivot-v3:** about 30% fewer output tokens and a tighter p95. Use it when cost or latency matters.
- **pivot-v4:** better coverage of advice and evaluative statements, which a user may act on (+1.0 points with
  contestable claims included on test-2). It costs more escalations. It is the service default.

## Limitations

- Test-2 is small: 11 cases, 2 families, 125 headline claims. Differences under about 3 points cannot be resolved, and
  the v3/v4 comparison is a tie at this size, not proof that they are equivalent.
- All labels, including the blind second labels, come from LLM annotators (Claude agents, deepseek-v4.1-flash). No
  human has re-labelled yet.
- The author wrote test-2 after the test-1 analysis and knew v4's design (see "Order of events").
- Latency comes from runs under different concurrency.

## Files

- Runs: `bench/runs_dev/rep{1,2,3}`, `bench/runs_test2/rep{1,2,3}` and `bench/runs_test_posthoc/rep{1,2,3}`, with one
  LLM cache per repeat under `bench/cache_*`.
- Reports: [dev_v4.md](dev_v4.md), [test2_report.md](test2_report.md), [test1_posthoc_v4.md](test1_posthoc_v4.md).
- Data: `data/test2.jsonl`, `data/spec_test2.py`, `data/review/test2/`.
- Code: v4 is `PivotVerifier(version="pivot-v4")` in `verifier/pipelines.py`; the prompts are
  `verifier/prompts.py::PIVOT_PROMPTS`; the tests are `tests/test_v4.py`.

*Naming:* the pipeline was called "pointer" in earlier logs, caches and notes. It was renamed PiVoT. Run
directories and run labels were renamed with it, and the regenerated reports are numerically identical to the
originals.
