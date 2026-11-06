"""Write raw runs/v1: promos.json, promos.csv, report.md, rejected.json."""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .llm import USED, model_for
from .models import clip_script
from .parser import fmt


def _segs(p) -> str:
    return " + ".join(f"Ep{s.episode} {fmt(s.start)}-{fmt(s.end)}" for s in p.segments)


def write_outputs(res: dict, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ranked, idx = res["ranked"], res["index"]

    meta = {"generated": datetime.now().isoformat(timespec="seconds"),
            "picker_model": model_for("picker"), "judge_model": model_for("judge"),
            "episodes": len(res["episodes"]), "beats": len(idx.by_id),
            "promos_ranked": len(ranked), "rejected": len(res["rejected"]),
            "duplicates_removed": len(res["duplicates"]),
            "failed_llm_calls": res.get("failed_calls", []),
            "picks_by_model": dict(Counter(p.picker_model for p in ranked + res["rejected"])),
            "judged_by_model": dict(Counter(p.judge_model for p in ranked)),
            "uncached_calls_by_model": dict(USED)}
    (out / "promos.json").write_text(json.dumps(
        {"meta": meta, "promos": [p.model_dump() for p in ranked]}, indent=2))
    (out / "rejected.json").write_text(json.dumps(
        {"rejected": [p.model_dump() for p in res["rejected"]],
         "duplicates": [{"dropped": a, "kept": b} for a, b in res["duplicates"]]}, indent=2))

    with open(out / "promos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "id", "kind", "segments", "duration_s", "final_score", "hook_score",
                    "cliff_score", "standalone", "intensity", "spoiler_risk", "would_post",
                    "hook", "cliffhanger", "why", "judge_verdict", "judge_issues", "flags", "fixes",
                    "picker_model", "judge_model"])
        for p in ranked:
            j = p.judge
            w.writerow([p.rank, p.id, p.kind, _segs(p), p.duration, p.final_score, j.hook, j.cliffhanger,
                        j.standalone, j.intensity, j.spoiler_risk, j.would_post, p.hook, p.cliffhanger,
                        p.why, j.verdict, j.issues, "; ".join(p.flags), "; ".join(p.fixes),
                        p.picker_model, p.judge_model])

    md = [f"# Promo report: {len(ranked)} ranked promos",
          "", f"Picker: `{meta['picker_model']}` | Judge: `{meta['judge_model']}` | "
          f"{meta['episodes']} episodes, {meta['beats']} beats | "
          f"{meta['rejected']} rejected by rules, {meta['duplicates_removed']} near-duplicates removed", "",
          "| # | Promo | Segments | Len | Score | Hook | Cliff | Standalone | Post? |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in ranked:
        j = p.judge
        md.append(f"| {p.rank} | {p.id} {p.title} | {_segs(p)} | {p.duration:.0f}s | {p.final_score} | "
                  f"{j.hook:g} | {j.cliffhanger:g} | {j.standalone:g} | {'yes' if j.would_post else 'no'} |")
    md.append("")
    for p in ranked:
        j = p.judge
        md += [f"## #{p.rank} {p.id}: {p.title} ({p.kind}, {p.duration:.1f}s, score {p.final_score})", "",
               f"- **Segments:** {_segs(p)}",
               f"- **Hook:** {p.hook}", f"- **Cliffhanger:** {p.cliffhanger}", f"- **Why:** {p.why}",
               f"- **Judge:** {j.verdict} " + (f"_Issue: {j.issues}_" if j.issues else ""),
               *([f"- **Auto-fixes:** {'; '.join(p.fixes)}"] if p.fixes else []),
               *([f"- **Flags:** {', '.join(p.flags)}"] if p.flags else []),
               "", "<details><summary>Clip script</summary>", "", "```", clip_script(p, idx), "```",
               "</details>", ""]
    (out / "report.md").write_text("\n".join(md))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return out
