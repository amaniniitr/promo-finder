"""Images for the README: a banner, plus diagrams cut from the deck.
Run after deck/build_deck.py:  .venv/bin/python scripts/build_docs.py  -> docs/*.png
Only cards without script text are exported (no phone, no posters), so nothing confidential reaches git."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
FONT = (ROOT / "web" / "fonts" / "Figtree.ttf").as_uri()
LOGO = '<span class="wm">promo finder<i>.</i></span>'

BANNER = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:Figtree; src:url('{FONT}') }}
* {{ box-sizing:border-box; margin:0 }}
body {{ width:1280px; height:420px; font-family:Figtree, sans-serif; color:#fff; overflow:hidden;
  background: radial-gradient(ellipse 70% 90% at 85% 10%, #5A0A0E 0%, #1A0204 45%, #000 75%) }}
.w {{ padding:44px 56px; height:100%; display:flex; flex-direction:column }}
.top {{ display:flex; align-items:center; gap:14px }} .top svg {{ height:30px; width:auto }}
.wm {{ font-size:30px; font-weight:800; letter-spacing:-1px; color:#fff; border:0 !important; padding:0 !important }} .wm i {{ color:#EC1C24; font-style:normal }}
.top span:not(.wm) {{ font-weight:700; font-size:17px; color:#C9CBD1; border-left:1px solid #333; padding-left:14px }}
h1 {{ font-size:64px; font-weight:800; letter-spacing:-2.2px; line-height:1.02; margin-top:46px }} h1 span {{ color:#EC1C24; display:block }}
p {{ font-size:19px; color:#C9CBD1; margin-top:18px; max-width:860px; line-height:1.4 }} p b {{ color:#fff }}
.pills {{ display:flex; gap:10px; margin-top:auto }}
.pill {{ font-size:14px; font-weight:700; border:1px solid rgba(255,255,255,.18); border-radius:999px; padding:6px 14px; background:rgba(255,255,255,.04) }}
.pill b {{ color:#2BD49A }}
</style></head><body><div class="w">
<div class="top">{LOGO}<span>find the promo hiding in every script</span></div>
<h1>every show hides its best promo.<span>we find it in the script.</span></h1>
<p>Reads a show's timestamped screenplays and returns <b>ranked 20–60 s promos</b>, each with exact cut times, the hook, the cliffhanger, why it works, and a <b>week-1 posting plan</b>.</p>
<div class="pills"><span class="pill"><b>0 / 176</b> clips break a rule</span><span class="pill"><b>~7 min</b> per 50-episode show</span>
<span class="pill"><b>$1.48</b> per show</span><span class="pill"><b>26 / 29</b> planted hooks found</span><span class="pill"><b>81%</b> verdicts same in both orders</span></div>
</div></body></html>"""

# (file name, page index, CSS selector, which match)
CUTS = [("architecture.png", 1, ".card", 0), ("versions.png", 1, ".card", 1), ("tests.png", 1, ".card", 2),
        ("ranking.png", 1, ".card", 3), ("limits.png", 1, ".card", 4), ("ai-tools.png", 1, ".card", 5),
        ("rules.png", 0, ".rules", 0), ("pipeline.png", 0, ".pipe", 0)]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 420}, device_scale_factor=2)
    (DOCS / "_banner.html").write_text(BANNER)
    pg.goto((DOCS / "_banner.html").as_uri())
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(DOCS / "banner.png"))
    (DOCS / "_banner.html").unlink()

    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    pg.goto((ROOT / "deck" / "solution.html").as_uri())
    pg.wait_for_timeout(400)
    pages = pg.query_selector_all(".page")
    for name, pi, sel, k in CUTS:
        el = pages[pi].query_selector_all(sel)[k]
        el.screenshot(path=str(DOCS / name))
        print("wrote", name)
    b.close()

# Map card: the 4th .card on page 1 is the episode map (cards: phone card, map card ...). Find it by its label.
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    pg.goto((ROOT / "deck" / "solution.html").as_uri())
    pg.wait_for_timeout(400)
    pg.locator(".page").nth(0).locator(".card", has_text="where the top 20 come from").screenshot(path=str(DOCS / "episode-map.png"))
    print("wrote episode-map.png")
    b.close()
