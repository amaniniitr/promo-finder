"""Measure Jev against the current LLM screen and LLM pairwise ranker. -> experiments/JEV_RESULTS.md

python experiments/jev_experiment.py [--shortlist-size 20]

A. Pointwise: Jev rubric scores on every v2 candidate, asked twice (levels low->high and high->low).
B. Pairwise: every pair of the v2 shortlist, both orders; split-half reliability, position bias, cascade.
C. External check: correlation with the blind auditor (gemma-4-31b) on the 40 clips it scored.
"""
import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo import jev  # noqa: E402
from promo.metrics import kendall_tau, mean, spearman, tie_share, topk_overlap  # noqa: E402
from promo.models import BeatIndex, Promo  # noqa: E402
from promo.parser import parse_show  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--v2", default="runs/v2_llm")
ap.add_argument("--v1", default="runs/v1")
ap.add_argument("--show", default=str(DEFAULT_SHOW))
a = ap.parse_args()

idx = BeatIndex(parse_show(a.show))
diag = json.loads(Path(a.v2, "diagnostics.json").read_text())
v2 = [Promo(**p) for p in json.loads(Path(a.v2, "promos.json").read_text())["promos"]]
cands = [Promo(**p) for p in diag["all_candidates"]]
short = [p for p in v2 if p.bt is not None]
S = diag["screen_per_sample"]
llm_screen = {i: mean(s[i] for s in S if i in s) for i in S[0]}
order = lambda ids, d: sorted(ids, key=lambda i: -d[i])
L = ["# Jev (TypeSafe System One) vs the LLM judges", "",
     f"Model `{jev.JEV_MODEL}`. All numbers below come from `experiments/jev_experiment.py`; raw answers are cached in `.cache/jev/`.", ""]

# ---------------- A. pointwise
t0 = time.time()
A1 = jev.screen(cands, idx, reverse=False)
A2 = jev.screen(cands, idx, reverse=True)
tA = time.time() - t0
ids = [p.id for p in cands]
j1, j2 = [A1[i]["weighted"] for i in ids], [A2[i]["weighted"] for i in ids]
jm = {i: (A1[i]["weighted"] + A2[i]["weighted"]) / 2 for i in ids}
lv = [llm_screen.get(i, float("nan")) for i in ids]
sid = [p.id for p in short]
sd = lambda v: st.pstdev(v)
L += ["## A. Pointwise rubric scores (all 138 candidates)", "",
      "| metric | LLM screen (3.5-flash-lite) | Jev |", "|---|---|---|",
      f"| two independent passes, Spearman | 0.55 (1 sample vs 1), 0.67 (avg-2 vs avg-2) | "
      f"{spearman(j1, j2):.2f} (levels low->high vs high->low) |",
      f"| two passes, top-10 overlap | 22% / 40% | {topk_overlap(order(ids, dict(zip(ids, j1))), order(ids, dict(zip(ids, j2))), 10):.0%} |",
      f"| tied scores | 84% | {tie_share(list(jm.values())):.0%} |",
      f"| score SD, all candidates / inside shortlist | {sd([llm_screen[i] for i in ids if i in llm_screen]):.2f} / "
      f"{sd([llm_screen[i] for i in sid]):.2f} | {sd(list(jm.values())):.2f} / {sd([jm[i] for i in sid]):.2f} |",
      f"| calls for 138 clips | 72 (batched, x4 samples) | {len(ids) * 2} (1 clip per call, x2 orders) |",
      f"| wall time | ~6 min (free-tier throttled) | {tA:.0f}s |", "",
      f"Agreement Jev vs LLM screen (Spearman): {spearman([jm[i] for i in ids], lv):.2f}.",
      "Per-criterion mean Jev confidence: " + ", ".join(
          f"{k} {mean(A1[i][k + '_conf'] for i in ids):.2f}" for k in jev.RUBRIC) + ".", ""]

# ---------------- B. pairwise
t0 = time.time()
comps = jev.all_pairs(short, idx)
tB = time.time() - t0
h1, h2 = jev.split_half(short, comps)
bt = jev.rank(short, comps, soft=True)
bth = jev.rank(short, comps, soft=False)
x, y = [h1[i] for i in sid], [h2[i] for i in sid]
agree = mean(float(c["agree"]) for c in comps)
first = mean(float(f) for c in comps for f in c["first_shown_won"])
# overlap with gemma tournament verdicts
gv = {}
for v in diag["pairwise_verdicts"]:
    gv.setdefault(frozenset((v["first"], v["second"])), []).append(v["winner"])
both = []
for c in comps:
    k = frozenset((c["a"], c["b"]))
    if k in gv and len(gv[k]) == 2 and gv[k][0] == gv[k][1]:      # gemma consistent in both orders
        both.append((c, gv[k][0]))
