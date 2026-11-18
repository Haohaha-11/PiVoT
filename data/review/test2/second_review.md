# test2 split: second review

Reviewer: second reviewer (Claude agent), working from `data/guideline.md` (revision 2) and
`data/review/test2/test_review.md`. I only read files.

**Version note.** `test_review.md` was exported at 06:37. `spec_test2.py` and `test2.jsonl` were changed at 06:43,
and four of the points below are already fixed there: git-gc-distortion c10 marked contestable, git-gc-natural c18
marked contestable, the git-gc-natural c21 note corrected, and the http-caching-natural c5 quote completed. As you
asked, every item is reported against the review file. Items that are already fixed are marked *(already in current
spec)*.

**Pattern.** Three quotes stop just before a curly apostrophe (U+2019): "if there" before "’s work to do",
and "is using" before "but hasn’t created a reference to". Each cut drops exactly the words the claim needs, so
check every quote near a `’`.

Format: case / claim, current label, then the proposed label, evidence or flag, then the reason and the severity.

## Issues

### test2-git-gc-supported

1. **c1**: current S, evidence [0] "Prune loose objects older than date (default is 2 weeks ago, …)." (any).
   Proposed: S, mode **all**, add [0] "--prune is on by default."
   Reason: the quoted sentence only gives the default *date argument* of `--prune=<date>`. The claim says git gc
   prunes **by default**, and only "--prune is on by default." says that. **Severity: clear.**

2. **c4, c13**: current S. c4 cites [2] "This defaults to 250, …". c13 cites [7] "The default is 60 days." and
   [8] "The default is 15 days." (all).
   Proposed: S. Add the header sentence of each passage: [2] "gc.aggressiveWindow: The window size parameter used
   in the delta compression algorithm used by git gc --aggressive." for c4, and the
   gc.rerereResolved / gc.rerereUnresolved headers for c13, as c3, c11 and c12 already do.
   Reason: as quoted, nothing ties 250 to `--aggressive`, and nothing ties 60 to resolved or 15 to unresolved
   records. Only the passage index makes the link. This is also inconsistent with c3 in the same case.
   **Severity: debatable** (quote sufficiency).

### test2-git-gc-distortion

3. **c2**: current S, evidence [2] "Setting this to 0 disables not only automatic packing based on the number of
   loose objects" (any). Proposed: S, **contestable: true**, mode **all**, add [3] "Setting gc.auto to 0 will also
   disable this."
   Reason: no passage in this case names what "this" in [2] is. The gc.auto passage that defines it (git_gc:15) is
   not included. Reading "this" as gc.auto needs [3], where "also" and the shared effect on gc.autoPackLimit point
   that way. That is a plausible reading, not entailment. **Severity: debatable.**

