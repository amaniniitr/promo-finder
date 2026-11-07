"""2-page solution deck (16:9 PDF), built from runs/v3_final and experiments/*.
python deck/build_deck.py  ->  deck/solution.pdf (+ page-1.png, page-2.png previews)

Design rules: one idea per block, big type for the point and small type for the proof,
Kuku red only for emphasis, every number generated from the run files."""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deck"
sys.path.insert(0, str(ROOT))
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.models import BeatIndex  # noqa: E402
from promo.parser import parse_show  # noqa: E402

RUN = ROOT / "runs" / "v3_final"
meta = json.loads((RUN / "meta.json").read_text())
P = json.loads((RUN / "promos.json").read_text())["promos"]
DIAG = json.loads((RUN / "diagnostics.json").read_text())
TITLES = json.loads((OUT / "titles.json").read_text()) if (OUT / "titles.json").exists() else {}
_L = json.loads((ROOT / "links.json").read_text()) if (ROOT / "links.json").exists() else {}
NAME = "Aman Kumar · 22322004"
EPS = parse_show(DEFAULT_SHOW)
IDX = BeatIndex(EPS)
by = {p["id"]: p for p in P}
jev, pw = meta["jev_usage"], meta["pairwise"]
tok = meta["llm_tokens_by_model"]["vertex/gemini-3.5-flash"]
SHOW_USD = tok[0] * 1.5e-6 + tok[1] * 9e-6 + jev["cost_usd"]      # list prices, Gemini 3.5 Flash $1.50/$9 per M (estimate)
WATCH_MIN = sum(e.duration for e in EPS) / 60
PLAN = meta["posting_plan"]["plan"]
HOLD = meta["posting_plan"]["hold"]
PLAN_MIN = sum(by[x["id"]]["duration"] for x in PLAN) / 60
TOP20_MIN = sum(p["duration"] for p in P[:20]) / 60
N_TAGS = sum(len(t["hooks"]) + len(t["cliffs"]) for t in DIAG["tags"].values())
N_BEATS = sum(len(e.beats) for e in EPS)
FONT = (ROOT / "web" / "fonts" / "Figtree.ttf").as_uri()
RED, INK, MUT, LINE, SOFT, GOOD = "#EC1C24", "#111318", "#6B7080", "#E6E7EB", "#F6F6F8", "#0E9F6E"


def e(s):
    return html.escape(str(s))


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{int(s):02d}"


def short(u):
    return e(u.replace("https://", "").replace("http://", "").rstrip("/"))


def title(pid):
    return TITLES.get(pid, pid)


LOGO = (ROOT / "web" / "kuku-logo.svg").read_text() if (ROOT / "web" / "kuku-logo.svg").exists() else ""


# ------------------------------------------------------------------ visuals
import math  # noqa: E402

PURPLE = "#7A3FE0"


def rule_icons():
    """Three small pictograms: the length window, the 3-second hook, the open cut."""
    W = 168
    X = lambda t: 8 + (W - 16) * t / 90  # noqa: E731   axis 0-90 s
    length = (f'<svg width="{W}" height="34"><line x1="8" y1="20" x2="{W - 8}" y2="20" stroke="{LINE}" stroke-width="6" stroke-linecap="round"/>'
              f'<line x1="{X(20)}" y1="20" x2="{X(60)}" y2="20" stroke="{RED}" stroke-width="6" stroke-linecap="round"/>'
              f'<text x="{X(20)}" y="10" class="ax" text-anchor="middle">20 s</text><text x="{X(60)}" y="10" class="ax" text-anchor="middle">60 s</text>'
              f'<text x="{X(0)}" y="33" class="ax2">0</text><text x="{W - 8}" y="33" class="ax2" text-anchor="end">90 s</text></svg>')
    Y = lambda t: 8 + (W - 16) * t / 35  # noqa: E731
    hook = (f'<svg width="{W}" height="34"><rect x="8" y="15" width="{W - 16}" height="10" rx="5" fill="{LINE}"/>'
            f'<rect x="8" y="15" width="{Y(3) - 8}" height="10" rx="5" fill="{RED}"/>'
            f'<text x="{Y(3) + 4}" y="11" class="ax">first 3 s</text><text x="8" y="34" class="ax2">clip starts</text></svg>')
    cut = (f'<svg width="{W}" height="34"><rect x="8" y="15" width="{W - 46}" height="10" rx="5" fill="{LINE}"/>'
           f'<rect x="{W - 66}" y="15" width="28" height="10" rx="3" fill="{PURPLE}"/>'
           f'<line x1="{W - 36}" y1="6" x2="{W - 36}" y2="32" stroke="{INK}" stroke-width="2" stroke-dasharray="3 2"/>'
           f'<text x="{W - 28}" y="25" class="q2">?</text><text x="{W - 66}" y="11" class="ax">tension peaks</text><text x="{W - 32}" y="34" class="ax2">cut</text></svg>')
    return length, hook, cut


