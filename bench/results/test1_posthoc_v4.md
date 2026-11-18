# test: 3 independent repeats, model deepseek-v4.1-flash

Mean ± std across repeats (each repeat has its own LLM cache). Contestable gold claims excluded.

| config | claim acc | acc on matched | macro-F1 | halluc. recall | false alarm | reasoning acc | plain acc | evidence hit | claim recall | claim precision | errors | calls | out tokens | p50 s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| minimal | 0.959 ± 0.011 | 0.987 ± 0.006 | 0.956 ± 0.008 | 0.98 ± 0.01 | 0.007 ± 0.008 | 0.952 ± 0.015 | 0.963 ± 0.014 | 0.93 ± 0.01 | 0.97 ± 0.01 | 0.84 ± 0.04 | 0.0 ± 0.0 | 1.0 ± 0.0 | 6514 ± 470 | 33.9 ± 2.6 | 79.1 ± 9.5 |
| pivot-v3 | 0.953 ± 0.017 | 0.975 ± 0.010 | 0.926 ± 0.032 | 0.92 ± 0.03 | 0.022 ± 0.013 | 0.918 ± 0.033 | 0.968 ± 0.012 | 0.94 ± 0.01 | 0.98 ± 0.01 | 0.99 ± 0.01 | 0.0 ± 0.0 | 1.9 ± 0.0 | 2614 ± 403 | 14.6 ± 1.3 | 50.4 ± 24.7 |
| pivot-v4 | 0.974 ± 0.009 | 0.978 ± 0.009 | 0.953 ± 0.015 | 0.98 ± 0.02 | 0.018 ± 0.008 | 0.961 ± 0.022 | 0.979 ± 0.003 | 0.94 ± 0.01 | 1.00 ± 0.00 | 0.97 ± 0.01 | 0.0 ± 0.0 | 2.1 ± 0.1 | 3267 ± 520 | 14.2 ± 0.7 | 83.9 ± 57.7 |

Claim accuracy with contestable claims included: minimal 0.934 ± 0.009, pivot-v3 0.925 ± 0.023, pivot-v4 0.949 ± 0.013

## Repeat 1: claim accuracy with 95% case-level bootstrap CI

- minimal: 0.953 [0.930, 0.979]
- pivot-v3: 0.933 [0.890, 0.974]
- pivot-v4: 0.969 [0.953, 0.984]

## Paired accuracy difference vs pivot-v3 (per repeat, case-level bootstrap)

| config | repeat 1 | repeat 2 | repeat 3 | mean delta |
|---|---|---|---|---|
| pivot-v4 | +0.035 [+0.003, +0.074] | +0.024 [+0.003, +0.051] | +0.004 [-0.021, +0.030] | +0.021 |

## Claim accuracy by case category (mean over repeats)

| config | fully_supported | subtle_distortion | extrinsic_hallucination | multi_passage | natural_answer |
|---|---|---|---|---|---|
| minimal | 0.959 | 0.964 | 0.954 | 0.974 | 0.918 |
| pivot-v3 | 0.989 | 0.936 | 0.929 | 0.886 | 0.918 |
| pivot-v4 | 0.974 | 0.968 | 0.979 | 0.947 | 0.965 |