jev_g = mean(float((c["p"] > 0.5) == (w == c["a"])) for c, w in both) if both else float("nan")
gem_ps = json.loads(Path(a.v2, "meta.json").read_text())["pairwise"]
L += [f"## B. Pairwise on the shortlist ({len(short)} clips, all {len(comps)} pairs, both orders = {2 * len(comps)} calls)", "",
      "| metric | gemma-4-26b Swiss tournament (v2) | Jev all-pairs |", "|---|---|---|",
      f"| pairs compared | 39 (4 Swiss rounds) | {len(comps)} (every pair) |",
      f"| same winner in both orders | {gem_ps['position_consistency']:.0%} | {agree:.0%} |",
      f"| first-shown clip wins (50% = no bias) | {gem_ps['first_position_win_rate']:.0%} | {first:.0%} |",
      f"| split-half BT Spearman (order-1 answers vs order-2 answers) | 0.44 | {spearman(x, y):.2f} |",
      f"| split-half Kendall | 0.33 | {kendall_tau(x, y):.2f} |",
      f"| split-half top-10 overlap | 60% | {topk_overlap(order(sid, h1), order(sid, h2), 10):.0%} |",
      f"| split-half top-5 overlap | - | {topk_overlap(order(sid, h1), order(sid, h2), 5):.0%} |",
      f"| wall time | ~25 min | {tB:.0f}s |", "",
      f"Hard-vote BT vs soft-probability BT on the same verdicts: Spearman {spearman([bt[i] for i in sid], [bth[i] for i in sid]):.2f}.",
      f"Jev vs gemma, on the {len(both)} pairs gemma answered the same way in both orders: Jev agrees on {jev_g:.0%}.",
      f"Jev pairwise BT vs Jev pointwise score on the shortlist: Spearman {spearman([bt[i] for i in sid], [jm[i] for i in sid]):.2f}.", ""]

# cascade
rows = []
for tau in (0.0, 0.5, 0.7, 0.8, 0.9):
    acc, esc = jev.cascade(comps, tau)
    agr = [(c, w) for c, w in both if c in acc]
    rows.append(f"| {tau:.1f} | {len(acc) / len(comps):.0%} | "
                f"{(mean(float((c['p'] > 0.5) == (w == c['a'])) for c, w in agr) if agr else float('nan')):.0%} (n={len(agr)}) | "
                f"{len(esc)} |")
L += ["**Cascade (accept Jev when both orders agree and confidence >= tau, else escalate to the LLM):**", "",
      "| tau | pairs Jev settles | agreement with consistent gemma verdicts | pairs escalated |", "|---|---|---|---|", *rows, ""]

# ---------------- C. external check with the blind auditor
aud = json.loads(Path("experiments/audit_raw.json").read_text())
v1 = {p["id"]: Promo(**p) for p in json.loads(Path(a.v1, "promos.json").read_text())["promos"]}
pool = {**v1, **{p.id: p for p in v2}}
aud_clips = [(r["id"], mean(r["scores"]), r["src"]) for r in aud.values() if r["id"] in pool]
J = jev.screen([pool[i] for i, _, _ in aud_clips], idx)
aj = [J[i]["weighted"] for i, _, _ in aud_clips]
au = [s for _, s, _ in aud_clips]
v2a = [(i, s) for i, s, src in aud_clips if src == "v2" and i in llm_screen]
L += [f"## C. External check: blind auditor (gemma-4-31b) on {len(aud_clips)} clips", "",
      f"- Jev pointwise vs auditor: Spearman {spearman(aj, au):.2f}.",
      f"- LLM screen vs auditor (v2 clips only, n={len(v2a)}): Spearman "
      f"{spearman([llm_screen[i] for i, _ in v2a], [s for _, s in v2a]):.2f}; Jev on the same clips: "
      f"{spearman([J[i]['weighted'] for i, _ in v2a], [s for _, s in v2a]):.2f}.",
      f"- Mean Jev score, v1 top-20 vs v2 top-20: {mean(J[i]['weighted'] for i, _, s in aud_clips if s == 'v1'):.2f} vs "
      f"{mean(J[i]['weighted'] for i, _, s in aud_clips if s == 'v2'):.2f}.",
      "- The auditor is itself an LLM, not a human editor. Agreement measures consistency between judges, not truth.", ""]

L += ["## Cost", "", f"New Jev requests this run: {jev.USAGE['requests']}, cached: {jev.USAGE['cached']}, "
      f"input tokens {jev.USAGE['input_tokens']:,}, cost ${jev.cost_usd():.4f} at $0.042 per million input tokens.", ""]
Path("experiments/JEV_RESULTS.md").write_text("\n".join(L))
json.dump({"pointwise": {"normal": A1, "reversed": A2}, "pairwise": comps}, open("experiments/jev_raw.json", "w"), indent=1)
print("\n".join(L))
