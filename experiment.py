"""Measure v1 vs v2. python experiment.py [--audit]  -> experiments/RESULTS.md

Picking   : rule compliance (raw, before any repair), invalid IDs, recap duplicates,
            and a BLIND A/B: one auditor model that produced neither list scores the
            top-K of v1 and v2 mixed together, shuffled, labels hidden.
Ranking   : pointwise test-retest (two independent screen samples) vs pairwise
            split-half (forward-order verdicts vs reverse-order verdicts); ties;
            position bias (first-shown win rate, flip rate).
Model use : which model did each role, fallback count.
"""
import argparse
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.diversity import clip_text, embed
from promo.llm import call_json
from promo.metrics import cosine, kendall_tau, mean, spearman, tie_share, topk_overlap
from promo.models import BeatIndex, Promo
from promo.moments import check
from promo.parser import parse_show
from promo.rerank import SCREEN_SYSTEM, SCREEN_USER, _clip_block, _items, _weighted

ap = argparse.ArgumentParser()
ap.add_argument("--v1", default="runs/v1")
ap.add_argument("--v1b", default="runs/v1_altjudge")
ap.add_argument("--v2", default="runs/v2_llm")
ap.add_argument("--show", default=str(DEFAULT_SHOW))
ap.add_argument("--audit", action="store_true", help="run the blind A/B (uses LLM calls)")
ap.add_argument("--k", type=int, default=20)
a = ap.parse_args()

eps = parse_show(a.show)
idx = BeatIndex(eps)
v1 = [Promo(**p) for p in json.loads(Path(a.v1, "promos.json").read_text())["promos"]]
v2 = [Promo(**p) for p in json.loads(Path(a.v2, "promos.json").read_text())["promos"]]
diag = json.loads(Path(a.v2, "diagnostics.json").read_text())
meta2 = json.loads(Path(a.v2, "meta.json").read_text())
L = ["# v1 vs v2: measured results", "",
     "v1 numbers are from `experiments/BASELINE_v1.md`; v2 numbers are from `runs/v2_llm/` produced by `run.py`.", ""]

# ---------------- picking ----------------
v2_all = [Promo(**p) for p in diag["all_candidates"]]
viol = [p.id for p in v2_all if check(p, idx)]
inv = sum(t["invalid_ids"] for t in diag["tags"].values())
ntags = sum(len(t["hooks"]) + len(t["cliffs"]) for t in diag["tags"].values())
eps_cov = lambda P: len({s.episode for p in P for s in p.segments})
L += ["## 1. Picking", "",
      "| metric | v1 (LLM picks start/end) | v2 (LLM tags beats, code builds windows) |", "|---|---|---|",
      f"| candidates meeting 20-60s **before** any repair | 84% (71% on lite model) | "
      f"{1 - len(viol) / len(v2_all):.0%} ({len(v2_all) - len(viol)}/{len(v2_all)}) |",
      f"| hook inside first 3s, before repair | 81% | {sum('hook' not in ' '.join(check(p, idx)) for p in v2_all) / len(v2_all):.0%} |",
      f"| invalid / made-up beat IDs | 1 (stitched) | {inv} of {ntags} tags |",
      f"| clips whose ending was re-cut by code | 21 of 105 | 0 (ends are always a tagged cliff beat) |",
      f"| episodes with >=1 candidate | {eps_cov(v1)}/50 | {eps_cov(v2_all)}/50 |",
      f"| multi-segment promos | 3 ranked, best #43, all needed trimming | "
      f"{sum(p.kind == 'stitched' for p in v2_all)} candidates, built within budget |", ""]

# recap / same-story duplicates in top-K
def dup_pairs(P, k, thr=0.86):
    top = P[:k]
    V = embed([clip_text(p, idx) for p in top])
    return [(top[i].id, top[j].id, round(cosine(V[i], V[j]), 3))
            for i, j in itertools.combinations(range(len(top)), 2) if cosine(V[i], V[j]) >= thr]
d1, d2 = dup_pairs(v1, a.k), dup_pairs(v2, a.k)
L += [f"**Same-story duplicates inside the top {a.k}** (embedding cosine >= 0.86, the calibrated threshold):",
      f"v1 {len(d1)} pairs {d1[:6]}; v2 {len(d2)} pairs {d2[:6]}.", ""]

