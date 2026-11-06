"""Turn a pipeline result (or saved run) into the JSON the web viewer renders."""
from __future__ import annotations

from .models import BeatIndex, Promo, clip_script

META_KEYS = ["candidates", "rule_violations", "story_duplicates_removed", "ranked", "shortlist_size", "pairwise",
             "posting_plan", "episodes", "judge", "generated"]


def promo_rows(promos: list[dict], idx: BeatIndex, titles: dict | None = None) -> list[dict]:
    out = []
    for p in promos:
        j = p.get("judge") or {}
        out.append({"rank": p["rank"], "id": p["id"], "kind": p["kind"], "duration": p["duration"],
                    "title": (titles or {}).get(p["id"], ""),
                    "segments": [{"episode": s["episode"], "start": s["start"], "end": s["end"]} for s in p["segments"]],
                    "hook": p["hook"], "cliffhanger": p["cliffhanger"], "why": p["why"], "record": p.get("record", ""),
                    "bt": p.get("bt"), "screen": p.get("screen_score"),
                    "scores": {k: j.get(k) for k in ("hook", "cliffhanger", "standalone", "intensity", "spoiler_risk")},
                    "script": clip_script(Promo(**p), idx)})
    return out


def bundle(meta: dict, promos: list[dict], idx: BeatIndex, titles: dict | None = None) -> dict:
    m = {k: meta.get(k) for k in META_KEYS}
    m["jev_cost_usd"] = (meta.get("jev_usage") or {}).get("cost_usd")
    return {"meta": m, "promos": promo_rows(promos, idx, titles)}
