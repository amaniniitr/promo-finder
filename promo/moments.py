"""v2 picking: LLM labels moments, code builds the clips.

What went wrong in v1: the LLM chose start/end beats itself and had to add up
timestamps to hit 20-60s. Raw compliance was 84% overall and 71% on the
fallback lite model, and the code repairs that followed cut endings badly.

v2 (constrained candidate selection, as in topic-to-timestamp alignment work and
'select a range, compute times in code' pipelines):
  1. LLM (cheap 'tag' model) only marks HOOK beats and CLIFFHANGER beats by ID,
     with a 1-10 strength. A classification task, not arithmetic.
  2. Code enumerates every (hook -> cliff) window in the same episode:
       20-60s apart  -> one continuous clip, starting exactly on the hook
       60-240s apart -> two segments: hook teaser (6-18s) + run-up to the cliff
  3. Non-max suppression keeps the best non-overlapping windows per episode.
Every candidate meets the length and hook-in-3s rules by construction.
"""
from __future__ import annotations

from .llm import call_json
from .models import HOOK_WINDOW, MAX_LEN, MIN_LEN, BeatIndex, Promo, Segment, _snap
from .parser import Episode, fmt

TAG_SYSTEM = """You are a promo editor for vertical microdrama apps (ReelShort, DramaBox).
You label moments in a screenplay. You do NOT choose clip lengths; code does that."""

TAG_USER = """STORY SO FAR (for your understanding only): {context}

EPISODE {ep} SCRIPT (each line: [BEAT_ID] start-end SPEAKER/TYPE: text):
{script}

Label two kinds of beats, using beat IDs copied exactly from the script.

HOOKS: a beat that could be the very FIRST thing a cold, scrolling viewer sees and makes them stop:
a slap, a shocking line, an insult, a threat, a reveal, a scream, violence, a kiss. It must land without
knowing the show. Quiet setup or establishing shots are not hooks.

CLIFFS: a beat to END a promo on: it leaves an open question (a threat, a reveal about to land, a
discovery, a decision not yet made, danger). A beat that resolves tension is not a cliff.

Give up to 6 of each, strongest first. strength: 1-10, be strict.
Return JSON:
{{"hooks": [{{"beat": "E..-B...", "strength": n, "what": "short description, quote the line"}}],
  "cliffs": [{{"beat": "E..-B...", "strength": n, "open_question": "what the viewer needs to know next"}}]}}"""

EP_END_STRENGTH = 7.0   # writers end every episode on a sting / cut to black


def _context(episodes: list[Episode], upto: int, k: int = 5) -> str:
    prev = [e for e in episodes if e.number < upto][-k:]
    return " | ".join(f"Ep{e.number}: {e.logline}" for e in prev) or "(first episode)"


def tag_episode(ep: Episode, episodes: list[Episode], idx: BeatIndex, log=print) -> dict:
    """Returns {'hooks': [...], 'cliffs': [...], 'model', 'invalid_ids'}. Invalid IDs are dropped and counted."""
    info: dict = {}
    try:
        data = call_json(TAG_SYSTEM, TAG_USER.format(context=_context(episodes, ep.number), ep=ep.number,
                                                     script=ep.render()), role="tag", temperature=0.2,
                         log=log, info=info)
    except RuntimeError as e:
        log(f"  [tag] Ep{ep.number} FAILED: {str(e)[:120]}")
        data = {}
    data = data if isinstance(data, dict) else {}
    out = {"hooks": [], "cliffs": [], "model": info.get("model", ""), "invalid_ids": 0}
    for kind in ("hooks", "cliffs"):
        for t in data.get(kind, []) or []:
            if not isinstance(t, dict):
                continue
            b = idx.get(str(t.get("beat", "")))
            if b is None or b.episode != ep.number:
                out["invalid_ids"] += 1
                continue
            try:
                s = float(t.get("strength", 5) or 5)
            except (TypeError, ValueError):
                s = 5.0
            out[kind].append({"beat": b.id, "strength": s,
                              "note": t.get("what") or t.get("open_question") or ""})
    # The episode's own last beat is the writers' cliffhanger: always a cliff candidate.
    last = ep.beats[-1]
    if not any(c["beat"] == last.id for c in out["cliffs"]):
        out["cliffs"].append({"beat": last.id, "strength": EP_END_STRENGTH, "note": "episode ending (writers' cliffhanger)",
                              "auto": True})
    log(f"  [tag] Ep{ep.number}: {len(out['hooks'])} hooks, {len(out['cliffs'])} cliffs, "
        f"{out['invalid_ids']} invalid ids ({out['model']})")
    return out


