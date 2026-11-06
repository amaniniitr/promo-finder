# Real-World Ground-Truth Tests for the Promo-Clip Tool

**Problem.** Our promo-clip tool reads timestamped microdrama screenplays (1–2 min vertical episodes)
and emits 20–60s promos (hook in first 3s, ends on cliffhanger). Every quality signal so far is
LLM-judging-LLM, and judges disagree (inter-judge Spearman 0.26–0.49). We need **ground truth that
does not come from an LLM.**

Research date: 2026-11-07. All links below were fetched and marked **[VERIFIED]** or **[UNVERIFIED]**.

---

## TL;DR ranking (validity of ground truth × feasibility < 4h)

| Rank | Option | GT validity | Feasible <4h | Why |
|------|--------|-------------|--------------|-----|
| 1 | **Own-screenplay structural GT** (episode cliffhanger = last beat, hook = first beat) | Medium-High (writer-designed, human, not LLM) | ✅ Yes | Uses data we already have; zero download; real human authorial intent |
| 2 | **Planted-signal recall test** | High (we define the answer key) | ✅ Yes | Deterministic; isolates whether the ranker *finds* known strong lines |
| 3 | **TRIPOD scene-level turning-point labels** | High (human screenwriting-theory annotation) | ✅ Yes | Text-only, scene-indexed, free, directly maps "promo-worthy moment" |
| 4 | **Mr.HiSum "most replayed"** (text-only via subtitles) | High (50k+ real viewers) | ⚠️ Borderline (subtitle crawl + align) | Real engagement GT, but needs yt-dlp caption pull + alignment |
| 5 | **TVSum / QVHighlights saliency** | Medium (20 raters, generic web video) | ⚠️ Borderline | Human scores but domain gap + mostly visual |
| 6 | **Small human rating protocol** (we run it) | Highest (our exact task) | ❌ Not <4h to recruit, ~setup only | Gold standard but needs raters; prep tonight, run later |
| 7 | **ReelShort/DramaBox promo ads via Meta/TikTok** | High in principle (real engagement, exact domain) | ❌ No | ToS + no reliable per-ad engagement numbers + matching transcripts is hard |

---

## Direction 1 — Screenplay datasets with trailer/turning-point labels

### TRIPOD — TuRnIng POint Dataset  **[VERIFIED]**
- URL: https://github.com/ppapalampidi/TRIPOD
- **Ground truth:** For each movie, human-annotated **turning points** (5 TPs from screenwriting theory:
  Opportunity, Change of Plans, Point of No Return, Major Setback, Climax). Crucially, for the **test set**
  it ships `TRIPOD_screenplays_test.csv` with **scene-level gold TP labels** = "list of screenplay scene
  indices corresponding to each TP." Synopsis TP labels (sentence index) for train+test.
- **Licence/access:** Public GitHub repo, free, no registration. (Screenplays sourced from ScriptBase;
  cite accordingly. No explicit SPDX licence file — treat as research-use.)
- **Size:** 99 movies; screenplays + IMDb meta + synopses. Small but each is scene-segmented.
- **Maps to our task:** A turning point is the movie-scale analogue of our "promo-worthy moment / cliffhanger."
  Scene-level labels give a per-scene binary/graded relevance we can treat as ground truth for "this scene is
  a key dramatic beat." Our ranker should score gold-TP scenes above filler scenes.
- **Effort to adapt:** ~2–3h. Parse `screenplays_scene_segmentation.py` output + `TRIPOD_screenplays_test.csv`,
  run our scorer over each scene's text, compare.
- **Metric:** For each test movie, rank scenes by our promo-score; compute **Precision@k / mAP** against
  gold TP scenes, and **Spearman** between our scene scores and a TP-proximity score. Report mean over ~30 test movies.

