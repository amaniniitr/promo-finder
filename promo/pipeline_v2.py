"""v2 pipeline: tag -> enumerate windows -> screen (x2) -> story dedupe -> MMR
shortlist -> bidirectional pairwise tournament (strongest model) -> final order.

Final order: the shortlist is ordered by Bradley-Terry strength; everything else
follows, ordered by screen score. Each promo records which model did each step.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .diversity import mmr, story_dedupe
from .llm import CALLS, TOKENS
from .models import BeatIndex
from .moments import build_cross, build_windows, check, tag_episode
from .parser import parse_show
from .rerank import pairwise_stats, screen, split_half_bt, tournament

DEDUPE_THR = 0.90  # embedding cosine for cross-scene repeats, plus same-footage time overlap > 50%.
                   # Calibrated on v2 windows (experiments/RESULTS.md): 0.86 flagged 9 of 27
                   # distinct same-scene moments as duplicates; 0.90 flags 3 and still removes
                   # both known Ep1/Ep2 recap pairs (cos 0.886-0.91).


def _jev_available() -> bool:
    try:
        from . import jev  # noqa: F401  (loads .env)
        import os
        return bool(os.getenv("TYPESAFE_API_KEY"))
    except ImportError:
        return False


def run_v2(folder: str, per_episode: int = 4, shortlist: int = 20, rounds: int = 4,
           screen_samples: int = 4, workers: int = 4, episodes_filter: list[int] | None = None,
           log=print, judge: str = "auto", escalate: bool = False, cross: int = 12, notes: int = 30) -> dict:
    """judge: 'jev' (TypeSafe Jev screen + all-pairs ranking), 'llm' (v2 LLM screen + Swiss tournament),
    or 'auto' (jev if TYPESAFE_API_KEY is set). escalate: with jev, send pairs whose two presentation
    orders disagree to the LLM ranker (JEV-as-a-Judge cascade)."""
    if judge == "auto":
        judge = "jev" if _jev_available() else "llm"
    episodes = parse_show(folder)
    sel = [e for e in episodes if not episodes_filter or e.number in episodes_filter]
    idx = BeatIndex(episodes)
    log(f"[v2] {len(episodes)} episodes parsed, tagging {len(sel)}")

    with ThreadPoolExecutor(workers) as ex:
        tags = dict(zip([e.number for e in sel], ex.map(lambda e: tag_episode(e, episodes, idx, log), sel)))

    cands, wstats = [], {}
    for e in sel:
        ws, st = build_windows(e, tags[e.number], idx, per_episode)
        cands += ws
        wstats[e.number] = st
    xs, xstats = build_cross(cands, idx, max_out=cross) if cross else ([], {})
    cands += xs
    wstats["cross"] = xstats
    log(f"[v2] cross-episode promos: {len(xs)} ({xstats})")
    violations = {p.id: check(p, idx) for p in cands if check(p, idx)}
    log(f"[v2] {len(cands)} candidate windows, {len(violations)} rule violations")

    log(f"[v2] judge = {judge}")
    if judge == "jev":
        from . import jev
        sc = jev_screen(cands, idx, log)
    else:
        sc = screen(cands, idx, samples=screen_samples, workers=workers, log=log)
    kept, dups, vecs = story_dedupe(cands, idx, DEDUPE_THR, log)
    log(f"[v2] story dedupe: {len(kept)} kept, {len(dups)} dropped")

    short = mmr(kept, vecs, shortlist)
    if judge == "jev":
        tr = jev_tournament(short, idx, escalate, log)
    else:
        tr = tournament(short, idx, rounds=rounds, workers=2, log=log)
    pstats = pairwise_stats(tr["verdicts"])
    h1, h2 = split_half_bt([p.id for p in short], tr["verdicts"])

    # Final order of the shortlist = Bradley-Terry strength, screen score breaks ties.
    # Measured over two full runs (experiments/RESULTS.md), BT alone was the most consistent
    # split-half estimator (Spearman 0.39 / 0.22, top-10 overlap 60% / 60%); z(BT)+z(screen)
    # was 0.49 / 0.06, screen alone 0.23 / 0.01. None of them orders the top 20 reliably with
    # the free-tier ranker, so the UI presents the shortlist as a tier, not a strict order.
    short_sorted = sorted(short, key=lambda p: (-(p.bt or 0), -p.screen_score))
    rest = sorted([p for p in kept if p not in short], key=lambda p: -p.screen_score)
    ranked = short_sorted + rest
    for i, p in enumerate(ranked, 1):
        p.rank = i
        p.final_score = round(p.screen_score, 2)
        p.judge_model = ", ".join(sorted({v["model"] for v in tr["verdicts"]
                                          if p.id in (v["first"], v["second"])})) or "(screen only)"
    log(f"[v2] pairwise: {pstats}")
    plan = {}
    if notes:
        from .explain import posting_plan, write_notes
        write_notes(ranked[:notes], idx, log=log)
        plan = posting_plan(short_sorted, log=log)
    return {"plan": plan,"episodes": episodes, "index": idx, "ranked": ranked, "candidates": cands, "tags": tags,
            "window_stats": wstats, "violations": violations, "duplicates": dups, "screen": sc,
            "tournament": tr, "pairwise_stats": pstats, "split_half": (h1, h2), "shortlist": short,
            "calls": list(CALLS), "judge": judge, "tokens": {k: list(v) for k, v in TOKENS.items()},
            "jev_usage": _jev_usage() if judge == "jev" else None}


def _jev_usage() -> dict:
    from . import jev
    return {**jev.USAGE, "cost_usd": round(jev.cost_usd(), 5), "model": jev.JEV_MODEL}


def jev_screen(cands, idx, log=print) -> dict:
    """Jev rubric scores, asked with levels in both orders and averaged (measured: Spearman 0.99
    between orders, 34% ties vs 84% for the LLM screen). Same output shape as rerank.screen."""
    from . import jev
    from .models import Judge
    a1 = jev.screen(cands, idx, reverse=False)
    a2 = jev.screen(cands, idx, reverse=True)
    for p in cands:
        r = {k: (a1[p.id][k] + a2[p.id][k]) / 2 for k in a1[p.id]}
        p.screen_samples = [a1[p.id]["weighted"], a2[p.id]["weighted"]]
        p.screen_score = round(r["weighted"], 3)
        conf = min(r[k + "_conf"] for k in ("hook", "cliffhanger", "standalone", "intensity"))
        p.judge = Judge(hook=round(r["hook"], 2), cliffhanger=round(r["cliffhanger"], 2),
                        standalone=round(r["standalone"], 2), intensity=round(r["intensity"], 2),
                        spoiler_risk=round(r["spoiler"], 2), would_post=r["weighted"] >= 7.5,
                        verdict=f"Jev rubric (min confidence {conf:.2f})",
                        issues="low Jev confidence: review" if conf < 0.4 else "")
    log(f"  [jev] screened {len(cands)} clips, {jev.USAGE['requests']} requests, ${jev.cost_usd():.4f}")
    return {"per_sample": [{p.id: a1[p.id]["weighted"] for p in cands}, {p.id: a2[p.id]["weighted"] for p in cands}]}


def jev_tournament(short, idx, escalate: bool, log=print) -> dict:
    """Every pair, both orders (Jev is cheap enough), soft Bradley-Terry on P(a beats b).
    Pairs whose orders disagree are ties unless escalate=True sends them to the LLM ranker."""
    from . import jev
    from .rerank import _ask_pairs, bradley_terry
    by = {p.id: p for p in short}
    comps = jev.all_pairs(short, idx, log=log)
    verdicts, games = [], []
    for c in comps:
        for first_is_a, pa in ((True, c["p_a_first"]), (False, c["p_a_second"])):
            first, second = (c["a"], c["b"]) if first_is_a else (c["b"], c["a"])
            winner = c["a"] if pa > 0.5 else c["b"]
            verdicts.append({"first": first, "second": second, "winner": winner,
                             "first_won": winner == first, "model": jev.JEV_MODEL, "p_a": pa})
        games.append((c["a"], c["b"], c["p"]))
    escalated = []
    if escalate:
        dis = [c for c in comps if not c["agree"]]
        log(f"  [jev] escalating {len(dis)} order-dependent pairs to the LLM ranker")
        for c in dis:
            res = _ask_pairs([(by[c["a"]], by[c["b"]])], idx, "esc-f", log) + \
                  _ask_pairs([(by[c["b"]], by[c["a"]])], idx, "esc-r", log)
            if len(res) == 2 and res[0]["winner"] == res[1]["winner"]:
                s = 1.0 if res[0]["winner"] == c["a"] else 0.0
                games = [g for g in games if {g[0], g[1]} != {c["a"], c["b"]}] + [(c["a"], c["b"], s)]
                escalated.append({**c, "llm_winner": res[0]["winner"]})
    bt = bradley_terry([p.id for p in short], games)
    for p in short:
        w = sum(1 for c in comps if c["agree"] and ((c["a"] == p.id) == (c["p"] > 0.5)) and p.id in (c["a"], c["b"]))
        l_ = sum(1 for c in comps if c["agree"] and p.id in (c["a"], c["b"])) - w
        t = sum(1 for c in comps if not c["agree"] and p.id in (c["a"], c["b"]))
        p.bt, p.record = bt[p.id], f"{w}-{l_}-{t}"
    return {"verdicts": verdicts, "games": games, "bt": bt, "comparisons": comps, "escalated": escalated}
