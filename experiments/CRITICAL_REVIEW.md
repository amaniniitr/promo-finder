# Critical Review — Promo Finder (Problem 1)

Independent reviewer. I did not build this. Every claim below is checked against files.

## Verdict: NOT READY (small, fixable gaps; ~1–2 hours of work)

The engineering is genuinely strong and the top picks are real: I pulled the clip scripts for the
top 8 and the hooks land at 0.0s and the cliffhangers are open questions that match the actual
screenplay lines (no hallucination found in 8/8 checked). The pipeline enforces 20–60s and
hook-in-3s by construction (`runs/v3_final/meta.json`: `rule_violations: 0`), covers all 50 episodes,
produces per-segment timestamps, hook, cliffhanger, one-line why, a ranking with pairwise evidence,
and an honest quality section. But it is **not submittable as-is** for three concrete reasons:
(1) there is **no solution-doc PDF** — only `SOLUTION.md`, and the brief requires a PDF ≤2 pages;
(2) `SOLUTION.md` is **stale** — it documents v2 as the current system while the stated "current best
output" is v3 (Vertex tagger, cross-episode promos, posting plan, written notes), none of which
appear in the doc; (3) several **numbers in the doc are wrong vs the v3 runs/v1** (cost, the
headline "where it fails" dedupe example is already fixed in v3). None of these are deep; they are
communication/packaging failures on an otherwise well-built prototype. Fix the doc and export a PDF
and this becomes a strong submission.

## Done and verified

- **All 50 episodes covered.** `runs/v3_final/meta.json` → `"episodes": 50`; input pack has 50 `.txt`
  files (`ls .../*.txt | wc -l` = 50).
- **Per-promo required fields present.** `runs/v3_final/report.md` and `promos.json` give, per promo:
  episode + start/end of every segment in order (e.g. `#6 E03-W1 stitched: Ep3 01:24.00-01:40.80 +
  Ep3 01:44.20-02:25.75`), hook, cliffhanger, one-line why.
- **20–60s + hook-in-3s enforced in code, not asked of the model.** `promo/moments.py` builds windows
  from tagged beats; `check()` re-verifies; `meta.json rule_violations: 0`. Spot-checked top 8: all
  durations 25.6–58.9s, every hook beat at clip start (0.0s).
- **Hooks/cliffs are not hallucinated.** Read clip scripts for E32-W1, E15-W1, E13-W2, E16-W1,
  E03-W2, E23-W1, E13-W1, E31-W4 via `clip_script()`. Each note's quoted line is verbatim in the
  script (e.g. E03-W2 hook "Guards! Remove her!" at 0.0s; cliff ends "...let her go." unresolved).
- **Ranking with reasons.** Top 20 ordered by Bradley-Terry over all-pairs, both orders; W-L-T and BT
  strength shown (`report.md` table). E32-W1 = 19-0-0, BT +1.79, #1.
- **Quality / failure section is honest and real.** `experiments/ANALYSIS.md` §6 states plainly:
  judges agree with each other at only Spearman ~0.26–0.49, "self-consistency is not validity," and
  "not proven that any version picks promos people prefer." That is the right admission.
- **Confidentiality basics correct.** `.gitignore` excludes `.env`, `.venv/`, `.cache/`, and
  `I Married a Broken Soldier*/`. The input pack folder lives OUTSIDE `promo-finder/`, so a repo
  rooted at `promo-finder/` would not contain the scripts.
- **Model is swappable** as claimed: every role reads an env var (`PROMO_TAG_MODEL`,
  `PROMO_SCREEN_MODEL`, `PROMO_RANK_MODEL`, `PROMO_EMBED_MODEL`, `TYPESAFE_API_KEY`) via LiteLLM; no
  code change needed to swap. Verified in `llm.py`/`diversity.py`/`moments.py` usages.
