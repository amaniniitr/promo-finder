"""v2 runs/v1: promos.json/csv, report.md, diagnostics.json (everything needed to measure)."""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .llm import model_for
from .models import clip_script
from .parser import fmt


def _segs(p) -> str:
    return " + ".join(f"Ep{s.episode} {fmt(s.start)}-{fmt(s.end)}" for s in p.segments)


def write_v2(res: dict, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ranked, idx, short = res["ranked"], res["index"], {p.id for p in res["shortlist"]}
    calls = res["calls"]
    meta = {
        "version": "v2", "generated": datetime.now().isoformat(timespec="seconds"),
        "configured_models": {r: model_for(r) for r in ("tag", "screen", "rank")},
        "models_actually_used": {r: dict(Counter(c["model"] for c in calls if c["role"] == r))
                                 for r in ("tag", "screen", "rank")},
        "fallback_calls": sum(c["fallback"] for c in calls),
        "episodes": len(res["episodes"]), "candidates": len(res["candidates"]),
        "rule_violations": len(res["violations"]), "story_duplicates_removed": len(res["duplicates"]),
        "ranked": len(ranked), "shortlist_size": len(short), "pairwise": res["pairwise_stats"],
        "judge": res.get("judge", "llm"), "jev_usage": res.get("jev_usage"),
        "llm_tokens_by_model": res.get("tokens"), "posting_plan": res.get("plan"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    (out / "promos.json").write_text(json.dumps({"meta": meta, "promos": [p.model_dump() for p in ranked]}, indent=2))
    (out / "diagnostics.json").write_text(json.dumps({
        "tags": res["tags"], "window_stats": res["window_stats"], "violations": res["violations"],
        "duplicates": [{"dropped": a, "kept": b, "cosine": c} for a, b, c in res["duplicates"]],
        "screen_per_sample": res["screen"]["per_sample"],
        "pairwise_verdicts": res["tournament"]["verdicts"],
        "bt": res["tournament"]["bt"], "split_half_bt": list(res["split_half"]),
        "all_candidates": [p.model_dump() for p in res["candidates"]], "calls": calls,
        "jev_comparisons": res["tournament"].get("comparisons"),
        "escalated": res["tournament"].get("escalated")}, indent=1))

    with open(out / "promos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "id", "kind", "segments", "duration_s", "in_tournament", "bt_strength",
                    "pairwise_record", "screen_score", "screen_samples", "hook", "cliffhanger", "why",
                    "judge_verdict", "judge_issues", "spoiler_risk", "tag_model", "rank_model"])
        for p in ranked:
            j = p.judge
            w.writerow([p.rank, p.id, p.kind, _segs(p), p.duration, p.id in short, p.bt, p.record,
                        p.screen_score, " / ".join(f"{x:.2f}" for x in p.screen_samples), p.hook, p.cliffhanger, p.why,
                        j.verdict if j else "", j.issues if j else "", j.spoiler_risk if j else "",
                        p.picker_model, p.judge_model])

    md = [f"# Promo report (v2): {len(ranked)} promos, top {len(short)} ordered by pairwise tournament", "",
          (f"Judge: TypeSafe {res['jev_usage']['model']} (screen + all-pairs rank), "
           f"{res['jev_usage']['requests']} requests, ${res['jev_usage']['cost_usd']:.4f} | tag "
           f"{meta['models_actually_used']['tag']}" if res.get("judge") == "jev" else
           f"Models used: tag {meta['models_actually_used']['tag']} | screen {meta['models_actually_used']['screen']}"
           f" | rank {meta['models_actually_used']['rank']}"), "",
          f"Pairwise position consistency {res['pairwise_stats'].get('position_consistency')} | "
          f"rule violations {len(res['violations'])} | story duplicates removed {len(res['duplicates'])}", "",
          *(["## Posting plan (week 1)", "",
              *[f"{x.get('day', '?')}. **{x['id']}**: {x.get('reason', '')}" for x in res.get("plan", {}).get("plan", [])],
              "", "**Hold for later:** " + ("; ".join(f"{x['id']} ({x.get('reason', '')})"
                                                     for x in res.get("plan", {}).get("hold", [])) or "none"), ""]
             if res.get("plan") else []),
          "## All promos", "",
          "| # | Promo | Kind | Segments | Len | Pairwise W-L-T | BT | Screen | Why |", "|---|---|---|---|---|---|---|---|---|"]
    for p in ranked:
        md.append(f"| {p.rank} | {p.id} | {p.kind} | {_segs(p)} | {p.duration:.0f}s | {p.record or '-'} | "
                  f"{'' if p.bt is None else f'{p.bt:+.2f}'} | {p.screen_score:.2f} | {p.why.replace('|', '/')} |")
    md.append("")
    for p in ranked[:40]:
        j = p.judge
        md += [f"## #{p.rank} {p.id} ({p.kind}, {p.duration:.1f}s)", "",
               f"- **Segments:** {_segs(p)}", f"- **Hook:** {p.hook}", f"- **Cliffhanger:** {p.cliffhanger}",
               f"- **Why:** {p.why}" + (f" | Judge: {j.verdict}" if j else ""),
               *([f"- **Issue:** {j.issues}"] if j and j.issues else []),
               "", "<details><summary>Clip script</summary>", "", "```", clip_script(p, idx), "```", "</details>", ""]
    (out / "report.md").write_text("\n".join(md))
    return out