### Film Trailer Generation / "Finding the Right Moment" (Papalampidi, Keller, Lapata)  **[VERIFIED paper]**
- URLs: https://arxiv.org/abs/2111.08774 (TPAMI "Finding the Right Moment"), https://arxiv.org/html/2111.08774v2
- **Ground truth:** "**Trailer Labels**" = shots in the **official trailer** matched back to the movie →
  binary per-shot "went into the trailer." Built on **TRIPOD-L** (122 screenplays, scene-level silver TP
  labels + corresponding videos). This is *exactly* the "this went into the promo" label requested.
- **Licence/access:** Paper CC BY-SA 4.0 **[VERIFIED]**. BUT the per-shot trailer-match labels + video
  features are **not cleanly released as a standalone download** — they depend on copyrighted movie/trailer
  video and MovieNet features. **[UNVERIFIED that labels are downloadable]**. Practically: use the *method*
  (match official trailer to source) as a recipe, not a ready dataset.
- **Maps to our task:** Direct conceptual match (trailer = promo). But it's shot/video-level and gated by
  video access, so not text-only out of the box.
- **Effort:** High (10h+) to reconstruct; **not** a <4h option. Keep as the theoretical justification for
  "trailer-membership = promo ground truth."
- **Metric (if reconstructed):** per-shot ROC-AUC / AP of our score vs trailer-membership.

### MovieSum  **[VERIFIED]**
- URL: https://huggingface.co/datasets/rohitsaxena/MovieSum
- **Ground truth:** 2,200 screenplays (XML: `<scene>`, `<stage_direction>`, `<dialogue>`…) each with a
  Wikipedia **plot summary**. GT here is "salient scene" via summary-to-scene alignment, **not** trailer membership.
- **Licence/access:** **CC BY-NC 4.0** [VERIFIED], free, no registration, ~477 MB, 1800/200/200 split.
- **Maps to our task:** Weaker — salient-for-plot ≠ promo-worthy (promos favor hooks/cliffhangers, not
  balanced plot coverage). Useful as a *scene-segmented screenplay corpus* and as a secondary "importance" signal.
- **Effort:** ~2h to load + align, but the GT is only loosely on-task.
- **Metric:** Spearman(our score, scene-appears-in-summary). Report as a weak secondary check only.

### Others (noted, lower priority)
- **MovieNet** — https://movienet.github.io/ **[VERIFIED]**: 1.1M chars, 42K scene boundaries, trailers +
  films, 2.5K aligned description sentences. Rich but **requires registration + huge video**; overkill, not text-only. **[UNVERIFIED download friction]**
- **ScriptBase** — source corpus behind TRIPOD; gated/research-request. Use TRIPOD's extracted scenes instead.
- **MENSA / SUMMER / GraphTP** (ppapalampidi) — screenplay-summarization models/data (CSI gold scene summaries);
  same "salient scene" GT flavor as MovieSum. https://github.com/ppapalampidi/SUMMER **[VERIFIED repo exists]**.
- **IMSDb** — raw screenplay scrape, **no labels** → not ground truth by itself.

---

## Direction 2 — Video-highlight datasets with human scores + subtitles

### Mr.HiSum  **[VERIFIED]**
- URLs: https://github.com/MRHiSum/MR.HiSum , dataset doc
  https://github.com/MRHiSum/MR.HiSum/blob/main/dataset/DATASET.md
- **Ground truth:** YouTube **"Most replayed"** per-segment importance = **real behavior of 50,000+ viewers/video**,
  aggregated. 31,892 videos. This is the strongest *non-LLM, real-engagement* signal available publicly.
- **Licence/access:** Code + labels (frame-importance scores) free on GitHub. `metadata.csv` gives
  `youtube_id, duration, views, labels`. A **crawler** (`crawler.py --vid <id>`) re-pulls most-replayed stats.
  **Subtitles are NOT in the dataset** — you must pull captions yourself (e.g. `yt-dlp --write-auto-subs`).
  YouTube ToS applies to any crawling. **[VERIFIED no subtitles shipped]**.
- **Size:** 31,892 videos; scores already provided as features (video_1…). Big.
- **Maps to our task (text-only):** Yes, with work: take each video's auto-captions, window them to match the
  most-replayed time bins, and test whether our text-only promo-score predicts which caption windows are the
  replay peaks. Domain gap (generic YouTube ≠ microdrama) is real but the GT is genuinely human.