- **Multi-segment + cross-episode supported.** `build_windows` (stitched) and `build_cross` produce
  two-part and cross-episode promos; both appear in v3 top 20 (e.g. X06-E25E36 at #10).

## Gaps vs brief (BLOCKING)

1. **No solution-doc PDF.** Brief: "Solution doc — Yes — PDF, up to 2 pages." Only `SOLUTION.md`
   exists (`find promo-finder -name '*.pdf'` → none; the only PDF is the brief itself).
   `SOLUTION.md` is **992 words** (`wc -w`) — that will likely exceed 2 pages once rendered with the
   two tables; needs a trim + PDF export. **BLOCKING: no required deliverable.**

2. **Solution doc is stale — describes v2, not the "current best" v3.** The task names
   `runs/v3_final` as current best. `SOLUTION.md` never mentions v3, "cross-episode," "Vertex," or the
   "posting plan" (`grep` → zero hits), yet all four are in v3 and in the README. Its comparison
   table is only "v1 | v2." A reviewer reading the doc would not know what the submitted runs/v1
   actually are. **BLOCKING: doc does not match submitted artifact.**

3. **Doc numbers contradict the v3 runs/v1.**
   - Cost: `SOLUTION.md` says "~$0.03 per show" (lines 35, 49). `runs/v3_final/meta.json` →
     `jev_usage.cost_usd = 0.04852` for the actual full run. ~60% understated.
   - "Where it still fails" headline example is already fixed: doc says "#1 and #3 are the same
     dungeon scene (similarity 0.895, just under the 0.90 threshold)." In v3,
     `diagnostics.json` shows that pair recomputed at **cosine 0.919 and E31-W1 was DROPPED** as a
     duplicate of E32-W1. So the flagship failure anecdote no longer applies to the submitted run.
   - `candidates`: doc/ANALYSIS lean on "138 candidates"; v3 `meta.json` → 176 candidates, 93 ranked,
     83 duplicates removed. Different run, not reconciled in the doc.
   These make the doc look careless even though the system is fine.

4. **"AI tool that went wrong" is present** (SOLUTION.md: model returned 9–160s clips; daily-quota
   misread). Satisfies the brief. Keep it.

## Should improve (NON-BLOCKING)

- **No git repo at all.** `git rev-parse` fails in both `promo-finder/` and parent. "Prototype link"
  wants a repo/host. Nothing is committed, so the correct `.gitignore` has never actually protected
  anything. `git init` + verify the pack is ignored before any push.
- **README run steps use `.venv/bin/python`, not `python run_v1.py`** as the top line implies. A fresh
  clone: `pip install -r requirements.txt` works, but **nothing runs without `GEMINI_API_KEY`** (tag,
  screen, and **embeddings** all call Gemini; `diversity.embed` → `gemini/gemini-embedding-001`).
  Without `TYPESAFE_API_KEY` it falls back to LLM judges (documented). There is **no offline/demo
  path** — a reviewer with no key cannot see it run; they can only read `runs/v3_final/`. Worth a
  `--dry-run`/cached-replay note or a hosted demo.
- **Too many output folders / versions committed.** 7 `runs/v1*` dirs + `run_v1.py` (v1) + `run.py`
  + `experiment.py`, `qa.py`, `jev.py`, `rerank.py`, `diversity.py` plus v1 `pipeline.py`/`report.py`
  kept "for comparison." A senior reviewer will read this as unpruned. For submission, keep
  `runs/v3_final` as the raw runs/v1 and archive the rest.
- **Report header is mislabeled.** `runs/v3_final/report.md` line 1 says "Promo report (v2)" — it is the
  v3 run. Cosmetic but looks sloppy in the raw runs/v1.
- **`.DS_Store` files scattered** (root, `promo/`, `.venv/`). Gitignored, but delete before packaging.

## Architecture / design weaknesses a senior reviewer would flag

- **Quality is unvalidated by any human.** Every "better" claim rests on LLM/Jev judges that agree
  with each other at only ~0.26–0.49 Spearman (ANALYSIS §6). The doc admits this, which is good, but
  it means the ranking's *validity* is unproven — only its *reproducibility* is.
- **Judge disagreement undercuts the headline.** The gemma audit said v2 > v1 (p=0.01); the stronger
  3.8-flash audit saw no significant difference (all p≥0.58). The honest read is "process fixed,
  picks not proven" — and the doc should lead with that, not the earlier favorable number.
- **Threshold overfitting to one show.** `DEDUPE_THR = 0.90` was "calibrated on known cases" from
  this single show (Ep1/Ep2 recap). On a new show the right threshold is unknown; this is explicit
  single-show tuning. Same risk for the `EP_END_STRENGTH = 7.0` auto-cliff and the 60–240s stitch
  band.
- **Cost claim partly unverified.** Jev cost is measured ($0.0485), but "well under $1/show on paid
  Gemini" is "estimated from list prices, not measured" (doc admits it).
- **Cross-episode standalone risk.** X06-E25E36 (#10) joins an Ep25 hook to an Ep36 cliff — 11
  episodes apart. "Makes sense to someone who's never seen the show" is doubtful for a clip stitched
  across a third of the season; only a shared-speaker check guards coherence, not narrative sense.

## Parser: what breaks on a new show (the interview test)

`run.py` will run on any folder of `.txt`, but `promo/parser.py` hard-codes this show's exact
format. Concrete assumptions that will silently break on a differently-formatted pack:
- **Episode number** must be `EPISODE NUMBER: Episode <n>` (`RE_EP_NUM`). Any other header →
  `.group(1)` on `None` → crash.
- **Scene headers** must be `SCENE 01` on its own line (`RE_SCENE`, `^SCENE\s+\d+\s*$`). `INT./EXT.`
  slug lines, "Scene 1:", or numbered `1.` → scene stays 0.
- **Timestamps** must be `Start: (mm:ss.ss) | End: (mm:ss.ss)` on the line immediately after a
  `**LABEL:**` line (`RE_TIME`, `RE_LABEL`). Different label syntax (ALL-CAPS name with no `**`,
  `[VO]`, HH:MM:SS, frame counts, or timestamps inline) → **zero beats parsed**, and every downstream
  step produces nothing with no clear error.
- **Logline/continuity** are optional (defaults to ""), so those degrade gracefully — the one soft spot.
- **Speaker/emotion** parsing assumes `NAME (Emotion)`; other conventions just mislabel, not fatal.
- **Hard-coded show path** in several files: `app.py:19 DEFAULT_SHOW = .../I Married a Broken
  Soldier...`, and `--show` defaults in `experiment.py`, `qa.py`, `experiments/jev_experiment.py`,
  `experiments/audit_nway.py`, `experiments/scripts/screen_4samples.py`. The main `run.py` takes
  the folder as a positional arg (good), but the UI and every experiment default to this show. In the
  interview, a new show with ReelShort-style formatting would likely parse to zero beats.

## Confidentiality

- **No script text leaks from `promo-finder/`** as structured: `promos.json`/`report.md`/`diagnostics.json`
  contain **quoted dialogue and action lines** from the Kuku scripts (e.g. clip scripts, hook quotes
  "Silence! Silence!", full beat text in `all_candidates`). These ARE Kuku content. If the repo is
  made public *with* `runs/v3_final/` included, **substantial verbatim screenplay excerpts would be
  published** — this violates the confidentiality clause. `.gitignore` protects the raw pack but NOT
  the runs/v1, and the brief requires sharing raw runs/v1 via a link, so the candidate must share
  runs/v1 via a private/link-restricted location, not a public repo.
- `.gitignore` for the pack is correct (`I Married a Broken Soldier*/`), `.env` is ignored. **No git
  repo exists**, so nothing is committed yet — the moment to get this right.

## Remaining work, ranked by value per hour

1. **Rewrite SOLUTION.md to describe v3, fix the numbers, export to PDF ≤2 pages.** (~1.0h)
   Biggest value: it is a required deliverable, it is currently wrong, and the doc is 60% of the
   evaluation lenses. Lead with "process proven, picks not yet human-validated."
2. **Decide how raw runs/v1 are shared without leaking script text.** (~0.25h) Private Drive/link,
   not a public repo. State it in the doc.
3. **`git init`, confirm pack + .env ignored, fix `runs/v3_final/report.md` "(v2)" label, delete
   `.DS_Store`, archive extra `runs/v1*` dirs.** (~0.5h) Makes the prototype link clean.
4. **Add a no-key demo path** (replay from `runs/v3_final/` in `app.py`, or a 1-line note that reviewers
   read the folder). (~0.5h) Lets a keyless reviewer "see it run."
5. **Add a one-paragraph "parser assumptions / what to change for a new format" note** to the doc.
   (~0.25h) Directly answers the interview "run on a new input" test and shows you know the limits.
6. **(Optional, higher effort) Rate ~40 blind clips yourself as a human anchor.** (~1.5h) Turns the
   honest "unvalidated" caveat into at least one human data point — the single biggest credibility
   win if time allows.

## Evidence log

- Brief requirements: `pdftotext -layout "Kuku — AI Generalist Assignment.pdf"` — Problem 1 fields,
  PDF ≤2pp, prototype link, raw runs/v1 on full pack, AI-tool-gone-wrong.
- Coverage/rules: `runs/v3_final/meta.json` (episodes 50, rule_violations 0, candidates 176, ranked 93,
  dups 83, jev cost 0.04852, judge jev); `ls .../*.txt` = 50.
- Field presence + ordering: `runs/v3_final/report.md` lines 1–70 (table + posting plan + per-promo).
- Hallucination check (8/8 clean): `clip_script()` via `.venv/bin/python` for E32-W1, E15-W1, E13-W2,
  E16-W1, E03-W2, E23-W1, E13-W1, E31-W4 — hooks at 0.0s, cliffs open, quotes verbatim.
- Dedupe "failure" is fixed in v3: `runs/v3_final/diagnostics.json` duplicates → `{dropped E31-W1, kept
  E32-W1, cosine 0.919}`. Contradicts `SOLUTION.md` "0.895, just under 0.90."
- Cost contradiction: `SOLUTION.md` lines 35,49 "~$0.03" vs `meta.json` 0.04852; `JEV_RESULTS.md:55`
  "$0.0525"; `ANALYSIS.md:107` "$0.027 for a full run." Three different figures.
- Doc currency: `grep "v3|cross-episode|Vertex|posting plan" SOLUTION.md` → 0 hits; README line 61
  lists v3 as current.
- Parser assumptions: `promo/parser.py` (RE_EP_NUM, RE_SCENE, RE_TIME, RE_LABEL); input sample
  `episode-001...txt` lines 1–40.
- Hard-coded paths: `grep "Broken Soldier"` → `app.py:19`, `experiment.py:30`, `qa.py:16`,
  `experiments/jev_experiment.py:25`, `experiments/audit_nway.py:24`,
  `experiments/scripts/screen_4samples.py:7`.
- Git: `git rev-parse` fails in `promo-finder/` and parent — no repo.
- Confidentiality: `.gitignore` ignores pack + .env + .venv + .cache; runs/v1 contain verbatim
  dialogue (`diagnostics.json all_candidates`, `report.md` clip scripts).
- Embedding/key dependency: `promo/diversity.py` `EMBED_MODEL=gemini/gemini-embedding-001`.
- Doc length: `wc -w SOLUTION.md` = 992.
