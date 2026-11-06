"""TypeSafe Jev integration (System One model: typed answers + calibrated probabilities, no text).

Why Jev here (measured problems in experiments/ANALYSIS.md):
  * pointwise LLM scores are integers, so the shortlist is full of ties and the order doesn't reproduce;
  * the free-tier pairwise ranker (gemma) flipped 32% of verdicts when the order was swapped;
  * the strong LLM is rate-limited, so we could only afford a 4-round Swiss tournament.
Jev returns a probability distribution per question (Score: expected level; Choice: P(A), P(B)),
answers in ~0.3s, and costs $0.042 per million input tokens (docs.typesafe.ai/models). That makes
it affordable to compare EVERY pair on the shortlist, in both orders.

Its documented weak spots (docs.typesafe.ai/model-jaggedness) shape the design:
  * "Choice option order: leans toward the option that comes first" -> every pair is asked both ways
    and the two probabilities are averaged.
  * "Large state full of irrelevant detail" -> state holds only the clip script(s), named fields.
  * "Math and numbers" -> durations and arithmetic stay in code; Jev only judges meaning.
  * Literal reading -> each rubric level is described explicitly.

Cascade (JEV-as-a-Judge, arXiv 2609.26550): accept Jev's pairwise verdict when both orders agree and
confidence is high; escalate the rest to the generative LLM ranker.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path

from dotenv import load_dotenv

from .llm import CACHE_DIR
from .models import BeatIndex, Promo, clip_script

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

JEV_MODEL = os.getenv("PROMO_JEV_MODEL", "jev-1.14.0")  # pinned version, per TypeSafe's advice on thresholds
_CACHE = CACHE_DIR / "jev"
_CACHE.mkdir(parents=True, exist_ok=True)
USAGE = {"requests": 0, "cached": 0, "input_tokens": 0, "seconds": 0.0}
_lock = threading.Lock()
_client = None

# ---------------------------------------------------------------- rubric (pointwise)
W = {"hook": 0.30, "cliffhanger": 0.30, "standalone": 0.20, "intensity": 0.20}
RUBRIC = {
    "hook": ("How strongly do the first 3 seconds of `clip` (timestamps 0-3s) make a cold TikTok viewer stop scrolling?",
             ["Quiet setup, establishing shot or calm talk; nothing grabs attention",
              "Mild curiosity; something is happening but it is not urgent",
              "Clear conflict or strong emotion is visible immediately",
              "A shocking line, threat, insult, or reveal lands immediately",
              "Violence, a scream, or a public humiliation lands immediately; impossible to scroll past"]),
    "cliffhanger": ("How strongly does the END of `clip` leave the viewer needing to know what happens next?",
                    ["Ends resolved or calm; no open question",
                     "Ends with a weak or vague open question",
                     "Ends on a clear unresolved question",
                     "Ends mid-threat, mid-reveal or on a decision not yet made",
                     "Cuts at the peak of danger or a reveal about to land; the viewer must see the next episode"]),
    "standalone": ("How well can a stranger who never saw the show follow who is who and what is at stake in `clip`?",
                   ["Confusing without prior episodes",
                    "Partly understandable; key relationships are unclear",
                    "Understandable; stakes are mostly clear",
                    "Fully clear who wants what and why it matters"]),
    "intensity": ("How intense is the emotional conflict, power shift or reversal in `clip`?",
                  ["Flat", "Mild tension", "Clear conflict", "Strong conflict or reversal", "Explosive conflict or shocking reversal"]),
    "spoiler": ("How much does `clip` give away a major twist of the story?",
                ["Gives nothing away", "Hints at a twist", "Reveals a mid-season twist", "Reveals a major twist or the ending"]),
}

PAIR_INSTRUCTIONS = ("Two promo clips from the same vertical drama: `clip_A` and `clip_B`. A cold viewer scrolling TikTok "
                     "has never seen the show. Which clip would make MORE such viewers stop in the first 3 seconds, "
                     "understand the conflict without context, and need to see what happens next? "
                     "Ignore clip length and which clip is listed first.")


def _get_client():
    global _client
    if _client is None:
        from typesafe_sdk import RetryPolicy, TypeSafeClient
        if not os.getenv("TYPESAFE_API_KEY"):
            raise RuntimeError("TYPESAFE_API_KEY not set (put it in .env)")
        _client = TypeSafeClient(model=JEV_MODEL, retry=RetryPolicy(max_retries=6, backoff_max=20.0, timeout=60.0))
    return _client


def ask(state: dict, questions: dict, log=print) -> dict:
    """One System One request, cached on disk by (model, state, questions). Returns answers as plain dicts."""
    key = hashlib.sha256(json.dumps([JEV_MODEL, state, questions], sort_keys=True).encode()).hexdigest()[:24]
    f = _CACHE / f"{key}.json"
    if f.exists():
        with _lock:
            USAGE["cached"] += 1
        return json.loads(f.read_text())["answers"]
    from typesafe_sdk import Choice, Noul, Score
    typed = {k: {"score": Score, "choice": Choice, "noul": Noul}[q["type"]](
        **{kk: vv for kk, vv in q.items() if kk != "type"}) for k, q in questions.items()}
    t = time.time()
    r = _get_client().system_one(state=state, questions=typed)
    ans = {k: v.model_dump() for k, v in r.answers.items()}
    f.write_text(json.dumps({"model": r.model, "answers": ans, "usage": r.usage.model_dump()}))
    with _lock:
        USAGE["requests"] += 1
        USAGE["input_tokens"] += r.usage.input_tokens
        USAGE["seconds"] += time.time() - t
    return ans


def cost_usd() -> float:
    return USAGE["input_tokens"] * 0.042 / 1e6


# ---------------------------------------------------------------- pointwise screen
def _score_questions(reverse: bool) -> dict:
    """reverse=True lists rubric levels high->low: a robustness probe for Jev's documented order bias."""
    qs = {}
    for k, (ins, levels) in RUBRIC.items():
        qs[k] = {"type": "score", "instructions": ins, "criteria": list(reversed(levels)) if reverse else levels}
    return qs


