# test2: 3 independent repeats, model deepseek-v4.1-flash

Mean ± std across repeats (each repeat has its own LLM cache). Contestable gold claims excluded.

| config | claim acc | acc on matched | macro-F1 | halluc. recall | false alarm | reasoning acc | plain acc | evidence hit | claim recall | claim precision | errors | calls | out tokens | p50 s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lexical | 0.256 ± 0.000 | 0.256 ± 0.000 | 0.215 ± 0.000 | 0.71 ± 0.00 | 0.769 ± 0.000 | 0.250 ± 0.000 | 0.258 ± 0.000 | 0.75 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| minimal | 0.952 ± 0.016 | 0.992 ± 0.000 | 0.968 ± 0.003 | 0.97 ± 0.03 | 0.010 ± 0.000 | 0.938 ± 0.031 | 0.957 ± 0.011 | 0.93 ± 0.02 | 0.96 ± 0.02 | 0.83 ± 0.04 | 0.0 ± 0.0 | 1.0 ± 0.0 | 6755 ± 235 | 32.4 ± 2.2 | 61.4 ± 4.5 |
| minimal-nothink | 0.875 ± 0.005 | 0.956 ± 0.000 | 0.909 ± 0.001 | 1.00 ± 0.00 | 0.048 ± 0.000 | 0.969 ± 0.000 | 0.842 ± 0.006 | 0.91 ± 0.01 | 0.91 ± 0.00 | 0.99 ± 0.00 | 0.0 ± 0.0 | 1.0 ± 0.0 | 1272 ± 30 | 6.3 ± 0.2 | 9.5 ± 0.5 |
| pivot-v3 | 0.979 ± 0.005 | 0.987 ± 0.005 | 0.977 ± 0.007 | 1.00 ± 0.00 | 0.016 ± 0.006 | 1.000 ± 0.000 | 0.971 ± 0.006 | 0.90 ± 0.00 | 0.99 ± 0.00 | 1.00 ± 0.00 | 0.0 ± 0.0 | 2.1 ± 0.0 | 2082 ± 267 | 14.7 ± 0.8 | 19.5 ± 2.5 |
| pivot-v4 | 0.976 ± 0.008 | 0.984 ± 0.008 | 0.973 ± 0.012 | 1.00 ± 0.00 | 0.019 ± 0.010 | 1.000 ± 0.000 | 0.968 ± 0.011 | 0.89 ± 0.01 | 0.99 ± 0.00 | 0.99 ± 0.01 | 0.0 ± 0.0 | 2.3 ± 0.1 | 2995 ± 822 | 15.7 ± 1.7 | 30.4 ± 4.5 |

Claim accuracy with contestable claims included: lexical 0.284 ± 0.000, minimal 0.894 ± 0.012, minimal-nothink 0.839 ± 0.004, pivot-v3 0.929 ± 0.012, pivot-v4 0.939 ± 0.004

## Repeat 1: claim accuracy with 95% case-level bootstrap CI

- lexical: 0.256 [0.163, 0.378]
- minimal: 0.968 [0.910, 1.000]
- minimal-nothink: 0.872 [0.786, 0.958]
- pivot-v3: 0.976 [0.950, 0.993]
- pivot-v4: 0.976 [0.950, 0.993]

## Paired accuracy difference vs minimal (per repeat, case-level bootstrap)

| config | repeat 1 | repeat 2 | repeat 3 | mean delta |
|---|---|---|---|---|
| pivot-v3 | +0.008 [-0.027, +0.052] | +0.040 [+0.008, +0.077] | +0.032 [+0.007, +0.069] | +0.027 |
| pivot-v4 | +0.008 [-0.027, +0.052] | +0.048 [+0.017, +0.086] | +0.016 [-0.029, +0.066] | +0.024 |
| minimal-nothink | -0.096 [-0.173, -0.026] | -0.056 [-0.122, +0.018] | -0.080 [-0.164, +0.016] | -0.077 |

## Claim accuracy by case category (mean over repeats)

| config | fully_supported | subtle_distortion | extrinsic_hallucination | multi_passage | natural_answer |
|---|---|---|---|---|---|
| lexical | 0.153 | 0.279 | 0.478 | 0.095 | 0.139 |
| minimal | 0.960 | 0.922 | 0.986 | 0.952 | 0.954 |
| minimal-nothink | 0.819 | 0.907 | 0.957 | 1.000 | 0.731 |
| pivot-v3 | 0.983 | 0.961 | 1.000 | 0.968 | 0.972 |
| pivot-v4 | 0.972 | 0.969 | 1.000 | 0.984 | 0.954 |
