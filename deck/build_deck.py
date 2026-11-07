"""2-page solution deck, dark Kuku studio look (matches the website). 16:9 PDF, 1280x720 CSS px per page.
python deck/build_deck.py  ->  deck/solution.pdf (+ page-1.png, page-2.png)
Checks after rendering: overflow (must be <= 0) and empty space (largest blank band + card slack).
Every number comes from runs/v3_final and experiments/*. Icons: Lucide (ISC), deck/icons/."""
import html
import json
import math
import re
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
SHOW_USD = tok[0] * 1.5e-6 + tok[1] * 9e-6 + jev["cost_usd"]     # list-price estimate
WATCH_MIN = sum(e.duration for e in EPS) / 60
PLAN = meta["posting_plan"]["plan"]
HOLD = meta["posting_plan"]["hold"]
PLAN_MIN = sum(by[x["id"]]["duration"] for x in PLAN) / 60
TOP20_MIN = sum(p["duration"] for p in P[:20]) / 60
N_TAGS = sum(len(t["hooks"]) + len(t["cliffs"]) for t in DIAG["tags"].values())
N_BEATS = sum(len(e.beats) for e in EPS)
FONT = (ROOT / "web" / "fonts" / "Figtree.ttf").as_uri()
LOGO = (ROOT / "web" / "kuku-logo-white.svg").read_text()


def e(s):
    return html.escape(str(s))


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{int(s):02d}"


def short(u):
    return e(u.replace("https://", "").replace("http://", "").rstrip("/"))


def title(pid):
    return TITLES.get(pid, pid)


