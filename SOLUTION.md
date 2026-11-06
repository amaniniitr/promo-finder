# Promo Finder for microdrama screenplays (Problem 1)

**Why this problem.** The pack fits it directly: timestamped scripts make "right start and end" checkable in code, and an editor watching every episode of every weekly show is a real bottleneck. The output is easy to check: a list of clips an editor can watch.

## Assumptions
- Script timestamps match the final cut. If the edit drifts, a person nudges the cuts.
- A promo is 20-60s of existing footage with the hook in the first 3s. These are hard rules enforced in code, not requests to the model.
- A cold viewer knows nothing about the show, so every judge sees only the clip.
- Posting order means "most likely to stop a scroller and make them want the next episode".
- Free tier only. Stronger models plug in through one environment variable per role.

## How it works (AI vs code vs human)
1. **Parse (code).** 50 episodes -> 3,727 beats with IDs and times.
2. **Tag (cheap LLM).** For each episode, mark hook beats and cliffhanger beats by ID, with a strength. The model never writes a timestamp or picks a length.
3. **Build windows (code).** Every hook-to-cliff pair becomes a candidate clip: one continuous clip if 20-60s apart, or a two-part clip (hook teaser, then the run-up to the cliff) if 60-240s apart. Non-max suppression keeps 4 per episode.
4. **Screen (cheap LLM, 4 samples).** Each sample uses a different random batching, and the 4 scores are averaged.
5. **Dedupe + shortlist (code).** Same footage or same story (embedding similarity) counts as a duplicate. MMR then picks a varied top 20.
6. **Rank (TypeSafe Jev).** Jev is a decision-only model that returns probabilities instead of text, in about 0.3s, at $0.042 per million tokens. It compares every pair on the shortlist in both orders, and a Bradley-Terry fit on P(a beats b) orders the list. Jev also does step 4's screen as a rubric score. Without a Jev key, an LLM Swiss tournament does the same job.
7. **Editor (human).** A review UI with the script around each cut and approve/reject buttons. Decisions are saved as labels.

Ideas reused rather than invented: select-from-candidates instead of generating timestamps (constrained temporal selection papers); pairwise ranking asked in both orders (PRP, Qin et al. 2023); multiple trials against judge noise ("Coin Flip Judge" 2026); MMR diversity; LiteLLM for model swapping.

## How I measured it, and what changed
v1 had the LLM pick start/end directly and ranked with one judge pass. I measured its failures first, then fixed each one and remeasured (`experiments/RESULTS.md`, `ANALYSIS.md`).

| problem | v1 | v2 |
|---|---|---|
| raw clips meeting 20-60s / hook in 3s | 84% / 81% (71% / 66% on lite model) | **100% / 100%** (138/138) |
| endings re-cut by code | 21 of 105 (scored 5.6 vs 6.2) | 0 |
| two-part promos | 3, all trimmed, best rank #43 | 70 candidates, built within budget |
| tied final scores | 81% | 0% |
| same clips judged twice, top-10 overlap | 30% | screen avg-of-2: 40%; pairwise on shortlist: 60% |
| shortlist order, split-half Spearman | - | LLM ranker 0.44 → **Jev 0.75-0.90**, same top 5 in 80-100% |
| blind auditor (gemma-4-31b), top 20 | 6.78 | LLM judge 7.62, Jev judge 7.60 (p = 0.01-0.02 vs v1; Jev = LLM, p = 0.97) |
| judge time / cost per show | - | Jev: ~20s, ~$0.03 (LLM judges: ~30 min on free tier) |

## Where it still fails
- **Better ordering, not proven better picks.** Jev made the order reproducible (split-half Spearman 0.44 → 0.75-0.90), but the blind auditor rates Jev's top 20 the same as the LLM judge's. An earlier audit with a different batch mix put v2 vs v1 at p = 0.32, so effect sizes are uncertain. Every quality number comes from another model; editor labels are the real test.
- **Jev has a position bias too.** It leans toward the second-shown clip (37-40% first-shown wins), and 20-25% of pairs flip when swapped. Asking both orders and counting a split as a tie handles this.
- **Story dedupe is approximate.** #1 and #3 are the same dungeon scene told in two episodes (similarity 0.895, just under the 0.90 threshold). Lowering the threshold merged distinct moments, so I calibrated it on known cases and accepted this miss.
- **The tagger mislabels some cliffs.** It sometimes marks a resolution as a cliff (e.g., she finds the ring). Picking quality now depends on tag quality.
- **Visual hooks can't be verified from text.**

## AI tools used, and one place they went wrong
Kiro (Claude) for research, code and analysis. Gemini Flash / Flash-Lite and Gemma inside the pipeline, plus TypeSafe Jev as the judge.
**Where it went wrong:** told "20-60 seconds", the model returned 9-160s clips. It doesn't add up timestamps reliably. Patching that in code damaged endings. The real fix was to stop asking the model for arithmetic: it labels moments, and code builds the clips. The assistant also misread a *daily* quota error as a per-minute one and kept retrying. The client now detects daily caps and falls back to the next model.

## Scale and cost
Per 50-episode show: ~50 tag calls (cheap LLM), 1 embedding pass, and ~650 Jev requests (~1.2M tokens, ~$0.03, ~20s). Using half the pairs gives the same order (Spearman 0.99), which halves the Jev cost. Expensive calls stay flat as the show grows, because only the top 20 reach the ranker. Rough cost on paid Gemini is well under $1 per show (estimated from list prices, not measured). Shows run independently and caching makes reruns free. Next steps: put the strongest available model on `rank`, use editor approvals to tune the tagger and score weights, and check the first 3s of footage with a vision model once video is available.
