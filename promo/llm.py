"""Thin LLM wrapper: LiteLLM (any provider via model string), JSON output,
disk cache, retries + fallback models for free-tier rate limits.

Swap models with env vars, no code change:
  PROMO_RANK_MODEL=openai/gpt-5      (strongest model: final pairwise ranking)
  PROMO_TAG_MODEL=... PROMO_SCREEN_MODEL=... (cheap high-volume roles)
  PROMO_<ROLE>_FALLBACKS=a,b,c         (per-role fallback chain)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

import litellm
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
litellm.suppress_debug_info = True
import logging  # noqa: E402

logging.getLogger("LiteLLM").setLevel(logging.ERROR)

CACHE_DIR = Path(os.getenv("PROMO_CACHE", Path(__file__).resolve().parent.parent / ".cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Role-based model cascade. Cheap models do high-volume, easy work; the strongest
# model is spent only where it changes the answer (ordering the final shortlist).
#   tag    : mark hook / cliffhanger beats in each episode     (~50 calls, easy)
#   screen : pointwise score of every candidate window, x2     (~40 calls, easy)
#   rank   : pairwise comparisons on the shortlist             (~10-20 calls, hard)
#   audit  : blind judge used only for experiments             (different family/model)
#   picker/judge : v1 roles, kept for the A/B baseline
VERTEX_BASE = "https://aiplatform.googleapis.com/v1beta1/publishers/google"


def _route(model: str) -> tuple[str, dict]:
    """'vertex/<id>' = Vertex AI express mode (API key) through LiteLLM's Gemini adapter."""
    if model.startswith("vertex/"):
        return "gemini/" + model.split("/", 1)[1], {"api_key": os.getenv("VERTEX_API_KEY"), "api_base": VERTEX_BASE}
    return model, {}


# With a Vertex key (paid, no daily cap) the strong model does the job that limits quality most:
# tagging hook/cliff beats. Without it, the free AI Studio cascade below is used.
_HAS_VERTEX = bool(os.getenv("VERTEX_API_KEY"))
VERTEX_DEFAULTS = {
    "tag":     ("vertex/gemini-3.5-flash", "vertex/gemini-3.1-flash-lite,gemini/gemini-3.1-flash-lite"),
    "screen":  ("vertex/gemini-3.1-flash-lite", "gemini/gemini-3.5-flash-lite"),
    "rank":    ("vertex/gemini-3.5-flash", "gemini/gemini-3-flash-preview,gemini/gemma-4-26b-a4b-it"),
    "explain": ("vertex/gemini-3.5-flash", "gemini/gemini-3.5-flash-lite"),
    "audit":   ("vertex/gemini-3.8-flash", "vertex/gemini-3.5-flash"),
}

ROLE_DEFAULTS = {
    "explain": ("gemini/gemini-3.5-flash-lite", "gemini/gemini-3.1-flash-lite"),
    "tag":    ("gemini/gemini-3.1-flash-lite", "gemini/gemini-3.5-flash-lite,gemini/gemini-2.5-flash"),
    "screen": ("gemini/gemini-3.5-flash-lite", "gemini/gemini-3.1-flash-lite,gemini/gemini-2.5-flash"),
    "rank":   ("gemini/gemini-3.5-flash", "gemini/gemini-3-flash-preview,gemini/gemini-2.5-flash,"
                                          "gemini/gemma-4-26b-a4b-it"),
    "audit":  ("gemini/gemini-3-flash-preview", "gemini/gemini-2.5-flash,gemini/gemma-4-26b-a4b-it"),
    "picker": ("gemini/gemini-3.5-flash", "gemini/gemini-2.5-flash,gemini/gemini-3.1-flash-lite"),
    "judge":  ("gemini/gemini-2.5-flash", "gemini/gemini-3.5-flash-lite"),
}


def _defaults(role: str):
    if _HAS_VERTEX and role in VERTEX_DEFAULTS:
        return VERTEX_DEFAULTS[role]
    return ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["picker"])


def model_for(role: str) -> str:
    """PROMO_<ROLE>_MODEL overrides; PROMO_MODEL / PROMO_JUDGE_MODEL kept for v1."""
    legacy = {"picker": "PROMO_MODEL", "judge": "PROMO_JUDGE_MODEL"}.get(role)
    return (os.getenv(f"PROMO_{role.upper()}_MODEL") or (legacy and os.getenv(legacy))
            or _defaults(role)[0])


def _fallbacks(role: str = "picker") -> list[str]:
    raw = (os.getenv(f"PROMO_{role.upper()}_FALLBACKS") or os.getenv("PROMO_FALLBACKS")
           or _defaults(role)[1])
    return [m.strip() for m in raw.split(",") if m.strip()]


