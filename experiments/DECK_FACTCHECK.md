# DECK_FACTCHECK — deck/solution.pdf vs sources

Method: deck text via `pdftotext -layout deck/solution.pdf`. Every number/claim checked against
`runs/v3_final/meta.json` + `promos.json`/`diagnostics.json`, `experiments/*`, `runs/new_show_test/meta.json`,
and `tests/test_parser.py` (run live). No API calls; `.env` not read.

## Summary
- WRONG: 1
- UNSUPPORTED: 2
- VERIFIED: everything else below.

---

## Page 1

### Header KPI strip
| Claim | Status | Source / value |
|---|---|---|
| "93 ranked promos from 176 candidates, all 50 episodes covered" | VERIFIED | meta.json ranked 93, candidates 176, episodes 50 |
| "0 rule violations: every clip 20–60s, hook in first 3s" | VERIFIED | meta.json rule_violations 0; all top-5 durations 25.6–41.6s; hook at segment[0].start by construction |
| "90% planted shocking lines found as hooks; 0/29 neutral decoys" | VERIFIED | REALWORLD_RESULTS.md (vertex 3.5-flash): 26/29=90%, decoy 0/29 |
| "0.75–0.90 ranking reproducibility (split-half Spearman), vs 0.44 before" | VERIFIED | JEV_RESULTS.md split-half BT Jev 0.90; ANALYSIS.md final run 0.75; LLM ranker 0.44 |
| "~$1.48 per 50-ep show at list prices; ~7 min end to end, judging ~20 s" | VERIFIED | tag $1.432 (236200×1.50 + 119792×9 per M) + Jev $0.04852 = $1.48; Jev seconds 217.6 (~3.6 min judging — "~20 s" is wall time w/ caching, see §9 note) |
| "1 cmd: python run.py <show>" | VERIFIED | run.py takes folder positional (READINESS_REVIEW) |

Note on "~20 s judging": meta jev_usage.seconds = 217.6 (full experiment). The "~20 s" matches
JEV_RESULTS.md / ANALYSIS.md "wall time screen+rank ~20 s" for the cached final run. Consistent with sources, not a fabrication.

### §1 Problem & why — VERIFIED (narrative; matches brief problem 1)
### §2 Assumptions — VERIFIED (narrative; timestamps≈cut, whole-line snapping, cold judge, "post first")
### §3 How it works
| Claim | Status | Source |
|---|---|---|
| "3,727 beats" | UNSUPPORTED (see item U1) | hard-coded in build_deck.py / SOLUTION.md; not in any run file. Lower bound from diagnostics tags = 3,677 (max tagged beat-id per ep). Not derivable from provided sources. |
| "mark … beats by ID (1 call/ep)" | VERIFIED | diagnostics calls: role tag, 50 calls, 1/ep |
| "every hook→cliff, 20–60s, 2-part & cross-episode" | VERIFIED | window_stats; promos.json |
| "0 invented IDs in 500 tags; 100% compliant" | VERIFIED | diagnostics: 500 tag entries total; ANALYSIS.md "500 tags, 0 invalid IDs"; rule_violations 0 |
| "position bias can't pick winners (Jev: same winner both ways 80%)" | VERIFIED | meta position_consistency 0.805 |
| "Reused, not invented: AI-Shorts-Generator, deepclip, PRP, MMR, LiteLLM, TypeSafe Jev" | VERIFIED | ANALYSIS.md references |

### §4 Post-first week-1 plan
| Claim | Status | Source |
|---|---|---|
| Day1 E32-W1 rank1; Day2 E15-W1 rank2; Day3 E13-W2 rank3; Day4 E03-W2 rank5; Day5 E16-W1 rank4 | VERIFIED | meta.posting_plan days 1–5 = E32-W1,E15-W1,E13-W2,E03-W2,E16-W1; promos.json ranks 1,2,3,5,4 respectively |
| "Held back (7): spoiler risk ≥ 5, e.g. E03-W1, X06-E25E36, E36-W3, E33-W2" | VERIFIED | meta.posting_plan.hold = 7 entries incl. all four named (E03-W1 5.8, X06-E25E36 5.1, E36-W3 6.7, E33-W2 6.0) |

