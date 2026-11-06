# v1 vs v2: measured results

v1 numbers are from `experiments/BASELINE_v1.md`; v2 numbers are from `runs/v2_llm/` produced by `run.py`.

## 1. Picking

| metric | v1 (LLM picks start/end) | v2 (LLM tags beats, code builds windows) |
|---|---|---|
| candidates meeting 20-60s **before** any repair | 84% (71% on lite model) | 100% (138/138) |
| hook inside first 3s, before repair | 81% | 100% |
| invalid / made-up beat IDs | 1 (stitched) | 0 of 381 tags |
| clips whose ending was re-cut by code | 21 of 105 | 0 (ends are always a tagged cliff beat) |
| episodes with >=1 candidate | 50/50 | 50/50 |
| multi-segment promos | 3 ranked, best #43, all needed trimming | 70 candidates, built within budget |

**Same-story duplicates inside the top 20** (embedding cosine >= 0.86, the calibrated threshold):
v1 4 pairs [('E01-P2', 'E01-P3', 0.88), ('E01-P2', 'E02-P1', 0.872), ('E18-P3', 'E18-P1', 0.931), ('E01-P3', 'E02-P1', 0.879)]; v2 3 pairs [('E31-W1', 'E32-W1', 0.895), ('E31-W1', 'E29-W1', 0.869), ('E13-W1', 'E12-W1', 0.865)].

## 2. Ranking reliability (test-retest: same clips, two independent passes)

v1 reference: two judge runs on 76 identical clips gave Spearman 0.68, Kendall 0.50, top-10 overlap 30%, and 81% tied scores.

| comparison | items | Spearman | Kendall | top-10 overlap |
|---|---|---|---|---|
| 1 sample vs 1 sample (all candidates) | 138 | 0.55 | 0.41 | 22% |
| avg of 2 vs avg of 2 (all candidates) | 138 | 0.67 | 0.50 | 40% |
| shortlist: screen avg2 vs avg2 | 20 | 0.01 | 0.01 | 50% |
| shortlist: pairwise BT, fwd vs rev verdicts (used for final order) | 20 | 0.44 | 0.33 | 60% |
| shortlist: z(BT)+z(screen) (tested, not used) | 20 | 0.28 | 0.21 | 50% |

- Pointwise scores compress at the top: screen score SD is 1.00 across all candidates but 0.25 inside the shortlist. That's why pointwise can shortlist but can't order the top.
- Pairwise position bias (80 verdicts, 40 pairs asked both ways): the same clip won in both orders 68% of the time (flip rate 32%); the first-shown clip won 61% (50% = unbiased). Split verdicts count as ties instead of wins.
- Shortlisting is more reliable than ordering: of the bottom quarter by one avg-of-2 pass, 85% are in the bottom half of the other pass; the top-20 *set* overlaps 45% between passes. Averaging more samples helps as test theory predicts (1 sample -> 2 samples raised Spearman from ~0.55 to ~0.67; Spearman-Brown predicts ~0.80 for 4).
- Ties in the final shortlist order: 0% (v1: 81%).

## 3. Model use

| role | job | calls by model (this run) |
|---|---|---|
| tag | mark hook/cliff beats, 1 call per episode | {'gemini/gemini-3.1-flash-lite': 50} |
| screen | pointwise score, 4 shuffled samples | {'gemini/gemini-3.5-flash-lite': 70, 'gemini/gemini-3.1-flash-lite': 2} |
| rank | pairwise tournament on the shortlist | {'gemini/gemma-4-26b-a4b-it': 32} |

Fallback calls: 34. v1 sent the hardest job (ranking) to the cheapest model and the easy job (reading every script) to the largest one; v2 reverses that.

## 4. Blind A/B: top 20 of each version, one auditor

Auditor: {'gemini/gemma-4-31b-it': 64}. It never saw which version a clip came from; clips from both versions were mixed and shuffled into the same batches, and each batch was scored twice.

| | v1 top-20 | v2 top-20 |
|---|---|---|
| mean weighted score | 7.00 | 7.31 |
| hook | 6.90 | 7.45 |
| cliffhanger | 6.29 | 6.76 |
| standalone | 7.71 | 7.82 |
| intensity | 7.10 | 7.70 |
| would post | 71% | 79% |
| clips scored | 20 | 20 |

Difference v2 - v1 = +0.31 (permutation test p = 0.32). Auditor test-retest Spearman across its two passes: 0.85 (n=24).
