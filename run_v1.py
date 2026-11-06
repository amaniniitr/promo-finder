"""CLI: python run_v1.py <show_folder> [--out runs/v1] [--episodes 1,2,3]"""
import argparse

from promo.pipeline import run
from promo.report import write_outputs

ap = argparse.ArgumentParser(description="Find ranked promos in a microdrama screenplay folder.")
ap.add_argument("folder", help="folder of episode .txt screenplays")
ap.add_argument("--out", default="runs/v1")
ap.add_argument("--episodes", help="comma list, e.g. 1,2,3 (default: all)")
ap.add_argument("--per-episode", type=int, default=3)
ap.add_argument("--stitched", type=int, default=6)
ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()

eps = [int(x) for x in a.episodes.split(",")] if a.episodes else None
res = run(a.folder, a.per_episode, a.stitched, a.workers, eps)
out = write_outputs(res, a.out)
print(f"\nWrote {out}/report.md, promos.json, promos.csv, rejected.json")
for p in res["ranked"][:10]:
    print(f"#{p.rank:>2} {p.final_score:>5} {p.id:<8} {p.duration:>5.1f}s  {p.title}")
