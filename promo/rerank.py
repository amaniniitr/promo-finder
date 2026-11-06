"""v2 ranking: cheap pointwise screen (multi-sample) -> diverse shortlist ->
bidirectional pairwise tournament with the strongest model -> Bradley-Terry.

What went wrong in v1 (measured in experiments/BASELINE_v1.md):
  * one pointwise pass with integer 1-10 sub-scores: 81% of final scores tied;
  * swapping the judge model kept only 30% of the top 10;
  * the cheapest model did the ranking, because of quota.

Fixes, each from published practice:
  * Screen with >=2 samples, each with a different shuffled batch composition,
    then average. This cuts single-trial noise (Coin Flip Judge, arXiv 2606.13685:
    13.6% of pairwise verdicts flip between identical runs; multi-trial + order
    randomisation recommended).
  * Order the shortlist by pairwise comparison (Pairwise Ranking Prompting,
    Qin et al. 2023, arXiv 2306.17563): comparing two clips is easier than placing
    one on an absolute scale. Every pair is asked in BOTH orders (A/B and B/A) in
    different calls; a split verdict counts as a tie. This cancels position bias
    and gives a measured flip rate.
  * Swiss pairing (neighbours in the current standing play each other) spends
    comparisons where the order is uncertain. ~K*rounds/2 pairs instead of K^2/2.
  * Bradley-Terry fit (MM algorithm, Hunter 2004) turns wins into a strength per clip.
"""
from __future__ import annotations

import math
import random
from concurrent.futures import ThreadPoolExecutor

from .llm import call_json
from .models import BeatIndex, Judge, Promo, clip_script
from .prompts import JUDGE_CLIP

W = {"hook": 0.30, "cliffhanger": 0.30, "standalone": 0.20, "intensity": 0.20}

SCREEN_SYSTEM = """You are a skeptical social-media growth lead for a vertical drama app. You review promo
clips before they go on TikTok. You have NEVER seen the show; you see only the clip, like a cold viewer.
Most clips are mediocre. Use the full scale; a 9-10 should be rare."""

SCREEN_USER = """Review these {k} promo clips independently (each viewer sees only one).

{clips}

Score each 1-10:
- hook: do the first 3 seconds alone make a scroller stop?
- cliffhanger: does it cut at an unresolved moment that creates a need to see what happens next?
- standalone: can a stranger follow who is who and what is at stake from this clip alone?
- intensity: emotional punch, conflict, reversal
- spoiler_risk: 10 = gives away a major twist
Return JSON: {{"reviews": [{{"id": "...", "hook": n, "cliffhanger": n, "standalone": n, "intensity": n,
"spoiler_risk": n, "would_post": true/false, "verdict": "one sentence", "issues": "biggest problem or empty"}}]}}"""

PAIR_SYSTEM = """You are the head of growth for a vertical microdrama app deciding which promo clip to post.
A cold viewer, scrolling TikTok, has never seen the show. You compare clips two at a time.
Judge only what the clip shows. Ignore which clip is listed first; position carries no information.
Do not prefer a clip for being longer."""

PAIR_USER = """For each pair, which clip would make MORE cold viewers (1) stop scrolling in the first 3 seconds,
(2) understand the conflict without context, and (3) need to see what happens next?

{pairs}

Return JSON: {{"results": [{{"pair": "<pair id>", "winner": "A" or "B", "reason": "few words"}}]}}"""


import re as _re

_ID = _re.compile(r"(X\d{2}-E\d{2}E\d{2}|E\d{2}-[A-Z]\d+|S\d{2}|X\d{2})")


def norm_id(raw) -> str:
    """Models sometimes echo 'CLIP E02-W1' or '=== CLIP E02-W1 ==='; keep just the ID."""
    m = _ID.search(str(raw))
    return m.group(1) if m else str(raw).strip()


def _items(data, key):
    items = data if isinstance(data, list) else (data or {}).get(key, [])
    return [x for x in items if isinstance(x, dict)]


def _clip_block(p: Promo, idx: BeatIndex, label: str | None = None) -> str:
    return JUDGE_CLIP.format(id=label or p.id, dur=p.duration, clip=clip_script(p, idx),
                             hook=p.hook, cliff=p.cliffhanger)


def _weighted(r: dict) -> float:
    try:
        base = sum(float(r[k]) * w for k, w in W.items())
        return round(base - max(0.0, float(r.get("spoiler_risk", 0)) - 6) * 0.3, 3)
    except (KeyError, TypeError, ValueError):
        return float("nan")


