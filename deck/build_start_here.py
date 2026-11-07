"""One-page "start here" guide for the submission folder (Google Drive).
.venv/bin/python deck/build_start_here.py  ->  ../submission/  (outside the repo; the passphrase is read from .env, never stored in git)"""
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "submission"
RUN = ROOT / "runs" / "v3_final"
L = json.loads((ROOT / "links.json").read_text())
ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
PASS = ENV["SITE_PASSPHRASE"].strip()
FONT = (ROOT / "web" / "fonts" / "Figtree.ttf").as_uri()
LOGO = (ROOT / "web" / "kuku-logo-white.svg").read_text()
SITE, REPO = L["site"], L["repo"]
EMAIL = "aman_k@hs.iitr.ac.in"
DECK = "01 Solution deck (2 pages).pdf"

shutil.rmtree(OUT, ignore_errors=True)
(OUT / "02 Raw outputs").mkdir(parents=True)
shutil.copy(ROOT / "deck" / "solution.pdf", OUT / DECK)
for f in ("promos.csv", "report.md", "meta.json"):
    shutil.copy(RUN / f, OUT / "02 Raw outputs" / f)

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:Figtree; src:url('{FONT}') }}
* {{ box-sizing:border-box; margin:0 }} @page {{ size:1280px 720px; margin:0 }}
body {{ width:1280px; height:720px; font-family:Figtree, sans-serif; color:#fff; overflow:hidden; -webkit-print-color-adjust:exact; print-color-adjust:exact;
  background: radial-gradient(ellipse 60% 80% at 92% 0%, #4A080C 0%, #160204 45%, #000 75%) }}
.w {{ padding:26px 34px 18px; height:100%; display:flex; flex-direction:column }}
a {{ color:inherit; text-decoration:none }}
.top {{ display:flex; align-items:center; gap:12px }} .top svg {{ height:24px; width:auto }}
.top .pr {{ font-weight:700; font-size:14px; color:#C9CBD1; border-left:1px solid #333; padding-left:12px }}
.top .me {{ margin-left:auto; font-size:12px; color:#C9CBD1 }} .top .me b {{ color:#fff }}
h1 {{ font-size:42px; font-weight:800; letter-spacing:-1.8px; line-height:1; margin-top:16px }} h1 span {{ color:#EC1C24 }}
.sub {{ font-size:15px; color:#C9CBD1; margin-top:8px }} .sub b {{ color:#fff }}
.steps {{ display:grid; grid-template-columns: 1fr 1.35fr 1fr; gap:14px; margin-top:14px; flex:1 }}
.st {{ background:#0E0E10; border:1px solid #232327; border-radius:18px; padding:14px 16px; display:flex; flex-direction:column }}
.st.main {{ border-color:rgba(236,28,36,.55); background:linear-gradient(160deg,#1A0507,#0E0E10 60%) }}
.n {{ width:30px; height:30px; border-radius:50%; background:#EC1C24; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:15px }}
.st h2 {{ font-size:20px; font-weight:800; letter-spacing:-.5px; margin:9px 0 2px }} .st .t {{ font-size:12px; color:#8A8D96 }}
.st p {{ font-size:13px; color:#C9CBD1; line-height:1.42; margin-top:8px }} .st p b {{ color:#fff }}
.btn {{ display:inline-block; align-self:flex-start; margin-top:10px; background:#EC1C24; color:#fff; font-weight:800; font-size:14px; border-radius:999px; padding:10px 18px }}
.btn.g {{ background:#1C1C20; border:1px solid #333 }}
.url {{ font-size:12px; color:#8A8D96; margin-top:6px; word-break:break-all }}
.pass {{ margin-top:10px; background:#000; border:1px dashed rgba(255,255,255,.35); border-radius:12px; padding:10px 14px }}
.pass span {{ font-size:10px; font-weight:800; letter-spacing:1.4px; color:#8A8D96 }} .pass code {{ display:block; font-family:Menlo,monospace; font-size:20px; font-weight:700; margin-top:3px; color:#fff }}
ol {{ margin:10px 0 0 18px; padding:0; font-size:12px; color:#C9CBD1; line-height:1.45 }} ol b {{ color:#fff }}
.thumbs {{ margin-top:auto; position:relative; height:235px }} .thumbs img {{ position:absolute; width:80%; border-radius:8px; border:1px solid #2A2A2E; box-shadow:0 0 0 4px #0E0E10 }} .thumbs img:first-child {{ left:0; top:0 }} .thumbs img:last-child {{ right:0; bottom:0 }}
.term {{ margin-top:auto; background:#000; border:1px solid #2A2A2E; border-radius:12px; padding:11px 13px; font-family:Menlo,monospace; font-size:10.5px; line-height:1.6; color:#E6E6EA }} .term span {{ display:block; color:#6E717A }}
.files {{ margin-top:8px; display:grid; grid-template-columns: 1.1fr 1.6fr 1fr; gap:14px }}
.f {{ background:#0E0E10; border:1px solid #232327; border-radius:14px; padding:9px 13px; font-size:11.5px; color:#C9CBD1; line-height:1.45 }}
.f b {{ color:#fff; display:block; font-size:12.5px; margin-bottom:2px }} .f code {{ font-family:Menlo,monospace; font-size:11px; color:#FFB3B5 }}
.k {{ font-size:10px; font-weight:800; letter-spacing:1.6px; color:#8A8D96; text-transform:uppercase; margin-top:12px }}
</style></head><body><div class="w">
<div class="top">{LOGO}<span class="pr">Promo Finder</span><span class="me"><b>Aman Kumar · 22322004</b> · Problem 1, Find the promos · <a href="mailto:{EMAIL}">{EMAIL}</a></span></div>
<h1>start here<span>.</span></h1>
<div class="sub">Everything I'm submitting, in the order I'd look at it. <b>About 10 minutes in total.</b> Every link on this page is clickable.</div>
<div class="steps">
 <div class="st"><div class="n">1</div><h2>Read the deck</h2><div class="t">2 pages · 3 min</div>
  <p>What the tool does, the rules it enforces, how it's built, how I got from v1 to v3, and what I tested.</p>
  <p>File in this folder: <b>{DECK}</b></p>
  <div class="thumbs"><img src="{(ROOT / 'deck' / 'page-1.png').as_uri()}"><img src="{(ROOT / 'deck' / 'page-2.png').as_uri()}"></div></div>
 <div class="st main"><div class="n">2</div><h2>Try the live prototype</h2><div class="t">no login, any browser · 5 min</div>
  <a class="btn" href="{SITE}">Open promo-finder-five.vercel.app ↗</a><div class="url">{SITE}</div>
  <div class="pass"><span>PASSPHRASE</span><code>{PASS}</code></div>
  <ol><li>Scroll to the studio and open the <b>🔒 50-episode show</b> tab. Paste the passphrase and press <b>Unlock results</b>.</li>
   <li>Click any promo to <b>play it on the phone</b> with its script lines, hook, cliffhanger and why it works.</li>
   <li>See the <b>week-1 posting plan</b>, the ranking strength chart, and download the <b>CSV</b> or the deck.</li>
   <li>Optional: <b>▶ Try it live</b> runs the real pipeline on a sample show or your own episodes (same passphrase, 30–90 s).</li></ol></div>
 <div class="st"><div class="n">3</div><h2>Read the code</h2><div class="t">GitHub · 2 min</div>
  <a class="btn g" href="{REPO}">Open the GitHub repo ↗</a><div class="url">{REPO}</div>
  <p>The README explains the architecture, each step, the v1 → v3 evidence and how to run it with one command.</p>
  <p>Key files: <b>promo/moments.py</b> (tags → clips), <b>promo/rerank.py</b> (pairwise + Bradley-Terry), <b>experiments/ANALYSIS.md</b> (what failed and what changed).</p>
  <div class="term"><span># run it on any show</span>pip install -r requirements-local.txt<br>python run.py "&lt;show folder&gt;"<br><span># no keys needed</span>python demo.py runs/new_show_test</div></div>
</div>
<div class="k">Also in this folder · 02 Raw outputs</div>
<div class="files">
 <div class="f"><b><code>promos.csv</code></b>All 93 ranked promos: episode and start/end of every segment, hook, cliffhanger, why, head-to-head record, models used.</div>
 <div class="f"><b><code>report.md</code></b>The same results as a readable report: the week-1 posting plan, then every promo with its timestamps, hook, cliffhanger and why.</div>
 <div class="f"><b><code>meta.json</code></b>Run facts: models used, token counts and cost, rule violations (0), pairwise consistency.</div>
</div>
</div></body></html>"""

(OUT / "_start.html").write_text(HTML)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.goto((OUT / "_start.html").as_uri())
    pg.wait_for_timeout(400)
    over = pg.evaluate("() => Math.max(...[...document.querySelectorAll('.w *')].map(e => e.getBoundingClientRect().bottom)) - 702")
    pg.pdf(path=str(OUT / "00 START HERE.pdf"), width="1280px", height="720px", print_background=True)
    pg.screenshot(path="/tmp/start_here.png")
    b.close()
(OUT / "_start.html").unlink()
print("overflow:", round(over))
for f in sorted(OUT.rglob("*")):
    print(f.relative_to(OUT))
