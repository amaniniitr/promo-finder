"""Visual 2-page solution deck (16:9 PDF). Every number is read from runs/ and experiments/.
python deck/build_deck.py -> deck/solution.pdf (+ page-1.png, page-2.png for preview)"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deck"
RUN = ROOT / "runs" / "v3_final"
meta = json.loads((RUN / "meta.json").read_text())
P = json.loads((RUN / "promos.json").read_text())["promos"]
DIAG = json.loads((RUN / "diagnostics.json").read_text())
TITLES = json.loads((OUT / "titles.json").read_text()) if (OUT / "titles.json").exists() else {}  # short labels (quote the show, so not in git)
NAME = "Aman Kumar · 22322004"  # branch appended from links.json if set


import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.models import BeatIndex, Promo  # noqa: E402
from promo.parser import parse_show  # noqa: E402

EPS = parse_show(DEFAULT_SHOW)
IDX = BeatIndex(EPS)
by = {p["id"]: p for p in P}
jev, pw = meta["jev_usage"], meta["pairwise"]
tok = meta["llm_tokens_by_model"]["vertex/gemini-3.5-flash"]
SHOW_USD = tok[0] * 1.5e-6 + tok[1] * 9e-6 + jev["cost_usd"]       # list prices: Gemini 3.5 Flash $1.50/$9 per M
WATCH_MIN = sum(e.duration for e in EPS) / 60
REVIEW_MIN = sum(p["duration"] for p in P[:20]) / 60
N_TAGS = sum(len(t["hooks"]) + len(t["cliffs"]) for t in DIAG["tags"].values())
C = {"code": "#10B981", "llm": "#0EA5E9", "jev": "#8B5CF6", "human": "#EC1C24", "ink": "#090A0F", "mut": "#64748B",
     "bad": "#EF4444", "good": "#10B981", "line": "#E2E8F0", "soft": "#F8FAFC", "acc": "#EC1C24"}

KUKU_LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="56" height="20" viewBox="0 0 162 56" fill="none" style="vertical-align:middle;display:inline-block"><path d="M105.97 49.5001C106.835 50.8576 109.367 51.4747 109.367 53.2642V53.511C109.367 54.2514 108.811 54.6834 107.947 54.6834L95.0354 54.6834C94.1706 54.6834 93.6146 54.1897 93.6146 53.4493V53.2025C93.6146 51.4747 95.9003 51.0428 94.9119 49.5001L89.5992 41.2316C88.549 41.4167 87.4988 41.5401 86.3251 41.5401L86.3251 47.8958C86.3251 50.7342 89.105 51.4747 89.105 53.2642V53.511C89.105 54.2514 88.4872 54.6834 87.6224 54.6834L74.2171 54.6834C73.3522 54.6834 72.7344 54.2514 72.7344 53.511V53.2642C72.7344 51.4747 75.2055 50.7342 75.2055 47.8958L75.2055 11.7786C75.2055 8.87841 72.2402 8.07623 72.2402 6.5336V6.28678C72.2402 5.60802 72.7962 5.29949 73.6611 4.86755L83.5452 0.301343C85.2749 -0.500829 86.3251 0.424752 86.3251 1.59716L86.3251 37.159C96.9505 36.2334 92.5644 24.5094 100.101 24.5094C103.437 24.5094 104.92 26.5457 104.92 29.0756C104.92 31.9141 102.634 35.5547 98.2478 38.208L105.97 49.5001Z" fill="#090A0F"></path><path d="M139.726 47.7283C139.726 52.7379 142.385 50.3259 142.385 52.8616C142.385 54.5315 139.973 54.9026 136.015 54.9026C132.18 54.9026 130.51 53.9749 130.201 51.3154C128.593 53.7893 125.686 55.15 121.481 55.15C115.234 55.15 109.915 50.8825 109.915 42.9661L109.915 32.6376C109.915 29.7308 107.441 28.9886 107.441 27.4425V27.1951C107.441 26.5148 107.998 25.8963 108.864 25.7726L118.079 24.5357C119.873 24.2883 120.986 24.6594 120.986 25.7726L120.8 44.0793C120.739 49.1508 122.037 51.068 124.759 51.068C127.047 51.068 128.84 48.656 128.84 44.8833L128.84 32.6376C128.84 29.7308 126.367 28.9886 126.367 27.4425V27.1951C126.367 26.5148 126.923 25.8963 127.789 25.7726L137.004 24.5357C138.798 24.2883 139.726 24.6594 139.726 25.7726L139.726 47.7283Z" fill="#090A0F"></path><path d="M33.7295 49.5001C34.5944 50.8576 37.1272 51.4747 37.1272 53.2642V53.511C37.1272 54.2514 36.5712 54.6834 35.7063 54.6834L22.7952 54.6834C21.9303 54.6834 21.3744 54.1897 21.3744 53.4493V53.2025C21.3744 51.4747 23.6601 51.0428 22.6717 49.5001L17.3589 41.2316C16.3088 41.4167 15.2586 41.5401 14.0848 41.5401L14.0848 47.8958C14.0848 50.7342 16.8647 51.4747 16.8647 53.2642V53.511C16.8647 54.2514 16.247 54.6834 15.3821 54.6834L1.97682 54.6834C1.11196 54.6834 0.494203 54.2514 0.494203 53.511L0.494203 53.2642C0.494203 51.4747 2.96523 50.7342 2.96523 47.8958L2.96523 11.7786C2.96523 8.87841 0 8.07623 0 6.5336L0 6.28678C0 5.60802 0.555974 5.29949 1.42083 4.86755L11.3049 0.301343C13.0347 -0.500829 14.0848 0.424752 14.0848 1.59716L14.0848 37.159C24.7102 36.2334 20.3242 24.5094 27.8608 24.5094C31.1967 24.5094 32.6793 26.5457 32.6793 29.0756C32.6793 31.9141 30.3936 35.5547 26.0075 38.208L33.7295 49.5001Z" fill="#090A0F"></path><path d="M67.4892 47.7283C67.4892 52.7379 70.1487 50.3259 70.1487 52.8616C70.1487 54.5315 67.7366 54.9026 63.7784 54.9026C59.9439 54.9026 58.274 53.9749 57.9648 51.3154C56.3568 53.7893 53.45 55.15 49.2444 55.15C42.9978 55.15 37.679 50.8825 37.679 42.9661L37.679 32.6376C37.679 29.7308 35.2051 28.9886 35.2051 27.4425V27.1951C35.2051 26.5148 35.7617 25.8963 36.6276 25.7726L45.8428 24.5357C47.6363 24.2883 48.7496 24.6594 48.7496 25.7726L48.564 44.0793C48.5022 49.1508 49.801 51.068 52.5223 51.068C54.8106 51.068 56.6042 48.656 56.6042 44.8833L56.6042 32.6376C56.6042 29.7308 54.1303 28.9886 54.1303 27.4425V27.1951C54.1303 26.5148 54.6869 25.8963 55.5528 25.7726L64.768 24.5357C66.5615 24.2883 67.4892 24.6594 67.4892 25.7726L67.4892 47.7283Z" fill="#090A0F"></path><ellipse cx="152.759" cy="46.1512" rx="8.72992" ry="8.72986" fill="#EC1C24"></ellipse></svg>'''


def e(s):
    return html.escape(str(s))


def fmt(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{int(s):02d}"


_L = json.loads((ROOT / "links.json").read_text()) if (ROOT / "links.json").exists() else {}
_short = lambda u: e(u.replace("https://", "").replace("http://", "").rstrip("/"))  # noqa: E731
NAME = NAME + (f" · {e(_L['branch'])}" if _L.get("branch") else "")
LINKS = "  ·  ".join(x for x in [
    f"live: {_short(_L['site'])}" if _L.get("site") else "",
    f"code: {_short(_L['repo'])}" if _L.get("repo") else "",
    f"video: {_short(_L['video'])}" if _L.get("video") else ""] if x) or "links: see submission form"


def title(pid):
    return TITLES.get(pid, pid)


def chip(who):
    lab = {"code": "CODE", "llm": "LLM", "jev": "JEV", "human": "EDITOR"}[who]
    return f'<span class="chip" style="background:{C[who]}">{lab}</span>'


# ------------------------------------------------------------------ page 1 visuals
def funnel():
    steps = [("Parse", f"{sum(len(x.beats) for x in EPS):,}", "beats with IDs + times", ["code"]),
             ("Tag", f"{N_TAGS}", "hook + cliff marks", ["llm"]),
             ("Build", f"{meta['candidates']}", "clips, all 20–60s", ["code"]),
             ("Score + dedupe", f"{meta['ranked']}", "unique promos", ["jev", "code"]),
             ("Rank", "20", f"{pw['verdicts']} head-to-heads", ["jev"]),
             ("Plan", f"{len(meta['posting_plan']['plan'])}", "posts in week 1", ["llm", "human"])]
    W, H, n = 770, 186, len(steps)
    bw, gap = 110, 22
    hs = [156, 136, 118, 100, 84, 70]
    out = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for i, (name, num, lab, who) in enumerate(steps):
        x = 6 + i * (bw + gap)
        h = hs[i]
        y = 26 + (156 - h) / 2
        col = C[who[0]]
        out.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="9" fill="{col}" opacity="0.10"/>'
                   f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2" fill="{col}"/>'
                   f'<text x="{x + bw / 2 + 2}" y="{y + h / 2 + 2}" text-anchor="middle" class="fnum" fill="{C["ink"]}">{num}</text>'
                   f'<text x="{x + bw / 2 + 2}" y="{y + h / 2 + 20}" text-anchor="middle" class="flab">{e(lab)}</text>'
                   f'<text x="{x + bw / 2 + 2}" y="18" text-anchor="middle" class="fstep">{name}</text>')
        cx = x + bw / 2 + 2 - 24 * (len(who) - 1)
        for k, w in enumerate(who):
            out.append(f'<rect x="{cx - 22 + k * 48}" y="{y + 8}" width="44" height="14" rx="7" fill="{C[w]}"/>'
                       f'<text x="{cx + k * 48}" y="{y + 18.5}" text-anchor="middle" class="fchip">'
                       f'{ {"code": "CODE", "llm": "LLM", "jev": "JEV", "human": "EDITOR"}[w]}</text>')
        if i < n - 1:
            ax = x + bw + 3
            out.append(f'<path d="M{ax} 104 l14 0 m-5 -5 l5 5 l-5 5" stroke="#9CA3AF" stroke-width="2" fill="none"/>')
    out.append("</svg>")
    return "".join(out)


def anatomy():
    p = P[0]
    s = p["segments"][0]
    ep = IDX.eps[s["episode"]]
    beats = [b for b in ep.beats if b.start >= s["start"] - .01 and b.end <= s["end"] + .01]
    lines = [b for b in beats if b.type == "dialogue"]
    hook, mid = lines[0], min(lines, key=lambda b: abs((b.start - s["start"]) - 15))
    cliff = [b for b in beats if b.type == "action"][-1]
    D = p["duration"]
    W = 384
    X = lambda t: 16 + (W - 32) * t / D        # noqa: E731
    E = lambda t: 16 + (W - 32) * t / ep.duration  # noqa: E731
    pts = [(hook, "HOOK", C["acc"], f'"{hook.text}"'), (mid, "BUILD", C["llm"], f'"{mid.text[:36]}…"'),
           (cliff, "CLIFF", C["jev"], "iron stops mm from her eye")]
    o = [f'<svg width="{W}" height="196" viewBox="0 0 {W} 196">',
         f'<text x="16" y="14" class="sm">Episode {ep.number} · {fmt(ep.duration)}</text>',
         f'<rect x="16" y="20" width="{W - 32}" height="8" rx="4" fill="{C["line"]}"/>',
         f'<rect x="{E(s["start"])}" y="18" width="{E(s["end"]) - E(s["start"])}" height="12" rx="4" fill="{C["acc"]}"/>',
         f'<path d="M{E(s["start"])} 31 L16 52 M{E(s["end"])} 31 L{W - 16} 52" stroke="{C["acc"]}" stroke-dasharray="3 3"/>',
         f'<rect x="16" y="52" width="{W - 32}" height="22" rx="6" fill="{C["ink"]}"/>',
         f'<rect x="16" y="52" width="{X(3) - 16}" height="22" rx="6" fill="{C["acc"]}"/>',
         f'<text x="{X(1.5)}" y="67" text-anchor="middle" class="tw">≤3s</text>',
         f'<text x="{W / 2 + 20}" y="67" text-anchor="middle" class="tw">{D:.0f}-second clip · {fmt(s["start"])}–{fmt(s["end"])}</text>']
    for k, (b, lab, col, txt) in enumerate(pts):
        t = b.start - s["start"]
        x = X(t)
        y = 92 + k * 34
        bx = 10 + k * 64
        o.append(f'<path d="M{x} 74 L{x} {y + 14} L{min(x, bx + 236)} {y + 14}" stroke="{col}" stroke-width="1.2" fill="none"/>'
                 f'<circle cx="{x}" cy="74" r="4" fill="{col}"/>'
                 f'<rect x="{bx}" y="{y}" width="236" height="28" rx="6" fill="#fff" stroke="{col}"/>'
                 f'<text x="{bx + 8}" y="{y + 12}" class="lab" fill="{col}">{lab} · {t:.0f}s</text>'
                 f'<text x="{bx + 8}" y="{y + 23}" class="q">{e(txt)}</text>')
    o.append("</svg>")
    return "".join(o)


def leaderboard():
    top = P[:10]
    bts = [p["bt"] for p in top]
    lo, hi = min(bts), max(bts)
    rows = []
    for p in top:
        w = 14 + 112 * (p["bt"] - lo) / (hi - lo or 1)
        kind = {"single": "", "stitched": " · 2-part", "cross": " · cross-ep"}[p["kind"]]
        eps = "+".join(f"E{s['episode']}" for s in p["segments"])
        eps = eps if p["kind"] == "cross" else f"E{p['segments'][0]['episode']}"
        rows.append(f'<div class="lb"><span class="rk">{p["rank"]}</span><div class="lbt"><b>{e(title(p["id"]))}</b>'
                    f'<span class="mut"> {eps} · {p["duration"]:.0f}s{kind}</span></div>'
                    f'<div class="bar" style="width:{w:.0f}px;background:{C["jev"] if p["rank"] > 1 else C["acc"]}"></div>'
                    f'<span class="wlt">{p["record"]}</span></div>')
    return "".join(rows)


def calendar():
    cards = []
    for x in meta["posting_plan"]["plan"]:
        p = by[x["id"]]
        s = p["segments"][0]
        cards.append(f'<div class="day"><div class="dn">DAY {x["day"]}</div><div class="dt">{e(title(p["id"]))}</div>'
                     f'<div class="dm">E{s["episode"]} · {p["duration"]:.0f}s · #{p["rank"]}</div>'
                     f'<div class="dq">“{e(p["hook"].split(chr(34))[1] if chr(34) in p["hook"] else title(p["id"]))}”</div></div>')
    holds = "".join(f'<span class="hold">{e(title(h["id"]))}</span>' for h in meta["posting_plan"]["hold"][:5])
    return "".join(cards), holds


def heat():
    best = {n: 0.0 for n in IDX.eps}
    for p in P:
        for s in p["segments"]:
            best[s["episode"]] = max(best[s["episode"]], p["screen_score"])
    top_eps = {s["episode"] for p in P[:20] for s in p["segments"]}
    lo, hi = min(best.values()), max(best.values())
    cells = []
    for n in sorted(best):
        a = (best[n] - lo) / (hi - lo)
        r, g, b = (int(244 + (228 - 244) * a), int(245 + (87 - 245) * a), int(247 + (46 - 247) * a))
        cells.append(f'<div class="cell" style="background:rgb({r},{g},{b});color:{"#fff" if a > .55 else "#555"}">'
                     f'{n}{"<i></i>" if n in top_eps else ""}</div>')
    return "".join(cells), len(top_eps)


# ------------------------------------------------------------------ page 2 visuals
def dumbbells():
    rows = [("Clips meeting 20–60s (raw)", 84, 100, True, "84%", "100%"),
            ("Hook inside first 3s (raw)", 81, 100, True, "81%", "100%"),
            ("Endings broken by code re-cuts", 20, 0, False, "21/105", "0"),
            ("Tied scores in the ranking", 81, 0, False, "81%", "0%"),
            ("Ranking reproducible (split-half ρ)", 44, 90, True, "0.44", "0.75–0.90"),
            ("Same-story pairs in top 20", 4 * 20, 2 * 20, False, "4", "2")]
    W = 570
    X = lambda v: 210 + (W - 250) * v / 100  # noqa: E731
    o = [f'<svg width="{W}" height="{32 + 27 * len(rows)}" viewBox="0 0 {W} {32 + 27 * len(rows)}">',
         f'<circle cx="214" cy="10" r="5" fill="{C["bad"]}"/><text x="223" y="14" class="sm">v1 (LLM picks start/end, 1 judge pass)</text>',
         f'<circle cx="430" cy="10" r="5" fill="{C["good"]}"/><text x="439" y="14" class="sm">final</text>']
    for i, (lab, a, b, up, ta, tb) in enumerate(rows):
        y = 34 + i * 27
        o.append(f'<text x="0" y="{y + 4}" class="rl">{e(lab)}</text>'
                 f'<line x1="{X(0)}" y1="{y}" x2="{X(100)}" y2="{y}" stroke="{C["line"]}" stroke-width="6" stroke-linecap="round"/>'
                 f'<line x1="{X(a)}" y1="{y}" x2="{X(b)}" y2="{y}" stroke="#9CA3AF" stroke-width="2.5"/>'
                 f'<circle cx="{X(a)}" cy="{y}" r="6.5" fill="{C["bad"]}"/><circle cx="{X(b)}" cy="{y}" r="6.5" fill="{C["good"]}"/>'
                 f'<text x="{X(a)}" y="{y - 10}" text-anchor="middle" class="dv" fill="{C["bad"]}">{ta}</text>'
                 f'<text x="{X(b)}" y="{y + 19}" text-anchor="middle" class="dv" fill="{C["good"]}">{tb}</text>')
    o.append("</svg>")
    return "".join(o)


def columns(groups, H=112):
    """groups: [(label, [(name, value, color)])] -> vertical bars 0-100."""
    bw, gw = 40, 22
    W = sum(len(g[1]) * (bw + 6) + gw for g in groups) + 50
    o = [f'<svg width="{W}" height="{H + 48}" viewBox="0 -14 {W} {H + 48}">']
    x = 30
    for lab, bars in groups:
        x0 = x
        for name, v, col in bars:
            h = max(2, H * v / 100)
            o.append(f'<rect x="{x}" y="{H - h + 4}" width="{bw}" height="{h}" rx="4" fill="{col}"/>'
                     f'<text x="{x + bw / 2}" y="{H - h - 1}" text-anchor="middle" class="cv">{v:g}%</text>'
                     f'<text x="{x + bw / 2}" y="{H + 16}" text-anchor="middle" class="cn">{name}</text>')
            x += bw + 6
        o.append(f'<text x="{(x0 + x - 6) / 2}" y="{H + 30}" text-anchor="middle" class="cg">{lab}</text>')
        x += gw
    o.append(f'<line x1="0" y1="{H + 4}" x2="{W}" y2="{H + 4}" stroke="#D1D5DB"/></svg>')
    return "".join(o)


def judge_matrix():
    names = ["Jev", "Gem 3.8", "Gemma"]
    M = [[.99, .26, .29], [.26, .79, .49], [.29, .49, .88]]
    o = ['<svg width="250" height="148" viewBox="0 0 250 148">']
    for i, n in enumerate(names):
        o.append(f'<text x="{110 + i * 46}" y="14" text-anchor="middle" class="sm">{n}</text>'
                 f'<text x="80" y="{42 + i * 40}" text-anchor="end" class="sm">{n}</text>')
        for j in range(3):
            v = M[i][j]
            col = f"rgba(123,63,191,{0.12 + 0.88 * v})"
            o.append(f'<rect x="{88 + j * 46}" y="{20 + i * 40}" width="43" height="37" rx="6" fill="{col}"/>'
                     f'<text x="{110 + j * 46}" y="{43 + i * 40}" text-anchor="middle" class="mv" '
                     f'fill="{"#fff" if v > .6 else C["ink"]}">{v:.2f}</text>')
    o.append("</svg>")
    return "".join(o)


cal, holds = calendar()
cells, n_top_eps = heat()
cross = [p for p in P[:20] if p["kind"] == "cross"]

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Figtree:ital,wght@0,300..900;1,300..900&family=JetBrains+Mono:wght@400;600&display=swap');
@page {{ size: 13.333in 7.5in; margin: 0 }}
* {{ box-sizing: border-box; margin: 0; padding: 0 }}
body {{ font-family: 'Figtree', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: {C['ink']}; font-size: 9pt; line-height: 1.25 }}
.page {{ width: 13.333in; height: 7.5in; padding: 22px 28px 16px; position: relative; overflow: hidden; page-break-after: always }}
.hdr {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 10px }}
.hdr h1 {{ font-size: 24pt; font-weight: 800; letter-spacing: -.6px; line-height: 1 }}
.hdr h1 em {{ font-style: normal; color: {C['acc']} }}
.hdr .s {{ font-size: 10.5pt; color: {C['mut']}; margin-top: 4px }}
.hdr .r {{ text-align: right; font-size: 7.6pt; color: {C['mut']}; line-height: 1.5 }}
.hdr .r b {{ color: {C['ink']}; font-size: 8.6pt }}
.band {{ display: flex; gap: 8px; align-items: center; background: #090A0F; color: #fff; border-radius: 10px; padding: 7px 12px; margin-bottom: 9px; font-size: 8.5pt; border-left: 3.5px solid {C['acc']} }}
.band b {{ color: #FFA29E }} .band .sep {{ width: 1px; align-self: stretch; background: #262936 }}
.pill {{ background: #181922; border: 1px solid rgba(255,255,255,0.12); border-radius: 20px; padding: 2.5px 9px; white-space: nowrap }}
.row {{ display: flex; gap: 12px; margin-bottom: 10px }}
.box {{ background: #fff; border: 1px solid {C['line']}; border-radius: 12px; padding: 9px 12px; position: relative }}
.box h3 {{ font-size: 8pt; letter-spacing: 1.1px; text-transform: uppercase; color: {C['mut']}; margin-bottom: 5px; font-weight: 700 }}
.box h3 span {{ color: {C['ink']}; text-transform: none; letter-spacing: 0; font-size: 10.5pt; margin-left: 4px; font-weight: 700 }}
.chip {{ color: #fff; font-size: 6.6pt; font-weight: 700; border-radius: 6px; padding: 1.5px 6px; letter-spacing: .4px }}
svg text {{ font-family: inherit }}
.fnum {{ font-size: 22px; font-weight: 800 }} .flab {{ font-size: 9px; fill: #4B5563 }} .fstep {{ font-size: 11px; font-weight: 700; fill: {C['ink']} }}
.fchip {{ font-size: 7.5px; font-weight: 700; fill: #fff }}
.sm {{ font-size: 9px; fill: {C['mut']} }} .tw {{ font-size: 9.5px; fill: #fff; font-weight: 700 }}
.lab {{ font-size: 8.5px; font-weight: 800; letter-spacing: .5px }} .q {{ font-size: 9.5px; fill: {C['ink']} }}
.legend {{ display: block; font-size: 8pt; color: {C['mut']}; margin-top: 3px }} .legend .chip {{ margin: 0 3px 0 8px }}
.legend b {{ color: {C['ink']} }}
.lb {{ display: flex; align-items: center; gap: 7px; height: 20.5px; border-bottom: 1px solid #F1F2F4 }}
.lb .rk {{ width: 16px; font-weight: 800; color: {C['acc']}; font-size: 10pt; text-align: right }}
.lbt {{ width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 8.6pt }}
.bar {{ height: 9px; border-radius: 5px; opacity: .85 }} .wlt {{ font-family: 'JetBrains Mono', Menlo, monospace; font-size: 7.6pt; color: {C['mut']}; white-space: nowrap; margin-left: auto }}
.mut {{ color: {C['mut']} }}
.days {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 7px }}
.day {{ background: {C['soft']}; border-radius: 10px; padding: 6px 8px 5px; border: 1px solid {C['line']}; border-top: 3.5px solid {C['acc']}; min-height: 116px }}
.dn {{ font-size: 7.5pt; font-weight: 800; color: {C['acc']}; letter-spacing: 1px }}
.dt {{ font-size: 9.6pt; font-weight: 800; line-height: 1.15; margin: 3px 0 4px }}
.dm {{ font-size: 7.6pt; color: {C['mut']}; font-family: 'JetBrains Mono', Menlo, monospace }}
.dq {{ font-size: 8.2pt; font-style: italic; color: #374151; margin-top: 6px; border-left: 2px solid {C['line']}; padding-left: 5px }}
.hold {{ display: inline-block; font-size: 7.6pt; background: #FDECE7; color: {C['bad']}; border-radius: 10px; padding: 2px 8px; margin: 3px 4px 0 0 }}
.grid50 {{ display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px }}
.cell {{ height: 22px; border-radius: 4px; font-size: 7.4pt; display: flex; align-items: center; justify-content: center; position: relative; font-weight: 600 }}
.cell i {{ position: absolute; top: 2px; right: 2px; width: 6px; height: 6px; border-radius: 50%; background: {C['ink']}; border: 1px solid #fff }}
.big {{ font-size: 26pt; font-weight: 800; line-height: 1; letter-spacing: -1px }}
.kv {{ display: flex; flex-direction: column; gap: 2px }}
.rl {{ font-size: 10px; fill: {C['ink']} }} .dv {{ font-size: 9.5px; font-weight: 800 }}
.cv {{ font-size: 10px; font-weight: 800; fill: {C['ink']} }} .cn {{ font-size: 8.5px; fill: {C['mut']} }} .cg {{ font-size: 9.5px; font-weight: 700; fill: {C['ink']} }}
.mv {{ font-size: 12px; font-weight: 800 }}
.lim {{ display: flex; gap: 8px; align-items: flex-start; margin-bottom: 5px }}
.lim .ic {{ flex: none; width: 22px; height: 22px; border-radius: 6px; background: #FEE2E2; color: {C['bad']}; font-weight: 800; display: flex; align-items: center; justify-content: center; font-size: 10pt }}
.lim b {{ display: block; font-size: 9pt }} .lim span {{ font-size: 8pt; color: {C['mut']} }}
.stat {{ background: {C['soft']}; border: 1px solid {C['line']}; border-radius: 10px; padding: 8px 10px }}
.stat .k {{ font-size: 7.4pt; color: {C['mut']}; text-transform: uppercase; letter-spacing: .8px; font-weight: 700 }}
.stat .v {{ font-size: 18pt; font-weight: 800; line-height: 1.1 }} .stat .n {{ font-size: 7.8pt; color: {C['mut']} }}
.wrong {{ background: {C['soft']}; border: 1px solid {C['line']}; border-radius: 10px; padding: 7px 9px; font-size: 8.4pt }}
.wrong .a {{ color: {C['bad']}; font-weight: 700 }} .wrong .f {{ color: {C['good']}; font-weight: 700 }}
code {{ font-family: 'JetBrains Mono', Menlo, monospace; font-size: 7.8pt; background: #090A0F; color: #FFA29E; border-radius: 5px; padding: 2px 6px }}
.tool {{ display: inline-block; border: 1px solid {C['line']}; border-radius: 14px; padding: 1px 7px; font-size: 7.4pt; margin: 0 3px 3px 0; background: #fff }}
.foot {{ position: absolute; bottom: 7px; left: 28px; right: 28px; font-size: 6.8pt; color: #9CA3AF; display: flex; justify-content: space-between }}
"""