- **Effort:** ~3–5h for a pilot subset (pick ~50 dialogue-heavy videos, pull subs, align to peak bins).
  Borderline for one night.
- **Metric:** Per video, **Spearman(our text-score per window, most-replayed score per window)**; aggregate mean.
  Also **Top-1 peak hit-rate** (does our highest-scored window contain the global replay peak?).

### QVHighlights  **[VERIFIED paper]**
- URLs: https://arxiv.org/abs/2107.09609 , code/data https://github.com/jayleicn/moment_detr
- **Ground truth:** 10,000+ YouTube videos; human free-form query + relevant moments + **5-point saliency
  scores** per clip. Human-annotated.
- **Licence/access:** Public (GitHub), free. **[UNVERIFIED exact licence string]**.
- **Maps:** Saliency is query-conditioned ("moments relevant to this query"), not "promo-worthy / cliffhanger,"
  so it's an indirect match. Subtitles/ASR available for some splits.
- **Effort:** ~3h. **Metric:** Spearman(our score, mean saliency) on clips.

### TVSum  **[VERIFIED]**
- URL: https://github.com/yalesong/tvsum (data now at http://people.csail.mit.edu/yalesong/tvsum)
- **Ground truth:** 50 videos, **20 crowd raters each**, shot-level importance 1–5. **Cronbach α = 0.81**
  (good inter-rater reliability — a useful benchmark for what "real" agreement looks like). Videos CC-BY 3.0.
- **Licence/access:** Free; download page MIT-hosted (Yahoo Webscope retired). Small (50 videos).
- **Maps:** Importance ≈ highlight-worthiness; but genres are how-to/vlog/news, little dialogue → weak text signal.
- **Effort:** ~2h. **Metric:** rank correlation (Kendall τ / Spearman) vs averaged importance — the field's
  standard TVSum protocol.

### SumMe / YouTube Highlights / TVR-TVQA (noted)
- **SumMe** (25 videos, human summaries), **YouTube Highlights** (domain-specific), **TVR/TVQA**
  (TV subtitles + moment annotations, https://tvqa.cs.unc.edu). TVR is the most text-rich (real TV-show
  subtitles) but its GT is moment-retrieval-by-query, not promo-worthiness. Keep TVR as a fallback text corpus.

---

## Direction 3 — Real microdrama promos (ReelShort / DramaBox / Kuku TV)

**Honest verdict: not feasible as clean ground truth tonight, and ToS-risky.**

- **Meta Ad Library** — https://www.facebook.com/ads/library , API docs via Meta.
  - What it gives: creatives currently/recently running. **Engagement/impression numbers are only provided
    for *social-issue/political* ads, and for EU/UK ads (DSA) — NOT for ordinary commercial app-install ads.**
    So ReelShort/DramaBox promo ads will show the *creative* but **no reliable play/engagement metric**.
  - Access: API needs an access token + app review; scraping the web UI violates Meta ToS. **[Engagement for
    commercial ads: UNVERIFIED / generally unavailable]**.
