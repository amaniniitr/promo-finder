# Jev (TypeSafe System One) vs the LLM judges

Model `jev-1.14.0`. All numbers below come from `experiments/jev_experiment.py`; raw answers are cached in `.cache/jev/`.

## A. Pointwise rubric scores (all 138 candidates)

| metric | LLM screen (3.5-flash-lite) | Jev |
|---|---|---|
| two independent passes, Spearman | 0.55 (1 sample vs 1), 0.67 (avg-2 vs avg-2) | 0.99 (levels low->high vs high->low) |
| two passes, top-10 overlap | 22% / 40% | 90% |
| tied scores | 84% | 34% |
| score SD, all candidates / inside shortlist | 1.00 / 0.25 | 1.33 / 0.80 |
| calls for 138 clips | 72 (batched, x4 samples) | 276 (1 clip per call, x2 orders) |
| wall time | ~6 min (free-tier throttled) | 12s |

Agreement Jev vs LLM screen (Spearman): 0.65.
Per-criterion mean Jev confidence: hook 0.75, cliffhanger 0.66, standalone 0.58, intensity 0.77, spoiler 0.43.

## B. Pairwise on the shortlist (20 clips, all 190 pairs, both orders = 380 calls)

| metric | gemma-4-26b Swiss tournament (v2) | Jev all-pairs |
|---|---|---|
| pairs compared | 39 (4 Swiss rounds) | 190 (every pair) |
| same winner in both orders | 68% | 80% |
| first-shown clip wins (50% = no bias) | 61% | 40% |
| split-half BT Spearman (order-1 answers vs order-2 answers) | 0.44 | 0.90 |
| split-half Kendall | 0.33 | 0.76 |
| split-half top-10 overlap | 60% | 80% |
| split-half top-5 overlap | - | 80% |
| wall time | ~25 min | 16s |

Hard-vote BT vs soft-probability BT on the same verdicts: Spearman 0.99.
Jev vs gemma, on the 27 pairs gemma answered the same way in both orders: Jev agrees on 78%.
Jev pairwise BT vs Jev pointwise score on the shortlist: Spearman 0.37.

**Cascade (accept Jev when both orders agree and confidence >= tau, else escalate to the LLM):**

| tau | pairs Jev settles | agreement with consistent gemma verdicts | pairs escalated |
|---|---|---|---|
| 0.0 | 80% | 73% (n=22) | 38 |
| 0.5 | 47% | 80% (n=15) | 100 |
| 0.7 | 25% | 75% (n=8) | 143 |
| 0.8 | 16% | 75% (n=4) | 159 |
| 0.9 | 8% | 100% (n=1) | 175 |

## C. External check: blind auditor (gemma-4-31b) on 40 clips

- Jev pointwise vs auditor: Spearman 0.38.
- LLM screen vs auditor (v2 clips only, n=20): Spearman 0.19; Jev on the same clips: 0.58.
- Mean Jev score, v1 top-20 vs v2 top-20: 7.70 vs 7.95.
- The auditor is itself an LLM, not a human editor. Agreement measures consistency between judges, not truth.

## Cost

New Jev requests this run: 668, cached: 28, input tokens 1,250,626, cost $0.0525 at $0.042 per million input tokens.