def funnel():
    stages = [(N_BEATS, "beats in 50 scripts", "parsed", "CODE"), (N_TAGS, "moments tagged", "hook or cliffhanger lines", "AI"),
              (meta["candidates"], "candidate clips", "all 20–60 s, hook first", "CODE"),
              (meta["ranked"], "after removing repeats", "same footage or same story", "CODE"),
              (20, "shortlist", f"{pw['verdicts']} head-to-head judgements", "AI"), (len(PLAN), "posts for week 1", "editor approves", "EDITOR")]
    lmax = math.log10(N_BEATS)
    out = []
    for v, lab, sub, who in stages:
        w = 18 + 230 * math.log10(v) / lmax
        col = {"CODE": GOOD, "AI": RED, "EDITOR": INK}[who]
        out.append(f'<div class="fr"><div class="ftrack"><div class="fbar" style="width:{w:.0f}px;background:{col}"></div></div><b>{v:,}</b>'
                   f'<span class="fl">{lab}</span><span class="fs">{sub}</span><span class="fw2" style="color:{col}">{who}</span></div>')
    return "".join(out)


def featured():
    p = P[0]
    s = p["segments"][0]
    ep = IDX.eps[s["episode"]]
    beats = [b for b in ep.beats if b.start >= s["start"] - .01 and b.end <= s["end"] + .01]
    lines = [b for b in beats if b.type == "dialogue"]
    hook = lines[0]
    build = min(lines, key=lambda b: abs((b.start - s["start"]) - p["duration"] * 0.45))
    cliff = [b for b in beats if b.type in ("action", "dialogue")][-1]
    D = p["duration"]
    rows = [("0–3 s", hook, RED, "opening line"), ("middle", build, INK, "why she's in danger"),
            ("last beat", cliff, PURPLE, f"the cut; episode {ep.number + 1} answers it")]
    pct = lambda t: 100 * t / D  # noqa: E731
    beats_html = ""
    for lab, b, col, why in rows:
        t = b.start - s["start"]
        txt = f'“{b.text}”' if b.type == "dialogue" else b.text
        beats_html += (f'<div class="fb"><div class="ft" style="color:{col}">{t:.0f} s<span>{why}</span></div>'
                       f'<div class="fq">{e(txt[:112] + ("…" if len(txt) > 112 else ""))}</div></div>')
    marks = "".join(f'<i style="left:{pct(b.start - s["start"]):.1f}%;background:{"#fff" if c == INK else c}"></i>' for _, b, c, _ in rows)
    wins, losses, ties = p["record"].split("-")
    return f"""
    <div class="feat">
     <div class="phone"><div class="scr">
       <div class="ptag">#1 of {meta['ranked']} · {D:.0f} s</div>
       <div class="pline">“{e(hook.text)}”</div>
       <div class="pfoot">Episode {ep.number}, {fmt(s['start'])}–{fmt(s['end'])}</div>
       <div class="pbar"><b style="width:{pct(3):.1f}%"></b>{marks}</div>
       <div class="plab"><span>0 s</span><span>{D:.0f} s</span></div></div></div>
     <div class="fbeats">{beats_html}
      <div class="fmeta">It beat all {wins} clips it was compared with. The judge sees only the clip, never the rest of the show.</div></div>
    </div>"""


