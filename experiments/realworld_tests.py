"""Real-life tests with ground truth that does NOT come from an LLM.  -> experiments/REALWORLD_RESULTS.md

Test 1  Writer cliffhangers (no new calls). Every episode was written to end on a cliffhanger
        (final beats = sting / cut to black). Does the tagger, on its own, mark a cliff beat in the
        last 8 s of the episode? The pipeline's automatic "episode end" cliff is excluded.
        Baseline = a tagger that marks the same number of beats uniformly at random.
Test 2  Planted hooks (new tag calls). In 30 real episodes we overwrite one calm dialogue line
        in the middle of the episode with a known shocking line, and another calm line with a
        neutral decoy of similar length. Ground truth is known by construction.
        Metric: planted line tagged as a hook (recall), decoy tagged (false positive), and whether
        a final candidate window starts on the planted hook. Baseline = random tags.

python experiments/realworld_tests.py [--planted 30]
"""
import argparse
import json
import math
import random
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.models import BeatIndex  # noqa: E402
from promo.moments import build_windows, tag_episode  # noqa: E402
from promo.parser import parse_episode, parse_show  # noqa: E402

SHOW = DEFAULT_SHOW
ap = argparse.ArgumentParser()
ap.add_argument("--planted", type=int, default=30)
ap.add_argument("--end-window", type=float, default=8.0)
ap.add_argument("--out", default="experiments/REALWORLD_RESULTS.md")
a = ap.parse_args()


def wilson(k, n, z=1.96):
    if not n:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def binom_p_greater(k, n, p0):
    """One-sided P(X >= k) for X ~ Bin(n, p0)."""
    return sum(math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1))


def ci(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} (95% CI {lo:.0%}-{hi:.0%})"


eps = parse_show(SHOW)
idx = BeatIndex(eps)
L = ["# Real-life tests (ground truth not produced by an LLM)", ""]

# ------------------------------------------------------------ Test 1
L += [f"## Test 1: does the tagger find the writers' episode-ending cliffhanger? (last {a.end_window:g}s)", "",
      "| tagger | episodes hit | random-tagger expectation | one-sided p |", "|---|---|---|---|"]
for name, path in [("v2: gemini-3.1-flash-lite (free)", "runs/v2_llm/diagnostics.json"),
                   ("v3: vertex gemini-3.5-flash", "runs/v3_final/diagnostics.json")]:
    tags = json.loads(Path(path).read_text())["tags"]
    hits, exp = 0, []
    for e in eps:
        t = tags.get(str(e.number)) or tags.get(e.number)
        if not t:
            continue
        own = [c for c in t["cliffs"] if not c.get("auto")]
        end0 = e.duration - a.end_window
        hits += any(idx.get(c["beat"]).end >= end0 for c in own)
        elig = [b for b in e.beats if b.type in ("dialogue", "action", "sfx")]
        f = sum(b.end >= end0 for b in elig) / len(elig)
        exp.append(1 - (1 - f) ** max(1, len(own)))
    p0 = sum(exp) / len(exp)
    L.append(f"| {name} | {ci(hits, len(exp))} | {p0:.0%} | {binom_p_greater(hits, len(exp), p0):.1e} |")
L += ["", "A hit means the model independently labelled a beat inside the writers' final beat window as a "
      "cliffhanger. The writers' intent is the ground truth here.", ""]

# ------------------------------------------------------------ Test 2
PLANTS = ["You poisoned my mother, and I watched you do it.", "Kneel, or I will cut her throat in front of you.",
          "The man you are about to marry murdered your father.", "Slap her again and see what happens.",
          "I have the letter. Everyone will know you are a fraud tonight.", "Your husband is alive. I buried an empty coffin.",
          "Lock the doors. Nobody leaves this room breathing.", "She is not your daughter. She never was."]
DECOYS = ["The carriage will be ready after breakfast tomorrow.", "Please bring more candles to the east hall.",
          "The weather has been mild for this time of year.", "I left the ledger on the desk by the window."]
rng = random.Random(42)
pick = rng.sample(eps, min(a.planted, len(eps)))
tmp = Path(tempfile.mkdtemp(prefix="planted_"))
truth = {}
for e in pick:
    src = (SHOW / e.source_file).read_text(encoding="utf-8")
    calm = [b for b in e.beats if b.type == "dialogue" and 0.25 * e.duration < b.start < 0.75 * e.duration
            and len(b.text) > 15 and not re.search(r"scream|shout|furious|enraged|hyster", (b.emotion or ""), re.I)]
    if len(calm) < 2:
        continue
    pb, db = rng.sample(calm, 2)
    plant, decoy = rng.choice(PLANTS), rng.choice(DECOYS)
    for b, new, emo in ((pb, plant, "Shouting, Venomous"), (db, decoy, "Calm")):
        # replace the line text and its emotion label in the raw script
        src = src.replace(f'"{b.text}"', f'"{new}"', 1).replace(f"{b.speaker} ({b.emotion}):", f"{b.speaker} ({emo}):", 1) \
            if b.emotion else src.replace(f'"{b.text}"', f'"{new}"', 1)
    (tmp / e.source_file).write_text(src, encoding="utf-8")
    truth[e.number] = (pb.idx, db.idx)

peps = parse_show(tmp)
pidx = BeatIndex(peps)
rec = fp = win = n = 0
exp_r, exp_f = [], []
for pe in peps:
    if pe.number not in truth:
        continue
    pi, di = truth[pe.number]
    assert pidx.eps[pe.number].beats[pi].text in PLANTS, "plant not parsed"
    t = tag_episode(pe, peps, pidx, log=lambda *x: None)
    hook_idx = {pidx.get(h["beat"]).idx for h in t["hooks"]}
    rec += pi in hook_idx
    fp += di in hook_idx
    ws, _ = build_windows(pe, t, pidx, 4)
    win += any(w.hook_beat == pe.beats[pi].id for w in ws)
    elig = sum(b.type in ("dialogue", "action", "sfx") for b in pe.beats)
    k = max(1, len(t["hooks"]))
    exp_r.append(k / elig)
    n += 1
p0 = sum(exp_r) / len(exp_r)
L += [f"## Test 2: planted hooks in {n} real episodes (tagger: `{t['model']}`)", "",
      "| metric | result | random tagger |", "|---|---|---|",
      f"| planted shocking line tagged as a hook | {ci(rec, n)} | {p0:.0%} |",
      f"| neutral decoy tagged as a hook | {ci(fp, n)} | {p0:.0%} |",
      f"| a final candidate window starts on the planted hook | {ci(win, n)} | - |", "",
      f"Recall vs random: one-sided p = {binom_p_greater(rec, n, p0):.1e}. "
      "The plant competes with every real hook in the episode (up to 6 hooks are tagged), so recall below 100% "
      "can mean the episode already had stronger moments, not a miss. Decoy false positives are a clean error rate.", ""]
shutil.rmtree(tmp)
Path(a.out).write_text("\n".join(L))
print("\n".join(L))
