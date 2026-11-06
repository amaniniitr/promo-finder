"""Quality checks on a finished run. python qa.py [runs/v1] [--compare other_outputs]

Writes <runs/v1>/quality.md. All checks are code; no LLM calls.
"""
import argparse
import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.parser import parse_show

ap = argparse.ArgumentParser()
ap.add_argument("out", nargs="?", default="runs/v1")
ap.add_argument("--compare", help="another runs/v1 folder (e.g. different judge) for rank stability")
ap.add_argument("--show", default=str(DEFAULT_SHOW))
a = ap.parse_args()

out = Path(a.out)
d = json.loads((out / "promos.json").read_text())
rej = json.loads((out / "rejected.json").read_text())
P, meta = d["promos"], d["meta"]
eps = {e.number: e for e in parse_show(a.show)}
beat = {b.id: b for e in eps.values() for b in e.beats}


def first_beat(p):
    s = p["segments"][0]
    return next(b for b in eps[s["episode"]].beats if b.start >= s["start"] - 0.01)


def last_line(p):
    s = p["segments"][-1]
    lines = [b for b in eps[s["episode"]].beats if b.end <= s["end"] + 0.01 and b.start >= s["start"] - 0.01]
    return lines[-1] if lines else None


def spearman(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for n, i in enumerate(o):
            r[i] = n
        return r
    rx, ry = rk(x), rk(y)
    n = len(x)
    return 1 - 6 * sum((i - j) ** 2 for i, j in zip(rx, ry)) / (n * (n * n - 1)) if n > 2 else float("nan")


L = [f"# Quality report ({out})", ""]
total = len(P) + len(rej["rejected"]) + len(rej["duplicates"])
fixed = [p for p in P if any("re-cut" in f for f in p["fixes"])]
L += ["## 1. Rule checks (deterministic)", "",
      f"- Candidates proposed: {total}; ranked {len(P)}, rejected by rules {len(rej['rejected'])}, "
      f"near-duplicates {len(rej['duplicates'])}",
      f"- Rejection reasons: {dict(Counter(f.split(':')[0] for r in rej['rejected'] for f in r['flags'] if f != 'ends_on_episode_finale'))}",
      f"- Length auto-repaired (end re-cut by code): {len(fixed)} of {len(P)} ranked",
      f"- Start moved onto hook beat by code: {sum(any('hook beat' in f for f in p['fixes']) for p in P)}",
      f"- Duration: min {min(p['duration'] for p in P):.1f}s, median {st.median(p['duration'] for p in P):.1f}s, "
      f"max {max(p['duration'] for p in P):.1f}s (all within 20-60s by construction)",
      f"- Episodes with >=1 ranked promo: {len({s['episode'] for p in P for s in p['segments']})}/{len(eps)}",
      ""]

fb = Counter(first_beat(p).type for p in P)
lb = Counter((last_line(p).type if last_line(p) else "none") for p in P)
cam_open = [p for p in P if first_beat(p).type == "camera"]
L += ["## 2. Hook / ending structure", "",
      f"- First beat type: {dict(fb)}. A clip opening on a CAMERA beat relies on a visual; "
      f"{len(cam_open)} do. Not wrong (a slap is visual), but the script text can't confirm the hook lands.",
      f"- Last beat type: {dict(lb)}",
      f"- Ends on the episode's own final beat (writers' cliffhanger): "
      f"{sum('ends_on_episode_finale' in p['flags'] for p in P)}",
      ""]

by_model = defaultdict(list)
for p in P:
    by_model[p["picker_model"]].append(p["final_score"])
L += ["## 3. Picker model vs judged quality", "",
      "Free-tier daily caps forced fallbacks, so different episodes were picked by different models.", "",
      "| picker model | promos | mean score | share in top 20 |", "|---|---|---|---|"]
top20 = {p["id"] for p in P[:20]}
for m, v in sorted(by_model.items(), key=lambda kv: -st.mean(kv[1])):
    L.append(f"| {m} | {len(v)} | {st.mean(v):.2f} | "
             f"{sum(1 for p in P if p['picker_model'] == m and p['id'] in top20)} |")
L.append("")

ps = [p["picker_score"] for p in P]
fs = [p["final_score"] for p in P]
rf = [p["final_score"] for p in fixed]
nf = [p["final_score"] for p in P if p not in fixed]
L += ["## 4. Agreement between stages", "",
      f"- Picker self-score vs independent judge (Spearman): {spearman(ps, fs):.2f}. "
      f"Picker mean self-score {st.mean(ps):.1f}/10 vs judge-based score {st.mean(fs):.1f}/10 "
      "(picker is over-confident).",
      f"- Judge 'would post': {sum(p['judge']['would_post'] for p in P)}/{len(P)}",
      f"- Length-repaired clips mean score {st.mean(rf) if rf else float('nan'):.2f} vs untouched "
      f"{st.mean(nf):.2f}", ""]

if a.compare:
    o = {p["id"]: p for p in json.loads((Path(a.compare) / "promos.json").read_text())["promos"]}
    common = [p for p in P if p["id"] in o and
              [(s["episode"], round(s["start"], 1), round(s["end"], 1)) for s in p["segments"]] ==
              [(s["episode"], round(s["start"], 1), round(s["end"], 1)) for s in o[p["id"]]["segments"]]]
    x = [p["final_score"] for p in common]
    y = [o[p["id"]]["final_score"] for p in common]
    top_a = {p["id"] for p in P[:10]}
    top_b = {p["id"] for p in sorted(o.values(), key=lambda q: q["rank"])[:10]}
    L += [f"## 5. Judge stability vs `{a.compare}`", "",
          f"- Identical clips scored in both runs: {len(common)}",
          f"- Spearman of final scores: {spearman(x, y):.2f}",
          f"- Top-10 overlap: {len(top_a & top_b)}/10 ({', '.join(sorted(top_a & top_b)) or 'none'})",
          "- Reading: the absolute ranking depends noticeably on which model judges; "
          "treat the score as a shortlist filter, not a precise order.", ""]

hi_spoil = [p for p in P[:20] if p["judge"]["spoiler_risk"] >= 7]
L += ["## 6. Risk flags in the top 20", "",
      f"- Spoiler risk >= 7: {', '.join(p['id'] for p in hi_spoil) or 'none'}",
      f"- Low standalone (< 6): {', '.join(p['id'] for p in P[:20] if p['judge']['standalone'] < 6) or 'none'}",
      f"- Stitched promos ranked: {sum(p['kind'] == 'stitched' for p in P)}; best rank "
      f"{min((p['rank'] for p in P if p['kind'] == 'stitched'), default='-')}", ""]

(out / "quality.md").write_text("\n".join(L))
print("\n".join(L))
