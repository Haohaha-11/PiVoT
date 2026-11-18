Gold: 116 claims, S 85, C 21, U 10. Always-SUPPORTED reference: acc 0.73, macro-F1 0.28

## Oracle mode (gold claims given; tests judgment only)

| model | acc | macro-F1 | recall S/C/U | false-support | false-alarm | evidence hit | quote valid | unusable (unwrapped) | p50 s |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | 0.99 | 0.97 | 1.00/1.00/0.90 | 0.00 | 0.00 | 0.96 | 1.00 (125) | 0 (0) | 19.7 |
| deepseek-v4.1-flash@nothink | 0.95 | 0.89 | 0.98/0.90/0.80 | 0.03 | 0.02 | 0.96 | 1.00 (125) | 0 (0) | 7.0 |
| glm-5.3 | 1.00 | 1.00 | 1.00/1.00/1.00 | 0.00 | 0.00 | 0.99 | 1.00 (134) | 0 (0) | 45.3 |
| kimi-k3 | 0.99 | 0.97 | 1.00/1.00/0.90 | 0.00 | 0.00 | 0.96 | 1.00 (128) | 0 (3) | 49.4 |
| kimi-k3@nothink | 0.95 | 0.88 | 0.98/0.90/0.80 | 0.03 | 0.02 | 0.96 | 1.00 (124) | 0 (0) | 22.3 |
| qwen3.8-flash | 0.95 | 0.87 | 0.98/0.90/0.80 | 0.00 | 0.02 | 0.82 | 0.81 (117) | 0 (0) | 17.9 |
| qwen3.8-flash@think | 0.97 | 0.91 | 0.98/1.00/0.80 | 0.00 | 0.02 | 0.97 | 1.00 (131) | 0 (0) | 75.3 |
| qwen3.8-max | 0.91 | 0.83 | 0.93/0.90/0.80 | 0.00 | 0.07 | 0.97 | 0.99 (112) | 0 (0) | 19.9 |
| qwen3.8-max@think | 0.95 | 0.89 | 0.95/0.95/0.90 | 0.00 | 0.05 | 1.00 | 1.00 (127) | 0 (0) | 170.9 |

## End-to-end mode (model decomposes; greedy Dice alignment)

| model | strict acc* | macro-F1* | claim recall | claim precision | #pred/#gold | false-support* | answer-level acc | quote valid | invariant viol. | spurious on no-claim case | p50 s | tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | 0.95 | 0.94 | 0.98 | 0.80 | 142/116 | 0.06 | 1.00 | 1.00 (145) | 0 | 0 | 41.5 | 94170 |
| deepseek-v4.1-flash@nothink | 0.88 | 0.87 | 0.93 | 0.91 | 119/116 | 0.03 | 1.00 | 1.00 (123) | 0 | 0 | 7.2 | 27707 |
| glm-5.3 | 0.79 | 0.85 | 0.81 | 0.91 | 103/116 | 0.00 | 0.82 | 1.00 (118) | 0 | 0 | 149.1 | 106618 |
| kimi-k3 | 0.93 | 0.93 | 0.95 | 0.91 | 121/116 | 0.00 | 1.00 | 1.00 (138) | 0 | 0 | 67.8 | 55653 |
| kimi-k3@nothink | 0.82 | 0.84 | 0.87 | 0.92 | 110/116 | 0.00 | 1.00 | 0.99 (116) | 0 | 0 | 24.2 | 27993 |
| qwen3.8-flash | 0.86 | 0.83 | 0.94 | 0.90 | 121/116 | 0.03 | 1.00 | 0.90 (122) | 2 | 0 | 19.2 | 33304 |
| qwen3.8-flash@think | 0.91 | 0.83 | 0.98 | 0.77 | 149/116 | 0.06 | 1.00 | 0.98 (163) | 0 | 0 | 114.3 | 122004 |
| qwen3.8-max | 0.88 | 0.81 | 0.97 | 0.88 | 128/116 | 0.00 | 1.00 | 0.99 (124) | 0 | 0 | 21.3 | 27827 |
| qwen3.8-max@think | 0.96 | 0.92 | 0.98 | 0.72 | 159/116 | 0.00 | 1.00 | 1.00 (172) | 0 | 0 | 206.1 | 167539 |

\* over gold claims; an unmatched gold claim counts as wrong.

## Oracle accuracy by perturbation type

| type | deepseek-v4.1-flash | deepseek-v4.1-flash@nothink | glm-5.3 | kimi-k3 | kimi-k3@nothink | qwen3.8-flash | qwen3.8-flash@think | qwen3.8-max | qwen3.8-max@think |
|---|---|---|---|---|---|---|---|---|---|
| arithmetic | 4/4 | 4/4 | 4/4 | 4/4 | 2/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| arithmetic_error | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 |
| arithmetic_multi_hop | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 | 1/3 | 3/3 |
| case_confusion | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| condition_reasoning | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 |
| contrapositive | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| converse_of_only_if | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| converse_refuted | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 |
| exception_ignored | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 6/7 |
| extrinsic_plausible | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 |
| extrinsic_true | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| fabricated_detail | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| inference_modality_weak | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| instantiation | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 |
| invalid_transitive | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| light_inference | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 | 2/2 |
| modality_strengthening | 2/2 | 1/2 | 2/2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 |
| modality_weakening | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| multi_hop_necessity | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| multi_hop_refutation | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| near_miss_number | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| near_verbatim | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| negation_flip | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| paraphrase | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 | 51/54 |
| quantifier_change | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| reason_substitution | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| reversed_comparison | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| sufficiency_overclaim | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 |
| temporal_arithmetic | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 |
| temporal_update | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| version_range_entailed | 2/2 | 1/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 | 1/2 | 2/2 |