def week():
    cards = []
    for x in PLAN:
        p = by[x["id"]]
        cards.append(f'<div class="day"><div class="dd">DAY {x["day"]}</div><div class="dt">{e(title(p["id"]))}</div>'
                     f'<div class="dm">Ep {p["segments"][0]["episode"]} · {p["duration"]:.0f} s · #{p["rank"]}</div></div>')
    return "".join(cards)


def episode_strip():
    """50 episodes left to right. Dots = top-20 clips taken from that episode; arcs = clips that join two episodes."""
    W, cw = 560, 560 / 50
    X = lambda n: (n - 0.5) * cw  # noqa: E731
    count = {}
    arcs = []
    for p in P[:20]:
        eps = sorted({s["episode"] for s in p["segments"]})
        if len(eps) == 2:
            arcs.append((eps[0], eps[1], p["rank"]))
        for n in eps:
            count[n] = count.get(n, 0) + 1
    o = [f'<svg width="{W}" height="84" viewBox="0 0 {W} 84">']
    for a, b, r in arcs:
        x1, x2 = X(a), X(b)
        o.append(f'<path d="M{x1} 52 Q{(x1 + x2) / 2} {52 - (x2 - x1) * 0.55} {x2} 52" fill="none" stroke="{PURPLE}" stroke-width="1.6"/>'
                 f'<text x="{(x1 + x2) / 2}" y="{50 - (x2 - x1) * 0.28}" text-anchor="middle" class="ax" fill="{PURPLE}">#{r}</text>')
    for n in range(1, 51):
        o.append(f'<rect x="{X(n) - cw / 2 + 1}" y="56" width="{cw - 2}" height="10" rx="2" fill="{LINE}"/>')
        for k in range(count.get(n, 0)):
            col = RED if (n == P[0]["segments"][0]["episode"] and k == 0) else INK
            o.append(f'<circle cx="{X(n)}" cy="{48 - k * 7}" r="2.8" fill="{col}"/>')
    for n in (1, 10, 20, 30, 40, 50):
        o.append(f'<text x="{X(n)}" y="80" text-anchor="middle" class="ax2">{n}</text>')
    o.append("</svg>")
    return "".join(o)


def dots(n_total, n_hit, color, per_row=29, r=3.6, gap=9.6):
    rows = math.ceil(n_total / per_row)
    o = [f'<svg width="{per_row * gap}" height="{rows * gap}">']
    for i in range(n_total):
        cx, cy = (i % per_row) * gap + gap / 2, (i // per_row) * gap + gap / 2
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color if i < n_hit else LINE}"/>')
    o.append("</svg>")
    return "".join(o)


def before_after():
    rows = [("Clips outside 20–60 s", 16, 0, "16%", "0%"), ("Clip endings cut short by code", 20, 0, "21 of 105", "0"),
            ("Ranking scores that were tied", 81, 0, "81%", "0%"),
            ("Top-20 order on a re-check (ρ)", 44, 83, "0.44", "0.75–0.90")]
    o = []
    for lab, a, b, ta, tb in rows:
        o.append(f'<div class="ba"><div class="bal">{lab}</div><div class="bab">'
                 f'<div class="bb"><div class="trk"><i style="width:{max(a, .8)}%;background:#C9CCD4"></i></div><em>{ta}</em></div>'
                 f'<div class="bb"><div class="trk"><i style="width:{max(b, .8)}%;background:{GOOD}"></i></div><em style="color:{GOOD}">{tb}</em></div></div></div>')
    return "".join(o)


def time_bars():
    W = 400
    segs = "".join(f'<rect x="{i * W / 50 + .5}" y="0" width="{W / 50 - 1}" height="16" rx="1.5" fill="#C9CCD4"/>' for i in range(50))
    w3 = W * PLAN_MIN / WATCH_MIN
    w20 = W * TOP20_MIN / WATCH_MIN
    return (f'<div class="tl"><b>{WATCH_MIN:.0f} min</b><span>watching all 50 episodes today</span></div><svg width="{W}" height="16">{segs}</svg>'
            f'<div class="tl" style="margin-top:8px"><b style="color:{GOOD}">{TOP20_MIN:.0f} min</b><span>watching the top 20 clips</span></div>'
            f'<svg width="{W}" height="16"><rect width="{w20:.1f}" height="16" rx="2" fill="{GOOD}" opacity=".55"/></svg>'
            f'<div class="tl" style="margin-top:8px"><b style="color:{GOOD}">{PLAN_MIN:.0f} min</b><span>approving the 5 week-1 posts</span></div>'
            f'<svg width="{W}" height="16"><rect width="{w3:.1f}" height="16" rx="2" fill="{GOOD}"/></svg>')


