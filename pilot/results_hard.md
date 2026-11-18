Gold: 130 claims, S 94, C 17, U 19. Always-SUPPORTED reference: acc 0.72, macro-F1 0.28

## Oracle mode (gold claims given; tests judgment only)

| model | acc | macro-F1 | recall S/C/U | false-support | false-alarm | evidence hit | quote valid | unusable | p50 s |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-flash-0731 | 0.99 | 0.98 | 1.00/0.94/1.00 | 0.00 | 0.00 | 0.97 | 0.97 (120) | 0 | 30.2 |
| kimi-k3 | 0.84 | 0.90 | 0.85/0.82/0.79 | 0.03 | 0.15 | 1.00 | 1.00 (105) | 2 | 46.1 |
| qwen3.6-35b-a3b | 0.96 | 0.93 | 0.98/0.88/0.95 | 0.03 | 0.02 | 0.96 | 0.95 (119) | 0 | 14.0 |
| qwen3.7-plus | 0.97 | 0.94 | 0.99/0.94/0.89 | 0.03 | 0.01 | 0.94 | 0.92 (122) | 0 | 25.5 |
| qwen3.8-flash | 0.97 | 0.96 | 0.98/0.94/0.95 | 0.06 | 0.02 | 0.88 | 0.88 (121) | 0 | 20.2 |
| qwen3.8-max | 0.98 | 0.96 | 1.00/1.00/0.84 | 0.06 | 0.00 | 0.98 | 0.98 (125) | 0 | 21.5 |

## End-to-end mode (model decomposes; greedy Dice alignment)

| model | strict acc* | macro-F1* | claim recall | claim precision | #pred/#gold | false-support* | answer-level acc | quote valid | invariant viol. | spurious on no-claim case | p50 s | tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-flash-0731 | 0.83 | 0.90 | 0.85 | 0.96 | 116/130 | 0.06 | 1.00 | 0.96 (112) | 0 | 0 | 28.6 | 61968 |
| kimi-k3 | 0.81 | 0.88 | 0.84 | 1.00 | 109/130 | 0.06 | 1.00 | 1.00 (113) | 0 | 0 | 54.2 | 46935 |
| qwen3.6-35b-a3b | 0.73 | 0.81 | 0.78 | 0.99 | 102/130 | 0.03 | 0.90 | 0.90 (98) | 0 | 0 | 10.4 | 30165 |
| qwen3.7-plus | 0.68 | 0.71 | 0.75 | 0.98 | 100/130 | 0.03 | 0.90 | 0.87 (97) | 2 | 0 | 26.7 | 28978 |
| qwen3.8-flash | 0.80 | 0.81 | 0.86 | 0.99 | 113/130 | 0.08 | 0.90 | 0.90 (113) | 1 | 0 | 18.3 | 31127 |
| qwen3.8-max | 0.87 | 0.92 | 0.89 | 0.97 | 119/130 | 0.03 | 1.00 | 0.99 (109) | 0 | 0 | 23.3 | 25990 |

\* over gold claims; an unmatched gold claim counts as wrong.

## Oracle accuracy by perturbation type

| type | deepseek-v4-flash-0731 | kimi-k3 | qwen3.6-35b-a3b | qwen3.7-plus | qwen3.8-flash | qwen3.8-max |
|---|---|---|---|---|---|---|
| arithmetic_error | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 1/1 |
| arithmetic_multi_hop | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 |
| config_name_swap | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| converse_of_only_if | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 | 1/2 |
| derived_recommendation | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| dropped_condition | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| exception_ignored | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| extrinsic_true | 8/8 | 7/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| fabricated_detail | 3/3 | 1/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| near_miss_fabrication | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| near_miss_number | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| near_miss_version | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 |
| near_verbatim | 12/12 | 9/12 | 12/12 | 12/12 | 12/12 | 12/12 |
| negation_flip | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| paraphrase | 77/77 | 68/77 | 76/77 | 77/77 | 76/77 | 77/77 |
| reversed_tradeoff | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| scope_change | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| scope_extension | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| superseded_statement | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| swapped_behavior | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| swapped_default | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| swapped_entity | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| temporal_inference | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| version_off_by_one | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| version_range_entailed | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 |
