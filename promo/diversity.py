"""Story-level dedupe + diverse shortlist.

v1 deduped on time overlap within one episode, so a recap that re-stages an
earlier scene (Ep2 replays the Ep1 altar rejection) slipped through as a
'different' promo. Here two clips are duplicates if their *content* is close
(embedding cosine of the clip's dialogue+action), regardless of episode.

Shortlist uses Maximal Marginal Relevance (Carbonell & Goldstein 1998):
pick = argmax  lambda * quality - (1 - lambda) * max_sim_to_already_picked
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import litellm

from .llm import CACHE_DIR
from .metrics import cosine

EMBED_MODEL = os.getenv("PROMO_EMBED_MODEL", "gemini/gemini-embedding-001")
_EMB_CACHE = CACHE_DIR / "embeddings.json"


def embed(texts: list[str], log=print) -> list[list[float]]:
    """Cached embeddings. Free tier counts every text toward 100/min, so batch 40 and wait."""
    store = json.loads(_EMB_CACHE.read_text()) if _EMB_CACHE.exists() else {}
    keys = [hashlib.sha256((EMBED_MODEL + t).encode()).hexdigest()[:20] for t in texts]
    todo = [(k, t) for k, t in zip(keys, texts) if k not in store]
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        for attempt in range(5):
            try:
                r = litellm.embedding(model=EMBED_MODEL, input=[t for _, t in chunk])
                for (k, _), d in zip(chunk, r.data):
                    store[k] = d["embedding"]
                _EMB_CACHE.write_text(json.dumps(store))
                break
            except Exception as e:
                log(f"  [embed] {type(e).__name__} -> wait 60s")
                time.sleep(60)
        if i + 40 < len(todo):
            time.sleep(25)
    return [store[k] for k in keys]


def clip_text(p, idx) -> str:
    out = []
    for s in p.segments:
        for b in idx.eps[s.episode].beats:
            if b.type in ("dialogue", "action") and b.start >= s.start - 0.01 and b.end <= s.end + 0.01:
                out.append((b.speaker + ": " if b.speaker else "") + b.text)
    return " ".join(out)[:6000]


def story_dedupe(promos, idx, thr: float, log=print, time_thr: float = 0.5):
    """Greedy by quality: drop a clip if it duplicates a better one already kept.
    Duplicate = same-episode time overlap > time_thr (same footage), OR content cosine >= thr
    (same story beat told again, e.g. a recap or a 'previously on' opening)."""
    vecs = embed([clip_text(p, idx) for p in promos], log)

    def t_overlap(a, b):
        inter = sum(max(0.0, min(s.end, t.end) - max(s.start, t.start))
                    for s in a.segments for t in b.segments if s.episode == t.episode)
        return inter / (min(a.duration, b.duration) or 1)

    order = sorted(range(len(promos)), key=lambda i: -promos[i].screen_score)
    kept, dropped = [], []
    for i in order:
        hit = None
        for k in kept:
            c = cosine(vecs[i], vecs[k])
            if t_overlap(promos[i], promos[k]) > time_thr or c >= thr:
                hit = (k, c)
                break
        if hit:
            dropped.append((promos[i].id, promos[hit[0]].id, round(hit[1], 3)))
        else:
            kept.append(i)
    return [promos[i] for i in kept], dropped, {promos[i].id: vecs[i] for i in range(len(promos))}


def mmr(promos, vecs: dict, k: int, lam: float = 0.75):
    """Quality-diversity shortlist. Quality = screen score scaled to 0..1."""
    pool = list(promos)
    picked = []
    while pool and len(picked) < k:
        def gain(p):
            sim = max((cosine(vecs[p.id], vecs[q.id]) for q in picked), default=0.0)
            return lam * p.screen_score / 10 - (1 - lam) * sim
        best = max(pool, key=gain)
        picked.append(best)
        pool.remove(best)
    return picked