length_ic, hook_ic, cut_ic = rule_icons()

CSS = f"""
@font-face {{ font-family: Figtree; src: url('{FONT}') format('truetype'); font-weight: 300 900 }}
@page {{ size: 13.333in 7.5in; margin: 0 }}
* {{ box-sizing: border-box; margin: 0; padding: 0 }}
body {{ font-family: Figtree, -apple-system, 'Helvetica Neue', Arial, sans-serif; color: {INK}; font-size: 10pt; line-height: 1.3 }}
.page {{ width: 13.333in; height: 7.5in; padding: 24px 36px 18px; position: relative; overflow: hidden; page-break-after: always; background: #fff }}
.top {{ display: flex; align-items: center; gap: 14px; padding-bottom: 10px; border-bottom: 1px solid {LINE}; margin-bottom: 14px }}
.top svg {{ height: 20px; width: auto }} .top .div {{ width: 1px; height: 20px; background: {LINE} }}
.top .prod {{ font-size: 9pt; font-weight: 700; letter-spacing: 1.6px; color: {MUT} }}
.top .me {{ margin-left: auto; text-align: right; font-size: 8.6pt; color: {MUT} }} .top .me b {{ color: {INK}; font-size: 9.6pt }}
h1 {{ font-size: 22pt; line-height: 1.12; font-weight: 800; letter-spacing: -.6px }}
.lead {{ font-size: 10.3pt; color: #3D4250; margin-top: 6px; line-height: 1.42 }} .lead b {{ color: {INK} }}
h2 {{ font-size: 11.5pt; font-weight: 800; margin-bottom: 8px; letter-spacing: -.1px }} h2 span {{ font-weight: 500; color: {MUT}; font-size: 9.2pt; margin-left: 6px }}
.row {{ display: flex; gap: 26px }}
svg text {{ font-family: Figtree, sans-serif }} .ax {{ font-size: 8px; fill: {INK}; font-weight: 700 }} .ax2 {{ font-size: 7.5px; fill: {MUT} }}
.q2 {{ font-size: 15px; font-weight: 800; fill: {PURPLE} }}
.rules {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px }}
.rule {{ border: 1px solid {LINE}; border-radius: 12px; padding: 9px 12px 8px }}
.rule b {{ display: block; font-size: 12.5pt; font-weight: 800 }} .rule span {{ display: block; font-size: 8.6pt; color: {MUT}; margin: 1px 0 4px; line-height: 1.3 }}
.fr {{ display: flex; align-items: center; gap: 8px; height: 21px }}
.ftrack {{ width: 252px; flex: none }} .fbar {{ height: 13px; border-radius: 3px }}
.fr b {{ font-size: 11pt; font-weight: 800; width: 46px; text-align: right; margin-right: 4px }} .fl {{ font-size: 9.4pt; font-weight: 700; width: 150px }}
.fs {{ font-size: 8.6pt; color: {MUT}; flex: 1 }} .fw2 {{ font-size: 7pt; font-weight: 800; letter-spacing: .8px }}
.feat {{ display: flex; gap: 14px; align-items: stretch }}
.phone {{ width: 150px; flex: none; background: {INK}; border-radius: 24px; padding: 6px }}
.scr {{ height: 100%; border-radius: 19px; background: linear-gradient(180deg, #2A1416 0%, #121318 55%, #0B0C10 100%); padding: 13px 11px 11px; color: #fff; display: flex; flex-direction: column }}
.ptag {{ font-size: 7.4pt; font-weight: 700; color: #FF8A8E }}
.pline {{ font-size: 14pt; font-weight: 800; line-height: 1.1; margin: auto 0 9px }}
.pfoot {{ font-size: 7.2pt; color: #A5A9B5; margin-bottom: 6px }}
.pbar {{ height: 5px; border-radius: 3px; background: #3A3D48; position: relative }}
.pbar b {{ position: absolute; left: 0; top: 0; bottom: 0; background: {RED}; border-radius: 3px }}
.pbar i {{ position: absolute; top: -3px; width: 3px; height: 11px; border-radius: 2px; margin-left: -1px }}
.plab {{ display: flex; justify-content: space-between; font-size: 6.6pt; color: #8A8E9A; margin-top: 4px }}
.fbeats {{ flex: 1; display: flex; flex-direction: column; gap: 8px }}
.fb {{ border-left: 2px solid {LINE}; padding-left: 9px }}
.ft {{ font-size: 8.4pt; font-weight: 800 }} .ft span {{ color: {MUT}; font-weight: 600; margin-left: 6px }}
.fq {{ font-size: 9.6pt; font-weight: 600; line-height: 1.28; margin-top: 1px }}
.fmeta {{ font-size: 8.4pt; color: {MUT}; margin-top: auto; line-height: 1.35 }}
.days {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 7px }}
.day {{ border: 1px solid {LINE}; border-top: 3px solid {RED}; border-radius: 10px; padding: 7px 9px }}
.dd {{ font-size: 7.4pt; font-weight: 800; color: {RED}; letter-spacing: 1.1px }}
.dt {{ font-size: 9.2pt; font-weight: 800; line-height: 1.2; margin: 2px 0 3px }} .dm {{ font-size: 7.8pt; color: {MUT} }}
.note {{ font-size: 8.6pt; color: {MUT}; margin-top: 6px; line-height: 1.35 }} .note b {{ color: {INK} }}
.legend {{ font-size: 8.2pt; color: {MUT} }} .legend i {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin: 0 3px 0 8px; vertical-align: 0 }}
.analogy {{ background: {SOFT}; border-radius: 12px; padding: 9px 12px; font-size: 9.2pt; color: #3D4250; line-height: 1.4 }} .analogy b {{ color: {INK} }}
.foot {{ position: absolute; left: 36px; right: 36px; bottom: 9px; display: flex; justify-content: space-between; font-size: 7pt; color: #A3A7B2 }}
.ba {{ display: flex; align-items: center; gap: 12px; padding: 5px 0; border-bottom: 1px solid {LINE} }} .ba:last-child {{ border: 0 }}
.bal {{ width: 175px; font-size: 9.4pt; font-weight: 700; line-height: 1.25 }} .bab {{ flex: 1 }}
.bb {{ display: flex; align-items: center; gap: 8px; margin: 3px 0 }} .trk {{ width: 260px; height: 12px; position: relative; flex: none }}
.trk i {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px }}
.bb em {{ font-style: normal; font-size: 8.6pt; font-weight: 800; color: {MUT}; white-space: nowrap }}
.tst {{ padding: 8px 0; border-bottom: 1px solid {LINE} }} .tst:last-of-type {{ border: 0 }}
.tst .h {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px }} .tst .h b {{ font-size: 15pt; font-weight: 800 }} .tst .h span {{ font-size: 9pt; color: #3D4250 }}
.tst .s {{ font-size: 8.2pt; color: {MUT}; margin-top: 3px }}
.tl {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 3px }} .tl b {{ font-size: 14pt; font-weight: 800 }} .tl span {{ font-size: 8.8pt; color: {MUT} }}
.stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px }}
.st {{ background: {SOFT}; border-radius: 10px; padding: 7px 10px }} .st b {{ display: block; font-size: 13pt; font-weight: 800 }} .st span {{ font-size: 7.8pt; color: {MUT} }}
.lim div {{ padding: 6px 0; border-bottom: 1px solid {LINE} }} .lim div:last-child {{ border: 0 }}
.lim b {{ font-size: 9.6pt }} .lim span {{ display: block; font-size: 8.6pt; color: {MUT}; line-height: 1.32 }}
.wrong div {{ background: {SOFT}; border-radius: 10px; padding: 8px 10px; font-size: 8.7pt; line-height: 1.35; margin-bottom: 7px }}
.wrong .x {{ color: {RED}; font-weight: 800 }} .wrong .ok {{ color: {GOOD}; font-weight: 800 }}
code {{ font-family: Menlo, monospace; font-size: 7.8pt; background: {INK}; color: #FFB3B5; border-radius: 4px; padding: 1px 5px }}
"""