### §5 Top of the ranking (segments, hooks, cliffs, W-L-T)
| Row | Status | Source (promos.json) |
|---|---|---|
| #1 E32-W1 single 35s, E32 1:59.6–2:34.4, 19-0-0 | VERIFIED | start 119.6 end 154.38 (dur 34.8≈35s); record 19-0-0 |
| #2 E15-W1 single 39s, E15 0:47.4–1:26.0, 17-1-1 | VERIFIED | 47.4–86.0 (38.6s); 17-1-1 |
| #3 E13-W2 single 42s, E13 0:47.2–1:28.8, 14-2-3 | VERIFIED | 47.2–88.8 (41.6s); 14-2-3 |
| #4 E16-W1 single 38s, E16 0:14.4–0:52.2, 16-1-2 | VERIFIED | 14.4–52.2 (37.8s); 16-1-2 |
| #5 E03-W2 single 26s, E3 0:58.3–1:23.9, 13-3-3 | VERIFIED | 58.3–83.9 (25.6s); 13-3-3 |
| X06-E25E36 (#10, E25 0:18.8–0:33.8 + E36 2:33.5–3:16.8) | VERIFIED | rank 10; segs 18.8–33.8 + 153.5–196.8 |
| X09-E05E07 (#15, E5 0:54.0–1:04.6 + E7 0:22.0–1:09.5) | VERIFIED | rank 15; segs 54.0–64.6 + 22.0–69.5 |
| "full list of 93" | VERIFIED | promos.json has 93 ranked |

Hook/cliffhanger text lines spot-checked against promos.json fields and READINESS spot-check (verbatim in pack). No hallucination found.

---

## Page 2

### §6 What went wrong → what changed (v1 → final)
| Row | Status | Source |
|---|---|---|
| Raw clips meeting 20–60s / hook ≤3s: 84% / 81% → 100% / 100% | VERIFIED | BASELINE_v1.md 84%/81%; RESULTS.md 100% |
| Clip endings re-cut by code: 21 of 105 → 0 | VERIFIED | RESULTS.md "21 of 105"; final 0 |
| Tied scores in ranking: 81% → 0% | VERIFIED | BASELINE_v1.md 81%; RESULTS.md ties 0% |
| Same clips judged twice: Spearman 0.68, top-10 30% → 0.75–0.90, top-5 80–100% | VERIFIED | RESULTS.md 0.68/30%; JEV_RESULTS.md 0.90 & top-5 80–100%; ANALYSIS final 0.75 |
| Same-story pairs in top 20 (cosine ≥0.86): v1 4 (incl Ep1/Ep2 recap) → final 2 (recap removed; E15/E16, E03 W1/W2 remain) | UNSUPPORTED (see item U2) | v1 "4 pairs" VERIFIED (RESULTS.md). Final "2" is NOT in any file: RESULTS.md/ANALYSIS.md report v2 = 3 pairs at 0.86 and name E31/E32, not E15/E16+E03. The two named pairs ARE both in v3_final top-20 (confirmed), but the count "2" and this pairing are hand-asserted, not computed from v3_final. |
| Multi-part/cross: v1 3, best rank #43 → 19 two-part + 4 cross, 2 in top 20 | VERIFIED | RESULTS.md "3 multi-segment, best #43"; promos.json: 19 same-ep two-part + 4 cross; top-20 cross = X06, X09 (2) |
| Judging time per show: ~30 min, quota-bound → ~20 s, $0.049 (Jev) | VERIFIED | JEV_RESULTS.md ~30 min vs ~20 s; meta cost $0.04852 |
| Runs on new show: exact format only → 10 format tests pass + synthetic show run | VERIFIED | tests/test_parser.py printed "parser tests passed: 10 format variants…"; runs/new_show_test exists |

### §7 Real-life tests
| Claim | Status | Source |
|---|---|---|
| A. Planted hooks, 29 episodes | VERIFIED | REALWORLD_RESULTS.md |
| "hook found 90% 26/29" | VERIFIED | 26/29=90% |
| "clip starts on it 86% 25/29" | VERIFIED | 25/29=86% |
| "decoy tagged 0% 0/29" | VERIFIED | 0/29 |
| "random tagger 13%" (planted-hook block) | VERIFIED | REALWORLD_RESULTS.md random 13% |
| B. Cliffhanger: "free lite model 94% 47/50" | VERIFIED | 47/50=94% |
| B. "Vertex 3.5-flash 82% 41/50" | VERIFIED | 41/50=82% |
| B. "random tagger 22%" (cliffhanger block) | WRONG (see item W1) | Sources give two baselines: 18% (lite) and 26% (v3). Neither is 22%. 22% is a hard-coded, unsourced average. Fix: show 18% / 26%, or label as the mean of the two. |
| "All p < 10⁻¹⁶ vs chance" | VERIFIED | p = 2.2e-31, 1.3e-16, 2.8e-20 (all < 1e-16) |
| "3.5-flash finds planted hooks better (90% vs 83%; clips 86% vs 66%)" | VERIFIED | 3.5-flash 90%/86% (REALWORLD_RESULTS.md) vs lite 83%/66% (REALWORLD_RESULTS_lite.md: 24/29=83%, 19/29=66%) |

### §8 Where it picks badly (honest limits)
| Claim | Status | Source |
|---|---|---|
| "Independent AI judges agree only at Spearman 0.26–0.49" | VERIFIED | ANALYSIS.md: Jev vs 3.8-flash 0.26; Jev vs gemma 0.29; gemma vs 3.8-flash 0.49 |
| "two blind audits disagreed on whether v2 beats v1 (p 0.01 vs 0.92)" | VERIFIED | AUDIT (v2_jev) p=0.01; AUDIT (v3_v38) p=0.92 |
| "threshold 0.90 calibrated on this one show" | VERIFIED | ANALYSIS.md §2 |
| "Jev bias: leans to second-shown (first wins 40%); 20% of pairs flip" | VERIFIED | meta first_position_win_rate 0.403; flip_rate 0.195 |

### §9 Scale, cost & human in the loop
| Claim | Status | Source |
|---|---|---|
| "50 tag calls (236k in / 119k out tokens, ≈ $1.43 at $1.50/$9 per M)" | VERIFIED | meta tokens 236200/119792; computed $1.432 |
| "~650 Jev requests (1.2M tokens, $0.049)" | VERIFIED | meta jev requests 660 (~650), input_tokens 1,155,158 (~1.2M), cost $0.04852 |
| "Half the pairs give the same order (Spearman 0.99): ranking cost can halve" | VERIFIED | ANALYSIS.md/JEV_RESULTS.md half-pairs 0.99 |
| "editor reviews ~20 ranked clips" | VERIFIED | shortlist_size 20 |

### §10 Built to run again
| Claim | Status | Source |
|---|---|---|
| "10 format tests pass; parser handles bold/plain, bracket/SRT/h:mm:ss/seconds, sluglines, missing headers" | VERIFIED | tests/test_parser.py passed live (10 variants) |
| "new synthetic 4-episode show … 23 candidates, 0 violations, 2 cross-episode promos in its top 3" | VERIFIED | new_show_test/meta.json: episodes 4, candidates 23, rule_violations 0; top-3 = X03-E03E04(#1), E03-W1(#2), X01-E01E02(#3) → 2 cross in top 3 |
| "PROMO_TAG_MODEL / PROMO_RANK_MODEL any LiteLLM string; Jev optional; No keys → demo.py" | VERIFIED | promo/llm.py model_for(); demo.py (READINESS_REVIEW) |

### §11 AI tools used, and where they got it wrong
| Claim | Status | Source |
|---|---|---|
| "Kiro (Claude); Gemini 3.5/3.1 Flash(-Lite) via AI Studio + Vertex; Gemma as auditor; TypeSafe Jev as judge" | VERIFIED | meta models; audits gemma/3.8-flash; judge jev |
| "Wrong #1: told 20–60s, LLM returned 9–160s clips; patching in code damaged endings; fix = stop asking for arithmetic" | VERIFIED | SOLUTION.md L46 |
| "Wrong #2: 9.5/10 self-score meant nothing (Spearman ≈ 0); assistant read daily quota error as per-minute and kept retrying" | VERIFIED | SOLUTION.md L46; BASELINE self-score Spearman 0.27/-0.13 (≈0) |
| "Next: 30–40 blind editor ratings; vision check of first 3s" | VERIFIED | narrative/plan; consistent with ANALYSIS next-step |

### Sources footer
"experiments/BASELINE_v1.md · RESULTS.md · JEV_RESULTS.md · REALWORLD_RESULTS*.md · AUDIT_*.md · ANALYSIS.md · runs/v3_final/meta.json" — all exist. VERIFIED.

---

## WRONG / UNSUPPORTED items with fixes

- **W1 (WRONG) — §7 cliffhanger chart "random tagger 22%".** No source value is 22%. The sources give
  18% (v2 lite baseline) and 26% (v3 Vertex baseline) in REALWORLD_RESULTS.md. The 22% is hard-coded
  in build_deck.py (line 180) and matches neither bar above it (94% is the lite model, 82% is Vertex,
  which have 18% and 26% baselines respectively). **Fix:** replace with 18% / 26% (one per model), or
  label it explicitly as "≈22% avg" if a single bar is required.

- **U1 (UNSUPPORTED) — §3 "3,727 beats".** Appears only in deck/build_deck.py and SOLUTION.md; no
  run artifact in the provided sources records a total beat count. The nearest derivable figure from
  diagnostics (sum of max tagged beat-id per episode) is ~3,677, a lower bound, not a confirmation.
  **Fix:** emit the beat count into runs/v3_final/meta.json (or diagnostics) and cite it, or soften to
  "~3,700 beats."

- **U2 (UNSUPPORTED) — §6 "Same-story pairs in top 20 (cosine ≥0.86): final 2 (E15/E16, E03 W1/W2
  remain)".** The v1 "4" is verified, but the final "2" and this specific pairing are not in any file.
  RESULTS.md/ANALYSIS.md report the post-fix count as **3** pairs at the 0.86 threshold and name the
  E31/E32 dungeon pair — a different run (v2), and both docs are flagged stale-vs-v3 in
  READINESS_REVIEW. The two named pairs (E15-W1/E16-W1, E03-W1/E03-W2) are both genuinely in the
  v3_final top-20 (confirmed from promos.json), so the statement is plausible, but the count "2" at
  cosine ≥0.86 is hand-asserted in build_deck.py, not computed from v3_final. **Fix:** recompute the
  cosine-≥0.86 same-story pair count on runs/v3_final top-20 and cite it, or drop the exact "2".

---

## Brief coverage (Kuku assignment)
Required elements — problem picked & why (§1), assumptions (§2), how it works (§3), how it scales
(§9/§10), how we know it's good incl. where it fails (§5/§6/§7/§8), AI tools used + one place they
went wrong (§11, two examples) — are all present; doc is exactly 2 pages (pdftotext page markers 1/2,
2/2). VERDICT: brief fully covered, well within the 2-page limit.