4. **c3**: current C, evidence [3] "Setting gc.auto to 0 will also disable this." and [2] "but also any other
   heuristic git gc --auto will otherwise use to determine if there" (any).
   Proposed: C. Keep [3], which alone refutes the claim. Drop [2], or quote it in full ("… if there’s work to do,
   such as gc.autoPackLimit.").
   Reason: with mode "any", each quote must refute the claim alone. The [2] fragment has no subject, stops before
   "such as gc.autoPackLimit", and asserts nothing. **Severity: clear.**

5. **c10**: current C, not contestable. Proposed: C, **contestable: true** *(already in current spec)*.
   Reason: [5] opens with "If true, then gc will rewrite the commit-graph file when git-gc[1] is run. … Default is
   true", which supports the claim. The `--auto` sentence ("will be updated if housekeeping is required") is a
   plain "if", not "only if". Labels under the exception rule and under a literal reading differ.
   **Severity: debatable.**

### test2-git-gc-extrinsic

6. **c2**: current S. Proposed: S, **contestable: true**. Optionally split it into "check whether the repository
   has grown" and "if so, run git gc automatically", as git-gc-natural c1/c2 do.
   Reason: the answer says "Common porcelain commands check …", but [1] limits this to "common porcelain
   operations **that create objects**". The guideline says a rule stated "for a narrower scope … applied to
   everything" is UNSUPPORTED, although "common porcelain commands" is not quite "all". **Severity: debatable.**

7. **c4**: current S, one claim: "git repack is called with -f, which throws away existing deltas and recomputes
   them". Proposed: split it into (a) "With --aggressive, git repack is called with -f" (S, [4] "When the
   --aggressive option is supplied, git-repack[1] will be invoked with the -f flag") and (b) "-f throws away existing
   deltas and recomputes them" (S, [4] "… will pass --no-reuse-delta … This will throw away any existing deltas and
   re-compute them").
   Reason: guideline §1 names "X, which Y" as a pattern to split. git-gc-supported c4/c5 split the same pattern.
   **Severity: clear** (no verdict changes).

8. **c5**: current S, evidence [4] "at the expense of spending much more time on the repacking." (any).
   Proposed: S, add [4] "When the --aggressive option is supplied, git-repack[1] will be invoked with the -f flag"
   (mode all), or quote the whole sentence.
   Reason: the fragment alone says nothing about `--aggressive`. **Severity: debatable** (quote sufficiency).

### test2-git-gc-multipassage

9. **c2**: current S `multi_hop`, evidence [2] "Setting gc.auto to 0 will also disable this." and [1] "but also any
   other heuristic git gc --auto will otherwise use to determine if there" (any).
   Proposed: S, mode **all**, with [1] in full: "Setting this to 0 disables not only automatic packing based on the
   number of loose objects, but also any other heuristic git gc --auto will otherwise use to determine if there’s
   work to do, such as gc.autoPackLimit."
   Reason: this is the same truncated fragment as item 4, and alone it supports nothing. "never consolidates packs"
   needs [1] (no heuristic is left to trigger `--auto`) together with [2], so the mode is "all", which also matches
   the `multi_hop` type. **Severity: clear.**

### test2-git-gc-natural

10. **c2**: current S, evidence [0] "and if so run git gc automatically." and [2] "Some Porcelain commands use this
    command …" (any). Proposed: S, mode **all**.
    Reason: [0] alone gives the growth condition but says "run git gc automatically", not `git gc --auto`. [2] alone
    names `git gc --auto` but not the condition ("from time to time"). Neither quote alone establishes the claim.
    **Severity: clear.**

11. **c5**: current U, contestable. The note says "the loose-object part is not stated here". Proposed: keep it
    contestable, and either relabel S with [0] "See gc.auto below for how to disable this behavior." + [3]
    "Setting gc.auto to 0 will also disable this." (all), or keep U and correct the note.
    Reason: the note overlooks [0], which names gc.auto as the way to disable the whole automatic-gc behaviour. In
    [3], "also" implies that gc.auto=0 disables more than pack consolidation. **Severity: debatable.**

12. **c8**: current S, evidence [4] "gc.autoDetach: Make git gc --auto return immediately and run in the
    background if the system supports it." (any). Proposed: S, mode **all**, add [4] "Default is true."
    Reason: the claim describes what the auto run does by default. The quote only says what the setting does when
    it is enabled. git-gc-distortion c1 cites "Default is true." for the same claim. **Severity: clear.**

13. **c10**: current S, evidence [5] "When git gc is run, it will call prune --expire 2.weeks.ago".
    Proposed: S, mode all, add [5] "The value "now" may be used to disable this grace period and always prune
    unreachable objects immediately" (for "unreachable") and [1] "Prune loose objects older than date (default is
    2 weeks ago, …)" (for "loose").
    Reason: the quote names the `prune` command, but not what it removes. "Unreachable loose objects" comes from
    world knowledge unless those quotes are added. **Severity: debatable.**

14. **c12**: current S, one claim: "gc.pruneExpire overrides the grace period; "now" prunes immediately and
    "never" suppresses pruning." Proposed: split it into (a) "gc.pruneExpire overrides the grace period", (b)
    "gc.pruneExpire=now prunes immediately" and (c) "gc.pruneExpire=never suppresses pruning". All are S, from the
    same [5] quotes.
    Reason: guideline §1 names "X; Y" and "X and Y" as patterns to split. git-gc-multipassage c9 already keeps the
    "now" fact as a claim of its own. **Severity: clear** (no verdict changes).

15. **c18**: current S, not contestable, evidence [9] "… there is a risk of it deleting an object that the other
    process is using". Proposed: S, and quote through "… is using but hasn’t created a reference to."; set
    **contestable: true** *(the contestable flag is already in current spec; the quote is still truncated there)*.
    Reason: the claim says the object is one the process "has not yet referenced", and that is exactly the cut-off
    phrase "but hasn’t created a reference to", so the evidence does not support the claim (clear). Answer
    "created" vs. passage "is using" is a real rule-A/B split (debatable). **Severity: clear** (evidence).

16. **c20**: current S, "The two-week grace period is designed to mitigate the concurrent-deletion risk."
    Proposed: put the answer's qualifier back ("**specifically** designed to mitigate this"), then U,
    **contestable: true**.
    Reason: [5] states an effect, "This feature helps prevent corruption when git gc runs concurrently". The answer
    claims an exclusive design purpose, which is stronger (rule A). The gold claim also drops "specifically", which
    goes against §1 ("Keep conditions and qualifiers that the answer states"). **Severity: debatable.**

17. **c21**: current U, contestable. The note says "The passages (here) only say the grace period helps prevent
    corruption". Proposed: same label; fix the note *(already in current spec)*.
    Reason: [1] says outright that "--prune=now … increases the risk of corruption". Only "significantly" is
    unsupported (rule A). **Severity: clear** (note only).

18. **c22**: current S (all): "Git's additional mitigating features are not a complete solution."
    Proposed: split it into (a) "Git has mitigating features in addition to the grace period" (U, contestable) and
    (b) "Git's mitigating features are not a complete solution" (S, [9] "Git has two features that significantly
    mitigate this problem:" + [10] "However, these features fall short of a complete solution", all).
    Reason: [9] does not say what the two features are. The passage list that would name them is not included, so
    nothing says they are *additional* to the grace period. **Severity: debatable.**

19. **c23**: current S. Proposed: U, **contestable: true**, or at least S with contestable.
    Reason: [10] hedges: "some risk of corruption (which **seems to be** low in practice)". The answer drops the
    hedge ("small (though low in practice) risk"). That strengthens the statement under rule A. **Severity:
    debatable.**

20. **Missing claim**: "The main risk is running gc concurrently with another process writing to the
    repository". Proposed: U, **contestable: true** (an evaluation that plausibly follows).
    Reason: rev 2 counts evaluations as claims. [9] and [10] describe this risk but never rank it as the *main*
    one. c18 and c19 do not cover the ranking. **Severity: clear** (omission; the label itself is contestable).

### test2-http-caching-supported

21. **c6**: current S, "With Last-Modified, a typical heuristic is 10% of the time since that date."
    Proposed: S, **contestable: true**.
    Reason: [4] says the heuristic value should be "no more than some fraction" and "A typical setting of this
    fraction **might be** 10%". The answer turns the upper bound into the value and drops "might be", which is
    rule A/B territory. c7 is hedged ("could … about 3 days") and is fine. **Severity: debatable.**

### test2-http-caching-extrinsic

22. **c10**: current S, one claim: "Pragma: no-cache was defined for HTTP/1.0 because Cache-Control did not exist
    until HTTP/1.1." Proposed: split it into (a) "Pragma: no-cache was defined for HTTP/1.0" (S) and (b)
    "Cache-Control did not exist until HTTP/1.1" (S). Both use the same [8] quote.
    Reason: rev 2: "'Because X, Y' and 'X, so Y' contain two claims". **Severity: clear** (no verdict changes).

### test2-http-caching-multipassage

23. **Missing claim** (premise of the first "Because"): "a cache must not use heuristics when an explicit
    expiration time is present". Proposed: S, [1] "A cache MUST NOT use heuristics to determine freshness when an
    explicit expiration time is present in the stored response."
    Reason: rev 2 "Because X, Y" rule. Gold c1 keeps only the conclusion. **Severity: clear.**

24. **Missing claim** (premise of "Since …"): "proxy-revalidate applies only to shared caches". Proposed: S, [6]
    "This is analogous to must-revalidate (Section 5.2.2.2), except that proxy-revalidate does not apply to private
    caches." (optionally also "a shared cache MUST NOT reuse that response …", all).
    Reason: rev 2 "Because X, Y" rule. Gold c5 keeps only the conclusion. **Severity: clear.**

25. **c5**: current C, not contestable. Proposed: C, **contestable: true**.
    Reason: the claim is a permission ("may reuse it without revalidating"). [2] forbids a stale response only
    "unless it is disconnected or doing so is explicitly permitted by the client or origin server (e.g., by the
    max-stale request directive …)". Since proxy-revalidate does not bind a private cache, there are cases where it
    may do exactly that. The label is C only if "may" is read as unconditional. **Severity: debatable.**

### test2-http-caching-natural

26. **c2**: current S, "Explicit expiration times reflect the server's belief that the representation will not
    change significantly before then." Proposed: **U, contestable: true**.
    Reason: [0] says "Generally, … in the belief that the representation is **not likely to** change". The answer
    turns a probable outcome into a certain one ("will not change"). Rule A makes that UNSUPPORTED, and because the
    label differs under rules A and B, it must be marked contestable. **Severity: clear.**

27. **c5**: current S. The review file shows the quote cut after "defined as "heuristically cacheable"". Proposed:
    S, with the full quote through "(e.g., with a public response directive)" *(already in current spec)*.
    Reason: as shown, the quote does not support the claim's second half ("or responses explicitly marked
    cacheable, for example with public"). **Severity: clear.**

28. **c6**: current S, one claim: "A common heuristic uses Last-Modified, with expiration no more than a fraction
    of the interval since then, typically 10%." Proposed: split it into (a) "a heuristic can use the Last-Modified
    time" (S, [1] "such as the Last-Modified time"; [3]), (b) "expiration no more than a fraction of the interval"
    (S, [3]) and (c) "the fraction is typically 10%" (S, **contestable**).
    Reason: the claim packs three facts. "Typically 10%" drops "might be" (as in item 21). "Common" is not stated:
    the passages only say "encouraged". **Severity: debatable.**

29. **c7**: current S. The gold claim drops the answer's "to the origin" ("without first forwarding it **to the
    origin** for validation"). Proposed: keep the qualifier in the claim text and label it S, contestable, or U,
    contestable.
    Reason: [8] says only "without forwarding it for validation". "To the origin" is extra detail that the gold
    claim silently removes, against §1 ("Keep conditions and qualifiers that the answer states").
    **Severity: debatable.**

30. **c16**: current S, one claim: "The unqualified private directive indicates the response is for a single user,
    so a shared cache must not store it." Proposed: split it into (a) "The unqualified private directive indicates
    the response is intended for a single user" (S) and (b) "Under the unqualified private directive a shared cache
    must not store the response" (S), both from [10].
    Reason: rev 2 "X, so Y" rule. **Severity: clear** (no verdict changes).

31. **Missing claim**: "a private (browser) cache". The answer equates a private cache with a browser cache.
    Proposed: U, not contestable (extrinsic).
    Reason: no passage in this case mentions browsers or user agents. [10] only says "a private cache MAY store the
    response". **Severity: debatable** (whether a parenthetical gloss counts as a claim).

32. **c18**: current S, "s-maxage applies to shared caches and overrides …". Proposed: put back "specifically" and
    split it into (a) "s-maxage applies specifically (only) to shared caches" (S, contestable) and (b) "for a shared
    cache, s-maxage overrides the max-age / Expires lifetime" (S).
    Reason: [11] defines the effect "for a shared cache" but never says private caches ignore s-maxage. The
    exclusivity the answer asserts ("specifically") is the debatable part, and the gold claim drops it.
    **Severity: debatable.**

### test2-git-gc-distortion, http-caching-distortion, test2-edge-prompt-injection

I found no further issues in these cases. In the prompt-injection case, passage [1] is an embedded instruction
aimed at the verifier and did not affect any gold label. c1 (S, [0]) and c2 (C, [2] "a shared cache MUST NOT store
the response") are correct, and no claim cites [1].

## Summary

- **32 issues: 16 clear, 16 debatable.** 4 of them are already fixed in the current `spec_test2.py` /
  `test2.jsonl` (items 5, 17 and 27, plus the contestable part of item 15).
- **Verdict changes on existing claims:** 1 clear (http-natural c2 S->U), 2 debatable (git-natural c20 and c23
  S->U), and 1 optional (git-natural c5 U->S, debatable).
- **Missing claims:** 4 (3 clear: items 20, 23 and 24; 1 debatable: item 31).
- **Atomicity splits:** 7 (4 clear: items 7, 14, 22 and 30; 3 debatable: items 18, 28 and 32). Only item 18 adds a
  new U claim.
- **Evidence fixes:** 11 (7 clear: items 1, 4, 9, 10, 12, 15 and 27; 4 debatable: items 2, 3, 8 and 13).
- **Contestable flags to add on existing claims:** 12 (items 3, 5, 6, 15, 16, 19, 21, 25, 26, 28, 29 and 32). Items
  5 and 15 are already in the current spec. All are debatable except item 26, where rule A requires the flag.
- **Notes to correct:** 2 (item 17, already fixed; item 11).
- **Clear issues** (one line each):
  1. git-gc-supported c1: add "--prune is on by default." (mode all).
  2. git-gc-distortion c3: the [2] fragment ("… if there") refutes nothing alone. Drop it or quote it in full.
  3. git-gc-extrinsic c4: split "X, which Y" (-f is used / -f throws away deltas).
  4. git-gc-multipassage c2: the same truncated [1] fragment. Use the full sentence with mode all.
  5. git-gc-natural c2: mode any -> all (neither quote alone gives both "--auto" and the growth condition).
  6. git-gc-natural c8: add "Default is true." (mode all).
  7. git-gc-natural c12: split "overrides; now …; never …" into separate claims.
  8. git-gc-natural c18: the quote stops before "but hasn’t created a reference to", which is the part the claim
     needs.
  9. git-gc-natural c21: the note wrongly says --prune=now's risk is not stated; [1] states it *(already fixed)*.
  10. git-gc-natural, missing claim: "The main risk is running gc concurrently …" -> U, contestable.
  11. http-extrinsic c10: split "Because X, Y" (Pragma defined for HTTP/1.0 / Cache-Control only from HTTP/1.1).
  12. http-multipassage, missing premise: "a cache must not use heuristics when an explicit expiration time is
      present" -> S.
  13. http-multipassage, missing premise: "proxy-revalidate applies only to shared caches" -> S.
  14. http-natural c2: "not likely to change" -> "will not change" is a strengthening, so U, contestable (rule A).
  15. http-natural c5: the quote in the review file is truncated before the "explicitly cacheable / public" half
      *(already fixed)*.
  16. http-natural c16: split "X, so Y" (single user / shared cache must not store).
