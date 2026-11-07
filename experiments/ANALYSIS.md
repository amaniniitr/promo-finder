# What went wrong, what changed, what the numbers say

Generated numbers: `experiments/BASELINE_v1.md` (v1) and `experiments/RESULTS.md` (v2, rerun with `python experiment.py --audit`).
This file is my reading of them.

## 1. Picking

**What went wrong.** v1 asked the LLM to choose start and end beats, which means it had to add up timestamps to land in 20-60s. Raw output met the length rule 84% of the time and the 3-second hook rule 81% of the time; on the fallback lite model it was 71% / 66%. Code then trimmed or extended 21 of 105 clips. Those re-cut clips scored 5.6 vs 6.2, and the ending the picker described was often no longer in the clip.

**Existing solutions.** Timestamp-grounding work has the same failure and the same fix: don't let the model generate times; have it select from candidates and compute times in code. Examples: "Topic-to-Timestamp Alignment by Constrained Evidence Selection" (arXiv 2606.20890) and the Seahawk segment-range selection system (BioNLP 2026). Opus Clip, likewise, scores many candidate windows instead of asking for one clip.

**Change.** The LLM (cheap model) only labels hook beats and cliffhanger beats by ID, with a 1-10 strength. That's a classification task. Code enumerates every hook-to-cliff window:
- 20-60s apart: one continuous clip that starts on the hook.
- 60-240s apart: a two-part clip, a hook teaser followed by the run-up into the cliff.

Non-max suppression then keeps up to 4 windows per episode.