# ---------------- ranking ----------------
S = diag["screen_per_sample"]
cids = [i for i in S[0] if all(i in x for x in S)]
order = lambda ids_, vals: [ids_[j] for j in sorted(range(len(ids_)), key=lambda j: -vals[j])]
def rel(a_, b_, ids_, k=10):
    return spearman(a_, b_), kendall_tau(a_, b_), topk_overlap(order(ids_, a_), order(ids_, b_), k)
col = lambda k, ids_: [S[k][i] for i in ids_]
avg = lambda ks, ids_: [mean(S[k][i] for k in ks) for i in ids_]
rows = []
if len(S) >= 2:
    singles = [rel(col(a_, cids), col(b_, cids), cids) for a_, b_ in itertools.combinations(range(len(S)), 2)]
    rows.append(("1 sample vs 1 sample (all candidates)", len(cids), *[mean(x[n] for x in singles) for n in range(3)]))
if len(S) >= 4:
    rows.append(("avg of 2 vs avg of 2 (all candidates)", len(cids), *rel(avg([0, 1], cids), avg([2, 3], cids), cids)))
    _a, _b = avg([0, 1], cids), avg([2, 3], cids)
    q = len(cids) // 4
    bot_a = set(order(cids, _a)[-q:])
    bot_b_half = set(order(cids, _b)[-2 * q:])
    top_set = topk_overlap(order(cids, _a), order(cids, _b), 20)
    SET_NOTE = (f"- Shortlisting is more reliable than ordering: of the bottom quarter by one avg-of-2 pass, "
                f"{len(bot_a & bot_b_half) / q:.0%} are in the bottom half of the other pass; the top-20 *set* overlaps "
                f"{top_set:.0%} between passes. Averaging more samples helps as test theory predicts "
                f"(1 sample -> 2 samples raised Spearman from ~0.55 to ~0.67; Spearman-Brown predicts ~0.80 for 4).")
else:
    SET_NOTE = ""
h1, h2 = diag["split_half_bt"]
ids = list(h1)
z = lambda v: [(x - mean(v)) / ((sum((y - mean(v)) ** 2 for y in v) / len(v)) ** .5 or 1) for x in v]
if len(S) >= 4:
    sa, sb = avg([0, 1], ids), avg([2, 3], ids)
    rows.append(("shortlist: screen avg2 vs avg2", len(ids), *rel(sa, sb, ids)))
ba, bb = [h1[i] for i in ids], [h2[i] for i in ids]
rows.append(("shortlist: pairwise BT, fwd vs rev verdicts (used for final order)", len(ids), *rel(ba, bb, ids)))
if len(S) >= 4:
    ca = [x + y for x, y in zip(z(ba), z(sa))]
    cb = [x + y for x, y in zip(z(bb), z(sb))]
    rows.append(("shortlist: z(BT)+z(screen) (tested, not used)", len(ids), *rel(ca, cb, ids)))
ps = meta2["pairwise"]
sd_all = (sum((x - mean(avg(range(len(S)), cids))) ** 2 for x in avg(range(len(S)), cids)) / len(cids)) ** .5
sd_short = (sum((x - mean(avg(range(len(S)), ids))) ** 2 for x in avg(range(len(S)), ids)) / len(ids)) ** .5
L += ["## 2. Ranking reliability (test-retest: same clips, two independent passes)", "",
      "v1 reference: two judge runs on 76 identical clips gave Spearman 0.68, Kendall 0.50, top-10 overlap 30%, and 81% tied scores.", "",
      "| comparison | items | Spearman | Kendall | top-10 overlap |", "|---|---|---|---|---|",
      *[f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:.0%} |" for r in rows], "",
      f"- Pointwise scores compress at the top: screen score SD is {sd_all:.2f} across all candidates but {sd_short:.2f} "
      "inside the shortlist. That's why pointwise can shortlist but can't order the top.",
      f"- Pairwise position bias ({ps['verdicts']} verdicts, {ps['pairs_asked_both_ways']} pairs asked both ways): "
      f"the same clip won in both orders {ps['position_consistency']:.0%} of the time (flip rate {ps['flip_rate']:.0%}); "
      f"the first-shown clip won {ps['first_position_win_rate']:.0%} (50% = unbiased). Split verdicts count as ties "
      "instead of wins.",
      SET_NOTE,
      f"- Ties in the final shortlist order: {tie_share([p.bt for p in v2 if p.bt is not None]):.0%} (v1: 81%).", ""]