def icon(name, size=18, color="currentColor", stroke=2):
    s = (OUT / "icons" / f"{name}.svg").read_text()
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<svg[^>]*>", lambda m: re.sub(r'\s(class|width|height)="[^"]*"', "", m.group(0)), s, count=1)
    s = s.replace('stroke-width="2"', f'stroke-width="{stroke}"').replace('stroke="currentColor"', f'stroke="{color}"')
    return s.replace("<svg", f'<svg width="{size}" height="{size}"', 1).strip()


# ------------------------------------------------------------------ data for the #1 promo
p1 = P[0]
s1 = p1["segments"][0]
ep1 = IDX.eps[s1["episode"]]
beats1 = [b for b in ep1.beats if b.start >= s1["start"] - .01 and b.end <= s1["end"] + .01 and b.type != "camera"]
lines1 = [b for b in beats1 if b.type == "dialogue"]
HOOK = lines1[0]
BUILD = min(lines1, key=lambda b: abs((b.start - s1["start"]) - p1["duration"] * .45))
CUT = [b for b in beats1 if b.type in ("action", "dialogue")][-1]
D1 = p1["duration"]
rel = lambda b: b.start - s1["start"]  # noqa: E731


def phone():
    feed = [b for b in beats1 if rel(b) <= rel(CUT) + .01][-3:]
    rows = []
    for k, b in enumerate(feed):
        now = k == len(feed) - 1
        who = b.speaker or ("sound" if b.type == "sfx" else "action")
        txt = f"“{b.text}”" if b.type == "dialogue" else b.text
        rows.append(f'<div class="fi{" now" if now else ""}{" a" if b.type != "dialogue" else ""}"><b>{e(who)}</b>'
                    f'<span>{e(txt[:96] + ("…" if len(txt) > 96 else ""))}</span></div>')
    pct = lambda t: 100 * t / D1  # noqa: E731
    marks = "".join(f'<i style="left:{pct(rel(b)):.1f}%;background:{c}"></i>' for b, c in ((HOOK, "#EC1C24"), (BUILD, "#fff"), (CUT, "#B48CFF")))
    return f"""<div class="phone"><div class="scr">
      <div class="ptop"><span>Promo #1 · {e(title(p1['id']))}</span><span class="chip">CUT</span></div>
      <div class="feed">{''.join(rows)}</div>
      <div class="pbar"><b style="width:{pct(3):.1f}%"></b><u style="width:{pct(rel(CUT)):.1f}%"></u>{marks}<em style="left:{pct(rel(CUT)):.1f}%"></em></div>
      <div class="plab"><span>0 s</span><span>{D1:.0f} s</span></div></div></div>"""


def callouts():
    rows = [("HOOK", HOOK, "#EC1C24", "zap", "Opens on a scream. Stops the scroll."),
            ("BUILD", BUILD, "#fff", "swords", "Stakes are clear with no back-story."),
            ("CUT", CUT, "#B48CFF", "scissors", f"Cuts mid-threat. Episode {ep1.number + 1} answers it.")]
    out = []
    for lab, b, col, ic, why in rows:
        txt = f"“{b.text}”" if b.type == "dialogue" else b.text
        out.append(f'<div class="co"><div class="coh" style="color:{col}">{icon(ic, 14, col)}{lab}<span>{rel(b):.0f} s</span></div>'
                   f'<div class="coq">{e(txt[:92] + ("…" if len(txt) > 92 else ""))}</div><div class="cow">{why}</div></div>')
    w, l_, t = p1["record"].split("-")
    out.append(f'<div class="cowin">{icon("trophy", 16, "#FFB547")}<span>Won <b>{w} of {int(w) + int(l_) + int(t)}</b> head-to-heads. '
               'The judge sees only the clip, like a stranger scrolling.</span></div>')
    return "".join(out)


def pipeline():
    steps = [("scroll-text", "parse", f"{N_BEATS:,}", "timed beats", "CODE", "Every line, action and sound with its exact start and end"),
             ("sparkles", "tag", f"{N_TAGS}", "moments", "AI", "Gemini marks hook and cliffhanger lines by ID. It never writes a time"),
             ("scissors", "assemble", f"{meta['candidates']}", "clips", "CODE", "Every hook → cliff window that fits 20–60 s, incl. cross-episode"),
             ("git-compare-arrows", "rank", "20", "shortlisted", "AI", f"{pw['verdicts']} head-to-heads, each asked in both orders"),
             ("calendar-days", "plan", f"{len(PLAN)}", "posts, week 1", "EDITOR", f"{len(HOLD)} spoiler-heavy clips held for later weeks")]
    out = []
    for i, (ic, name, num, unit, who, txt) in enumerate(steps):
        col = {"CODE": "#2BD49A", "AI": "#EC1C24", "EDITOR": "#FFFFFF"}[who]
        out.append(f'<div class="st"><div class="sth"><span class="sti" style="color:{col};border-color:{col}55;background:{col}14">{icon(ic, 17, col)}</span>'
                   f'<span class="stn">{i + 1:02d} · {name}</span><span class="stw" style="color:{col}">{who}</span></div>'
                   f'<div class="stv"><b>{num}</b>{unit}</div><div class="stt">{txt}</div></div>')
        if i < len(steps) - 1:
            out.append('<div class="sta">›</div>')
    return "".join(out)


GRADS = ["linear-gradient(160deg,#7A0B10 0%,#2A0507 55%,#0B0B0D 100%)", "linear-gradient(160deg,#5B1E6E 0%,#1E0A26 55%,#0B0B0D 100%)",
         "linear-gradient(160deg,#8A3B0B 0%,#2B1205 55%,#0B0B0D 100%)", "linear-gradient(160deg,#0E4F5C 0%,#071F24 55%,#0B0B0D 100%)",
         "linear-gradient(160deg,#6E0E3A 0%,#260715 55%,#0B0B0D 100%)"]


def posters():
    out = []
    for k, x in enumerate(PLAN):
        p = by[x["id"]]
        out.append(f'<div class="pos" style="background:{GRADS[k % 5]}"><div class="pday">DAY {x["day"]}</div>'
                   f'<div class="pt">{e(title(p["id"]))}</div><div class="pm">Ep {p["segments"][0]["episode"]} · {p["duration"]:.0f} s · #{p["rank"]}</div>'
                   f'<div class="pplay">{icon("film", 12, "#fff")}</div></div>')
    return "".join(out)


def episode_map():
    W, cw = 400, 400 / 50
    X = lambda n: (n - .5) * cw  # noqa: E731
    count, arcs = {}, []
    for p in P[:20]:
        eps = sorted({s["episode"] for s in p["segments"]})
        if len(eps) == 2:
            arcs.append((eps[0], eps[1], p["rank"]))
        for n in eps:
            count[n] = count.get(n, 0) + 1
    o = [f'<svg width="{W}" height="96" viewBox="0 0 {W} 96">']
    for a, b, r in arcs:
        x1, x2 = X(a), X(b)
        o.append(f'<path d="M{x1} 62 Q{(x1 + x2) / 2} {62 - (x2 - x1) * .75} {x2} 62" fill="none" stroke="#B48CFF" stroke-width="1.5"/>'
                 f'<text x="{(x1 + x2) / 2}" y="{58 - (x2 - x1) * .38}" text-anchor="middle" class="ax" fill="#B48CFF">#{r}</text>')
    for n in range(1, 51):
        o.append(f'<rect x="{X(n) - cw / 2 + .8}" y="66" width="{cw - 1.6}" height="9" rx="2" fill="#26262B"/>')
        for k in range(count.get(n, 0)):
            col = "#EC1C24" if (n == s1["episode"] and k == 0) else "#fff"
            o.append(f'<circle cx="{X(n)}" cy="{59 - k * 6.5}" r="2.5" fill="{col}"/>')
    for n in (1, 10, 20, 30, 40, 50):
        o.append(f'<text x="{X(n)}" y="90" text-anchor="middle" class="ax2">{n}</text>')
    return "".join(o) + "</svg>"


def dots(n, hit, col, per=29, r=4.2, g=10.2):
    rows = math.ceil(n / per)
    o = [f'<svg width="{per * g}" height="{rows * g}">']
    for i in range(n):
        o.append(f'<circle cx="{(i % per) * g + g / 2}" cy="{(i // per) * g + g / 2}" r="{r}" fill="{col if i < hit else "#2A2A30"}"/>')
    return "".join(o) + "</svg>"


def evo():
    rows = [("timer", "Clips outside 20–60 s", "16%", "0%", "the AI only tags; code builds clips"),
            ("scissors", "Endings cut short by code", "21", "0", "clips end on a tagged cliff beat"),
            ("git-compare-arrows", "Tied scores in the ranking", "81%", "0%", f"head-to-head, both orders; {pw['position_consistency'] * 100:.0f}% verdicts match"),
            ("gauge", "Top-20 order on a re-check (ρ)", "0.44", "0.75–0.90", "every pair asked in both orders"),
            ("split", "Same-story pairs in top 20", "4", "2", "dedupe on story, not just footage")]
    return "".join(f'<div class="ev"><span class="evi">{icon(ic, 16, "#2BD49A")}</span><div class="evl"><b>{a}</b><span>{d}</span></div>'
                   f'<div class="evn"><s>{b}</s><i>→</i><b>{c}</b></div></div>' for ic, a, b, c, d in rows)


def tbar(label, val, maxv, col, sub):
    return (f'<div class="tl"><div class="tlh"><b style="color:{col}">{val:.0f} min</b><span>{sub}</span></div>'
            f'<div class="tlt"><i style="width:{max(1.2, 100 * val / maxv):.1f}%;background:{col}"></i></div></div>')


CSS = """
@font-face { font-family: Figtree; src: url('__FONT__') format('truetype'); font-weight: 300 900 }
@page { size: 13.333in 7.5in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
:root { --red:#EC1C24; --red2:#FF4D52; --tx2:#C9CBD1; --mut:#8A8D96; --line:rgba(255,255,255,.09); --card:#0F0F12; --good:#2BD49A; --vio:#B48CFF }
body { font-family: Figtree, -apple-system, Arial, sans-serif; color:#fff; font-size:10px; line-height:1.3; background:#000 }
.page { width:1280px; height:720px; position:relative; overflow:hidden; page-break-after:always; padding:18px 30px 14px;
  background: radial-gradient(ellipse 60% 50% at 30% 0%, rgba(236,28,36,.20), transparent 70%), linear-gradient(90deg, #000 55%, #1C0204 100%), #000 }
.top { display:flex; align-items:center; gap:12px; height:30px; margin-bottom:12px }
.top svg { height:20px; width:auto } .top .pr { font-weight:700; font-size:12.5px; color:var(--tx2); padding-left:12px; border-left:1px solid rgba(255,255,255,.18) }
.top .me { margin-left:auto; display:flex; gap:16px; align-items:center; font-size:11px; color:var(--tx2) } .top .me b { color:#fff; font-size:12px }
.top .dot { width:6px; height:6px; border-radius:50%; background:var(--red); display:inline-block; margin-right:6px; box-shadow:0 0 8px var(--red) }
.card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:12px 14px; position:relative }
.k { font-size:9px; font-weight:800; letter-spacing:1.6px; color:var(--mut); text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px }
.k em { color:var(--red2); font-style:normal } .k svg { flex:none }
.grid { display:grid; gap:12px }
/* page 1 */
.eyebrow { display:inline-block; font-size:10px; font-weight:700; color:var(--tx2); border:1px solid rgba(255,255,255,.18); border-radius:999px; padding:2px 10px; margin-bottom:8px }
h1 { font-size:35px; line-height:1.02; font-weight:800; letter-spacing:-1.3px } h1 span { color:var(--red); display:block }
.lead { font-size:12px; color:var(--tx2); margin-top:8px; line-height:1.42 } .lead b { color:#fff }
.ba { display:grid; grid-template-columns:1fr 26px 1fr; align-items:center; margin-top:10px; gap:0 }
.bab { border-radius:14px; padding:7px 12px; display:flex; gap:10px; align-items:center }
.bab.o { background:#141417; border:1px solid var(--line) } .bab.n { background:rgba(43,212,154,.08); border:1px solid rgba(43,212,154,.35) }
.bab b { display:block; font-size:21px; font-weight:800; letter-spacing:-.6px; line-height:1 } .bab span { font-size:10px; color:var(--tx2) }
.baa { text-align:center; color:var(--mut); font-size:18px }
.rules { margin-top:10px; border-radius:18px; padding:11px 16px; background: radial-gradient(ellipse 90% 140% at 0% 100%, #D6363B 0%, #A3080E 45%, #8E0207 100%);
  display:grid; grid-template-columns:repeat(3,1fr); gap:0 }
.rule { padding:0 14px; border-left:1px solid rgba(255,255,255,.28) } .rule:first-child { padding-left:0; border-left:0 }
.rule .rh { display:flex; align-items:center; gap:6px; font-size:9px; font-weight:800; letter-spacing:1.3px; color:rgba(255,255,255,.8) }
.rule b { display:block; font-size:22px; font-weight:800; letter-spacing:-.6px; line-height:1.05; margin:4px 0 3px } .rule span { font-size:10px; color:rgba(255,255,255,.88); line-height:1.3; display:block }
.rule svg.mini { margin-top:4px }
.phone { width:180px; height:318px; flex:none; border-radius:32px; background:#050505; padding:8px; box-shadow:0 0 0 2px #2A2A2E, 0 30px 60px -20px rgba(236,28,36,.35); position:relative }
.phone::before { content:""; position:absolute; top:16px; left:50%; width:60px; height:16px; margin-left:-30px; background:#000; border-radius:9px; z-index:2 }
.scr { height:100%; border-radius:25px; overflow:hidden; position:relative; padding:38px 12px 12px; display:flex; flex-direction:column;
  background: radial-gradient(ellipse 120% 70% at 50% 25%, #3A1013 0%, #120709 55%, #050505 100%) }
.ptop { display:flex; justify-content:space-between; align-items:center; font-size:9px; font-weight:700; color:rgba(255,255,255,.8) }
.chip { font-size:8px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:999px; background:#fff; color:#000 }
.feed { margin-top:auto; display:flex; flex-direction:column; gap:8px; margin-bottom:12px }
.fi b { display:block; font-size:7.5px; letter-spacing:1px; color:var(--red2); text-transform:uppercase }
.fi span { display:block; font-size:10px; font-weight:700; color:rgba(255,255,255,.5); line-height:1.25 } .fi.a span { font-style:italic; font-weight:500 }
.fi.now span { font-size:12px; font-weight:800; color:#fff } .fi.now.a span { font-size:10.5px; font-weight:600; color:#E9EAEE }
.pbar { position:relative; height:5px; border-radius:3px; background:rgba(255,255,255,.2) }
.pbar b { position:absolute; left:0; top:0; bottom:0; background:var(--red); border-radius:3px; z-index:2 } .pbar u { position:absolute; left:0; top:0; bottom:0; background:rgba(255,255,255,.7); border-radius:3px }
.pbar i { position:absolute; top:-3px; width:3px; height:11px; border-radius:2px; margin-left:-1px; z-index:3 }
.pbar em { position:absolute; top:-5px; width:13px; height:13px; border-radius:50%; background:#fff; margin-left:-6px; box-shadow:0 0 0 3px rgba(236,28,36,.55); z-index:4 }
.plab { display:flex; justify-content:space-between; font-family:Menlo,monospace; font-size:8px; color:rgba(255,255,255,.55); margin-top:6px }
.cos { flex:1; display:flex; flex-direction:column; gap:6px; justify-content:space-between }
.co { border-left:2px solid rgba(255,255,255,.14); padding-left:10px }
.coh { display:flex; align-items:center; gap:5px; font-size:9.5px; font-weight:800; letter-spacing:1.2px } .coh span { color:var(--mut); font-weight:600; letter-spacing:0; margin-left:3px }
.coq { font-size:11px; font-weight:700; line-height:1.28; margin:3px 0 2px } .cow { font-size:10px; color:var(--mut) }
.cowin { display:flex; gap:8px; align-items:flex-start; background:rgba(255,181,71,.08); border:1px solid rgba(255,181,71,.3); border-radius:12px; padding:8px 10px; font-size:10px; color:var(--tx2) }
.cowin b { color:#fff } .cowin svg { flex:none; margin-top:1px }
.pipe { display:flex; align-items:stretch; gap:6px }
.st { flex:1; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:8px 11px }
.sth { display:flex; align-items:center; gap:7px } .sti { width:28px; height:28px; border-radius:9px; border:1px solid; display:inline-flex; align-items:center; justify-content:center }
.stn { font-size:12.5px; font-weight:800 } .stw { margin-left:auto; font-size:8px; font-weight:800; letter-spacing:1.2px }
.stv { font-size:10.5px; color:var(--mut); margin:4px 0 2px } .stv b { font-size:21px; font-weight:800; color:#fff; letter-spacing:-.6px; margin-right:5px }
.stt { font-size:9.6px; color:var(--mut); line-height:1.3 } .sta { align-self:center; color:var(--red); font-size:22px; font-weight:800 }
.posters { display:grid; grid-template-columns:repeat(5,1fr); gap:9px; flex:1 }
.pos { border-radius:14px; padding:10px 11px; position:relative; display:flex; flex-direction:column; border:1px solid rgba(255,255,255,.08); overflow:hidden }
.pos::after { content:""; position:absolute; inset:0; background:repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 1px, transparent 1px 3px); pointer-events:none }
.pday { font-size:8.5px; font-weight:800; letter-spacing:1.4px; color:#FF8A8E } .pt { font-size:14px; font-weight:800; line-height:1.14; margin-top:auto; letter-spacing:-.2px }
.pm { font-size:9px; color:rgba(255,255,255,.65); margin-top:4px } .pplay { position:absolute; right:9px; top:8px; width:22px; height:22px; border-radius:50%; background:rgba(255,255,255,.14); display:flex; align-items:center; justify-content:center }
.note { font-size:10px; color:var(--mut); line-height:1.35 } .note b { color:#fff }
svg text { font-family:Figtree, sans-serif } .ax { font-size:8px; font-weight:800 } .ax2 { font-size:7.5px; fill:#8A8D96 }
.lg { font-size:9px; color:var(--mut); display:flex; gap:12px; flex-wrap:wrap } .lg i { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:4px; vertical-align:0 }
.foot { position:absolute; left:30px; right:30px; bottom:7px; display:flex; justify-content:space-between; font-size:8px; color:#5D606A }
/* page 2 */
h2 { font-size:30px; font-weight:800; letter-spacing:-.9px; line-height:1 } h2 span { color:var(--red) }
.ev { display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid var(--line) } .ev:last-child { border:0 }
.evi { width:30px; height:30px; border-radius:9px; background:rgba(43,212,154,.1); display:flex; align-items:center; justify-content:center; flex:none }
.evl { flex:1 } .evl b { display:block; font-size:12px } .evl span { font-size:9.8px; color:var(--mut) }
.evn { display:flex; align-items:baseline; gap:7px } .evn s { font-size:14px; color:#6E717B; font-weight:700 } .evn i { color:#6E717B; font-style:normal }
.evn b { font-size:22px; font-weight:800; color:var(--good); letter-spacing:-.5px }
.ts { padding:9px 0; border-bottom:1px solid var(--line) } .ts:last-of-type { border:0 }
.tsh { display:flex; align-items:center; gap:9px; margin-bottom:6px } .tsh .ic { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex:none }
.tsh b { font-size:21px; font-weight:800; letter-spacing:-.5px } .tsh span { font-size:11px; color:var(--tx2) }
.tss { font-size:9.6px; color:var(--mut); margin-top:5px }
.tl { margin-bottom:9px } .tlh { display:flex; align-items:baseline; gap:8px; margin-bottom:4px } .tlh b { font-size:20px; font-weight:800; letter-spacing:-.5px } .tlh span { font-size:10.5px; color:var(--tx2) }
.tlt { height:12px; border-radius:6px; background:#1C1C21; overflow:hidden } .tlt i { display:block; height:100%; border-radius:6px }
.lim { display:flex; gap:10px; padding:7px 0; border-bottom:1px solid var(--line) } .lim:last-child { border:0 }
.lim .ic { width:28px; height:28px; border-radius:9px; background:rgba(255,181,71,.1); display:flex; align-items:center; justify-content:center; flex:none }
.lim b { display:block; font-size:11.5px } .lim span { font-size:9.8px; color:var(--mut); line-height:1.3 }
.wr { border-radius:12px; padding:9px 11px; background:#141417; border:1px solid var(--line); font-size:10.2px; line-height:1.38; color:var(--tx2); margin-bottom:8px }
.wr .x { color:var(--red2); font-weight:800 } .wr .ok { color:var(--good); font-weight:800 }
.tools { display:flex; flex-wrap:wrap; gap:5px } .tool { display:inline-flex; align-items:center; gap:5px; border:1px solid rgba(255,255,255,.14); border-radius:999px; padding:3px 9px; font-size:9.5px; color:var(--tx2); background:#121215 }
.kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:10px }
.kp { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:10px 12px; display:flex; gap:10px; align-items:center }
.kp .ic { width:34px; height:34px; border-radius:10px; background:rgba(236,28,36,.12); display:flex; align-items:center; justify-content:center; flex:none }
.kp b { display:block; font-size:14px; font-weight:800; line-height:1.15 } .kp span { display:block; font-size:9.6px; color:var(--tx2); line-height:1.3; margin-top:2px }
.arch { display:flex; align-items:stretch; gap:0 }
.an { flex:1; background:#141417; border:1px solid var(--line); border-radius:12px; padding:6px 8px; display:flex; flex-direction:column; gap:3px; min-width:0 }
.anh { display:flex; align-items:center; gap:6px } .anh .ic { width:24px; height:24px; border-radius:7px; display:flex; align-items:center; justify-content:center; flex:none }
.anh b { font-size:11.5px; font-weight:800; line-height:1.1 } .anh i { margin-left:auto; font-style:normal; font-size:7.5px; font-weight:800; letter-spacing:1px }
.an code { align-self:flex-start; font-size:8.5px } .an > span { font-size:9.2px; color:var(--tx2); line-height:1.28 }
.aa { width:14px; flex:none; display:flex; align-items:center; justify-content:center; color:var(--red); font-weight:800; font-size:16px }
.infra { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:6px }
.infra > div { display:flex; gap:7px; align-items:flex-start; font-size:9.2px; color:var(--tx2); line-height:1.3; border-top:1px solid var(--line); padding-top:5px } .infra b { color:#fff } .infra svg { flex:none; margin-top:1px }
.vers { display:grid; grid-template-columns:repeat(3,1fr); gap:10px }
.vc { background:#141417; border:1px solid var(--line); border-radius:12px; padding:9px 11px }
.vh { display:flex; align-items:center; gap:7px; margin-bottom:5px } .vh b { font-size:12.5px; font-weight:800 }
.vt { font-size:9px; font-weight:800; background:var(--red); color:#fff; border-radius:6px; padding:2px 6px }
.vd { font-size:9.3px; color:var(--tx2); line-height:1.28; min-height:0 } .vb { font-size:9.2px; color:#FF8A8E; font-weight:700; line-height:1.28; margin:3px 0 2px; min-height:0 }
.vn { display:flex; align-items:baseline; gap:4px; border-top:1px solid var(--line); padding:1px 0 }
.vn s { font-size:10px; color:var(--mut) } .vn i { font-style:normal; font-size:9px; color:var(--mut) } .vn b { font-size:13.5px; font-weight:800; color:var(--good) } .vn span { margin-left:auto; font-size:9px; color:var(--mut); text-align:right }
.p2 .ts { padding:5px 0 } .p2 .tsh { margin-bottom:4px } .p2 .tsh b { font-size:18px; white-space:nowrap } .p2 .tsh span { font-size:10px } .p2 .tsh .ic { width:26px; height:26px }
.p2b .lim { padding:4px 0; gap:8px } .p2b .lim .ic { width:24px; height:24px } .p2b .lim b { font-size:11px } .p2b .lim span { font-size:9.3px } .p2b .card { padding:10px 12px }
.p2b .wr { padding:6px 9px; margin-bottom:5px; font-size:9.6px } .p2 .card { padding:10px 12px } .p2 h2 { font-size:26px }
.tst { display:grid; grid-template-columns:1fr 1fr; gap:14px } .tst > div { display:flex; flex-direction:column; gap:8px }
.tsl b { display:block; font-size:11.5px; font-weight:800 } .tsl span { display:block; font-size:9.3px; color:var(--mut); line-height:1.3; margin-top:2px }
.hm { flex:none } .hml { font-size:7.5px; color:var(--mut); margin-top:3px; display:flex; align-items:center; gap:4px } .hml i { width:7px; height:7px; border-radius:2px; display:inline-block }
.lim .ic.g { background:rgba(43,212,154,.1) }
code { font-family:Menlo,monospace; font-size:9px; background:rgba(255,255,255,.08); color:#FFB3B5; border-radius:5px; padding:1px 5px }
""".replace("__FONT__", FONT)

links = " · ".join(x for x in [short(_L["site"]) if _L.get("site") else "", short(_L["repo"]) if _L.get("repo") else ""] if x)
TOP = (f'<div class="top">{LOGO}<span class="pr">Promo Finder</span>'
       f'<div class="me"><span><span class="dot"></span><b>{NAME}</b></span><span>{links}</span></div></div>')
X3 = lambda t: 4 + 132 * t / 90  # noqa: E731
mini_len = (f'<svg class="mini" width="140" height="16"><rect x="4" y="6" width="132" height="5" rx="2.5" fill="rgba(255,255,255,.25)"/>'
            f'<rect x="{X3(20)}" y="6" width="{X3(60) - X3(20)}" height="5" rx="2.5" fill="#fff"/><text x="{X3(20)}" y="4" font-size="6" fill="#fff" text-anchor="middle">20</text>'
            f'<text x="{X3(60)}" y="4" font-size="6" fill="#fff" text-anchor="middle">60</text></svg>')
mini_hook = ('<svg class="mini" width="140" height="16"><rect x="4" y="6" width="132" height="5" rx="2.5" fill="rgba(255,255,255,.25)"/>'
             '<rect x="4" y="6" width="14" height="5" rx="2.5" fill="#fff"/><text x="24" y="11" font-size="6.5" fill="#fff">first 3 s</text></svg>')
mini_cut = ('<svg class="mini" width="140" height="16"><rect x="4" y="6" width="100" height="5" rx="2.5" fill="rgba(255,255,255,.25)"/>'
            '<rect x="80" y="6" width="24" height="5" rx="2.5" fill="#fff"/><line x1="110" y1="1" x2="110" y2="16" stroke="#fff" stroke-dasharray="2 2"/>'
            '<text x="116" y="12" font-size="10" font-weight="800" fill="#fff">?</text></svg>')

page1 = f"""<div class="page">{TOP}
 <div class="grid" style="grid-template-columns: 1fr 530px; gap:22px">
  <div>
   <div class="eyebrow">Kuku AI Generalist · Problem 1 · Find the promos</div>
   <h1>every show hides its best promo.<span>we find it in the script.</span></h1>
   <div class="lead">An editor watches all <b>{WATCH_MIN:.0f} minutes</b> of every new show to choose promo moments, and a new show ships every week.
    Promo Finder reads the timestamped screenplay instead and hands back <b>{meta['ranked']} ranked, post-ready promos</b> and a week-1 plan.</div>
   <div class="ba">
    <div class="bab o">{icon("eye-off", 22, "#8A8D96")}<div><b>{WATCH_MIN:.0f} min</b><span>of footage watched per show, today</span></div></div>
    <div class="baa">→</div>
    <div class="bab n">{icon("wand-sparkles", 22, "#2BD49A")}<div><b style="color:#2BD49A">~7 min</b><span>script to ranked promos, then {PLAN_MIN:.0f} min to approve</span></div></div>
   </div>
   <div class="rules">
    <div class="rule"><div class="rh">{icon("timer", 12, "#fff")}RULE 1</div><b>20–60 s</b><span>One stretch, or moments joined across episodes</span>{mini_len}</div>
    <div class="rule"><div class="rh">{icon("zap", 12, "#fff")}RULE 2</div><b>hook ≤ 3 s</b><span>Opens on the slap, threat or reveal, not a lead-in</span>{mini_hook}</div>
    <div class="rule"><div class="rh">{icon("scissors", 12, "#fff")}RULE 3</div><b>cut early</b><span>Ends before the answer, and still makes sense cold</span>{mini_cut}</div>
   </div>
  </div>
  <div class="card" style="display:flex; gap:14px; padding:11px 12px; background:linear-gradient(160deg,#160709,#0B0B0D)">
   {phone()}
   <div class="cos"><div class="k" style="margin:0">{icon("clapperboard", 12, "#8A8D96")}the #1 promo, beat by beat</div>{callouts()}</div>
  </div>
 </div>

 <div style="margin-top:10px"><div class="k">{icon("cpu", 12, "#8A8D96")}how it works · <em>code owns every timestamp and length, so 0 of {meta['candidates']} clips break a rule; the AI only judges drama</em></div>
  <div class="pipe">{pipeline()}</div></div>

 <div class="grid" style="grid-template-columns: 1fr 432px; gap:14px; margin-top:10px; height:146px">
  <div style="display:flex; flex-direction:column"><div class="k">{icon("calendar-days", 12, "#8A8D96")}week 1 · <em>post these first</em><span style="margin-left:auto;text-transform:none;letter-spacing:0;font-weight:600">{len(HOLD)} clips held back for giving away twists</span></div>
   <div class="posters">{posters()}</div></div>
  <div class="card" style="padding:10px 14px"><div class="k" style="margin-bottom:2px">{icon("crosshair", 12, "#8A8D96")}where the top 20 come from · episodes 1–50</div>{episode_map()}
   <div class="lg"><span><i style="background:#fff"></i>top-20 clip</span><span><i style="background:#EC1C24"></i>the #1 clip</span><span><i style="background:#B48CFF;border-radius:0;height:2px;width:12px;vertical-align:2px"></i>joins two episodes</span></div></div>
 </div>
 <div class="foot"><span>Run on all 50 episodes of <i>I Married a Broken Soldier. He was a Duke</i>. Every number is generated from the run files.</span><span>1 / 2</span></div>
</div>"""

PC = int(pw["position_consistency"] * 100 + 0.5)
FIRST = int(pw["first_position_win_rate"] * 100 + 0.5)
DUPS = meta["story_duplicates_removed"]


def arch():
    n = [("scroll-text", "parse", "parser.py", "CODE", f"50 scripts become {meta.get('beats', 3727):,} beats, each with an ID, start, end and speaker"),
         ("sparkles", "tag", "moments.py", "AI", "Gemini 3.5 Flash (Vertex) marks hook and cliff beats by ID. 500 tags, 0 bad IDs"),
         ("scissors", "build windows", "moments.py", "CODE", f"Each hook→cliff pair becomes a clip: 20–60 s, two parts, or two episodes. {meta['candidates']} clips"),
         ("gauge", "screen", "jev.py", "AI", "Jev scores each clip on a rubric, in both list orders. 660 calls, 218 s"),
         ("split", "dedupe + shortlist", "diversity.py", "CODE", f"Embeddings drop {DUPS} same-story clips. MMR keeps a varied top {meta['shortlist_size']}"),
         ("swords", "rank", "rerank.py", "AI", f"Jev judges {pw['pairs_asked_both_ways']} pairs both ways. Bradley-Terry orders {pw['verdicts']} verdicts"),
         ("calendar-days", "notes + plan", "explain.py", "AI", "Hook, cliff and why for the top 30, plus the week-1 plan, after ranking"),
         ("film", "review site", "web/ · export.py", "EDITOR", "Phone player, notes, CSV. The editor approves or rejects")]
    col = {"CODE": "#2BD49A", "AI": "#FF4D52", "EDITOR": "#C9CBD1"}
    out = []
    for i, (ic, t, f, kind, d) in enumerate(n):
        c = col[kind]
        out.append(f'<div class="an"><div class="anh"><span class="ic" style="background:{c}1F">{icon(ic, 14, c)}</span><b>{t}</b><i style="color:{c}">{kind}</i></div>'
                   f'<code>{f}</code><span>{d}</span></div>' + ('<div class="aa">›</div>' if i < len(n) - 1 else ''))
    return "".join(out)


def h2h(cell=5.9):
    ids = [x["id"] for x in P[:20]]
    pr = {}
    for c in DIAG["jev_comparisons"]:
        pr[(c["a"], c["b"])] = c["p"]; pr[(c["b"], c["a"])] = 1 - c["p"]
    L, T = 16, 12
    out = [f'<svg width="{L + 20 * cell + 2}" height="{T + 20 * cell + 2}">']
    for i, a in enumerate(ids):
        for j, b in enumerate(ids):
            x, y = L + j * cell, T + i * cell
            if i == j:
                out.append(f'<rect x="{x}" y="{y}" width="{cell - .8}" height="{cell - .8}" fill="#222"/>'); continue
            v = pr.get((a, b))
            if v is None:
                col = "#1A1A1D"
            elif v >= .5:
                col = f"rgba(236,28,36,{.18 + 1.6 * (v - .5):.2f})"
            else:
                col = f"rgba(120,124,135,{.10 + .9 * (.5 - v):.2f})"
            out.append(f'<rect x="{x}" y="{y}" width="{cell - .8}" height="{cell - .8}" rx="1" fill="{col}"/>')
    for k in (1, 5, 10, 15, 20):
        out.append(f'<text x="{L - 3}" y="{T + (k - .5) * cell + 2.5}" font-size="6.5" fill="#8A8D96" text-anchor="end">{k}</text>')
        out.append(f'<text x="{L + (k - .5) * cell}" y="{T - 3}" font-size="6.5" fill="#8A8D96" text-anchor="middle">{k}</text>')
    out.append("</svg>")
    return "".join(out)


def confusion():
    c = 40
    cells = [(0, 0, "26", "hit", "#2BD49A", .9), (1, 0, "3", "missed", "#55575F", .25), (0, 1, "0", "false alarm", "#FF4D52", .08), (1, 1, "29", "ignored", "#2BD49A", .9)]
    L, T = 50, 14
    o = [f'<svg width="{L + 2 * c + 2}" height="{T + 2 * c + 2}">',
         f'<text x="{L + c / 2}" y="9" font-size="7.5" fill="#8A8D96" text-anchor="middle">tagged</text>',
         f'<text x="{L + 1.5 * c}" y="9" font-size="7.5" fill="#8A8D96" text-anchor="middle">not tagged</text>',
         f'<text x="{L - 5}" y="{T + c / 2 + 3}" font-size="7.5" fill="#8A8D96" text-anchor="end">planted hook</text>',
         f'<text x="{L - 5}" y="{T + 1.5 * c + 3}" font-size="7.5" fill="#8A8D96" text-anchor="end">dull decoy</text>']
    for cx, cy, n, lab, col, a in cells:
        x, y = L + cx * c, T + cy * c
        o.append(f'<rect x="{x}" y="{y}" width="{c - 3}" height="{c - 3}" rx="7" fill="{col}" fill-opacity="{a}"/>'
                 f'<text x="{x + (c - 3) / 2}" y="{y + 19}" font-size="15" font-weight="800" fill="#fff" text-anchor="middle">{n}</text>'
                 f'<text x="{x + (c - 3) / 2}" y="{y + 30}" font-size="6.5" fill="rgba(255,255,255,.75)" text-anchor="middle">{lab}</text>')
    o.append("</svg>")
    return "".join(o)


def cliffbars(w=128):
    rows = [("3.1 Flash Lite", 94, 84, 98, 18), ("3.5 Flash", 82, 69, 90, 26)]
    o = [f'<svg width="{w + 30}" height="92">']
    y = 4
    for name, v, lo, hi, ch in rows:
        o.append(f'<text x="0" y="{y + 7}" font-size="8" fill="#C9CBD1" font-weight="700">{name}</text>')
        o.append(f'<rect x="0" y="{y + 11}" width="{w}" height="9" rx="4.5" fill="#1E1E22"/>'
                 f'<rect x="0" y="{y + 11}" width="{w * v / 100}" height="9" rx="4.5" fill="#2BD49A"/>'
                 f'<line x1="{w * lo / 100}" x2="{w * hi / 100}" y1="{y + 15.5}" y2="{y + 15.5}" stroke="#0B0B0D" stroke-width="1.6"/>'
                 f'<text x="{w + 5}" y="{y + 19}" font-size="9" font-weight="800" fill="#2BD49A">{v}%</text>')
        o.append(f'<rect x="0" y="{y + 24}" width="{w}" height="9" rx="4.5" fill="#1E1E22"/>'
                 f'<rect x="0" y="{y + 24}" width="{w * ch / 100}" height="9" rx="4.5" fill="#55575F"/>'
                 f'<text x="{w * ch / 100 + 4}" y="{y + 31.5}" font-size="7" fill="#8A8D96">chance {ch}%</text>')
        y += 46
    o.append("</svg>")
    return "".join(o)



def ver(tag, title, did, broke, nums):
    rows = "".join(f'<div class="vn">' + (f'<s>{b}</s><i>→</i>' if b else '') + f'<b>{c}</b><span>{l}</span></div>' for l, b, c in nums)
    return (f'<div class="vc"><div class="vh"><span class="vt">{tag}</span><b>{title}</b></div><div class="vd">{did}</div>'
            f'<div class="vb">{broke}</div>{rows}</div>')


page2 = f"""<div class="page p2">{TOP}
 <h2 style="margin-bottom:6px">how it's built <span>· and how i got there</span></h2>
 <div class="card" style="padding:10px 12px 10px">
  <div class="k">{icon("cpu", 12, "#8A8D96")}architecture · <em>code owns time and length, AI only judges drama, the editor decides</em>
   <span style="margin-left:auto;text-transform:none;letter-spacing:0;font-weight:600"><b style="color:#2BD49A">CODE</b> deterministic · <b style="color:#FF4D52">AI</b> model call · <b style="color:#C9CBD1">EDITOR</b> person</span></div>
  <div class="arch">{arch()}</div>
  <div class="infra">
   <div>{icon("git-compare-arrows", 12, "#C9CBD1")}<span><b>Model layer.</b> LiteLLM with one env var per role (<code>PROMO_TAG_MODEL</code>, <code>PROMO_RANK_MODEL</code>…) and fallback chains. Every call logs which model answered.</span></div>
   <div>{icon("zap", 12, "#C9CBD1")}<span><b>Serving.</b> Vercel: static site plus a Python function (<code>api/run.py</code>) for passphrase-gated live runs. Keys live in Vercel env, never in code.</span></div>
   <div>{icon("shield-check", 12, "#C9CBD1")}<span><b>Confidential pack.</b> Results are AES-256-GCM encrypted (PBKDF2, 310k rounds) and decrypted in the browser. Scripts never enter the repo.</span></div>
  </div>
 </div>

 <div class="grid" style="grid-template-columns: 1fr 420px; gap:12px; margin-top:8px">
  <div class="card"><div class="k">{icon("flask-conical", 12, "#8A8D96")}how i got there · <em>measure what fails, fix it, measure again</em></div>
   <div class="vers">
    {ver("v1", "LLM picks the clip", "The model chose start and end beats and scored each clip 1–10 in one pass.",
         "Broke: models can't add up timestamps, and 1–10 scores tie.",
         [("raw clips in 20–60 s", "", "84%"), ("endings re-cut by code", "", "21/105"), ("tied scores", "", "81%")])}
    {ver("v2", "LLM tags, code builds", "The model only labels hook and cliff beats. Code builds every window. Jev ranks pairs.",
         "Fixed: rules hold by construction; head-to-head can't tie.",
         [("clips in 20–60 s", "84%", "100%"), ("endings re-cut", "21", "0"), ("re-check order ρ", "0.44", "0.75–0.90")])}
    {ver("v3", "Story-level dedupe, notes", "Stronger tagger on Vertex. Dedupe by story, not footage. Teasers can join two episodes.",
         "Added: notes and week-1 plan, written after ranking so they can't bias it.",
         [("same-story pairs, top 20", "4", "2"), ("cross-episode clips, top 20", "", "2"), ("cost per show", "", f"${SHOW_USD:.2f}")])}
   </div></div>
  <div class="card"><div class="k">{icon("target", 12, "#8A8D96")}tests with a known answer <em>· I wrote the key</em></div>
   <div class="tst">
    <div><div class="tsl"><b>Hooks: 26 of 29 found</b><span>29 shocking lines and 29 dull decoys planted in real episodes.</span></div>{confusion()}</div>
    <div><div class="tsl"><b>Cliffhangers: 41–47 of 50</b><span>The writers' own episode ending, found. Dark line = 95% CI.</span></div>{cliffbars()}</div>
   </div>
  </div>
 </div>

 <div class="grid p2b" style="grid-template-columns: 1fr 1fr 1fr; gap:12px; margin-top:8px">
  <div class="card"><div class="k">{icon("git-compare-arrows", 12, "#8A8D96")}how the top 20 are ordered</div>
   <div style="display:flex; gap:10px; align-items:flex-start">
    <div class="hm">{h2h()}<div class="hml"><i style="background:#EC1C24"></i>row wins <i style="background:#6E717A"></i>row loses</div></div>
    <div style="flex:1">
     <div class="lim"><div><b>Every pair, both orders</b><span>Jev gives P(row beats column) for all {pw['pairs_asked_both_ways']} pairs. First-shown wins {FIRST}%, so asking twice cancels order bias.</span></div></div>
     <div class="lim"><div><b>Bradley-Terry fit</b><span>Turns {pw['verdicts']} verdicts into one strength per clip. The #1 clip beats all 19 others.</span></div></div>
     <div class="lim"><div><b>Cheap enough to ask all</b><span>{pw['verdicts']} verdicts for ${jev['cost_usd']:.3f}, ~0.3 s each.</span></div></div>
    </div></div></div>
  <div class="card"><div class="k">{icon("triangle-alert", 12, "#8A8D96")}what it can't do yet</div>
   <div class="lim"><span class="ic">{icon("brain-circuit", 14, "#FFB547")}</span><div><b>Prove its taste</b><span>AI judges agree weakly (ρ 0.26–0.49). Editor labels would settle it.</span></div></div>
   <div class="lim"><span class="ic">{icon("film", 14, "#FFB547")}</span><div><b>See the performance</b><span>It reads the script, not the actor's delivery.</span></div></div>
   <div class="lim"><span class="ic">{icon("clock", 14, "#FFB547")}</span><div><b>Know the final cut</b><span>If the edit drifts from script times, the editor nudges cuts.</span></div></div>
   <div class="lim"><span class="ic">{icon("split", 14, "#FFB547")}</span><div><b>Catch every repeat</b><span>Two same-story pairs remain in the top 20.</span></div></div>
</div>
  <div class="card"><div class="k">{icon("wand-sparkles", 12, "#8A8D96")}where AI tools misled me</div>
   <div class="wr"><span class="x">Asked for 20–60 s clips, it returned 9–160 s.</span> <span class="ok">So code builds every clip.</span></div>
   <div class="wr"><span class="x">The first picker rated its own clips 9.5/10;</span> an independent judge disagreed (ρ ≈ 0). <span class="ok">So a separate judge ranks.</span></div>
   <div class="wr"><span class="x">One audit said v2 beat v1 (p = 0.01);</span> a stronger one saw no gain. <span class="ok">So I claim only what's measured.</span></div>
   <div class="note" style="margin-top:2px"><b>Tools:</b> Kiro (Claude) for code · Gemini 3.5 Flash · TypeSafe Jev · Gemma and Gemini 3.8 as blind auditors</div></div>
 </div>
 <div class="foot"><span>Sources: experiments/BASELINE_v1 · RESULTS · ANALYSIS · JEV_RESULTS · REALWORLD_RESULTS(_lite) · AUDIT_* · runs/v3_final/meta.json · Icons: Lucide (ISC)</span><span>2 / 2</span></div>
</div>"""

(OUT / "solution.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{page1}{page2}</body></html>")
from playwright.sync_api import sync_playwright  # noqa: E402

CHECK = """() => [...document.querySelectorAll('.page')].map(pg => {
  const R = pg.getBoundingClientRect(), padB = 26, padR = 30;
  let over = -999;
  pg.querySelectorAll('*').forEach(e => { if (e.closest('.foot')) return; const q = e.getBoundingClientRect();
    if (q.width && q.height) over = Math.max(over, q.bottom - (R.bottom - padB), q.right - (R.right - padR)); });
  // largest fully empty horizontal band between the header and the footer
  const blocks = [...pg.children].filter(c => !c.classList.contains('foot')).map(c => c.getBoundingClientRect());
  const ys = []; for (let y = R.top + 50; y < R.bottom - padB; y += 2) {
    const hit = [...pg.querySelectorAll('.card, .rules, .pos, .st, h1, h2, .lead, .ba, .eyebrow, .k, .kp, .phone')].some(el => { const q = el.getBoundingClientRect(); return y >= q.top && y <= q.bottom; });
    ys.push(hit); }
  let gap = 0, run = 0; ys.forEach(h => { run = h ? 0 : run + 2; gap = Math.max(gap, run); });
  // slack inside cards: empty space under the last child
  let slack = 0, where = '';
  pg.querySelectorAll('.card').forEach(c => { const kids = [...c.children]; if (!kids.length) return;
    const last = Math.max(...kids.map(k => k.getBoundingClientRect().bottom)); const s = c.getBoundingClientRect().bottom - last - 14;
    if (s > slack) { slack = s; where = (c.querySelector('.k') || c).textContent.slice(0, 30); } });
  const lastBottom = Math.max(...blocks.map(b => b.bottom));
  return { overflow: Math.round(over), biggest_empty_band: gap, bottom_gap: Math.round(R.bottom - padB - lastBottom), card_slack: Math.round(slack), slack_in: where };
})"""

with sync_playwright() as pwr:
    b = pwr.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    pg.goto((OUT / "solution.html").as_uri())
    pg.wait_for_timeout(400)
    pg.pdf(path=str(OUT / "solution.pdf"), width="13.333in", height="7.5in", print_background=True)
    rep = pg.evaluate(CHECK)
    font_ok = pg.evaluate("document.fonts.check('12px Figtree')")
    for i, el in enumerate(pg.query_selector_all(".page"), 1):
        el.screenshot(path=str(OUT / f"page-{i}.png"))
    b.close()
for i, r in enumerate(rep, 1):
    print(f"page {i}: {r}")
print("Figtree loaded:", font_ok)
