# Readiness Review — Promo Finder (Problem 1)

Independent reviewer. Did not build this. Every claim checked against files/commands this session.
Scope: is everything ready EXCEPT the solution-doc PDF (which gets built next from this evidence)?

## Verdict: READY_FOR_DOC

The three CRITICAL_REVIEW blockers that were in scope are fixed: a git repo now exists with a clean
tree, the confidential runs (v1/v2_*/v3_final) and the input pack are NOT tracked, and the main
run path (`run.py`) takes the show folder as a positional arg with a clear no-key error. The one
remaining blocker from CRITICAL_REVIEW — "no PDF, stale SOLUTION.md, wrong numbers" — is the
solution doc itself, which is explicitly out of scope and will be built from this evidence. Nothing
else is blocking. The remaining items are cosmetic.

## Fixed since CRITICAL_REVIEW

- **Git repo now exists, working tree clean.** `git log`: 2 commits; `git status --short`: empty.
  CRITICAL_REVIEW said "no git repo at all" — fixed.
- **Confidentiality of runs is now correct.** `git ls-files` (51 files) tracks ONLY
  `runs/new_show_test/` (synthetic). v1, v2_llm, v2_jev, v3_final are untracked.
  `.gitignore` has `runs/*` + `!runs/new_show_test/` and `I Married a Broken Soldier*/`. The two
  tracked `experiments/AUDIT_outputs_*` files are process notes with aggregate scores only — no
  script text. `grep` of `runs/new_show_test/*` for Juliana/Alexander/Catherine/Duke → 0 hits
  (it is the synthetic "CEO twin" show). CRITICAL_REVIEW's "runs contain verbatim dialogue and
  are not git-protected" risk is resolved by not committing them.
- **Main path has no hard-coded show.** `run.py` takes `folder` positional; `grep "Broken Soldier"`
  in `run.py`/`promo/pipeline_v2.py`/`promo/parser.py` → none. Clear keyless error present in
  `run.py` ("No GEMINI_API_KEY or VERTEX_API_KEY ... python demo.py runs/new_show_test").
- **No-key demo path added.** `demo.py runs/v3_final` and `demo.py runs/new_show_test` both run
  offline and print full promos — addresses CRITICAL_REVIEW's "no offline path for a keyless
  reviewer."
- **New-show interview test is real and passing.** `tests/test_parser.py` → "parser tests passed:
  10 format variants". `tests/fixtures/new_show/` is a 4-episode show in a different format (bracket
  times, SCENE/INT. sluglines, no bold labels, no header fields) and produced
  `runs/new_show_test` with **0 rule violations** (`meta.json`: episodes 4, candidates 23, ranked 6,
  rule_violations 0, judge jev).
- **Model is swappable per role.** `promo/llm.py`: `model_for()` reads `PROMO_<ROLE>_MODEL`
  (tag/screen/rank/explain/audit), plus `VERTEX_API_KEY` and `TYPESAFE_API_KEY` switches and
  per-role fallback chains. No code change to swap.

## Still blocking

None in scope. (The only open CRITICAL_REVIEW blocker is the PDF/doc rewrite, which is the next
step and explicitly excluded.)

## Minor issues (fix during doc build or ignore)

- **Report header mislabeled.** `runs/v3_final/report.md` line 1 reads "Promo report (v2)" though it
  is the v3 run; same in `new_show_test/report.md`. Cosmetic; CRITICAL_REVIEW flagged it, still there.
  One-line fix in `promo/report_v2.py`.
- **`promo/config.py` keeps a `DEFAULT_SHOW` default** pointing at the pack (env-overridable via
  `PROMO_SHOW`). It is NOT imported by the main pipeline (only `report_v2` imports `model_for` from
  llm), so it does not affect `run.py`. Used by UI/experiment scripts only. Harmless but a reviewer
  skimming `promo/` will see the show name hard-coded — consider dropping the default.
- **`experiments/ANALYSIS.md` spot-check is stale vs v3.** Its "top 5" still lists E31-W1 + E32-W1
  as the duplicate dungeon pair; in v3 E31-W1 was dropped as a dup of E32-W1. This is process notes,
  not the submitted artifact, but the doc must NOT reuse that anecdote.
