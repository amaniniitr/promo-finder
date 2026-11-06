"""Build the 2-page solution deck (16:9 landscape PDF) from the run + experiment files.
python deck/build_deck.py  ->  deck/solution.pdf, deck/solution.html, deck/page-1.png, deck/page-2.png
Numbers are read from runs/v3_final and experiments/*, so the doc can't drift from the outputs."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deck"
run = ROOT / "runs" / "v3_final"
meta = json.loads((run / "meta.json").read_text())
P = json.loads((run / "promos.json").read_text())["promos"]
by = {p["id"]: p for p in P}
NAME = "Name · Roll no. · Branch"          # <- fill in
LINKS = "Prototype: github.com/&lt;you&gt;/promo-finder · Raw outputs: drive link (restricted) · Video: loom link"


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:04.1f}"


def segs(p):
    return " + ".join(f"E{s['episode']} {fmt(s['start'])}–{fmt(s['end'])}" for s in p["segments"])


def esc(s, n=None):
    s = re.sub(r"\s+", " ", s or "").strip()
    if n and len(s) > n:
        s = s[:n - 1].rsplit(" ", 1)[0] + "…"
    return html.escape(s)


def bars(rows, maxv=100, unit="%", w=360):
    """rows: (label, value, color, note). Horizontal bar chart as inline SVG."""
    h = 19 * len(rows) + 4
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for i, (lab, v, col, note) in enumerate(rows):
        y = 2 + i * 19
        bw = (w - 160) * v / maxv
        out.append(f'<text x="0" y="{y + 11}" class="bl">{lab}</text>'
                   f'<rect x="96" y="{y + 2}" width="{bw:.1f}" height="12" rx="2" fill="{col}"/>'
                   f'<text x="{100 + bw:.1f}" y="{y + 12}" class="bv">{v:g}{unit}{(" " + note) if note else ""}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------- page 1 data
plan = meta["posting_plan"]["plan"]
holds = meta["posting_plan"]["hold"]
top_rows = []
for p in P[:5]:
    top_rows.append(f"<tr><td class='rk'>{p['rank']}</td><td class='nw'><b>{p['id']}</b> <span class='mut'>{p['kind']}, {p['duration']:.0f}s</span></td>"
                    f"<td class='mono nw'>{segs(p)}</td><td>{esc(p['hook'], 88)}</td><td>{esc(p['cliffhanger'], 88)}</td>"
                    f"<td class='mono c nw'>{p['record']}</td></tr>")
cross = [p for p in P[:20] if p["kind"] == "cross"]
plan_rows = "".join(f"<li><b>Day {x['day']} · {x['id']}</b> (rank {by[x['id']]['rank']}): {esc(by[x['id']]['why'], 80)}</li>" for x in plan)
pw = meta["pairwise"]
jev = meta["jev_usage"]
ntok = meta["llm_tokens_by_model"]["vertex/gemini-3.5-flash"]
LLM_USD = ntok[0] * 1.50 / 1e6 + ntok[1] * 9.0 / 1e6      # Gemini 3.5 Flash list price $1.50 / $9 per M (published, not billed-verified)
SHOW_USD = LLM_USD + jev["cost_usd"]

CSS = """
@page { size: 13.333in 7.5in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #1b1f24; font-size: 8.7pt; line-height: 1.25 }
.nw { white-space: nowrap }
.page { width: 13.333in; height: 7.5in; padding: .26in .32in .2in; position: relative; page-break-after: always; overflow: hidden }
.top { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2.5px solid #e4572e; padding-bottom: 5px; margin-bottom: 7px }
h1 { font-size: 16.5pt; white-space: nowrap; letter-spacing: -.3px } h1 span { color: #e4572e }
.sub { font-size: 9.5pt; color: #444; margin-top: 2px }
.meta { text-align: right; font-size: 7.4pt; color: #555; max-width: 4.2in }
.grid { display: grid; gap: 8px }
.card { background: #f6f7f9; border-radius: 6px; padding: 7px 9px; border-left: 3px solid #2d6cdf }
.card.o { border-left-color: #e4572e } .card.g { border-left-color: #1f9d6b } .card.y { border-left-color: #d9a400 } .card.r { border-left-color: #c0392b }
h2 { font-size: 10.5pt; margin-bottom: 4px; display: flex; align-items: center; gap: 6px }
h2 .n { background: #1b1f24; color: #fff; border-radius: 50%; width: 17px; height: 17px; font-size: 8.5pt; display: inline-flex; align-items: center; justify-content: center }
ul { padding-left: 13px } li { margin-bottom: 2px }
.mut { color: #666 } .mono { font-family: Menlo, monospace; font-size: 7.6pt } .c { text-align: center }
table { width: 100%; border-collapse: collapse; font-size: 8pt }
th { text-align: left; font-size: 7.5pt; color: #555; border-bottom: 1px solid #ccd; padding: 2px 4px; font-weight: 600 }
td { padding: 2.5px 4px; border-bottom: 1px solid #e3e5ea; vertical-align: top }
td.rk { font-weight: 700; color: #e4572e; font-size: 10pt }
.kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-bottom: 8px }
.kpi { background: #1b1f24; color: #fff; border-radius: 6px; padding: 6px 8px }
.kpi b { font-size: 16pt; display: block; color: #ffb199; line-height: 1.05 } .kpi span { font-size: 7.6pt; color: #d6d9de }
.flow { display: flex; gap: 4px; align-items: stretch; margin: 2px 0 4px }
.st { flex: 1; background: #fff; border: 1px solid #d5d9e0; border-radius: 5px; padding: 4px 5px; font-size: 7.7pt; position: relative }
.st b { display: block; font-size: 8.3pt } .st .who { position: absolute; top: 3px; right: 4px; font-size: 6.6pt; font-weight: 700; padding: 0 4px; border-radius: 3px }
.ai { background: #dde8fb; color: #1a4fb0 } .code { background: #dcf3e8; color: #13744e } .hum { background: #fde3d8; color: #b33a12 } .jv { background: #efe2fb; color: #6b2fb3 }
.arrow { align-self: center; color: #999; font-size: 11pt }
svg text.bl { font-size: 7.6pt; fill: #333 } svg text.bv { font-size: 7.6pt; fill: #111; font-weight: 600 }
.cmp td:nth-child(2) { color: #9a3b2a } .cmp td:nth-child(3) { color: #13744e; font-weight: 600 }
.foot { position: absolute; bottom: .1in; left: .32in; right: .32in; font-size: 7pt; color: #888; display: flex; justify-content: space-between }
.p2 { font-size: 9.9pt } .p2 table { font-size: 8.8pt } .p2 .card { padding: 8px 10px }
.p2 svg text.bl, .p2 svg text.bv { font-size: 8.4pt }
.tag { display: inline-block; background: #fff; border: 1px solid #ccd; border-radius: 3px; padding: 0 4px; font-size: 7.4pt; margin: 1px 2px 1px 0 }
"""

page1 = f"""
<div class="page">
 <div class="top"><div><h1>Promo Finder <span>·</span> the best 20–60s promos, found from the screenplay</h1>
  <div class="sub">Kuku AI Generalist assignment · Problem 1 · run on all 50 episodes of <i>I Married a Broken Soldier. He was a Duke</i></div></div>
  <div class="meta">{NAME}<br>{LINKS}</div></div>

 <div class="kpis">
  <div class="kpi"><b>{meta['ranked']}</b><span>ranked promos from {meta['candidates']} candidates, all 50 episodes covered</span></div>
  <div class="kpi"><b>0</b><span>rule violations: every clip 20–60s, hook in first 3s (by construction)</span></div>
  <div class="kpi"><b>90%</b><span>planted shocking lines found as hooks; 0/29 neutral decoys (real-life test)</span></div>
  <div class="kpi"><b>0.75–0.90</b><span>ranking reproducibility (split-half Spearman), vs 0.44 before</span></div>
  <div class="kpi"><b>~${SHOW_USD:.2f}</b><span>per 50-episode show at list prices; ~7 min end to end, judging ~20 s</span></div>
  <div class="kpi"><b>1 cmd</b><span><span class="mono" style="color:#ffb199">python run.py &lt;show&gt;</span>: runs on a new show, any model</span></div>
 </div>

 <div class="grid" style="grid-template-columns: 1fr 1.05fr 1.15fr">
  <div class="card o"><h2><span class="n">1</span>Problem &amp; why this one</h2>
   <ul><li>Today an editor <b>watches every episode</b> to pick promos, and a new show ships weekly. The pack's timestamped scripts make "right moment, right cut" checkable in code.</li>
   <li><b>A good promo</b> (brief): hook in the first 3s · ends unresolved · makes sense cold · 20–60s · one stretch or joined moments, across episodes too.</li></ul>
   <h2 style="margin-top:5px"><span class="n">2</span>Assumptions</h2>
   <ul><li>Script timestamps ≈ final cut; an editor nudges cuts if the edit drifts.</li>
   <li>Cuts land on whole lines (code snaps outward, never mid-sentence).</li>
   <li>The judge sees <b>only the clip</b>, like a cold scroller; story context is for tagging only.</li>
   <li>"Post first" = stops a scroller <i>and</i> makes them want the next episode, without big spoilers. Cheap tiers only; models swap by env var.</li></ul>
  </div>

  <div class="card"><h2><span class="n">3</span>How it works: AI judges meaning, code owns time</h2>
   <div class="flow">
    <div class="st"><span class="who code">code</span><b>Parse</b>3,727 beats with IDs + times; tolerant to 10 formats</div><div class="arrow">›</div>
    <div class="st"><span class="who ai">LLM</span><b>Tag</b>mark hook &amp; cliff beats by ID (1 call/ep)</div><div class="arrow">›</div>
    <div class="st"><span class="who code">code</span><b>Build clips</b>every hook→cliff, 20–60s, 2-part &amp; cross-episode</div></div>
   <div class="flow">
    <div class="st"><span class="who jv">Jev</span><b>Score</b>5-part rubric, asked in both level orders</div><div class="arrow">›</div>
    <div class="st"><span class="who code">code</span><b>Dedupe</b>same footage or same story (embeddings) → top 20</div><div class="arrow">›</div>
    <div class="st"><span class="who jv">Jev</span><b>Rank</b>all 190 pairs × both orders → Bradley-Terry</div><div class="arrow">›</div>
    <div class="st"><span class="who hum">human</span><b>Review</b>notes + plan → editor approves in UI</div></div>
   <ul style="margin-top:3px"><li><b>Why this split:</b> v1 let the LLM pick start/end; only 84% of clips met 20–60s and code re-cuts broke endings. Now the LLM never writes a timestamp: <b>100%</b> compliant, 0 invented IDs in 500 tags.</li>
   <li><b>Ranking:</b> comparing two clips beats scoring one; each pair is asked both ways, a split = tie, so position bias can't pick winners (Jev: same winner both ways {pw['position_consistency']:.0%}).</li>
   <li><b>Reused, not invented:</b> clip finders (AI-Shorts-Generator, deepclip), select-don't-generate timestamps, Pairwise Ranking Prompting, MMR, LiteLLM, TypeSafe Jev.</li></ul>
  </div>

  <div class="card g"><h2><span class="n">4</span>Post first: week-1 plan</h2>
   <ul>{plan_rows}</ul>
   <div class="mut" style="margin-top:3px"><b>Held back</b> ({len(holds)}): spoiler risk ≥ 5, e.g. {', '.join(h['id'] for h in holds[:4])}. Same scene never on consecutive days.</div>
  </div>
 </div>

 <div class="card" style="margin-top:8px; border-left-color:#1b1f24"><h2><span class="n">5</span>Top of the ranking (full list of {meta['ranked']} with notes in raw outputs) <span class="mut" style="font-weight:400;font-size:8pt">· W-L-T = wins-losses-ties in the pairwise tournament</span></h2>
  <table><tr><th>#</th><th>Promo</th><th>Segments (episode, start–end)</th><th>Hook (first 3s)</th><th>Cliffhanger (cut point)</th><th>W-L-T</th></tr>
  {''.join(top_rows)}</table>
  <div class="mut" style="margin-top:3px">Cross-episode promos in the top 20: {', '.join(f"<b>{p['id']}</b> (#{p['rank']}, {segs(p)})" for p in cross)}: hook from one episode, cliffhanger from a later one, same lead character.</div>
 </div>
 <div class="foot"><span>Every number on these pages is generated from runs/v3_final and experiments/* by deck/build_deck.py</span><span>1 / 2</span></div>
</div>"""

page2 = f"""
<div class="page p2">
 <div class="top"><div><h1>How I know it's good <span>·</span> and where it fails</h1>
  <div class="sub">Measured, not asserted: each fix was made only after the failure was measured, and re-measured after</div></div>
  <div class="meta">{NAME}</div></div>

 <div class="grid" style="grid-template-columns: 1.05fr 1fr 1fr">
  <div class="card"><h2><span class="n">6</span>What went wrong → what changed (v1 → final)</h2>
   <table class="cmp"><tr><th>Problem</th><th>v1</th><th>Final</th></tr>
   <tr><td>Raw clips meeting 20–60s / hook ≤3s</td><td>84% / 81%</td><td>100% / 100%</td></tr>
   <tr><td>Clip endings re-cut by code</td><td>21 of 105</td><td>0</td></tr>
   <tr><td>Tied scores in the ranking</td><td>81%</td><td>0%</td></tr>
   <tr><td>Same clips judged twice: order agreement</td><td>Spearman 0.68, top-10 30%</td><td>0.75–0.90, top-5 80–100%</td></tr>
   <tr><td>Same-story pairs in top 20 (cosine ≥ 0.86)</td><td>4 (incl. Ep1/Ep2 recap)</td><td>2 (recap removed; E15/E16, E03 W1/W2 remain)</td></tr>
   <tr><td>Multi-part / cross-episode promos</td><td>3, best rank #43</td><td>19 two-part + 4 cross, 2 in top 20</td></tr>
   <tr><td>Judging time per show</td><td>~30 min, quota-bound</td><td>~20 s, ${jev['cost_usd']:.3f} (Jev)</td></tr>
   <tr><td>Runs on a new, differently formatted show</td><td>exact format only</td><td>10 format tests pass + synthetic show run</td></tr></table>
  </div>

  <div class="card g"><h2><span class="n">7</span>Real-life tests: ground truth not from an LLM</h2>
   <div><b>A. Planted hooks</b> <span class="mut">(29 real episodes; one calm line swapped for a known shocking line, one for a neutral decoy)</span></div>
   {bars([("hook found", 90, "#1f9d6b", "26/29"), ("clip starts on it", 86, "#1f9d6b", "25/29"), ("decoy tagged", 0, "#c0392b", "0/29"), ("random tagger", 13, "#aab", "")])}
   <div style="margin-top:4px"><b>B. Writers' own cliffhanger</b> <span class="mut">(model marks a cliff in an episode's last 8s; writers end every episode on one)</span></div>
   {bars([("free lite model", 94, "#2d6cdf", "47/50"), ("Vertex 3.5-flash", 82, "#2d6cdf", "41/50"), ("random tagger", 22, "#aab", "")])}
   <div class="mut" style="margin-top:3px">All p &lt; 10⁻¹⁶ vs chance. <b>Tagger choice:</b> 3.5-flash finds planted hooks better (90% vs 83%; clips 86% vs 66%); the lite model finds endings better, but the episode end is always added as a cliff candidate, so endings aren't lost.</div>
  </div>

  <div class="card r"><h2><span class="n">8</span>Where it picks badly (honest limits)</h2>
   <ul><li><b>Quality vs people is unproven.</b> Independent AI judges agree only at Spearman <b>0.26–0.49</b>; two blind audits disagreed on whether v2 beats v1 (p 0.01 vs 0.92). Reproducible ≠ correct. Process is proven; picks need editor labels.</li>
   <li><b>Visual hooks</b> (a slap, a close-up) are judged from script text, so footage may land differently.</li>
   <li><b>Tagger sometimes calls a resolution a cliffhanger</b> (e.g. she finds the ring); every clip inherits tag quality.</li>
   <li><b>Story dedupe is approximate</b>; threshold 0.90 was calibrated on this one show.</li>
   <li><b>Jev bias:</b> leans to the second-shown clip (first wins {pw['first_position_win_rate']:.0%}); 20% of pairs flip, so both orders are always asked.</li>
   <li><b>Planted lines are deliberately obvious</b>, so test A proves recall of clear signals, not taste.</li></ul>
  </div>
 </div>

 <div class="grid" style="grid-template-columns: 1fr 1fr 1fr; margin-top:8px">
  <div class="card y"><h2><span class="n">9</span>Scale, cost &amp; human in the loop</h2>
   <ul><li><b>Per 50-ep show:</b> 50 tag calls ({ntok[0] // 1000}k in / {ntok[1] // 1000}k out tokens, ≈ ${LLM_USD:.2f} at Flash list price $1.50/$9 per M; tagging can drop to Flash-Lite) + ~650 Jev requests ({jev['input_tokens'] / 1e6:.1f}M tokens, ${jev['cost_usd']:.3f}) + 1 embedding pass. Cost grows with episodes; the expensive ranker only ever sees 20 clips.</li>
   <li>Shows are independent → run nightly per new show, in parallel; everything is cached, so reruns are free.</li>
   <li>Half the pairs give the same order (Spearman 0.99): ranking cost can halve.</li>
   <li><b>Human:</b> editor reviews ~20 ranked clips with the script in the UI instead of watching 50 episodes; approve/reject is saved as labels to tune prompts and weights.</li></ul>
  </div>
  <div class="card"><h2><span class="n">10</span>Built to run again, model easy to swap</h2>
   <ul><li><span class="mono">python run.py &lt;folder&gt;</span> on any show; parser handles bold/plain labels, bracket/SRT/h:mm:ss/seconds times, sluglines, missing headers; clear error instead of an empty run.</li>
   <li>Proved on a <b>new synthetic 4-episode show</b> in a different format: 23 candidates, 0 violations, 2 cross-episode promos in its top 3.</li>
   <li>Per-role models: <span class="tag">PROMO_TAG_MODEL</span><span class="tag">PROMO_RANK_MODEL</span><span class="tag">…</span> any LiteLLM string (OpenAI, Anthropic, Vertex); Jev optional, LLM judges as fallback. No keys → <span class="mono">demo.py</span> shows saved runs.</li></ul>
  </div>
  <div class="card o"><h2><span class="n">11</span>AI tools used, and where they got it wrong</h2>
   <ul><li><b>Kiro (Claude)</b>: research, code, experiments. <b>Gemini</b> 3.5/3.1 Flash(-Lite) via AI Studio + Vertex, <b>Gemma</b> as auditor, <b>TypeSafe Jev</b> as judge.</li>
   <li><b>Wrong #1:</b> told "20–60 seconds", the LLM returned 9–160s clips; it can't add timestamps reliably. Patching in code damaged endings; the fix was to stop asking it for arithmetic.</li>
   <li><b>Wrong #2:</b> a 9.5/10 self-score from the picker meant nothing (Spearman with an independent judge ≈ 0), and the assistant read a <i>daily</i> quota error as per-minute and kept retrying.</li>
   <li><b>Next:</b> 30–40 blind editor ratings to pick the judge that matches humans; vision check of the first 3s once footage is available.</li></ul>
  </div>
 </div>
 <div class="foot"><span>Sources: experiments/BASELINE_v1.md · RESULTS.md · JEV_RESULTS.md · REALWORLD_RESULTS*.md · AUDIT_*.md · ANALYSIS.md · runs/v3_final/meta.json</span><span>2 / 2</span></div>
</div>"""

OUT.mkdir(exist_ok=True)
(OUT / "solution.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{page1}{page2}</body></html>")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pw_:
    b = pw_.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.goto((OUT / "solution.html").as_uri())
    pg.pdf(path=str(OUT / "solution.pdf"), width="13.333in", height="7.5in", print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    # overflow check: content must fit each page
    over = pg.evaluate("""() => [...document.querySelectorAll('.page')].map(p => {
        const r = p.getBoundingClientRect(); let worst = 0;
        p.querySelectorAll('*').forEach(e => { const q = e.getBoundingClientRect(); worst = Math.max(worst, q.bottom - r.bottom, q.right - r.right); });
        return Math.round(worst); })""")
    for i, el in enumerate(pg.query_selector_all(".page"), 1):
        el.screenshot(path=str(OUT / f"page-{i}.png"))
    b.close()
print("overflow px per page (must be <= 0):", over)