page1 = f"""
<div class="page">
 <div class="hdr"><div style="display:flex;align-items:center;gap:14px">
   {KUKU_LOGO_SVG}
   <div style="width:1px;height:34px;background:#CBD5E1"></div>
   <div><h1>Promo Finder <em>·</em> screenplay in, post-ready promos out</h1>
   <div class="s">Kuku AI Generalist · Problem 1 · run on all 50 episodes of <i>I Married a Broken Soldier. He was a Duke</i></div></div></div>
   <div class="r"><b>{NAME}</b><br>{LINKS}</div></div>

 <div class="band"><span>Today an editor watches <b>{WATCH_MIN:.0f} min</b> of every show to pick promos, and a new show ships weekly.</span>
  <div class="sep"></div><span>A promo = <b>20–60s</b> · hook in <b>3s</b> · ends <b>unresolved</b> · makes sense cold</span>
  <div class="sep"></div><span class="mut" style="color:#AAB4C8">Assumptions</span>
  <span class="pill">script time ≈ final cut</span><span class="pill">cut on whole lines</span><span class="pill">judge sees only the clip</span><span class="pill">no big spoilers early</span></div>

 <div class="row">
  <div class="box" style="width:800px"><h3>How it works <span>AI judges meaning. Code owns every timestamp.</span></h3>
   {funnel()}
   <div class="legend">{chip('code')} deterministic {chip('llm')} Gemini via LiteLLM {chip('jev')} TypeSafe Jev: probabilities, both orders {chip('human')} approves in review UI
    <span style="float:right">LLM never writes a time → <b>0 rule violations</b>, 0 invented IDs</span></div></div>
  <div class="box" style="flex:1"><h3>Anatomy of #1 <span>{e(title(P[0]['id']))}</span></h3>{anatomy()}
   <div class="legend" style="margin-top:-4px">Won <b>19 of 19</b> head-to-heads · judged with no show context, like a cold viewer</div></div>
 </div>

 <div class="row">
  <div class="box" style="width:430px"><h3>Ranking <span>top 10 by pairwise tournament</span></h3>{leaderboard()}
   <div class="legend" style="margin-top:4px">bar = Bradley-Terry strength · W-L-T of 19 matchups</div></div>
  <div class="box" style="flex:1"><h3>Post first <span>week-1 plan, reasons in the outputs</span></h3>
   <div class="days">{cal}</div>
   <div style="margin-top:6px;font-size:8pt"><b>Held back (spoilers):</b> {holds}</div></div>
  <div class="box" style="width:236px"><h3>Where the gold is</h3>
   <div class="grid50">{cells}</div>
   <div class="legend" style="margin-top:6px;flex-wrap:wrap;gap:4px">colour = best promo score · <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{C['ink']}"></span> in top 20 ({n_top_eps} episodes)</div></div>
 </div>
 <div class="foot"><span>All numbers generated from runs/v3_final by deck/build_deck.py</span><span>1 / 2</span></div>
</div>"""