- **TikTok Creative Center "Top Ads"** — https://ads.tiktok.com/business/creativecenter
  - Curated "top ads" showcase, often **login-gated**; metrics shown are relative/curated, not raw engagement.
  - The **DSA Commercial Content API** (https://developers.tiktok.com/products/commercial-content-api) exposes
    ad + advertiser metadata for the ad's run window, **not per-ad play-through/engagement**. Third-party
    scrapers (Apify) exist but their use violates TikTok ToS and numbers are unofficial.
- **Matching promo → episode transcript:** Even if you obtain a promo video, you'd need the matching episode
  script and to transcribe the promo and align — hours of manual work per title, with copyright exposure.

**Recommendation:** Skip for the tonight test. If pursued later, the only defensible path is *your own*
platform's promos + *your own* engagement logs (you have the rights and the numbers) — that becomes the
true gold standard (see Direction 4c).

---

## Direction 4 — Constructing our own ground truth cheaply

### 4a. Screenplay's own structure as GT  **(use what we already have)**
- Each episode is authored to **open on a hook** and **end on a cliffhanger** — human-designed, not LLM.
- **GT construction:** label the first beat of each episode = hook-positive; the last beat before the cut =
  cliffhanger-positive; mid-episode "connective" beats = negative. (Optionally use the *next* episode's cold
  open to confirm the cliffhanger payoff.)
- **Test:** Does our tool's chosen hook land in the episode's opening beat, and its chosen cliffhanger land in
  the closing beat?
- **Metric:**
  - **Hook hit-rate** = fraction of episodes where tool's hook ∈ first N seconds / first scene.
  - **Cliffhanger hit-rate** = fraction where tool's ending ∈ last scene.
  - **Boundary Spearman**: correlate tool's per-beat promo-score with distance-to-episode-boundary
    (expect U-shape: high at start+end). Report over all episodes we have.
- **Effort:** ~1–2h (we own the data; just need beat/scene boundaries + a scoring harness).

### 4b. Planted-signal recall test  **(deterministic answer key)**
- Take **bland/connective** scenes (low drama). Insert a **known strong hook line** and a **known strong
  cliffhanger line** (from a curated bank of ~30 obviously-strong lines, human-written). Also insert
  **decoy neutral lines** as controls.
- **Test:** Does the ranker surface the planted strong line into the promo (hook slot / cliff slot)?
- **Metric:**
  - **Recall@k** of planted lines (planted line appears in top-k selected segments).
  - **Hook/cliff slotting accuracy** (planted hook chosen as hook, planted cliff as cliff).
  - **Decoy false-positive rate** (neutral decoys wrongly promoted) — guards against "promotes anything inserted."
  - Run ≥ 30 planted episodes → Recall@1 with a Wilson 95% CI; also McNemar vs a random-selection baseline.
- **Effort:** ~1–2h. Fully deterministic, no raters, no external data.

### 4c. Small human rating protocol — sample-size math
Goal: a human (non-LLM) check that our promo ranking matches human preference.

**Design A — pairwise preference (recommended; cheapest to get agreement).**
Show raters two candidate promos for the same episode (ours vs baseline / ours-A vs ours-B); they pick the
better hook+cliffhanger. This is a binomial sign test on win-rate p.
- To detect a win-rate of **p = 0.70 vs null 0.50**, two-sided α = 0.05, power 0.80:
  n ≈ (z_α/2 + z_β)² · p(1−p) / (p − 0.5)²  = (1.96 + 0.84)² · 0.21 / 0.04 ≈ **~41 paired comparisons.**
- For a stronger p = 0.75: n ≈ 7.84 · 0.1875 / 0.0625 ≈ **~24 comparisons.**
- Use **≥ 3 raters per pair**, take majority; report **win-rate + 95% Wilson CI** and a binomial p-value.
  Inter-rater agreement: **Fleiss' κ** (target κ ≥ 0.4 = moderate; our current LLM Spearman 0.26–0.49 is the
  bar to beat).

**Design B — absolute rating → Spearman.**
Raters score each promo 1–5; correlate mean human score with tool score.
- Minimum to call a Spearman "real": to show **ρ = 0.5 is significantly > 0** (α = 0.05, power 0.80):
  n ≈ [ (z_α/2 + z_β) / C(ρ) ]² + 3, where C(ρ) = 0.5·ln((1+ρ)/(1−ρ)) = atanh(0.5) = 0.549.
  n ≈ (2.80 / 0.549)² + 3 ≈ 26 + 3 = **~29 clips.**
- To *estimate* ρ with a tight CI (half-width ≈ 0.2 around ρ≈0.5): need **~45–50 clips.**
- **Raters:** 3–5 per clip; report mean, **ICC(2,k)** for reliability, and Spearman of tool-vs-mean-human
  with its bootstrap CI.

