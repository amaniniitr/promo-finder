"""Pipeline: parse -> pick (per episode) -> stitch -> validate -> judge -> dedupe -> rank."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .llm import call_json
from .models import BeatIndex, Judge, Promo, Segment, clip_script, hard_errors, overlap, resolve
from .parser import Episode, fmt, parse_show
from .rerank import norm_id
from . import prompts as P

# Weights for final rank. Hook and cliffhanger are what the brief defines as a promo.
W = {"hook": 0.30, "cliffhanger": 0.30, "standalone": 0.20, "intensity": 0.20}
FAILED: list[str] = []  # LLM calls that failed after all retries/fallbacks (reported in runs/v1)


def _items(data, key: str) -> list:
    """Models sometimes return a bare list instead of {key: [...]}; accept both."""
    items = data if isinstance(data, list) else (data or {}).get(key, [])
    return [x for x in items if isinstance(x, dict)]


def _context(episodes: list[Episode], upto: int, k: int = 6) -> str:
    prev = [e for e in episodes if e.number < upto][-k:]
    head = episodes[0].logline if episodes and episodes[0].number < upto else ""
    lines = [f"Ep1: {head}"] if head and (not prev or prev[0].number != 1) else []
    lines += [f"Ep{e.number}: {e.logline}" for e in prev]
    return "\n".join(lines) or "(first episode)"


def pick_episode(ep: Episode, episodes: list[Episode], n: int = 3, log=print) -> list[Promo]:
    try:
        data = call_json(P.PICKER_SYSTEM, P.PICKER_USER.format(
            context=_context(episodes, ep.number), ep=ep.number, logline=ep.logline,
            dur=ep.duration, script=ep.render(), n=n), role="picker", log=log, info=(info := {}))
    except RuntimeError as e:
        log(f"  [pick] Ep{ep.number} SKIPPED: {str(e)[:150]}")
        FAILED.append(f"pick Ep{ep.number}")
        return []
    log(f"  [pick] Ep{ep.number}: {len(_items(data, 'candidates'))} candidates")
    out = []
    for i, c in enumerate(_items(data, "candidates")[:n]):
        try:
            out.append(Promo(
                id=f"E{ep.number:02d}-P{i + 1}", kind="single", title=c.get("title", ""),
                segments=[Segment(episode=ep.number, start_beat=c["start_beat"], end_beat=c["end_beat"])],
                hook_beat=c.get("hook_beat") or c["start_beat"], hook=c.get("hook", ""),
                cliffhanger=c.get("cliffhanger", ""), why=c.get("why", ""),
                picker_score=float(c.get("score", 0) or 0), picker_model=info.get("model", "")))
        except (KeyError, ValueError, TypeError) as e:
            log(f"  [pick] Ep{ep.number} candidate {i} malformed: {e}")
    return out


def stitch(top: list[Promo], idx: BeatIndex, episodes: list[Episode], n: int = 6, log=print) -> list[Promo]:
    moments = []
    for p in top:
        moments.append(f"### {p.id} (Ep{p.segments[0].episode}) {p.title}\n"
                       + "\n".join(f"[{b.id}] {fmt(b.start)}-{fmt(b.end)} {b.speaker or b.type.upper()}: {b.text}"
                                   for b in idx.span(p.segments[0]) if b.type != "camera"))
    try:
        data = call_json(P.STITCH_SYSTEM, P.STITCH_USER.format(
            loglines="\n".join(f"Ep{e.number}: {e.logline}" for e in episodes),
            moments="\n\n".join(moments), n=n), role="picker", log=log, info=(info := {}))
    except RuntimeError as e:
        log(f"  [stitch] SKIPPED: {str(e)[:150]}")
        FAILED.append("stitch")
        return []
    out = []
    for i, c in enumerate(_items(data, "candidates")[:n]):
        try:
            segs = [Segment(episode=0, start_beat=s["start_beat"], end_beat=s["end_beat"]) for s in c["segments"]]
            out.append(Promo(id=f"S{i + 1:02d}", kind="stitched", title=c.get("title", ""), segments=segs,
                             hook_beat=c.get("hook_beat") or segs[0].start_beat, hook=c.get("hook", ""),
                             cliffhanger=c.get("cliffhanger", ""), why=c.get("why", ""),
                             picker_score=float(c.get("score", 0) or 0), picker_model=info.get("model", "")))
        except (KeyError, ValueError, TypeError) as e:
            log(f"  [stitch] candidate {i} malformed: {e}")
    return out


def _score(p: Promo) -> None:
    j = p.judge
    base = sum(getattr(j, k) * w for k, w in W.items())
    # Spoiler penalty only above 6 (some reveal is what makes promos work).
    p.final_score = round(base - max(0.0, j.spoiler_risk - 6) * 0.3, 2)


def judge_batch(batch: list[Promo], idx: BeatIndex, log=print) -> list[Promo]:
    clips = "\n\n".join(P.JUDGE_CLIP.format(id=p.id, dur=p.duration, clip=clip_script(p, idx),
                                            hook=p.hook, cliff=p.cliffhanger) for p in batch)
    try:
        data = call_json(P.JUDGE_SYSTEM, P.JUDGE_USER.format(k=len(batch), clips=clips),
                         role="judge", temperature=0.0, log=log, info=(info := {}))
    except RuntimeError as e:
        log(f"  [judge] batch failed: {str(e)[:150]}")
        FAILED.append("judge " + ",".join(p.id for p in batch))
        data, info = {}, {}
    items = _items(data, "reviews")
    reviews = {norm_id(r.get("id", "")): r for r in items if isinstance(r, dict)}
    for p in batch:
        r = reviews.get(p.id)
        try:
            p.judge = Judge(**{k: v for k, v in r.items() if k in Judge.model_fields}) if r else None
        except Exception:
            p.judge = None
        if p.judge is None:
            log(f"  [judge] no valid review for {p.id}")
            p.judge = Judge(issues="judge returned no review")
            p.flags.append("unjudged")
        p.judge_model = info.get("model", "")
        _score(p)
    return batch


def dedupe(promos: list[Promo], thr: float = 0.5) -> tuple[list[Promo], list[tuple[str, str]]]:
    kept, dropped = [], []
    for p in sorted(promos, key=lambda x: -x.final_score):
        dup = next((k for k in kept if overlap(p, k) > thr), None)
        if dup:
            dropped.append((p.id, dup.id))
        else:
            kept.append(p)
    return kept, dropped


def run(folder: str, per_episode: int = 3, stitched: int = 6, workers: int = 4,
        episodes_filter: list[int] | None = None, judge_batch_size: int = 8, log=print) -> dict:
    episodes = parse_show(folder)
    if episodes_filter:
        episodes_sel = [e for e in episodes if e.number in episodes_filter]
    else:
        episodes_sel = episodes
    idx = BeatIndex(episodes)
    log(f"Parsed {len(episodes)} episodes, {len(idx.by_id)} beats. Picking from {len(episodes_sel)}.")

    # Stage 1: per-episode picker
    with ThreadPoolExecutor(workers) as ex:
        per_ep = list(ex.map(lambda e: pick_episode(e, episodes, per_episode, log), episodes_sel))
    singles = [resolve(p, idx) for ps in per_ep for p in ps]
    log(f"Stage 1: {len(singles)} single-episode candidates")

    # Stage 1b: stitched from strongest valid singles
    valid_singles = [p for p in singles if not hard_errors(p)]
    top = sorted(valid_singles, key=lambda p: -p.picker_score)[:16]
    stitches = [resolve(p, idx) for p in stitch(top, idx, episodes, stitched, log)] if stitched and len(top) >= 2 else []
    log(f"Stage 1b: {len(stitches)} stitched candidates")

    allc = singles + stitches
    valid = [p for p in allc if not hard_errors(p)]
    rejected = [p for p in allc if hard_errors(p)]
    log(f"Validator: {len(valid)} pass, {len(rejected)} rejected")

    # Stage 2: independent judge (different model, no show context), 5 clips per call.
    # Batches are shuffled across episodes so one call doesn't see only one episode.
    import random
    order = valid[:]
    random.Random(0).shuffle(order)
    batches = [order[i:i + judge_batch_size] for i in range(0, len(order), judge_batch_size)]
    with ThreadPoolExecutor(workers) as ex:
        judged = [p for b in ex.map(lambda b: judge_batch(b, idx, log), batches) for p in b]
    # Retry clips the judge skipped, one per call.
    miss = [p for p in judged if "unjudged" in p.flags]
    if miss:
        log(f"Re-judging {len(miss)} skipped clips individually")
        for p in miss:
            p.flags.remove("unjudged")
            judge_batch([p], idx, log)

    unjudged = [p for p in judged if "unjudged" in p.flags]
    judged = [p for p in judged if "unjudged" not in p.flags]
    ranked, dups = dedupe(judged)
    for i, p in enumerate(ranked, 1):
        p.rank = i
    log(f"Dedupe: {len(ranked)} kept, {len(dups)} near-duplicates removed, {len(unjudged)} unjudged")
    return {"episodes": episodes, "index": idx, "ranked": ranked, "rejected": rejected + unjudged,
            "duplicates": dups, "failed_calls": list(FAILED)}