def screen_one(p: Promo, idx: BeatIndex, reverse: bool = False, log=print) -> dict:
    ans = ask({"clip": clip_script(p, idx)}, _score_questions(reverse), log)
    out = {}
    for k, (_, levels) in RUBRIC.items():
        a = ans[k]
        top = len(levels) - 1
        s = (top - a["score"]) if reverse else a["score"]
        out[k] = round(10 * s / top, 3)               # 0-10 scale, continuous
        out[k + "_conf"] = a["confidence"]
    out["weighted"] = round(sum(out[k] * w for k, w in W.items()) - max(0.0, out["spoiler"] - 6) * 0.3, 3)
    return out


def screen(promos: list[Promo], idx: BeatIndex, reverse: bool = False, workers: int = 8, log=print) -> dict:
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda p: screen_one(p, idx, reverse, log), promos))
    return {p.id: r for p, r in zip(promos, res)}


# ---------------------------------------------------------------- pairwise
def compare(a: Promo, b: Promo, idx: BeatIndex, log=print) -> dict:
    """Ask a-vs-b in both orders. Returns P(a beats b) debiased, per-order probabilities, confidences."""
    q = {"winner": {"type": "choice", "instructions": PAIR_INSTRUCTIONS,
                    "criteria": {"A": "clip_A is the stronger promo", "B": "clip_B is the stronger promo"}}}
    fwd = ask({"clip_A": clip_script(a, idx), "clip_B": clip_script(b, idx)}, q, log)["winner"]
    rev = ask({"clip_A": clip_script(b, idx), "clip_B": clip_script(a, idx)}, q, log)["winner"]
    p_fwd = fwd["probabilities"]["A"]          # a shown first
    p_rev = rev["probabilities"]["B"]          # a shown second
    return {"a": a.id, "b": b.id, "p_a_first": p_fwd, "p_a_second": p_rev,
            "p": round((p_fwd + p_rev) / 2, 4),
            "agree": (p_fwd > 0.5) == (p_rev > 0.5),
            "conf": round(min(fwd["confidence"], rev["confidence"]), 4),
            "first_shown_won": [fwd["choice"] == "A", rev["choice"] == "A"]}


def all_pairs(shortlist: list[Promo], idx: BeatIndex, workers: int = 8, log=print) -> list[dict]:
    pairs = list(combinations(shortlist, 2))
    with ThreadPoolExecutor(workers) as ex:
        out = list(ex.map(lambda ab: compare(ab[0], ab[1], idx, log), pairs))
    log(f"  [jev] {len(out)} pairs x 2 orders, {USAGE['requests']} new requests, "
        f"{USAGE['input_tokens']:,} tokens (${cost_usd():.4f})")
    return out


def rank(shortlist: list[Promo], comps: list[dict], soft: bool = True) -> dict:
    """Bradley-Terry over all pairs. soft=True uses P(a beats b) as a fractional result (uses calibration)."""
    from .rerank import bradley_terry
    games = [(c["a"], c["b"], c["p"] if soft else (1.0 if c["p"] > 0.5 else 0.0 if c["p"] < 0.5 else 0.5))
             for c in comps]
    return bradley_terry([p.id for p in shortlist], games)


def split_half(shortlist: list[Promo], comps: list[dict]) -> tuple[dict, dict]:
    """BT fitted on first-shown answers only vs second-shown answers only (two independent views)."""
    from .rerank import bradley_terry
    ids = [p.id for p in shortlist]
    return (bradley_terry(ids, [(c["a"], c["b"], c["p_a_first"]) for c in comps]),
            bradley_terry(ids, [(c["a"], c["b"], c["p_a_second"]) for c in comps]))


def cascade(comps: list[dict], tau: float) -> tuple[list[dict], list[dict]]:
    """Accept when both orders agree and the less confident order still has confidence >= tau."""
    acc = [c for c in comps if c["agree"] and c["conf"] >= tau]
    esc = [c for c in comps if not (c["agree"] and c["conf"] >= tau)]
    return acc, esc