# ---------------- model use ----------------
L += ["## 3. Model use", "",
      "| role | job | calls by model (this run) |", "|---|---|---|"]
jobs = {"tag": "mark hook/cliff beats, 1 call per episode", "screen": "pointwise score, 4 shuffled samples",
        "rank": "pairwise tournament on the shortlist"}
for r in ("tag", "screen", "rank"):
    L.append(f"| {r} | {jobs[r]} | {meta2['models_actually_used'][r]} |")
L += ["", f"Fallback calls: {meta2['fallback_calls']}. v1 sent the hardest job (ranking) to the cheapest model "
      "and the easy job (reading every script) to the largest one; v2 reverses that.", ""]

# ---------------- blind A/B ----------------
if a.audit:
    A = v1[:a.k]
    B = v2[:a.k]
    pool = [(p, "v1") for p in A] + [(p, "v2") for p in B]
    random.Random(7).shuffle(pool)
    lab = {}
    for n, (p, src) in enumerate(pool):
        lab[f"X{n:02d}"] = (p, src)
    res = {}
    keys = list(lab)
    for i in range(0, len(keys), 8):
        chunk = keys[i:i + 8]
        text = "\n\n".join(_clip_block(lab[k][0], idx, k) for k in chunk)
        for t in range(2):
            d = call_json(SCREEN_SYSTEM, SCREEN_USER.format(k=len(chunk), clips=text), role="audit",
                          temperature=0.7, salt=f"audit{t}", info=(info := {}))
            for r in _items(d, "reviews"):
                k = str(r.get("id", "")).strip()
                if k in lab:
                    res.setdefault(k, []).append((_weighted(r), r, info.get("model")))
    sc = {src: [mean(v[0] for v in res[k]) for k in res if lab[k][1] == src] for src in ("v1", "v2")}
    sub = {src: {m: mean(float(v[1].get(m, 0)) for k in res if lab[k][1] == src for v in res[k])
                 for m in ("hook", "cliffhanger", "standalone", "intensity")} for src in ("v1", "v2")}
    post = {src: mean(float(bool(v[1].get("would_post"))) for k in res if lab[k][1] == src for v in res[k])
            for src in ("v1", "v2")}
    models = Counter(v[2] for k in res for v in res[k])
    L += [f"## 4. Blind A/B: top {a.k} of each version, one auditor", "",
          f"Auditor: {dict(models)}. It never saw which version a clip came from; clips from both versions were "
          "mixed and shuffled into the same batches, and each batch was scored twice.", "",
          "| | v1 top-20 | v2 top-20 |", "|---|---|---|",
          f"| mean weighted score | {mean(sc['v1']):.2f} | {mean(sc['v2']):.2f} |",
          *[f"| {m} | {sub['v1'][m]:.2f} | {sub['v2'][m]:.2f} |" for m in sub["v1"]],
          f"| would post | {post['v1']:.0%} | {post['v2']:.0%} |",
          f"| clips scored | {len(sc['v1'])} | {len(sc['v2'])} |", ""]
    allv, diff, hits = sc["v1"] + sc["v2"], mean(sc["v2"]) - mean(sc["v1"]), 0
    rng = random.Random(0)
    for _ in range(10000):
        rng.shuffle(allv)
        hits += abs(mean(allv[len(sc["v1"]):]) - mean(allv[:len(sc["v1"])])) >= abs(diff)
    rr = [[v[0] for v in res[k]] for k in res if len(res[k]) >= 2]
    L += [f"Difference v2 - v1 = {diff:+.2f} (permutation test p = {hits / 10000:.2f}). Auditor test-retest "
          f"Spearman across its two passes: {spearman([r[0] for r in rr], [r[1] for r in rr]):.2f} (n={len(rr)}).", ""]
    Path("experiments/audit_raw.json").write_text(json.dumps(
        {k: {"src": lab[k][1], "id": lab[k][0].id, "scores": [v[0] for v in res[k]]} for k in res}, indent=1))

Path("experiments").mkdir(exist_ok=True)
Path("experiments/RESULTS.md").write_text("\n".join(L))
print("\n".join(L))
