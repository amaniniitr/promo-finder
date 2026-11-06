# v1 baseline (measured from existing v1 runs/v1 and cached LLM responses, no new calls)

## Picking: the LLM generates clip boundaries itself
Raw picker output, before any code repair, n=150 candidates:

| picker model | n | length in 20-60s | hook within first 3s |
|---|---|---|---|
| gemini-3.1-flash-lite (fallback) | 76 | 71% | 66% |
| gemini-3-flash-preview | 22 | 95% | 91% |
| gemini-3.5-flash | 23 | 96% | 100% |
| gemini-2.5-flash | 29 | 100% | 100% |
| **all** | 150 | **84%** | **81%** |

The problem: compliance depends on the model. When the free-tier daily cap pushed 64 of 105 promos onto the lite model, a third of its clips broke the rules. Code repair then hurt quality: re-cut clips averaged 5.6 vs 6.2 for the rest.

## Ranking: one pointwise judge pass
- 81% of final scores tie with at least one other clip (46 distinct values across 105 clips). Judge sub-scores are integers clustered on 5-8, so the order inside each tie is arbitrary.
- Two judge runs on the same 76 clips (different judge models): Spearman 0.68, Kendall 0.50, **top-10 overlap 30%**, top-20 overlap 50%.
- The picker's self-score has almost no relation to the judge's (Spearman 0.27; -0.13 on an earlier run).
- The "strongest" model was never used deliberately. Ranking ran on gemini-3.5-flash-lite, the cheapest model, because of quota.

## Duplicates: overlap measured in time, within one episode
Ep2 re-stages the Ep1 altar scene with new dialogue. v1 dedupe (time overlap > 50%, same episode only) can't detect it.

Embedding cosine similarity of clip text (gemini-embedding-001, all 5,460 pairs of the 105 v1 promos):
- median 0.72, 95th percentile 0.81, 99th percentile 0.86
- known recap pairs: E01-P2 vs E02-P1 = **0.872**, E01-P3 vs E02-P1 = **0.879** (above the 99th percentile)
- but the most similar pairs (0.90-0.93) are mostly two clips of the *same scene* in one episode (E12-P1/P2, E18-P1/P3), which v1 kept because their time overlap was below 50%.
- Embedding only the hook+cliffhanger descriptions separates less well: the recap pair scores 0.75-0.81, inside the normal range.