links = "  ·  ".join(x for x in [short(_L["site"]) if _L.get("site") else "", short(_L["repo"]) if _L.get("repo") else ""] if x)
TOP = (f'<div class="top">{LOGO}<div class="div"></div><span class="prod">PROMO FINDER</span>'
       f'<div class="me"><b>{NAME}</b><br>{links}</div></div>')
n_cross = sum(p["kind"] == "cross" for p in P[:20])

page1 = f"""<div class="page">{TOP}
 <div class="row" style="align-items:flex-end;margin-bottom:14px">
  <div style="flex:1"><h1>Promo Finder picks a show's promo clips from its script.</h1>
   <div class="lead">To choose promos today, an editor watches all {WATCH_MIN:.0f} minutes of a new show, and a new show arrives every week.
    This tool reads the timestamped screenplay instead and returns clips that already meet the three promo rules, ranked, with a plan for the first week.</div></div>
  <div class="analogy" style="width:410px"><b>Think of it as a paper edit.</b> Film editors often plan cuts from a transcript before opening the footage.
   Promo Finder does that step for promos: the editor still opens the footage, but only to check {len(PLAN)} clips.</div>
 </div>

 <div class="row">
  <div style="flex:1">
   <h2>The three rules every clip must pass</h2>
   <div class="rules">
    <div class="rule"><b>20 to 60 seconds</b><span>One stretch, or two moments joined, even across episodes</span>{length_ic}</div>
    <div class="rule"><b>Hook within 3 seconds</b><span>The clip opens on the slap, threat or reveal, not a lead-in</span>{hook_ic}</div>
    <div class="rule"><b>Cut before the answer</b><span>It ends at peak tension and still makes sense to a new viewer</span>{cut_ic}</div>
   </div>
   <h2 style="margin-top:14px">From 50 scripts to 5 posts <span>bar length on a log scale</span></h2>
   {funnel()}
   <div class="note"><b>Code handles every timestamp and length</b>, so no clip can break a rule ({meta['rule_violations']} of {meta['candidates']} did).
    The AI makes only judgement calls: which line hooks, which beat leaves the viewer hanging, and which of two clips is stronger.</div>
  </div>
  <div style="width:440px"><h2>The #1 clip, second by second</h2>{featured()}</div>
 </div>

 <div class="row" style="margin-top:10px">
  <div style="flex:1"><h2>Week 1 <span>{PLAN_MIN:.0f} minutes of clips to approve</span></h2><div class="days">{week()}</div>
   <div class="note">{len(HOLD)} strong clips are held back because they give away twists. The same scene never runs two days in a row.</div></div>
  <div style="width:560px"><h2>Where the top 20 come from <span>episodes 1–50</span></h2>{episode_strip()}
   <div class="legend"><i style="background:{INK}"></i>one top-20 clip<i style="background:{RED}"></i>the #1 clip<i style="background:{PURPLE};border-radius:0;height:2px;width:12px;vertical-align:2px"></i>{n_cross} clips that join two episodes</div></div>
 </div>
 <div class="foot"><span>Run on all 50 episodes of <i>I Married a Broken Soldier. He was a Duke</i>. Every number is generated from the run files.</span><span>1 / 2</span></div>
</div>"""