CALLS: list[dict] = []          # every call this session: role, model, cached, fallback
TOKENS: dict[str, list[int]] = {}  # model -> [input, output] tokens, uncached calls this session


USED: dict[str, int] = {}       # model -> successful (uncached) calls this session
_EXHAUSTED: set[str] = set()    # models whose daily quota ran out this session


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"[\[{].*[\]}]", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


_locks: dict[str, threading.Lock] = {}
_last: dict[str, float] = {}
_g = threading.Lock()


# Free-tier input-token caps per minute where they are tight (Gemma: 16k TPM).
TPM = {"gemma": 15000}
NO_JSON_MODE = {"gemma-4-31b"}


def _throttle(model: str, tokens: int = 0) -> None:
    """Space calls per model to stay under free-tier RPM (PROMO_RPM) and, where known, TPM."""
    gap = 60.0 / float(os.getenv("PROMO_RPM", "8")) if not model.startswith("vertex/") else 0.2
    for k, tpm in TPM.items():
        if k in model and tokens:
            gap = max(gap, 60.0 * tokens / tpm)
    with _g:
        lock = _locks.setdefault(model, threading.Lock())
    with lock:
        wait = _last.get(model, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[model] = time.time()


def _short(e: Exception) -> str:
    s = str(e)
    m = re.search(r'"message":\s*"([^"]{0,140})', s)
    return f"{type(e).__name__}: {(m.group(1) if m else s[:140])}"


def call_json(system: str, user: str, role: str = "picker", temperature: float = 0.4,
              max_attempts: int = 6, log=print, info: dict | None = None, salt: str = ""):
    """Return parsed JSON from the model. Cached by (model, prompts).
    If `info` is given, info['model'] is set to the model that actually answered."""
    info = info if info is not None else {}
    primary = model_for(role)
    models = [primary] + [m for m in _fallbacks(role) if m != primary]
    models = [m for m in models if m not in _EXHAUSTED] or models
    # `salt` lets experiments request an independent sample of the same prompt (test-retest).
    key = hashlib.sha256(json.dumps([primary, system, user, temperature] + ([salt] if salt else [])).encode()).hexdigest()[:24]
    cache_file = CACHE_DIR / f"{role}-{key}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text())
        info["model"] = cached.get("model", primary)
        CALLS.append({"role": role, "model": info["model"], "cached": True, "fallback": info["model"] != primary})
        return cached["data"]

    last_err = None
    attempt = 0
    while attempt < max_attempts and models:
        model = models[0]
        try:
            _throttle(model, (len(system) + len(user)) // 4)
            # Some models (gemma-4-31b on AI Studio) 500 on JSON mode; for them we rely on the prompt + parser.
            kw = {} if any(k in model for k in NO_JSON_MODE) else {"response_format": {"type": "json_object"}}
            target, extra = _route(model)
            r = litellm.completion(
                model=target, temperature=temperature,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                timeout=300, **kw, **extra,
            )
            u = getattr(r, "usage", None)
            if u:
                TOKENS.setdefault(model, [0, 0])
                TOKENS[model][0] += u.prompt_tokens or 0
                TOKENS[model][1] += u.completion_tokens or 0
            data = _extract_json(r.choices[0].message.content or "")
            if model != primary:
                log(f"  [llm] used fallback {model} (primary {primary} unavailable)")
            cache_file.write_text(json.dumps({"model": model, "data": data}, indent=1))
            USED[model] = USED.get(model, 0) + 1
            info["model"] = model
            CALLS.append({"role": role, "model": model, "cached": False, "fallback": model != primary})
            return data
        except Exception as e:  # rate limit, 503 overload, bad JSON -> retry / fall back
            last_err, attempt = e, attempt + 1
            s = str(e)
            if "PerDay" in s or "limit: 0" in s:  # daily quota gone: retrying is pointless, drop this model for the session
                _EXHAUSTED.add(model)
                models = [m for m in models if m not in _EXHAUSTED]
                log(f"  [llm] {model}: daily free-tier quota exhausted -> falling back to {models[:1]}")
                if not models:
                    break
                continue
            hint = re.search(r"retry in ([\d.]+)s", s)
            wait = min(65.0, float(hint.group(1)) + 1 if hint else 5 * 2 ** min(attempt, 3))
            log(f"  [llm] {model} attempt {attempt}: {_short(e)} -> retry in {wait:.0f}s")
            time.sleep(wait)
            if attempt % 2 == 0 and len(models) > 1:  # 2 tries per model, then rotate
                models = models[1:] + models[:1]
    raise RuntimeError(f"LLM failed after {attempt} attempts: {last_err}")