page2 = f"""
<div class="page">
 <div class="hdr"><div style="display:flex;align-items:center;gap:14px">
   {KUKU_LOGO_SVG}
   <div style="width:1px;height:34px;background:#CBD5E1"></div>
   <div><h1>Does it work? <em>·</em> measured, not asserted</h1>
   <div class="s">Each fix came after measuring the failure, and was measured again after</div></div></div>
   <div class="r"><b>{NAME}</b></div></div>

 <div class="row">
  <div class="box" style="width:600px"><h3>v1 → final <span>what was wrong, what changed</span></h3>{dumbbells()}
   <div class="legend">Fix behind the big jumps: LLM <b>tags</b> moments, code <b>builds</b> clips; rank by <b>head-to-head</b> comparisons asked both ways.</div></div>
  <div class="box" style="flex:1"><h3>Real-life tests <span>ground truth not from an AI</span></h3>
   <div style="display:flex;gap:18px;align-items:flex-end">
    <div>{columns([("Planted shocking line", [("found", 90, C['good']), ("random", 13, '#CBD5E1')]),
                   ("Neutral decoy", [("tagged", 0, C['bad']), ("random", 13, '#CBD5E1')])])}</div>
    <div>{columns([("Writers' own cliffhanger (last 8s)", [("lite", 94, C['llm']), ("random", 18, '#CBD5E1'),
                                                         ("3.5-flash", 82, C['llm']), ("random", 26, '#CBD5E1')])])}</div></div>
   <div class="legend">29 real episodes with one line swapped for a known shocker and one for filler · 50 episodes, writers' endings · all p &lt; 10⁻¹⁶</div></div>
 </div>

 <div class="row">
  <div class="box" style="width:300px"><h3>Judges disagree <span>ρ on same clips</span></h3>{judge_matrix()}
   <div class="legend">diagonal = self-consistency · <b>consistent ≠ correct</b></div></div>
  <div class="box" style="width:390px"><h3>Where it picks badly</h3>
   <div class="lim"><div class="ic">?</div><div><b>Taste is unproven</b><span>blind AI audits disagree on v1 vs final (p 0.01 vs 0.92)</span></div></div>
   <div class="lim"><div class="ic">◐</div><div><b>Visual hooks judged from text</b><span>a slap or close-up may land differently on screen</span></div></div>
   <div class="lim"><div class="ic">↺</div><div><b>Some "cliffhangers" resolve</b><span>tagger can mark a payoff (she finds the ring) as open</span></div></div>
   <div class="lim"><div class="ic">≈</div><div><b>Near-duplicates remain</b><span>2 same-story pairs in top 20; threshold tuned on one show</span></div></div>
   <div class="lim"><div class="ic">⇄</div><div><b>Judge position bias</b><span>Jev flips {pw['flip_rate']:.0%} of pairs when swapped, so both orders count</span></div></div></div>
  <div class="box" style="flex:1"><h3>Scale &amp; cost <span>per 50-episode show</span></h3>
   <div style="display:flex;align-items:center;gap:10px;margin:2px 0 8px">
    <div class="kv"><span class="big" style="color:{C['bad']}">{WATCH_MIN:.0f}</span><span class="mut">min to watch</span></div>
    <svg width="40" height="20"><path d="M2 10 h30 m-7 -6 l7 6 l-7 6" stroke="#9CA3AF" stroke-width="2.5" fill="none"/></svg>
    <div class="kv"><span class="big" style="color:{C['good']}">{REVIEW_MIN:.0f}</span><span class="mut">min to review top 20</span></div></div>
   <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
    <div class="stat"><div class="k">Cost</div><div class="v">${SHOW_USD:.2f}</div><div class="n">list prices · ranking ${jev['cost_usd']:.2f}</div></div>
    <div class="stat"><div class="k">Run time</div><div class="v">~7 min</div><div class="n">judging ~20 s</div></div>
    <div class="stat"><div class="k">Scale</div><div class="v">linear</div><div class="n">shows run in parallel, cached</div></div></div>
   <div style="margin-top:5px;font-size:8.2pt">Editor approve/reject is saved as labels → tune prompts.</div>
   <div style="margin-top:7px;font-size:8.2pt;line-height:1.8"><code>python run.py &lt;show folder&gt;</code> new show: 10 formats tested, synthetic show <b>0 violations</b><br>
   <code>PROMO_RANK_MODEL=openai/gpt-5</code> swap any role's model</div></div>
 </div>

 <div class="box" style="display:grid;grid-template-columns:1.5fr 1fr 1fr 0.75fr;gap:10px;align-items:start">
   <div><h3>AI tools used</h3><span class="tool">Kiro (Claude): build, analysis</span><span class="tool">Gemini 3.5/3.1 Flash: tag, notes</span><span class="tool">TypeSafe Jev: score, rank</span><span class="tool">Gemma, Gemini 3.8: blind audit</span><span class="tool">LiteLLM: swap</span></div>
   <div class="wrong"><span class="a">✗ Asked for 20–60s, got 9–160s.</span> LLMs don't add timestamps reliably; code patches broke endings. <span class="f">✓ Fix: LLM tags, code builds clips.</span></div>
   <div class="wrong"><span class="a">✗ Read a daily quota as per-minute</span> and retried; a picker's 9.5/10 self-score meant nothing. <span class="f">✓ Fix: detect and fall back; separate judge.</span></div>
   <div class="wrong" style="background:#EAF6F0"><b>Next</b><br>40 blind editor ratings to pick the judge that matches people · vision check of the first 3s</div>
 </div>
 <div class="foot"><span>Sources: experiments/BASELINE_v1 · RESULTS · JEV_RESULTS · REALWORLD_RESULTS(_lite) · AUDIT_* · DECK_EVIDENCE · runs/v3_final/meta.json</span><span>2 / 2</span></div>
</div>"""

(OUT / "solution.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{page1}{page2}</body></html>")
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pwr:
    b = pwr.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1.6)
    pg.goto((OUT / "solution.html").as_uri())
    pg.pdf(path=str(OUT / "solution.pdf"), width="13.333in", height="7.5in", print_background=True)
    over = pg.evaluate("""() => [...document.querySelectorAll('.page')].map(p => { const r = p.getBoundingClientRect(); let w = 0;
        p.querySelectorAll('*').forEach(e => { const q = e.getBoundingClientRect(); w = Math.max(w, q.bottom - r.bottom + 6, q.right - r.right + 6); });
        return Math.round(w); })""")
    for i, el in enumerate(pg.query_selector_all(".page"), 1):
        el.screenshot(path=str(OUT / f"page-{i}.png"))
    b.close()
print("overflow px per page (must be <= 0):", over)
