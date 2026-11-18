Gold: 53 claims, S 36, C 9, U 8. Always-SUPPORTED reference: acc 0.68, macro-F1 0.27

## Oracle mode (gold claims given; tests judgment only)

| model | acc | macro-F1 | recall S/C/U | false-support | false-alarm | evidence hit | quote valid | unusable | p50 s |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-flash-0731 | 1.00 | 1.00 | 1.00/1.00/1.00 | 0.00 | 0.00 | 0.98 | 0.98 (47) | 0 | 10.0 |
| kimi-k3 | 0.87 | 0.93 | 0.86/0.89/0.88 | 0.00 | 0.14 | 0.97 | 1.00 (39) | 1 | 18.1 |
| qwen3.6-35b-a3b | 0.98 | 0.98 | 0.97/1.00/1.00 | 0.00 | 0.03 | 0.93 | 0.93 (46) | 0 | 6.5 |
| qwen3.7-plus | 0.98 | 0.96 | 1.00/1.00/0.88 | 0.00 | 0.00 | 0.93 | 0.94 (50) | 0 | 13.3 |
| qwen3.8-flash | 1.00 | 1.00 | 1.00/1.00/1.00 | 0.00 | 0.00 | 0.89 | 0.90 (51) | 0 | 9.5 |
| qwen3.8-max | 1.00 | 1.00 | 1.00/1.00/1.00 | 0.00 | 0.00 | 1.00 | 1.00 (48) | 0 | 10.6 |

## End-to-end mode (model decomposes; greedy Dice alignment)

| model | strict acc* | macro-F1* | claim recall | claim precision | #pred/#gold | false-support* | answer-level acc | quote valid | invariant viol. | spurious on no-claim case | p50 s | tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-flash-0731 | 0.91 | 0.98 | 0.91 | 0.98 | 49/53 | 0.00 | 1.00 | 0.91 (45) | 0 | 0 | 10.2 | 18486 |
| kimi-k3 | 0.94 | 0.99 | 0.94 | 0.94 | 53/53 | 0.00 | 1.00 | 1.00 (51) | 0 | 0 | 18.9 | 18597 |
| qwen3.6-35b-a3b | 0.85 | 0.93 | 0.87 | 0.98 | 47/53 | 0.00 | 1.00 | 0.88 (42) | 0 | 0 | 5.8 | 13420 |
| qwen3.7-plus | 0.75 | 0.82 | 0.81 | 0.96 | 45/53 | 0.00 | 0.90 | 0.85 (41) | 0 | 2 | 13.2 | 12678 |
| qwen3.8-flash | 0.83 | 0.89 | 0.87 | 1.00 | 46/53 | 0.00 | 1.00 | 0.88 (43) | 0 | 0 | 11.0 | 13117 |
| qwen3.8-max | 0.94 | 0.99 | 0.94 | 0.94 | 53/53 | 0.00 | 1.00 | 0.98 (49) | 0 | 0 | 11.1 | 11808 |

\* over gold claims; an unmatched gold claim counts as wrong.

## Oracle accuracy by perturbation type

| type | deepseek-v4-flash-0731 | kimi-k3 | qwen3.6-35b-a3b | qwen3.7-plus | qwen3.8-flash | qwen3.8-max |
|---|---|---|---|---|---|---|
| counting | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| extrinsic_plausible | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| extrinsic_true | 4/4 | 3/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| fabricated_detail | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| fabricated_number | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| multi_hop | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| near_verbatim | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 |
| negation_flip | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| number_change | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| overgeneralization | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 |
| paraphrase | 19/19 | 16/19 | 18/19 | 19/19 | 19/19 | 19/19 |
| swapped_behavior | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| swapped_procedure | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| swapped_value | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| version_change | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
