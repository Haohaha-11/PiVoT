# Annotation guideline

This guideline defines the gold labels in `data/dev.jsonl`, `data/test.jsonl` and `data/test2.jsonl`. It was
written before the test split was labelled and is the reference for every disputed case.

**Revision 2** was made after test-1 was frozen and evaluated, and before test-2 was built. It adds the two
clarifications marked *(rev 2)* below. Test-1 labels were not changed. The test-1 claim that this revision
re-decides is listed in `bench/results/test_failure_analysis.md`.

## 1. Claims

A gold claim is **one checkable fact** taken from the answer.

- Split coordinated facts ("X and Y", "X, which Y", "X; Y") into separate claims.
- Resolve pronouns so the claim reads on its own ("it uses two files" -> "WAL mode uses two files").
- Keep conditions and qualifiers that the answer states ("by default", "since 7.0", "for large datasets").
- Do not add anything the answer does not say.
- Skip text with no checkable content (greetings, offers to help, restated questions).
- *(rev 2)* Recommendations, advice and evaluations in the answer **are** claims ("keep transactions short", "a
  500-term limit is generous"). A user may act on them, so they need grounding just like facts. Label them by
  whether the passages make them.
- *(rev 2)* "Because X, Y" and "X, so Y" contain two claims: the premise X and the conclusion Y.
- `anchor` / `answer_span`: the shortest substring of the answer that expresses the claim. Two claims
  may share a span when the answer packs two facts into one phrase.

## 2. Verdicts

Judge each claim **against the provided passages only**. World knowledge never makes a claim supported.

| Verdict | Definition |
|---|---|
| SUPPORTED | Every part of the claim is entailed by the passages, possibly by combining several of them. |
| CONTRADICTED | If the passages are true, the claim must be false. |
| UNSUPPORTED | Neither entailed nor contradicted. This includes facts that are true in the real world but absent from the passages. |

### Allowed inference (counts as entailment)

- Paraphrase and synonyms.
- Counting ("three policies" when three are listed).
- Simple arithmetic and unit conversion on numbers in the passages (`30 * 10 = 300 s`, `200M / 2B = 10%`).
- Combining facts from several passages.
- Version-range containment ("since 2.4" entails "2.6 can").
- Date differences.
- Contrapositive of a stated condition ("only if Y" entails "not Y -> not X").
- Weakening ("always" entails "can"; "all" entails "some").

### Contradiction

The claim is incompatible with what the passages state. Typical forms:

- a different number, version, unit, name, or default for the same thing;
- a negation;
- a reversed comparison;
- an "always" or "never" claim that ignores an exception the passages state;
- an older statement that a later passage updates;
- the converse of an "only if" when another passage gives a counterexample.

### Not entailed and not contradicted (UNSUPPORTED)

- Extrinsic facts, even if true.
- An attribute the passages state for a different entity, without excluding this one.
- The converse of an "only if" with no counterexample in the passages.
- A sufficiency claim the passages do not make ("checking X is enough").
- Added specificity ("exactly 1000" for "about 1000").
- An invalid transitive comparison.
- A reason the passages do not give. A reason the passages explicitly deny makes the claim CONTRADICTED.
- The other side of a version boundary: "since 4.0, X" says nothing about versions before 4.0, and "before 9.1, Y"
  says nothing about what 9.1 introduced. These claims are UNSUPPORTED and contestable.
- A rule the passages state for a narrower scope (for example "built-in gRPC probes") applied to everything.
- Advice the passages do not give ("keep transactions short"). This is UNSUPPORTED and not contestable. A
  recommendation that plausibly follows from the passages is UNSUPPORTED and contestable.

### Strengthening (rule A, adopted)

A claim that is **stronger than the passage** about the same statement ("typical" -> "required",
"will try hard to" -> "never has to wait", "very safe" -> "loses nothing in any scenario", *(rev 2)*
"should" / "SHOULD" -> "must" / "MUST", "can ensure" -> "ensures") is
**UNSUPPORTED** unless the passages state an exception that makes the stronger claim false (then
CONTRADICTED).

The alternative reading (rule B: the passage's weaker wording itself refutes the stronger claim)
is reasonable, and models often follow it. Claims whose label differs under A and B are marked
`contestable: true`.

### Dropped default

A claim that describes default behaviour without saying "by default" is SUPPORTED when that is
clearly the behaviour the passage describes. It is UNSUPPORTED when the claim makes it unconditional
("always", "cannot be changed"). Borderline cases are marked `contestable`.

## 3. Evidence

For SUPPORTED and CONTRADICTED claims, gold evidence lists the minimal passage quotes needed.

- `evidence_mode: "all"`: the claim needs every quote, as in multi-passage synthesis.
- `evidence_mode: "any"`: each quote alone suffices.

UNSUPPORTED claims have no evidence.

## 4. Contestable claims

`contestable: true` marks a claim where a careful second annotator could reasonably disagree. Examples: rule A/B
cases, dropped defaults, recommendations derived from the passages, the other side of a version boundary, and
mechanisms that explain a stated effect. Headline metrics exclude contestable
claims; the report also gives the numbers with them included.

## 5. Process

1. Draft labels with this guideline.
2. Run `python data/build.py`, which rejects any non-verbatim quote, any anchor that is not in the
   answer, and any evidence or verdict inconsistency.
3. Review every claim on which the pilot models disagree with the gold label, and re-adjudicate
   **by this guideline**, not by model majority. Changes are logged in the case's `note`.
4. Freeze the test split. `data/MANIFEST.json` records its sha256. No prompt or pipeline change is
   made after looking at test results.