**Bottom line:** ~**30 episodes/clips, 3 raters each** gets you a defensible result for either design;
~45–50 if you want tight CIs. Prep tonight, run the rating pass tomorrow.

---

## Recommended plan — 2–3 tests to run tonight

### Test 1 (do first) — Own-structure hook/cliffhanger hit-rate  [Direction 4a]
1. Collect all episodes we have with scene/beat boundaries + timestamps.
2. Label GT: first scene = hook-positive, last scene = cliffhanger-positive, middle = negative.
3. Run the tool; record which beats it picks for the hook slot and the ending slot.
4. **Metric:** Hook hit-rate and Cliffhanger hit-rate (fraction landing in the correct boundary scene),
   each with a Wilson 95% CI; plus boundary-distance Spearman (expect U-shape). Baseline = random beat.
   *Pass bar:* both hit-rates significantly above the random baseline (non-overlapping CIs).

### Test 2 — Planted-signal recall  [Direction 4b]
1. Build a bank of ~30 human-written strong hook lines + 30 cliffhanger lines + 30 neutral decoys.
2. For ≥30 bland episodes, insert one planted hook + one planted cliff (+ decoys) at random positions.
3. Run the tool.
4. **Metric:** Recall@1 for planted hook into hook slot and planted cliff into cliff slot (Wilson CI);
   decoy false-positive rate; McNemar vs random selection.
   *Pass bar:* Recall@1 ≥ 0.7 and decoy FPR near chance.

### Test 3 (if time) — TRIPOD scene-level turning-point ranking  [Direction 1]
1. `git clone https://github.com/ppapalampidi/TRIPOD`; load `TRIPOD_screenplays_test.csv` (gold scene indices
   per TP) and the scene-segmented screenplays.
2. For each test movie, score every scene with our promo-scorer (text-only).
3. **Metric:** mAP / Precision@5 of our top-scored scenes against gold-TP scenes, and Spearman of
   our-score vs TP-proximity; mean across test movies.
   *Pass bar:* mAP meaningfully above a length/position baseline — shows our scorer tracks human-annotated
   dramatic beats on a second, independent, non-LLM corpus.

**Why this set:** Tests 1–2 use data we already own and need zero downloads, give deterministic or
authorial human ground truth, and run in <2h each. Test 3 adds an external, independently human-annotated
corpus (TRIPOD) so the result isn't circular. Mr.HiSum (real 50k-viewer replay data) is the best *external
engagement* follow-up once a caption-pull + alignment pipeline is built (~half a day), and a 30-clip,
3-rater pairwise human study (Design A, ~41 comparisons) is the gold standard to schedule next.

---

## Link verification summary
- **[VERIFIED]** TRIPOD repo (scene-level gold TP labels in test csv) — github.com/ppapalampidi/TRIPOD
- **[VERIFIED]** MovieSum (CC BY-NC 4.0, 2,200 scripts, scene XML) — huggingface.co/datasets/rohitsaxena/MovieSum
- **[VERIFIED]** Mr.HiSum (most-replayed, 31,892 vids, crawler, NO subtitles shipped) — github.com/MRHiSum/MR.HiSum
- **[VERIFIED]** TVSum (50 vids, 20 raters, α=0.81, CC-BY) — github.com/yalesong/tvsum
- **[VERIFIED]** Trailer paper "Finding the Right Moment" (trailer-membership labels concept; CC BY-SA) — arxiv.org/abs/2111.08774
- **[VERIFIED]** MovieNet exists — movienet.github.io ; **[UNVERIFIED]** download friction/registration specifics
- **[VERIFIED]** QVHighlights paper + moment_detr repo — arxiv.org/abs/2107.09609 ; **[UNVERIFIED]** exact licence
- **[UNVERIFIED / likely unavailable]** Per-ad engagement numbers for ReelShort/DramaBox commercial ads in Meta Ad Library / TikTok Creative Center
- **[UNVERIFIED]** Standalone downloadable per-shot trailer labels from TRIPOD-L (gated by copyrighted video)
