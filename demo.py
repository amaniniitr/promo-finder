"""No-key demo: show the final ranked promos and posting plan from the saved full-pack run.
python demo.py [run_folder]        (default runs/v3_final; or runs/new_show_test, which is synthetic)"""
import json
import sys
from pathlib import Path

from promo.parser import fmt

run = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/v3_final")
if not (run / "promos.json").exists():
    sys.exit(f"{run}/promos.json not found. The full-pack outputs are shared separately (confidential); "
             "try: python demo.py runs/new_show_test")
d = json.loads((run / "promos.json").read_text())
meta, P = d["meta"], d["promos"]
print(f"{run}: {meta['candidates']} candidates -> {meta['ranked']} ranked, {meta['rule_violations']} rule violations, "
      f"judge {meta.get('judge')}\n")
for p in P[:10]:
    segs = " + ".join(f"Ep{s['episode']} {fmt(s['start'])}-{fmt(s['end'])}" for s in p["segments"])
    print(f"#{p['rank']:>2} {p['id']:<11} {p['kind']:<8} {p['duration']:>4.0f}s  {segs}\n"
          f"     hook: {p['hook']}\n     cliff: {p['cliffhanger']}\n     why: {p['why']}\n")
plan = meta.get("posting_plan") or {}
if plan.get("plan"):
    print("Posting plan:")
    for x in plan["plan"]:
        print(f"  day {x.get('day')}: {x['id']}  {x.get('reason', '')}")