**Result.** 138/138 candidates meet both rules before any repair (v1: 84% / 81%). 0 of 381 tags had invalid IDs. 0 endings were re-cut. 70 two-part candidates fit the budget (v1: 3 multi-segment promos, all trimmed, best rank #43).

## 2. Duplicates

**What went wrong.** v1 deduped on time overlap within one episode. Ep2 re-stages the Ep1 altar scene with new dialogue, so three clips of the same moment sat in v1's top 20.

**Change.** Two clips are duplicates if they share footage (time overlap > 50%) or their dialogue+action embeddings have cosine ≥ 0.90. The shortlist is then built with MMR so it isn't one storyline. I calibrated the threshold on known cases:
- 0.86 removed both recap pairs but merged 9 of 27 distinct moments from the same scene.
- 0.90 still removes both recap pairs (cosine 0.886-0.91) and merges only 3 of 27.

**Result.** Same-story pairs in the top 20 dropped from 4 to 3 (at cosine ≥ 0.86). The Ep1/Ep2 recap is gone. **Still wrong:** E31-W1 and E32-W1 (both the dungeon branding-iron scene, cosine 0.895) rank #1 and #3. The 0.90 threshold misses them. Story-level dedupe from embeddings is approximate.

## 3. Ranking

**What went wrong.** v1 used one pointwise judge pass with integer sub-scores:
- 81% of final scores tied.
- A second judge run on the same 76 clips kept only 30% of the top 10 (Spearman 0.68).
- The ranking ran on the cheapest model.

**Existing solutions.**
- Pairwise Ranking Prompting (Qin et al. 2023; the avnlp/prp library): compare two clips instead of scoring one, ask each pair in both orders to cancel position bias, aggregate with a sort or Bradley-Terry.
- "The Coin Flip Judge" (arXiv 2606.13685): 13.6% of pairwise verdicts flip between identical runs, and there's a 72% first-position bias. Its recommendation is multiple trials, randomized order, and reporting the uncertainty.
- Opus Clip's own guidance: treat the score as a ranking signal and let a human choose the final few.

**Change.**
1. A cheap pointwise screen, run 4 times. Each run uses a different shuffle, so every clip appears with different neighbours and in a different position. The 4 scores are averaged.
2. Story dedupe, then an MMR shortlist of 20.
3. A 4-round Swiss tournament on the shortlist with the strongest available model. Every pair is asked in both orders, in separate calls. A 1-1 split counts as a tie.
4. A Bradley-Terry fit orders the shortlist.

**Results (test-retest: the same clips judged by two independent passes).**
- **Averaging works as predicted.** One sample vs one sample: Spearman 0.55, top-10 overlap 22%. Average of 2 vs average of 2: 0.67 and 40%. 4 samples should give about 0.80 (Spearman-Brown).
- **Pointwise can shortlist but can't order the top.** Screen-score SD is 1.00 across all candidates but 0.25 inside the shortlist. On the shortlist, two avg-of-2 passes correlate at 0.01.
- **Pairwise beats pointwise on the shortlist, but is still weak.** Bradley-Terry fitted on forward-order verdicts vs reverse-order verdicts: Spearman 0.44, top-10 overlap 60%. An earlier full run gave 0.39 / 60%. Combining BT with the screen score was not consistent across runs (0.49, then 0.28), so I didn't use it.
- **Ties: 0%** (v1: 81%).
- **The ranker shows clear position bias.** The free-tier ranker today was gemma-4-26b, because every Gemini Flash daily cap was used up. The same clip won in both orders only 68% of the time, and the first-shown clip won 61%. That flip rate is more than twice the 13.6% the Coin Flip paper reports for GPT-4o-mini. The both-orders protocol turns those split verdicts into ties instead of wrong wins.

**Blind A/B.** gemma-4-31b, which produced neither list, scored v1's top 20 and v2's top 20 mixed and unlabeled, twice. The auditor's own test-retest Spearman is 0.85.
- v2 mean 7.31 vs v1 7.00; hook +0.55, cliffhanger +0.47, intensity +0.60; would-post 79% vs 71%.
- **This is not significant** (permutation p = 0.32, n = 20 per side). The defensible claim: v2 fixed compliance, re-cuts and ties without losing quality, and *may* be better.

## 4. Model use

**What went wrong.** v1 spent the strongest model on reading every script and the cheapest one on ranking, and that happened by quota accident rather than by design.

**Change.** Each role has its own model and fallback chain, set by environment variables:

| role | default model | calls per show |
|---|---|---|
| tag | 3.1-flash-lite | 50 |
| screen | 3.5-flash-lite | ~72 |
| rank | 3.5-flash → 3-flash → 2.5-flash → gemma | ~30 |

Every call records which model answered. Point `PROMO_RANK_MODEL` at the strongest API you have; it only sees ~30 calls per show.

**Still wrong today:** quota pushed the rank role down to gemma. The pairwise numbers above are a lower bound. Rerun `run.py` and `experiment.py --audit` with a strong ranker to measure the gain.

## Spot check of the v2 top 5 (I read the clip scripts)
- **#1 E31-W1 and #3 E32-W1:** a shouted order, then a branding iron stopping inches from her eye. Strong hooks, open endings. But they're the same scene told twice (see §2).
- **#2 E24-W1:** the riding-crop strike is a good hook. The ending (a calm vow to return) is resolve rather than an open question, so the cliffhanger is weak.
- **#4 E01-W1 (two-part):** the sister's gloating line at the altar, followed by the heroine's fury rising. This is the clean version of the v1 altar promo, built inside 60s with no trimming.
- **#5 E13-W1:** opens on the thorn needle. It ends when she *finds* the ring, which resolves the tension. The tagger labelled a resolution as a cliff. Tag quality is now the main limit on picking.

## 5. Jev (TypeSafe System One) as the judge

**What Jev is.** A decision-only model: you send `state` plus typed questions (Score, Choice, Noul) and get back probabilities, not text. About 0.3s per request, $0.042 per million input tokens (docs.typesafe.ai/models). The JEV-as-a-Judge study (arXiv 2609.26550) reports it is close to frontier LLM judges when the verdict "can be read off the text", and weaker when it has to be derived (math, code). Promo judging is the first kind.

**Problems it targets** (from §3): integer LLM scores tie and don't reproduce; the free-tier pairwise ranker flipped 32% of verdicts when the order was swapped; rate limits capped us at a 4-round Swiss tournament.

**Implementation** (`promo/jev.py`, `run.py --judge jev`, the default when `TYPESAFE_API_KEY` is set):
- **Screen:** one request per clip, 5 Score questions (hook, cliffhanger, standalone, intensity, spoiler), each with explicitly described levels. Asked twice, with levels low→high and high→low, then averaged. TypeSafe documents an order bias, and asking both ways cancels it.
- **Rank:** every pair on the shortlist (190), in both orders (380 requests). Bradley-Terry runs on the averaged probability P(a beats b). A pair whose orders disagree counts as a tie. `--escalate` sends those pairs to the LLM ranker (the paper's cascade).
- State holds only the clip script, and arithmetic stays in code. TypeSafe's "jaggedness" page lists both irrelevant context and math as weak spots.

**Measured** (`experiments/JEV_RESULTS.md`, `experiments/jev_experiment.py`):

| | LLM judges (v2) | Jev |
|---|---|---|
| pointwise, two passes, Spearman | 0.55 (1 vs 1), 0.67 (avg-2 vs avg-2) | 0.99 (level order reversed) |
| pointwise, paraphrased rubric (40 clips) | - | 0.93 weighted; standalone weakest at 0.75 |
| identical request repeated | varies (sampling) | ±0.02 |
| tied scores | 84% | 34% |
| score SD inside shortlist | 0.25 | 0.80 |
| pairwise: same winner in both orders | 68% (gemma-4-26b) | 75-80% |
| pairwise: first-shown clip wins | 61% | 37-40% (leans to the *second*) |
| shortlist split-half BT Spearman | 0.44 | 0.90 (experiment), 0.75 (final run) |
| split-half top-5 overlap | - | 80-100% |
| pairs compared | 39 | 190, all of them |
| wall time, screen + rank | ~30 min | ~20 s |
| cost | free tier, quota-limited | $0.05 for the whole experiment; $0.027 for a full run |

Using half the pairs reproduces the all-pairs order (Spearman 0.99, same top 5). A quarter gives 0.94 and keeps the top 5 98% of the time. So the cost could be halved without losing the order.

**Blind audit of quality** (`experiments/AUDIT_v1_v2_v2jev_gemma.md`). gemma-4-31b judged the top 20 of v1, v2-LLM and v2-Jev: 53 distinct clips, mixed, unlabeled, each batch scored twice. Auditor test-retest was 0.88.

| | v1 | v2, LLM judge | v2, Jev judge |
|---|---|---|---|
| mean score | 6.78 | 7.62 | 7.60 |
| cliffhanger | 6.03 | 7.42 | 7.60 |
| would post | 65% | 70% | 82% |

- v2 beats v1 under both judges (p = 0.01 and 0.02).
- Jev vs the LLM judge: −0.02, p = 0.97. They're equal in quality, and the two top-20 lists share only 7 clips.
- **Caveat:** an earlier audit, with a different batch mix, gave v2 vs v1 as +0.31, p = 0.32. The auditor's absolute scores shift with which clips share a batch. Treat the direction as consistent and the size as uncertain.

**What Jev does not fix**
- Jev's #1 and #2 (E31-W1, E32-W1) are still the same dungeon scene. Story dedupe is a separate problem.
- Jev's pointwise and pairwise orders agree only moderately on the shortlist (Spearman 0.37). They measure different things: the rubric scores a clip alone, the comparison scores relative appeal.
- Spoiler confidence is low (mean 0.43), so treat the spoiler score as a hint.
- Every quality number here comes from another model, not from editors or view data. The next real test is editor approve/reject labels from the review UI.

## 6. v3: Vertex tagger, cross-episode promos, written notes, and a stronger auditor

**Changes** (`runs/v3_final/`):
- Tagging moved from free-tier 3.1-flash-lite to Vertex `gemini-3.5-flash`: 500 tags, 0 invalid IDs.
- Cross-episode promos are back. Code joins a hook teaser from one episode to the run-up into a cliff from a later episode (at most 12 episodes later, same main character speaking in both). 12 enter judging, 4 are ranked, 2 reach the top 20.
- After ranking, an LLM writes the hook / cliffhanger / one-line why for the top 30, plus a week-1 posting plan that holds back high-spoiler clips. Writing happens after ranking, so it can't bias the order.
- Pairwise ranking is still Jev: same winner in both orders 81%, first-shown wins 40%.

**Blind audit with the strongest model available** (Vertex `gemini-3.8-flash`, 69 distinct clips from the top 20 of v1, v2-LLM, v2-Jev and v3; test-retest 0.79):

| | v1 | v2, LLM judge | v2, Jev | v3 |
|---|---|---|---|---|
| mean score | 6.72 | 6.75 | 6.88 | 6.86 |
| cliffhanger | 5.92 | 6.08 | 6.85 | 6.55 |
| would post | 55% | 50% | 60% | 62% |

No pairwise difference is significant (all p ≥ 0.58). On cliffhangers, Jev-judged v2 beats v1 by +0.92 (p = 0.085).

**The AI judges don't agree with each other:**

| judge pair (same clips) | Spearman |
|---|---|
| gemma-4-31b vs gemini-3.8-flash | 0.49 (53 clips) |
| Jev vs gemini-3.8-flash | 0.26 (69 clips) |
| Jev vs gemma-4-31b | 0.29 (53 clips) |

The earlier gemma audit called v2 better than v1 (p = 0.01). The 3.8-flash audit sees no difference.

**What this means:**
- Self-consistency is not validity. Jev reproduces its own ranking (0.99), yet it agrees with other strong judges at only about 0.3.
- What is proven: the process fixes (rule compliance, no re-cuts, no ties, reproducible order, cost and speed, and the brief's required fields).
- What is not proven: that any version picks promos that people prefer. That needs human labels or real view data. The highest-value next step is an editor (or I) rating ~40 blind clips, then checking which judge agrees with the human.
