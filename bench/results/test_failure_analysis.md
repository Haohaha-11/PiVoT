# Test split: failure analysis

PiVoT is the optimized pipeline (benchmark config `pivot`, prompt version pivot-v3; earlier called "pointer"). This analysis covers 3 independent repeats of the frozen test split (23 cases, 255 non-contestable claims) with
deepseek-v4.1-flash. It was written after the final runs. **Nothing in the evaluated system (pivot-v3) was changed after
these runs.** pivot-v4 was developed afterwards, on dev only, and evaluated on a new held-out split; see [v4_report.md](v4_report.md).

## Headline

| config | claim acc (mean ± std) | output tokens | p50 / p95 latency |
|---|---|---|---|
| lexical | 0.192 | 0 | 0 s |
| minimal, thinking off | 0.898 ± 0.010 | 1.2k | 7 s / 12 s |
| minimal, provider-default thinking | **0.959 ± 0.011** | 6.5k | 34 s / 79 s |
| PiVoT (optimized) | 0.953 ± 0.017 | **2.6k** | **15 s / 50 s** |

Paired, case-level bootstrap, per repeat:

- **PiVoT vs minimal (thinking):** −0.020, +0.008, −0.008. The difference is not significant in any repeat; the two are tied.
- **PiVoT vs minimal (no thinking):** +0.027, +0.075, +0.063. Significant in 2 of 3 repeats.

On the dev split the same comparison was +0.007 (tie) and +0.059 (significant). The ranking held on unseen
documentation families, but PiVoT's small dev edge over minimal-with-thinking did not carry over. That is
consistent with dev having been used for development.

**Conclusion:** the optimized pipeline matches a thinking model's accuracy at about 40% of its output tokens
and 43% of its median latency. It does not beat it.

## Where PiVoT loses (18 distinct claims, 36 errors over 3 repeats)

1. **Claim-extraction scope (5 claims, all MISSING).** PiVoT's prompt skips text "with no factual content".
   It drops advice and evaluative phrases ("keep transactions short", "a real health endpoint better reflects
   application state", "a 500-term limit is generous") that the gold includes as claims. This is a definition
   mismatch more than a verification error. The guideline should say explicitly whether recommendations count
   as claims.
2. **Premise merged into conclusion (3 claims).** In "Because predicate locks never block, Serializable can never
   raise …", the gold splits the true premise (S) from the false conclusion (C). PiVoT keeps one C claim, so the
   S premise is scored wrong. This is the merge penalty working as designed.
3. **A near-miss version slipped past the deterministic trigger (1 claim, 3/3 repeats).** "Capped with
   SQLITE_LIMIT_SCHEMA since 3.45.0": 3.45.0 does occur in another cited sentence, about the page-count default,
   so `number_not_in_evidence` did not fire. The claim was never escalated and was judged SUPPORTED. The trigger
   checks whether the number appears in any cited sentence, not whether it appears in the sentence that states
   the fact.
4. **Rule A applied more strictly than the gold (1 claim, 3/3).** "You must use initialDelaySeconds or a startup
   probe to delay readiness" versus the passage's "you should use". PiVoT calls must-for-should a
   strengthening (U). The gold says S. Under the guideline's own rule A, PiVoT's reading is defensible. **This
   gold label is probably inconsistent.** It is left unchanged because the split is frozen, and recorded here.
5. **Light inference and multi-hop (3 claims).** "16 default databases means the DB > 63 exception never
   applies" (U instead of S). "Requesting Read Uncommitted never sees uncommitted data" (C instead of S; the model
   applied the standard's definition of Read Uncommitted rather than the passage).

## Where minimal loses (21 distinct claims, 31 errors)

- **Most errors are MISSING** (20 of 31 are paraphrase claims). Minimal writes paraphrased claim texts that cannot be
  located in the answer. The text-similarity fallback then fails to align them, often on long natural answers.
  Its accuracy on matched claims is 0.987, versus 0.975 for PiVoT. Part of minimal's deficit is therefore an
  aligner artefact, not a judgment error.
- **Over-generation:** minimal's claim precision is 0.84, against 0.99 for PiVoT. It emits claims that match no gold claim.
- **Real judgment errors:** swapped startup-probe behaviour (C judged U, 3/3), a version range (S judged U), and a
  swapped feature-gate condition.

## Limitations this exposes

- The aligner cannot place paraphrased claims; a validated aligner, or span-anchored output from every system, would remove this noise.
- Repeats show non-trivial run-to-run variance from thinking: PiVoT's std is 0.017 and its p95 latency std is 25 s.
  Single-run comparisons of one or two points are not meaningful at this size.
- The test split has 255 headline claims. Effects under about 3 points cannot be resolved.
