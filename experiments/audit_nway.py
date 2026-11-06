"""Blind N-way audit: one auditor model scores the top-K of several output folders, mixed and shuffled,
labels hidden, each batch twice. Writes experiments/AUDIT_<name>.md.

PROMO_AUDIT_MODEL=gemini/gemma-4-31b-it python experiments/audit_nway.py runs/v1 runs/v2_llm runs/v2_jev
"""
import itertools
import json
import os
from concurrent.futures import ThreadPoolExecutor
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.llm import call_json  # noqa: E402
from promo.metrics import mean, spearman  # noqa: E402
from promo.models import BeatIndex, Promo  # noqa: E402
from promo.parser import parse_show  # noqa: E402
from promo.rerank import SCREEN_SYSTEM, SCREEN_USER, _clip_block, _items, _weighted, norm_id  # noqa: E402

K = 20
dirs = sys.argv[1:] or ["runs/v1", "runs/v2_llm", "runs/v2_jev"]
idx = BeatIndex(parse_show(DEFAULT_SHOW))
seg = lambda p: tuple((s.episode, round(s.start, 1), round(s.end, 1)) for s in p.segments)

# A clip picked by several systems is scored once and counted for each.
clips, members = {}, {d: [] for d in dirs}
for d in dirs:
    for p in [Promo(**x) for x in json.loads(Path(d, "promos.json").read_text())["promos"][:K]]:
        clips.setdefault(seg(p), p)
        members[d].append(seg(p))
keys = list(clips)
random.Random(11).shuffle(keys)
label = {k: f"X{n:02d}" for n, k in enumerate(keys)}
scores = {k: [] for k in keys}
used = Counter()
SALT = os.getenv("AUDIT_SALT", "nway31")


def run(job):
    chunk, t = job
    text = "\n\n".join(_clip_block(clips[k], idx, label[k]) for k in chunk)
    info = {}
    d = call_json(SCREEN_SYSTEM, SCREEN_USER.format(k=len(chunk), clips=text), role="audit",
                  temperature=0.7, salt=f"{SALT}-{t}", info=info, max_attempts=12)
    return chunk, d, info.get("model")


jobs = [(keys[i:i + 8], t) for i in range(0, len(keys), 8) for t in range(2)]
with ThreadPoolExecutor(int(os.getenv("AUDIT_WORKERS", "1"))) as ex:
    for n, (chunk, d, model) in enumerate(ex.map(run, jobs), 1):
        used[model] += 1
        back = {norm_id(r.get("id", "")): r for r in _items(d, "reviews")}
        for k in chunk:
            r = back.get(label[k])
            if r:
                scores[k].append((_weighted(r), r))
        print(f"call {n}/{len(jobs)}")

mean_of = lambda k: mean(s for s, _ in scores[k]) if scores[k] else float("nan")
L = [f"# Blind audit of the top {K} from {', '.join(dirs)}", "",
     f"Auditor {dict(used)}. {len(keys)} distinct clips (clips picked by more than one system are scored once). "
     "Labels hidden, shuffled, each batch scored twice.", "",
     "| system | mean score | hook | cliffhanger | standalone | intensity | would post | n |", "|---|---|---|---|---|---|---|---|"]
for d in dirs:
    ks = [k for k in members[d] if scores[k]]
    sub = lambda m: mean(float(r.get(m, 0)) for k in ks for _, r in scores[k])
    post = mean(float(bool(r.get("would_post"))) for k in ks for _, r in scores[k])
    L.append(f"| {d} | {mean(mean_of(k) for k in ks):.2f} | {sub('hook'):.2f} | {sub('cliffhanger'):.2f} | "
             f"{sub('standalone'):.2f} | {sub('intensity'):.2f} | {post:.0%} | {len(ks)} |")
L.append("")
rng = random.Random(0)
for a, b in itertools.combinations(dirs, 2):
    xa = [mean_of(k) for k in members[a] if scores[k]]
    xb = [mean_of(k) for k in members[b] if scores[k]]
    diff, pool, hits = mean(xb) - mean(xa), xa + xb, 0
    for _ in range(10000):
        rng.shuffle(pool)
        hits += abs(mean(pool[len(xa):]) - mean(pool[:len(xa)])) >= abs(diff)
    L.append(f"- {b} - {a}: {diff:+.2f} (permutation p = {hits / 10000:.2f}); "
             f"shared clips: {len(set(members[a]) & set(members[b]))}")
rr = [[s for s, _ in scores[k]] for k in keys if len(scores[k]) >= 2]
L += [f"- Auditor test-retest Spearman: {spearman([r[0] for r in rr], [r[1] for r in rr]):.2f} (n={len(rr)}).", ""]
name = "_".join(Path(d).name for d in dirs) + ("" if SALT == "nway31" else f"_{SALT}")
Path(f"experiments/AUDIT_{name}.md").write_text("\n".join(L))
print("\n".join(L))