def screen(promos: list[Promo], idx: BeatIndex, samples: int = 2, batch: int = 8, workers: int = 4,
           role: str = "screen", log=print) -> dict:
    """Pointwise screen. Sample s uses a different shuffle, so each clip is scored next to different
    neighbours and in a different position. Returns per-sample scores for test-retest analysis."""
    per_sample: list[dict[str, float]] = []
    reviews: dict[str, dict] = {}
    for s in range(samples):
        order = promos[:]
        random.Random(1000 + s).shuffle(order)
        batches = [order[i:i + batch] for i in range(0, len(order), batch)]

        def run(b):
            text = "\n\n".join(_clip_block(p, idx) for p in b)
            try:
                d = call_json(SCREEN_SYSTEM, SCREEN_USER.format(k=len(b), clips=text), role=role,
                              temperature=0.7, log=log, salt=f"s{s}")
            except RuntimeError as e:
                log(f"  [screen] batch failed: {str(e)[:100]}")
                d = {}
            return {norm_id(r.get("id", "")): r for r in _items(d, "reviews")}

        got: dict[str, dict] = {}
        with ThreadPoolExecutor(workers) as ex:
            for res in ex.map(run, batches):
                got.update(res)
        # clips the model skipped: re-ask in small batches
        miss = [p for p in promos if p.id not in got]
        for i in range(0, len(miss), 3):
            got.update(run(miss[i:i + 3]))
        known = {p.id for p in promos}
        scores = {pid: _weighted(r) for pid, r in got.items() if pid in known and not math.isnan(_weighted(r))}
        per_sample.append(scores)
        for pid, r in got.items():
            reviews.setdefault(pid, r)
        log(f"  [screen] sample {s + 1}: scored {len(scores)}/{len(promos)}")

    for p in promos:
        vals = [sm[p.id] for sm in per_sample if p.id in sm]
        p.screen_samples = vals
        p.screen_score = round(sum(vals) / len(vals), 3) if vals else 0.0
        r = reviews.get(p.id)
        if r:
            p.judge = Judge(**{k: v for k, v in r.items() if k in Judge.model_fields})
    return {"per_sample": per_sample}


def bradley_terry(ids: list[str], games: list[tuple[str, str, float]], iters: int = 200, prior: float = 0.5):
    """MM estimate. games: (i, j, score_i) with score_i in {1, 0.5, 0}. A weak prior (one virtual
    tie against an average opponent) keeps undefeated / winless clips finite."""
    p = {i: 1.0 for i in ids}
    wins = {i: prior for i in ids}
    opp: dict[str, list[str]] = {i: [] for i in ids}
    for a, b, s in games:
        wins[a] += s
        wins[b] += 1 - s
        opp[a].append(b)
        opp[b].append(a)
    for _ in range(iters):
        new = {}
        for i in ids:
            den = sum(1.0 / (p[i] + p[j]) for j in opp[i]) + 2 * prior / (p[i] + 1.0)
            new[i] = wins[i] / den if den else p[i]
        g = math.exp(sum(math.log(v) for v in new.values()) / len(new))
        p = {i: v / g for i, v in new.items()}
    return {i: round(math.log(v), 4) for i, v in p.items()}


def _ask_pairs(pairs: list[tuple[Promo, Promo]], idx: BeatIndex, tag: str, log) -> list[dict]:
    """pairs are (first_shown, second_shown). Returns [{a, b, winner_id, first_won}]."""
    text = []
    for n, (x, y) in enumerate(pairs):
        text.append(f"##### PAIR p{n}\n" + _clip_block(x, idx, "A") + "\n\n" + _clip_block(y, idx, "B"))
    info: dict = {}
    try:
        d = call_json(PAIR_SYSTEM, PAIR_USER.format(pairs="\n\n".join(text)), role="rank",
                      temperature=0.0, log=log, info=info, salt=tag)
    except RuntimeError as e:
        log(f"  [rank] call failed: {str(e)[:100]}")
        return []
    out = []
    res = {str(r.get("pair", "")).strip(): str(r.get("winner", "")).strip().upper()[:1] for r in _items(d, "results")}
    for n, (x, y) in enumerate(pairs):
        w = res.get(f"p{n}")
        if w in ("A", "B"):
            out.append({"first": x.id, "second": y.id, "winner": x.id if w == "A" else y.id,
                        "first_won": w == "A", "model": info.get("model", "")})
    return out


