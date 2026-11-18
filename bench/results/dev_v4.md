# dev: 3 independent repeats, model deepseek-v4.1-flash

Mean ± std across repeats (each repeat has its own LLM cache). Contestable gold claims excluded.

| config | claim acc | acc on matched | macro-F1 | halluc. recall | false alarm | reasoning acc | plain acc | evidence hit | claim recall | claim precision | errors | calls | out tokens | p50 s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pivot-v3 | 0.978 ± 0.004 | 0.988 ± 0.004 | 0.973 ± 0.009 | 1.00 ± 0.01 | 0.005 ± 0.000 | 0.974 ± 0.015 | 0.980 ± 0.003 | 0.98 ± 0.00 | 0.99 ± 0.00 | 0.94 ± 0.00 | 0.0 ± 0.0 | 2.0 ± 0.0 | 2040 ± 55 | 13.3 ± 0.5 | 26.4 ± 6.6 |
| pivot-v4 | 0.983 ± 0.003 | 0.988 ± 0.002 | 0.976 ± 0.005 | 1.00 ± 0.00 | 0.009 ± 0.000 | 0.980 ± 0.010 | 0.984 ± 0.005 | 0.98 ± 0.00 | 0.99 ± 0.00 | 0.94 ± 0.01 | 0.0 ± 0.0 | 2.0 ± 0.0 | 2238 ± 244 | 14.8 ± 1.5 | 74.4 ± 20.4 |

Claim accuracy with contestable claims included: pivot-v3 0.962 ± 0.007, pivot-v4 0.971 ± 0.002

## Repeat 1: claim accuracy with 95% case-level bootstrap CI

- pivot-v3: 0.976 [0.957, 0.993]
- pivot-v4: 0.979 [0.962, 0.993]

## Paired accuracy difference vs pivot-v3 (per repeat, case-level bootstrap)

| config | repeat 1 | repeat 2 | repeat 3 | mean delta |
|---|---|---|---|---|
| pivot-v4 | +0.003 [-0.011, +0.018] | +0.000 [-0.011, +0.009] | +0.010 [-0.008, +0.030] | +0.005 |

## Claim accuracy by case category (mean over repeats)

| config | fully_supported | subtle_distortion | extrinsic_hallucination | multi_passage | natural_answer |
|---|---|---|---|---|---|
| pivot-v3 | 0.943 | 0.984 | 0.977 | 0.947 | 0.925 |
| pivot-v4 | 0.981 | 0.981 | 0.974 | 0.953 | 0.958 |
