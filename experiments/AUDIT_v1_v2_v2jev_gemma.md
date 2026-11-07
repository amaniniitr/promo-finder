# Blind audit of the top 20 from runs/v1, runs/v2_llm, runs/v2_jev

Auditor {'gemini/gemma-4-31b-it': 14}. 53 distinct clips (clips picked by more than one system are scored once). Labels hidden, shuffled, each batch scored twice.

| system | mean score | hook | cliffhanger | standalone | intensity | would post | n |
|---|---|---|---|---|---|---|---|
| runs/v1 | 6.78 | 6.75 | 6.03 | 7.67 | 7.12 | 65% | 20 |
| runs/v2_llm | 7.62 | 7.65 | 7.42 | 7.58 | 7.95 | 70% | 20 |
| runs/v2_jev | 7.60 | 7.28 | 7.60 | 7.83 | 7.92 | 82% | 20 |

- runs/v2_llm - runs/v1: +0.84 (permutation p = 0.01); shared clips: 0
- runs/v2_jev - runs/v1: +0.83 (permutation p = 0.02); shared clips: 0
- runs/v2_jev - runs/v2_llm: -0.02 (permutation p = 0.97); shared clips: 7
- Auditor test-retest Spearman: 0.88 (n=53).