def _line_end_at_or_before(beats, t: float, lo: float) -> float | None:
    ends = [b.end for b in beats if b.type == "dialogue" and lo < b.end <= t]
    return max(ends) if ends else None


def _line_start_at_or_after(beats, t: float, hi: float) -> float | None:
    starts = [b.start for b in beats if b.type == "dialogue" and t <= b.start < hi]
    return min(starts) if starts else None


def _iou(a: Promo, b: Promo) -> float:
    inter = union = 0.0
    sa = [(s.start, s.end) for s in a.segments if s.episode == b.segments[0].episode]
    sb = [(s.start, s.end) for s in b.segments]
    for x0, x1 in sa:
        for y0, y1 in sb:
            inter += max(0.0, min(x1, y1) - max(x0, y0))
    union = a.duration + b.duration - inter
    return inter / union if union > 0 else 0.0


def build_windows(ep: Episode, tags: dict, idx: BeatIndex, per_episode: int = 4) -> tuple[list[Promo], dict]:
    beats = ep.beats
    cands: list[Promo] = []
    stats = {"pairs": 0, "single": 0, "stitched": 0, "too_close": 0, "too_far": 0}
    for h in tags["hooks"]:
        hb = idx.get(h["beat"])
        for c in tags["cliffs"]:
            cb = idx.get(c["beat"])
            if cb.idx <= hb.idx:
                continue
            stats["pairs"] += 1
            start = hb.start
            seg = Segment(episode=ep.number, start_beat=hb.id, end_beat=cb.id, start=start, end=cb.end)
            _snap(seg, beats)
            if seg.start < start - HOOK_WINDOW:      # a long line straddles the hook: skip
                continue
            gap = seg.end - seg.start
            prior = 0.5 * h["strength"] + 0.5 * c["strength"]
            base = dict(hook_beat=hb.id, hook=h["note"] or hb.text,
                        cliffhanger=c["note"] or cb.text,
                        why=f"hook {h['strength']:g}/10 -> cliff {c['strength']:g}/10")
            if gap < MIN_LEN:
                stats["too_close"] += 1
                continue
            if gap <= MAX_LEN:
                prior += 0.5 if 25 <= gap <= 50 else 0.0
                p = Promo(id="", kind="single", segments=[seg], picker_score=round(prior, 2), **base)
                stats["single"] += 1
            elif gap <= 240:
                # Two segments: hook teaser, then the run-up into the cliff.
                s1_end = _line_end_at_or_before(beats, seg.start + 18, seg.start + 6)
                if s1_end is None:
                    continue
                s1 = Segment(episode=ep.number, start_beat=hb.id, end_beat=hb.id, start=seg.start, end=s1_end)
                budget = MAX_LEN - s1.length - 1
                s2_start = _line_start_at_or_after(beats, seg.end - budget, seg.end - 12)
                if s2_start is None or s2_start <= s1.end:
                    continue
                s2 = Segment(episode=ep.number, start_beat=cb.id, end_beat=cb.id, start=s2_start, end=seg.end)
                total = s1.length + s2.length
                if not (MIN_LEN <= total <= MAX_LEN):
                    continue
                p = Promo(id="", kind="stitched", segments=[s1, s2], picker_score=round(prior - 0.5, 2), **base)
                stats["stitched"] += 1
            else:
                stats["too_far"] += 1
                continue
            p.duration = round(sum(s.length for s in p.segments), 2)
            p.picker_model = tags["model"]
            p.hook_strength, p.cliff_strength = h["strength"], c["strength"]
            if c.get("auto"):
                p.flags.append("ends_on_episode_finale")
            cands.append(p)

    # Non-max suppression: best prior first, drop windows overlapping a kept one (IoU > 0.5).
    kept: list[Promo] = []
    for p in sorted(cands, key=lambda x: -x.picker_score):
        if all(_iou(p, k) <= 0.5 for k in kept):
            kept.append(p)
        if len(kept) == per_episode:
            break
    for i, p in enumerate(kept, 1):
        p.id = f"E{ep.number:02d}-W{i}"
        p.title = f"{'2-part ' if p.kind == 'stitched' else ''}{fmt(p.segments[0].start)} hook -> cliff"
    stats["kept"] = len(kept)
    return kept, stats


