"""Write the human-facing text the brief asks for, AFTER ranking (so it can't bias the rank):
  * per promo: hook (what the first 3s show), cliffhanger (what is left open), one line on why it works;
  * a posting plan: which to post first and why, with spoiler-risk holds.
The judge numbers are passed in as facts; the model only writes. Code checks every returned ID.
"""
from __future__ import annotations

from .llm import call_json
from .models import BeatIndex, Promo, clip_script
from .rerank import _items, norm_id

SYSTEM = """You write promo notes for an editor at a vertical microdrama app. Be concrete: quote the line or
name the action. One sentence each. No hype words (stunning, gripping, must-watch). Do not invent events that
are not in the clip script."""

USER = """For each clip below write:
- hook: what a viewer sees/hears in the first 3 seconds (quote the line if it is dialogue)
- cliffhanger: the exact open question the clip ends on
- why: one sentence on why a cold viewer would stop and then need the next episode

{clips}

Return JSON {{"notes": [{{"id": "...", "hook": "...", "cliffhanger": "...", "why": "..."}}]}}"""

PLAN_USER = """You are given the top promos, already ranked by a pairwise judging tournament (rank 1 = won the most
comparisons). For each, you get its record, rubric scores (0-10) and a one-line summary.

{rows}

Write a posting plan for the first week: which 5 to post first and in what order, one sentence each on why.
Hold back anything with spoiler_risk >= 5 until later and say so, unless that would leave fewer than 3 to post: then post the lowest-risk ones and mention the risk in the reason. Don't post two clips of the same scene on
consecutive days. Return JSON {{"plan": [{{"id": "...", "day": n, "reason": "..."}}], "hold": [{{"id": "...", "reason": "..."}}]}}"""


def _block(p: Promo, idx: BeatIndex) -> str:
    return f"=== CLIP {p.id} ({p.duration:.0f}s) ===\n{clip_script(p, idx)}"


def write_notes(promos: list[Promo], idx: BeatIndex, batch: int = 6, log=print) -> int:
    done = 0
    for i in range(0, len(promos), batch):
        chunk = promos[i:i + batch]
        try:
            d = call_json(SYSTEM, USER.format(clips="\n\n".join(_block(p, idx) for p in chunk)),
                          role="explain", temperature=0.3, log=log)
        except RuntimeError as e:
            log(f"  [explain] failed: {str(e)[:100]}")
            continue
        got = {norm_id(n.get("id", "")): n for n in _items(d, "notes")}
        for p in chunk:
            n = got.get(p.id)
            if n and n.get("why"):
                p.hook = n.get("hook") or p.hook
                p.cliffhanger = n.get("cliffhanger") or p.cliffhanger
                p.why = n["why"]
                done += 1
    log(f"  [explain] notes written for {done}/{len(promos)}")
    return done


def posting_plan(short: list[Promo], log=print) -> dict:
    rows = []
    for p in short:
        j = p.judge
        rows.append(f"- {p.id} (rank {p.rank}, {p.kind}, {p.duration:.0f}s, W-L-T {p.record}): hook {j.hook:.1f}, "
                    f"cliffhanger {j.cliffhanger:.1f}, standalone {j.standalone:.1f}, spoiler_risk {j.spoiler_risk:.1f}. "
                    f"{p.why}")
    try:
        d = call_json(SYSTEM, PLAN_USER.format(rows="\n".join(rows)), role="explain", temperature=0.2, log=log)
    except RuntimeError as e:
        log(f"  [plan] failed: {str(e)[:100]}")
        return {}
    ids = {p.id for p in short}
    plan = [x for x in _items(d, "plan") if norm_id(x.get("id", "")) in ids]
    hold = [x for x in _items(d, "hold") if norm_id(x.get("id", "")) in ids]
    for x in plan + hold:
        x["id"] = norm_id(x["id"])
    return {"plan": plan, "hold": hold}
