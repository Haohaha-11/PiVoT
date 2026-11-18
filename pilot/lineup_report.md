
### v1 (53 claims)

| model | thinking | oracle acc | oracle macro-F1 | S-vs-nonS | e2e acc | quote valid | unwrapped / unusable | p50 s | avg out tokens |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | on (default) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 / 0 | 8.6 | 1438 |
| kimi-k3 | on (default) | 1.00 | 1.00 | 1.00 | 0.94 | 1.00 | 1 / 0 | 18.3 | 999 |
| glm-5.3 | on (cannot disable) | 1.00 | 1.00 | 1.00 | 0.94 | 1.00 | 0 / 0 | 9.1 | 1345 |
| qwen3.8-flash | off | 1.00 | 1.00 | 1.00 | 0.83 | 0.89 | 0 / 0 | 10.0 | 660 |
| qwen3.8-max | off | 1.00 | 1.00 | 1.00 | 0.94 | 0.99 | 0 / 0 | 10.8 | 511 |

### hard (130)

| model | thinking | oracle acc | oracle macro-F1 | S-vs-nonS | e2e acc | quote valid | unwrapped / unusable | p50 s | avg out tokens |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | on (default) | 0.99 | 0.99 | 1.00 | 0.92 | 1.00 | 0 / 0 | 23.4 | 5069 |
| kimi-k3 | on (default) | 0.99 | 0.99 | 1.00 | 0.81 | 1.00 | 2 / 0 | 50.7 | 2957 |
| glm-5.3 | on (cannot disable) | 0.98 | 0.98 | 1.00 | 0.89 | 1.00 | 0 / 0 | 33.4 | 7133 |
| qwen3.8-flash | off | 0.97 | 0.96 | 0.98 | 0.80 | 0.89 | 0 / 0 | 18.5 | 1745 |
| qwen3.8-max | off | 0.98 | 0.96 | 1.00 | 0.87 | 0.99 | 0 / 0 | 21.9 | 1214 |

### reasoning (116)

| model | thinking | oracle acc | oracle macro-F1 | S-vs-nonS | reasoning acc* | plain acc | e2e acc | quote valid | unwrapped / unusable | p50 s | avg out tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | on (default) | 0.99 | 0.97 | 1.00 | 1.00 | 1.00 | 0.95 | 1.00 | 0 / 0 | 26.5 | 5409 |
| deepseek-v4.1-flash | off | 0.95 | 0.89 | 0.97 | 0.90 | 1.00 | 0.88 | 1.00 | 0 / 0 | 7.1 | 1167 |
| kimi-k3 | on (default) | 0.99 | 0.97 | 1.00 | 0.98 | 1.00 | 0.93 | 1.00 | 3 / 0 | 52.8 | 3036 |
| kimi-k3 | off | 0.95 | 0.88 | 0.97 | 0.90 | 1.00 | 0.82 | 1.00 | 0 / 0 | 23.3 | 1113 |
| glm-5.3 | on (cannot disable) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 1.00 | 0 / 0 | 70.7 | 9450 |
| qwen3.8-flash | off | 0.95 | 0.87 | 0.98 | 0.92 | 1.00 | 0.86 | 0.86 | 0 / 0 | 18.5 | 1640 |
| qwen3.8-flash | on | 0.97 | 0.91 | 0.99 | 0.94 | 1.00 | 0.91 | 0.99 | 0 / 0 | 99.5 | 8697 |
| qwen3.8-max | off | 0.91 | 0.83 | 0.96 | 0.83 | 1.00 | 0.88 | 0.99 | 0 / 0 | 21.0 | 1139 |
| qwen3.8-max | on | 0.95 | 0.89 | 0.96 | 0.96 | 0.95 | 0.96 | 1.00 | 0 / 0 | 195.7 | 11929 |

\* reasoning-type claims only, contestable excluded. S-vs-nonS also excludes contestable.

Note: glm-5.3 generated the two natural answers in the hard set (natural-01/02), so its hard-set numbers include self-verification on those two cases.
