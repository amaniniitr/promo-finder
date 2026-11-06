"""Data models + deterministic timing/validation rules (no AI)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .parser import Beat, Episode, fmt

MIN_LEN, MAX_LEN, HOOK_WINDOW = 20.0, 60.0, 3.0


class Segment(BaseModel):
    episode: int
    start_beat: str
    end_beat: str
    start: float = 0.0
    end: float = 0.0

    @property
    def length(self) -> float:
        return self.end - self.start

    def label(self) -> str:
        return f"Ep{self.episode} {fmt(self.start)}-{fmt(self.end)}"


class Judge(BaseModel):
    hook: float = 0
    cliffhanger: float = 0
    standalone: float = 0
    intensity: float = 0
    spoiler_risk: float = 0
    would_post: bool = False
    verdict: str = ""
    issues: str = ""


class Promo(BaseModel):
    id: str
    kind: str = "single"            # single | stitched
    title: str = ""
    segments: list[Segment]
    hook_beat: str
    hook: str
    cliffhanger: str
    why: str
    picker_score: float = 0
    hook_strength: float = 0         # v2: tagger strength of the hook beat
    cliff_strength: float = 0        # v2: tagger strength of the cliff beat
    picker_model: str = ""
    judge_model: str = ""
    duration: float = 0
    flags: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list)
    judge: Judge | None = None
    screen_score: float = 0          # v2: mean of independent pointwise samples (0-10)
    screen_samples: list[float] = Field(default_factory=list)
    bt: float | None = None          # v2: Bradley-Terry strength from pairwise tournament
    record: str = ""                 # v2: pairwise wins-losses-splits
    final_score: float = 0
    rank: int = 0


class BeatIndex:
    """Lookup beats by ID across the whole show."""

    def __init__(self, episodes: list[Episode]):
        self.eps = {e.number: e for e in episodes}
        self.by_id: dict[str, Beat] = {b.id: b for e in episodes for b in e.beats}

    def get(self, bid: str) -> Beat | None:
        return self.by_id.get(bid.strip().strip("[]"))

    def span(self, seg: Segment) -> list[Beat]:
        a, b = self.get(seg.start_beat), self.get(seg.end_beat)
        if not a or not b or a.episode != b.episode:
            return []
        return self.eps[a.episode].beats[a.idx: b.idx + 1]


def _snap(seg: Segment, beats: list[Beat]) -> None:
    """Never cut mid-line: widen to include any dialogue/sfx the cut points fall inside."""
    for b in beats:
        if b.type in ("dialogue", "sfx") and b.start < seg.start < b.end:
            seg.start = b.start
    for _ in range(3):
        for b in beats:
            if b.type == "dialogue" and b.start < seg.end < b.end:
                seg.end = b.end


def resolve(promo: Promo, idx: BeatIndex) -> Promo:
    """Map beat IDs -> timestamps, auto-fix hook position, attach rule flags."""
    flags, fixes = [], list(promo.fixes)
    for seg in promo.segments:
        span = idx.span(seg)
        if not span:
            flags.append(f"bad_beat_ids:{seg.start_beat}..{seg.end_beat}")
            continue
        seg.episode = span[0].episode
        seg.start = span[0].start
        seg.end = max(b.end for b in span)
        _snap(seg, idx.eps[seg.episode].beats)

    if any(f.startswith("bad_beat_ids") for f in flags):
        promo.flags, promo.duration = flags, 0
        return promo

    # Hook must land in the first 3 s. If the picker started too early, move the
    # start to the hook beat (deterministic fix, logged).
    hook = idx.get(promo.hook_beat)
    first = promo.segments[0]
    if hook is None:
        flags.append("hook_beat_missing")
    elif hook.episode == first.episode and first.start <= hook.start <= first.end:
        lead = hook.start - first.start
        if lead > HOOK_WINDOW:
            first.start = hook.start
            _snap(first, idx.eps[first.episode].beats)
            fixes.append(f"moved start to hook beat (was {lead:.1f}s before hook)")
    else:
        flags.append("hook_not_in_first_segment")

    promo.duration = round(sum(s.length for s in promo.segments), 2)
    _repair_length(promo, idx, fixes)
    if any("re-cut" in f for f in fixes) and not promo.cliffhanger.startswith("[re-cut]"):
        # The picker's described ending is no longer the ending; describe what the clip now ends on.
        last = promo.segments[-1]
        tail = [b for b in idx.eps[last.episode].beats
                if b.type in ("dialogue", "action", "sfx") and last.start <= b.start and b.end <= last.end + 0.01]
        if tail:
            b = tail[-1]
            fixes.append(f"original cliffhanger: {promo.cliffhanger}")
            promo.cliffhanger = "[re-cut] ends on " + (f'{b.speaker}: "{b.text}"' if b.speaker else b.text)
    if promo.duration < MIN_LEN:
        flags.append(f"too_short:{promo.duration:.1f}s")
    if promo.duration > MAX_LEN:
        flags.append(f"too_long:{promo.duration:.1f}s")
    last = promo.segments[-1]
    if last.end >= idx.eps[last.episode].duration - 0.5:
        flags.append("ends_on_episode_finale")  # info: uses the writers' own cliffhanger
    promo.flags, promo.fixes = flags, fixes
    return promo


def _repair_length(p: Promo, idx: BeatIndex, fixes: list[str]) -> None:
    """Deterministic length repair on the LAST segment only (the start holds the hook).

    too long  -> pull the end back to the last dialogue line that fits in 60 s.
    too short -> push the end forward line by line until >= 20 s (stays in the episode).
    Either way the picker's claimed cliffhanger may no longer be the ending, so we
    flag it and let the judge score the clip as actually cut.
    """
    last = p.segments[-1]
    beats = idx.eps[last.episode].beats
    other = p.duration - last.length
    if p.duration > MAX_LEN and len(p.segments) > 1:
        # Stitched: give every segment an equal share of the budget, cut each on a line end.
        old, budget = p.duration, (MAX_LEN - 1) / len(p.segments)
        for s in p.segments:
            if s.length > budget:
                ends = [b.end for b in idx.eps[s.episode].beats
                        if b.type == "dialogue" and s.start + 2 < b.end <= s.start + budget]
                s.end = max(ends) if ends else s.start + budget
        p.duration = round(sum(s.length for s in p.segments), 2)
        fixes.append(f"trimmed segments to <= {budget:.0f}s each, {old:.0f}s->{p.duration:.0f}s (cliffhanger re-cut)")
        return
    if p.duration > MAX_LEN:
        limit = last.start + (MAX_LEN - other)
        ends = [b.end for b in beats if b.type == "dialogue" and last.start + 3 < b.end <= limit]
        if ends:
            old = p.duration
            last.end = max(ends)
            p.duration = round(other + last.length, 2)
            fixes.append(f"trimmed end {old:.0f}s->{p.duration:.0f}s (cliffhanger re-cut)")
    elif p.duration < MIN_LEN:
        target = last.start + (MIN_LEN - other)
        later = [b for b in beats if b.type == "dialogue" and b.end >= target and b.start >= last.end - 0.01]
        if later:
            end = min(b.end for b in later)
            if other + end - last.start <= MAX_LEN:
                old = p.duration
                last.end = end
                p.duration = round(other + last.length, 2)
                fixes.append(f"extended end {old:.0f}s->{p.duration:.0f}s (cliffhanger re-cut)")


def hard_errors(p: Promo) -> list[str]:
    return [f for f in p.flags if f.split(":")[0] in
            {"bad_beat_ids", "too_short", "too_long", "hook_not_in_first_segment", "hook_beat_missing"}]


def overlap(a: Promo, b: Promo) -> float:
    """Overlap seconds / shorter promo length (same-episode segments only)."""
    inter = 0.0
    for s in a.segments:
        for t in b.segments:
            if s.episode == t.episode:
                inter += max(0.0, min(s.end, t.end) - max(s.start, t.start))
    shorter = min(a.duration, b.duration) or 1
    return inter / shorter


def clip_script(p: Promo, idx: BeatIndex) -> str:
    """What a viewer would experience, in order, with cut markers. No show context."""
    out = []
    for n, seg in enumerate(p.segments):
        if n:
            out.append("--- CUT ---")
        for b in idx.eps[seg.episode].beats:
            if b.start >= seg.start - 0.01 and b.end <= seg.end + 0.01:
                t = round(b.start - seg.start + sum(s.length for s in p.segments[:n]), 1)
                who = f'{b.speaker} ({b.emotion}): "{b.text}"' if b.speaker else f"[{b.type.upper()}] {b.text}"
                out.append(f"{t:>5}s {who}")
    return "\n".join(out)
