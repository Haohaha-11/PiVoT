# test: 3 independent repeats, model deepseek-v4.1-flash

Mean ± std across repeats (each repeat has its own LLM cache). Contestable gold claims excluded.

| config | claim acc | acc on matched | macro-F1 | halluc. recall | false alarm | reasoning acc | plain acc | evidence hit | claim recall | claim precision | errors | calls | out tokens | p50 s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lexical | 0.192 ± 0.000 | 0.192 ± 0.000 | 0.202 ± 0.000 | 0.89 ± 0.00 | 0.900 ± 0.000 | 0.377 ± 0.000 | 0.112 ± 0.000 | 0.80 ± 0.00 | 1.00 ± 0.00 | 0.99 ± 0.00 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| minimal | 0.959 ± 0.011 | 0.987 ± 0.006 | 0.956 ± 0.008 | 0.98 ± 0.01 | 0.007 ± 0.008 | 0.952 ± 0.015 | 0.963 ± 0.014 | 0.93 ± 0.01 | 0.97 ± 0.01 | 0.84 ± 0.04 | 0.0 ± 0.0 | 1.0 ± 0.0 | 6514 ± 470 | 33.9 ± 2.6 | 79.1 ± 9.5 |
| minimal-nothink | 0.898 ± 0.010 | 0.957 ± 0.007 | 0.883 ± 0.014 | 0.93 ± 0.00 | 0.043 ± 0.006 | 0.866 ± 0.020 | 0.912 ± 0.006 | 0.93 ± 0.00 | 0.94 ± 0.00 | 0.97 ± 0.00 | 0.0 ± 0.0 | 1.0 ± 0.0 | 1238 ± 26 | 7.1 ± 0.3 | 11.9 ± 1.1 |
| pivot | 0.953 ± 0.017 | 0.975 ± 0.010 | 0.926 ± 0.032 | 0.92 ± 0.03 | 0.022 ± 0.013 | 0.918 ± 0.033 | 0.968 ± 0.012 | 0.94 ± 0.01 | 0.98 ± 0.01 | 0.99 ± 0.01 | 0.0 ± 0.0 | 1.9 ± 0.0 | 2614 ± 403 | 14.6 ± 1.3 | 50.4 ± 24.7 |

Claim accuracy with contestable claims included: lexical 0.227 ± 0.000, minimal 0.934 ± 0.009, minimal-nothink 0.870 ± 0.013, pivot 0.925 ± 0.023

## Repeat 1: claim accuracy with 95% case-level bootstrap CI

- lexical: 0.192 [0.123, 0.275]
- minimal: 0.953 [0.930, 0.979]
- minimal-nothink: 0.906 [0.863, 0.950]
- pivot: 0.933 [0.890, 0.974]

## Paired accuracy difference vs minimal (per repeat, case-level bootstrap)

| config | repeat 1 | repeat 2 | repeat 3 | mean delta |
|---|---|---|---|---|
| pivot | -0.020 [-0.068, +0.027] | +0.008 [-0.043, +0.055] | -0.008 [-0.038, +0.023] | -0.007 |
| minimal-nothink | -0.047 [-0.096, -0.004] | -0.067 [-0.102, -0.036] | -0.071 [-0.116, -0.020] | -0.061 |

## Claim accuracy by case category (mean over repeats)

| config | fully_supported | subtle_distortion | extrinsic_hallucination | multi_passage | natural_answer |
|---|---|---|---|---|---|
| lexical | 0.089 | 0.205 | 0.275 | 0.105 | 0.130 |
| minimal | 0.959 | 0.964 | 0.954 | 0.974 | 0.918 |
| minimal-nothink | 0.900 | 0.920 | 0.871 | 0.877 | 0.831 |
| pivot | 0.989 | 0.936 | 0.929 | 0.886 | 0.918 |