def tournament(shortlist: list[Promo], idx: BeatIndex, rounds: int = 4, per_call: int = 3,
               workers: int = 2, log=print) -> dict:
    ids = [p.id for p in shortlist]
    by = {p.id: p for p in shortlist}
    played: set[frozenset] = set()
    verdicts: list[dict] = []
    games: list[tuple[str, str, float]] = []
    standing = {p.id: p.screen_score / 10 for p in shortlist}  # round 1 seeds from the screen

    for rnd in range(rounds):
        order = sorted(ids, key=lambda i: -standing[i])
        pairs, used = [], set()
        for i in order:  # Swiss: pair each clip with the nearest unplayed opponent below it
            if i in used:
                continue
            for j in order:
                if j != i and j not in used and frozenset((i, j)) not in played:
                    pairs.append((i, j))
                    used |= {i, j}
                    played.add(frozenset((i, j)))
                    break
        if not pairs:
            break
        # Both presentation orders, in DIFFERENT calls (shuffled), so the model never sees its own answer.
        fwd = [(by[a], by[b]) for a, b in pairs]
        rev = [(by[b], by[a]) for a, b in pairs]
        rng = random.Random(rnd)
        rng.shuffle(fwd)
        rng.shuffle(rev)
        chunks = [(fwd[i:i + per_call], f"r{rnd}f{i}") for i in range(0, len(fwd), per_call)] + \
                 [(rev[i:i + per_call], f"r{rnd}r{i}") for i in range(0, len(rev), per_call)]
        with ThreadPoolExecutor(workers) as ex:
            for res in ex.map(lambda c: _ask_pairs(c[0], idx, c[1], log), chunks):
                verdicts.extend(res)
        # combine the two orders: 2-0 = win, 1-1 = tie (position-dependent verdict)
        for a, b in pairs:
            vs = [v for v in verdicts if {v["first"], v["second"]} == {a, b}]
            if not vs:
                continue
            sa = sum(v["winner"] == a for v in vs) / len(vs)
            games.append((a, b, sa))
        standing = bradley_terry(ids, games)
        log(f"  [rank] round {rnd + 1}: {len(pairs)} pairs, {len(verdicts)} verdicts so far")

    bt = bradley_terry(ids, games)
    for p in shortlist:
        w = sum(1 for a, b, s in games if (a == p.id and s == 1) or (b == p.id and s == 0))
        l_ = sum(1 for a, b, s in games if (a == p.id and s == 0) or (b == p.id and s == 1))
        t = sum(1 for a, b, s in games if p.id in (a, b) and s == 0.5)
        p.bt, p.record = bt[p.id], f"{w}-{l_}-{t}"
    return {"verdicts": verdicts, "games": games, "bt": bt}


def pairwise_stats(verdicts: list[dict]) -> dict:
    """Position consistency: same pair asked both ways, does the same clip win?"""
    by: dict[frozenset, list[dict]] = {}
    for v in verdicts:
        by.setdefault(frozenset((v["first"], v["second"])), []).append(v)
    both = [vs for vs in by.values() if len(vs) == 2]
    consistent = sum(vs[0]["winner"] == vs[1]["winner"] for vs in both)
    first = sum(v["first_won"] for v in verdicts)
    return {"pairs_asked_both_ways": len(both),
            "position_consistency": round(consistent / len(both), 3) if both else None,
            "flip_rate": round(1 - consistent / len(both), 3) if both else None,
            "first_position_win_rate": round(first / len(verdicts), 3) if verdicts else None,
            "verdicts": len(verdicts)}


def split_half_bt(ids: list[str], verdicts: list[dict]) -> tuple[dict, dict]:
    """Fit BT separately on the forward-order and reverse-order verdicts (two independent
    'raters' that saw identical pairs). Their agreement measures ranking reliability."""
    seen: dict[frozenset, int] = {}
    halves: tuple[list, list] = ([], [])
    for v in verdicts:
        k = frozenset((v["first"], v["second"]))
        h = seen.get(k, 0)
        seen[k] = h + 1
        if h < 2:
            halves[h].append((v["first"], v["second"], 1.0 if v["first_won"] else 0.0))
    return bradley_terry(ids, halves[0]), bradley_terry(ids, halves[1])