- **Ugly tracked filenames** (`AUDIT_outputs_outputs_v2_outputs_v2_jev*.md`). Cosmetic.
- **`.DS_Store` present locally** (gitignored). Delete before packaging.
- **run_v1.py / promo/pipeline.py / qa.py / experiment.py** kept for the v1 A/B. Defensible, but a
  senior reviewer reads it as unpruned. No stale `outputs_*` or `run_v2.py` refs found in tracked
  `.py`/`.md`.

## Brief-requirement checks (all present in runs/v3_final, 50 episodes)

- `meta.json`: episodes 50, candidates 176, ranked 93, rule_violations 0, judge jev, cost $0.04852.
- Per-promo fields complete (`promos.json` keys): segments (episode+start+end each), hook,
  cliffhanger, why, rank, record, bt. 0/93 promos outside 20–60s.
- Hook sits at clip start by construction (segment[0].start == hook_beat start); demo prints hook as
  the opening line for all top 10.
- Cross-episode promos present: 4 cross-episode (e.g. X06-E25E36: Ep25 18.8–33.8 + Ep36 153.5–196.8)
  and 19 stitched same-episode in the 93.
- Quality/failure section honest: `ANALYSIS.md` §6 — judges agree only Spearman ~0.26–0.49,
  "self-consistency is not validity," picks "not proven" preferred by people; named weak picks
  (weak-cliff cases). `REALWORLD_RESULTS.md` has non-LLM ground truth.

## Spot-check: 5 of top-10 vs the actual pack (no hallucination)

- **#1 E32-W1** hook "Silence! Silence!" → verbatim at `episode-032…txt:376`. Open cliff (eye-branding
  unresolved). ✓
- **#2 E15-W1** thug shoves Juliana / club in garden → matches logline + action lines 2,20,24,28. ✓
- **#4 E16-W1** "catches the weapon mid-air in his bare hand" + "Gerald Harrington paid us" →
  verbatim `episode-016…txt:68,188`. Cliff = reaction to confession, open. ✓
- **#5 E03-W2** "Guards! Remove her!" → verbatim `episode-003…txt:207`. Open cliff. ✓
- **#7 E23-W1** "Someone is poisoning her." → verbatim `episode-023…txt:172`. Open cliff (who's at the
  door). ✓
All five: hook at 0.0s, open ending, notes grounded in the script. 0/5 hallucinated.

## 6–10 facts/numbers the doc must lead with (with source)

1. **100% rule compliance by construction** — 0/93 promos outside 20–60 s; hook at clip start;
   `rule_violations: 0`. Source: `runs/v3_final/meta.json`, `promos.json`.
2. **All 50 episodes, 176 candidates → 93 ranked, 83 dups removed.** Source: `runs/v3_final/meta.json`.
3. **Picking fixed vs v1:** raw compliance 84% (v1, LLM picks boundaries) → 100% (LLM tags, code
   builds clips); 0 invented beat IDs in 500 tags. Source: `README.md`, `experiments/ANALYSIS.md`.
4. **Tagger validated on non-LLM ground truth:** writers' episode-ending cliffhanger found in
   82–94% of episodes (vs 18–26% by chance); planted shocking lines tagged as hooks 90%, neutral
   decoys 0/29. Source: `experiments/REALWORLD_RESULTS.md`.
5. **Ranking is reproducible, not yet valid:** Jev split-half Spearman 0.75 (final run)–0.90 vs 0.44
   for the free LLM ranker; full judging ~20 s / ~$0.05 per show. Independent AI judges agree only
   Spearman 0.26–0.49 — "process proven, picks not human-validated." Source: `ANALYSIS.md`,
   `JEV_RESULTS.md`, `meta.json` cost $0.04852.
6. **Runs again on a new show live:** parser passes 10 format variants; a differently-formatted
   4-episode synthetic show produced a clean run (0 violations) via `run.py <folder>`. Source:
   `tests/test_parser.py`, `runs/new_show_test/meta.json`.
7. **Model easy to swap:** per-role `PROMO_<ROLE>_MODEL` env vars + Vertex/TypeSafe switches, no code
   change. Source: `promo/llm.py`.
8. **Cross-episode + multi-segment promos supported:** 4 cross-episode, 19 stitched in the 93.
   Source: `runs/v3_final/promos.json`.
9. **Confidentiality:** pack and all runs on it are gitignored; only the synthetic show ships in the
   repo; raw v3_final shared via private link. Source: `.gitignore`, `git ls-files`.
10. **AI-tool-gone-wrong noted** (model returned 9–160 s clips; daily-quota misread). Source:
    `SOLUTION.md` (to carry into the PDF).
