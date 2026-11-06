# Blind audit of the top 20 from runs/v1, runs/v2_llm, runs/v2_jev, runs/v3_final

Auditor {'vertex/gemini-3.8-flash': 18}. 69 distinct clips (clips picked by more than one system are scored once). Labels hidden, shuffled, each batch scored twice.

| system | mean score | hook | cliffhanger | standalone | intensity | would post | n |
|---|---|---|---|---|---|---|---|
| runs/v1 | 6.72 | 7.05 | 5.92 | 7.30 | 6.97 | 55% | 20 |
| runs/v2_llm | 6.75 | 7.17 | 6.08 | 7.15 | 6.95 | 50% | 20 |
| runs/v2_jev | 6.88 | 6.83 | 6.85 | 7.12 | 6.97 | 60% | 20 |
| runs/v3_final | 6.86 | 7.05 | 6.55 | 6.92 | 6.97 | 62% | 20 |

- runs/v2_llm - runs/v1: +0.03 (permutation p = 0.92); shared clips: 0
- runs/v2_jev - runs/v1: +0.17 (permutation p = 0.58); shared clips: 0
- runs/v3_final - runs/v1: +0.14 (permutation p = 0.62); shared clips: 0
- runs/v2_jev - runs/v2_llm: +0.13 (permutation p = 0.69); shared clips: 7
- runs/v3_final - runs/v2_llm: +0.11 (permutation p = 0.73); shared clips: 1
- runs/v3_final - runs/v2_jev: -0.03 (permutation p = 0.95); shared clips: 4
- Auditor test-retest Spearman: 0.79 (n=69).