def check(p: Promo, idx: BeatIndex) -> list[str]:
    """Independent rule check, used to verify 'compliant by construction'."""
    errs = []
    if not (MIN_LEN <= p.duration <= MAX_LEN):
        errs.append(f"len {p.duration}")
    h = idx.get(p.hook_beat)
    if h is None or not (0 <= h.start - p.segments[0].start <= HOOK_WINDOW):
        errs.append("hook not in first 3s")
    for a, b in zip(p.segments, p.segments[1:]):
        if a.episode == b.episode and b.start < a.end:
            errs.append("segments overlap")
    return errs


def _speakers(p: Promo, idx: BeatIndex) -> set[str]:
    out = set()
    for s in p.segments:
        for b in idx.eps[s.episode].beats:
            if b.speaker and s.start - 0.01 <= b.start and b.end <= s.end + 0.01:
                out.add(b.speaker.replace("LADY ", "").replace("LORD ", "").strip())
    return out


def build_cross(cands: list[Promo], idx: BeatIndex, max_out: int = 12, max_gap: int = 12) -> tuple[list[Promo], dict]:
    """Cross-episode promos: hook teaser from an earlier episode + run-up into a cliff from a later one.

    Built in code from already-tagged windows, so the same rules hold (20-60s, hook in first 3s).
    Constraints that keep it a coherent mini-story: same main character speaks in both parts,
    episodes at most `max_gap` apart, later part strictly later in the story.
    """
    singles = [p for p in cands if p.kind == "single" and p.hook_strength and p.cliff_strength]
    out, stats = [], {"pairs_considered": 0, "no_shared_character": 0, "no_fit": 0}
    for a in singles:
        for b in singles:
            ea, eb = a.segments[0].episode, b.segments[0].episode
            if not (0 < eb - ea <= max_gap):
                continue
            stats["pairs_considered"] += 1
            if not (_speakers(a, idx) & _speakers(b, idx)):
                stats["no_shared_character"] += 1
                continue
            A, B = idx.eps[ea].beats, idx.eps[eb].beats
            s0 = a.segments[0].start
            s1_end = _line_end_at_or_before(A, s0 + 15, s0 + 6)
            if s1_end is None:
                stats["no_fit"] += 1
                continue
            s1 = Segment(episode=ea, start_beat=a.hook_beat, end_beat=a.hook_beat, start=s0, end=s1_end)
            bend = b.segments[-1].end
            budget = MAX_LEN - s1.length - 1
            s2_start = _line_start_at_or_after(B, bend - budget, bend - 10)
            if s2_start is None:
                stats["no_fit"] += 1
                continue
            s2 = Segment(episode=eb, start_beat=b.segments[-1].end_beat, end_beat=b.segments[-1].end_beat,
                         start=s2_start, end=bend)
            total = s1.length + s2.length
            if not (MIN_LEN <= total <= MAX_LEN):
                stats["no_fit"] += 1
                continue
            p = Promo(id="", kind="cross", segments=[s1, s2], hook_beat=a.hook_beat, hook=a.hook,
                      cliffhanger=b.cliffhanger, why=f"Ep{ea} hook {a.hook_strength:g}/10 -> Ep{eb} cliff {b.cliff_strength:g}/10",
                      picker_score=round(0.5 * a.hook_strength + 0.5 * b.cliff_strength - 0.5, 2),
                      hook_strength=a.hook_strength, cliff_strength=b.cliff_strength, picker_model=a.picker_model)
            p.duration = round(total, 2)
            out.append(p)
    # keep the best, using each source window at most once per side
    kept, used_a, used_b = [], set(), set()
    for p in sorted(out, key=lambda x: -x.picker_score):
        ka = (p.segments[0].episode, round(p.segments[0].start, 1))
        kb = (p.segments[1].episode, round(p.segments[1].end, 1))
        if ka in used_a or kb in used_b:
            continue
        kept.append(p)
        used_a.add(ka)
        used_b.add(kb)
        if len(kept) == max_out:
            break
    for i, p in enumerate(kept, 1):
        p.id = f"X{i:02d}-E{p.segments[0].episode:02d}E{p.segments[1].episode:02d}"
        p.title = f"cross-episode Ep{p.segments[0].episode} -> Ep{p.segments[1].episode}"
    stats["built"], stats["kept"] = len(out), len(kept)
    return kept, stats
