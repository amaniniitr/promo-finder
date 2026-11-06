"""Promo finder CLI: python run.py <show_folder> [--out runs/latest] [--episodes 1,2,3] [--shortlist 24]"""
import argparse

from promo.pipeline_v2 import run_v2
from promo.report_v2 import write_v2

ap = argparse.ArgumentParser(description="Find ranked promos (v2: tag -> windows -> screen -> pairwise rank).")
ap.add_argument("folder")
ap.add_argument("--out", default="runs/latest")
ap.add_argument("--episodes", help="comma list (default: all)")
ap.add_argument("--per-episode", type=int, default=4)
ap.add_argument("--shortlist", type=int, default=20, help="clips ordered by the pairwise tournament")
ap.add_argument("--rounds", type=int, default=4, help="Swiss rounds")
ap.add_argument("--screen-samples", type=int, default=4)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--judge", choices=["auto", "jev", "llm"], default="auto",
                help="jev = TypeSafe Jev screen + all-pairs rank; llm = LLM screen + Swiss tournament; auto = jev if TYPESAFE_API_KEY set")
ap.add_argument("--escalate", action="store_true", help="with jev: send order-dependent pairs to the LLM ranker")
ap.add_argument("--cross", type=int, default=12, help="max cross-episode promos (0 = off)")
ap.add_argument("--notes", type=int, default=30, help="write hook/cliff/why notes for the top N (0 = off)")
a = ap.parse_args()

import os  # noqa: E402
from promo import llm  # noqa: E402,F401  (loads .env)
if not (os.getenv("GEMINI_API_KEY") or os.getenv("VERTEX_API_KEY")):
    raise SystemExit("No GEMINI_API_KEY or VERTEX_API_KEY in the environment or .env (see .env.example).\n"
                     "Without keys you can still look at results: python demo.py runs/new_show_test")

res = run_v2(a.folder, a.per_episode, a.shortlist, a.rounds, a.screen_samples, a.workers,
             [int(x) for x in a.episodes.split(",")] if a.episodes else None, judge=a.judge, escalate=a.escalate, cross=a.cross, notes=a.notes)
out = write_v2(res, a.out)
print(f"\nWrote {out}/report.md, promos.csv, promos.json, diagnostics.json")
for p in res["ranked"][:12]:
    print(f"#{p.rank:>2} {p.id:<8} {p.duration:>5.1f}s  W-L-T {p.record or '-':<6} screen {p.screen_score:.2f}")