page2 = f"""<div class="page">{TOP}
 <h1 style="font-size:20pt;margin-bottom:8px">How I checked it</h1>
 <div class="row">
  <div style="flex:1.05"><h2>Before vs after each fix <span>grey = before, green = final</span></h2>{before_after()}
   <div class="note">The big change: in the first version the AI chose the start and end of each clip and got the arithmetic wrong.
    Now it only marks moments, code builds the clips, and clips are ranked by comparing them two at a time instead of scoring each one alone.</div></div>
  <div style="flex:1"><h2>Tests where the right answer was known <span>no AI involved in the answer key</span></h2>
   <div class="tst"><div class="h"><b>26 of 29</b><span>shocking lines I planted in real episodes were tagged as hooks</span></div>{dots(29, 26, GOOD)}
    <div class="s">A random tagger would find about 4 (13%).</div></div>
   <div class="tst"><div class="h"><b>0 of 29</b><span>dull lines planted the same way were wrongly tagged</span></div>{dots(29, 0, RED)}</div>
   <div class="tst"><div class="h"><b>41–47 of 50</b><span>episodes where it found the writers' own closing cliffhanger</span></div>{dots(50, 47, GOOD, per_row=50, r=2.6, gap=6.7)}
    <div class="s">Depending on the model (82–94%); chance is 18–26%.</div></div>
  </div>
 </div>

 <div class="row" style="margin-top:14px">
  <div style="width:410px"><h2>Editor time per show</h2>{time_bars()}
   <div class="stats"><div class="st"><b>~7 min</b><span>to process a 50-episode show</span></div>
    <div class="st"><b>${SHOW_USD:.2f}</b><span>per show at API list prices</span></div>
    <div class="st"><b>1 command</b><span>for a new show or a new model</span></div></div></div>
  <div style="flex:1"><h2>What it can't do yet</h2><div class="lim">
    <div><b>Prove its taste.</b><span>Three AI judges agree with each other only weakly (ρ 0.26–0.49). Ratings from real editors would settle it.</span></div>
    <div><b>See the performance.</b><span>A slap is judged from the script's description, not from how the actor plays it.</span></div>
    <div><b>Know the final cut.</b><span>Times come from the script; if the edit drifts, the editor nudges the in and out points.</span></div>
    <div><b>Catch every repeat.</b><span>Two same-story pairs are still in the top 20.</span></div></div></div>
  <div style="width:360px"><h2>Where AI tools misled me</h2><div class="wrong">
    <div><span class="x">Asked for 20–60 s clips, it returned 9–160 s.</span> Models don't add up timestamps reliably. <span class="ok">So code now builds every clip.</span></div>
    <div><span class="x">The first picker rated its own clips 9.5/10.</span> Those scores had no relation to an independent judge's. <span class="ok">So a separate judge ranks the clips.</span></div>
    <div style="background:none;padding:2px 0 0;color:{MUT}">Built with Kiro (Claude), Gemini 3.5 Flash on Vertex for tagging and notes, TypeSafe Jev for ranking, and LiteLLM, so any model plugs in with one setting such as <code>PROMO_RANK_MODEL=openai/gpt-5</code>.</div></div></div>
 </div>
 <div class="foot"><span>Sources: experiments/BASELINE_v1 · RESULTS · JEV_RESULTS · REALWORLD_RESULTS(_lite) · AUDIT_* · DECK_EVIDENCE · runs/v3_final</span><span>2 / 2</span></div>
</div>"""

(OUT / "solution.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{page1}{page2}</body></html>")
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pwr:
    b = pwr.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1.6)
    pg.goto((OUT / "solution.html").as_uri())
    pg.wait_for_timeout(300)
    pg.pdf(path=str(OUT / "solution.pdf"), width="13.333in", height="7.5in", print_background=True)
    over = pg.evaluate("""() => [...document.querySelectorAll('.page')].map(p => { const r = p.getBoundingClientRect(); let w = -999;
        p.querySelectorAll('*').forEach(e => { if (e.closest('.foot')) return; const q = e.getBoundingClientRect();
          w = Math.max(w, q.bottom - (r.bottom - 26), q.right - (r.right - 30)); });
        return Math.round(w); })""")
    font_ok = pg.evaluate("document.fonts.check('12px Figtree')")
    for i, el in enumerate(pg.query_selector_all(".page"), 1):
        el.screenshot(path=str(OUT / f"page-{i}.png"))
    b.close()
print("overflow px per page (must be <= 0):", over, "| Figtree loaded:", font_ok)
