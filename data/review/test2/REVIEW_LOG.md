# Test-2 split: label review log

Test-2 (`data/test2.jsonl`, spec `data/spec_test2.py`) was built after test-1 had been evaluated and analysed,
under guideline revision 2. Its two documentation families (git gc, HTTP caching RFC 9111) are used by no other
split. The labels were reviewed with the same four steps as test-1 and frozen (`data/MANIFEST.json`, `test2_frozen`)
**before any verifier configuration was run on it**. pivot-v4 was written during the review. Until the freeze it
ran only on dev.

## Who did what

| Step | Annotator | What it saw | Outcome |
|---|---|---|---|
| 1. Draft | Claude (the author's coding assistant) | guideline, passages, answers | 131 claims |
| 2. Independent-model audit | qwen3.8-max, kimi-k3 (minimal prompt, oracle mode) | passages, claim texts | agreement with draft 0.962 / 0.969. 6 disagreements: no label changed; 2 claims marked contestable; 1 note corrected ([audit.md](audit.md)) |
| 3. Second review | a separate Claude agent | guideline + full review file (gold included) | 32 issues (16 clear, 16 debatable) ([second_review.md](second_review.md)); see below |
| 2b. Audit of the final labels | same two models, same prompt | passages, claim texts | 0.950 / 0.957. All 7 disagreements are on contestable claims ([audit_final.md](audit_final.md)) |
| 4. Blind agreement | (a) a Claude Sonnet agent; (b) deepseek-v4.1-flash via `data/annotate.py` | guideline, passages, answer, claim text; **no gold** | see below |

Steps 2 and 3 ran in parallel on the same draft. The second reviewer's file predates the step-2 edits, which it
marks as "already in current spec". The audit was re-run on the final labels (step 2b) because step 3 added ten
claims. In step 2b one kimi-k3 call returned the degenerate output `[1]` and another `[0]`. Those two cases were
re-run once and are marked in the run file.

### Second review: what was applied

- **Evidence:** 11 fixes. Three quotes had been cut just before a curly apostrophe (U+2019) and lost the words the
  claim needs. Two `mode` fields changed from any to all, header sentences were added so quoted defaults are tied to
  their setting, and `git_gc:15` was inserted before its continuation paragraph `git_gc:16` in two cases, since that
  paragraph's "this" otherwise has no referent.
- **Decomposition** (guideline rev 2): split 6 compound claims ("X, which Y", "Because X, Y", "X, so Y",
  "X; Y and Z"). Added 3 missing claims: two premises of "Because / Since X, Y" and one evaluation ("the main risk
  is ..."). New claims are appended to the end of their case, so earlier claim ids are unchanged.
- **Labels:** 1 change, http-caching-natural c2 S -> U (contestable), "not likely to change" -> "will not change"
  (rule A).
- **Contestable flags:** 9 more, for dropped hedges ("might be", "seems to be"), restored qualifiers ("specifically",
  "to the origin"), a widened scope ("that create objects" dropped), and the proxy-revalidate permission claim.
- **Not applied:** "private (browser) cache" as a separate extrinsic claim (a parenthetical gloss, not an
  assertion); splitting the s-maxage claim (the qualifier "specifically" was restored instead); relabelling
  git-gc-natural c5 to S (both audit models agree with U; the note was corrected instead).

Every change is recorded in the affected claim's `note` field. Notes prefixed with "Second review:" come from step 3.

## Blind agreement (step 4)

The stratified sample has 40 non-contestable claims: 12 C, all 7 non-contestable U, and 21 S (seed 7). It was drawn
from the final labels, after steps 2, 3 and 2b.

| Second annotator | Raw agreement | Cohen's kappa |
|---|---|---|
| Claude Sonnet agent | 40 / 40 | 1.00 |
| deepseek-v4.1-flash | 39 / 40 | 0.96 |

The one disagreement is **git-gc-distortion c6**, "If gc.log exists, git gc --auto prints its content instead of
running". Gold says S and deepseek says C, because the passage gives an exception: the file is ignored once it is
older than gc.logExpiry. The answer states that exception in the same sentence, and the gold keeps it as a separate
claim, c8. As written, c6 drops a condition that the answer states (guideline §1). This is a real, minor
decomposition flaw. **It was not changed:** deepseek-v4.1-flash is the verifier's base model, and its labels are
used only to measure agreement, never to change gold. This is the same policy as for test-1.

### Caveats

- **The annotators are LLMs, not people.**
- **The step-2b agreement is not independent evidence.** Several contestable flags were set *because* the audit
  models disagreed, so the 100% agreement on non-contestable claims in step 2b is partly by construction. The blind
  sample (step 4) is the independent check.
- Headline metrics exclude contestable claims (16 of 141) by design.

## Final test-2 split

11 cases and 141 gold claims: S 112, C 16, U 13. 41 are reasoning claims and 16 are contestable, leaving 125
non-contestable claims. Frozen; sha256 in `data/MANIFEST.json`.
