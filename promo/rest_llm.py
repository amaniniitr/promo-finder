"""Minimal REST client for Gemini (AI Studio) and Vertex AI express mode.

Used when LiteLLM isn't installed (the Vercel serverless function, where LiteLLM's
161 MB is too heavy) or when PROMO_BACKEND=rest. Supports the model strings
'gemini/<id>' (GEMINI_API_KEY) and 'vertex/<id>' (VERTEX_API_KEY).
"""
from __future__ import annotations

import os

import httpx

AISTUDIO = "https://generativelanguage.googleapis.com/v1beta/models"
VERTEX = "https://aiplatform.googleapis.com/v1beta1/publishers/google/models"


class RestError(RuntimeError):
    pass


def _endpoint(model: str, op: str) -> tuple[str, dict]:
    prov, _, mid = model.partition("/")
    if prov == "vertex":
        key = os.getenv("VERTEX_API_KEY")
        base = VERTEX
    elif prov == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        base = AISTUDIO
    else:
        raise RestError(f"REST backend supports gemini/ and vertex/ models only, got {model}")
    if not key:
        raise RestError(f"no API key for {prov}")
    return f"{base}/{mid}:{op}", {"key": key}


def complete(model: str, system: str, user: str, temperature: float = 0.4, json_mode: bool = True,
             timeout: float = 240) -> tuple[str, int, int]:
    """Returns (text, input_tokens, output_tokens). Raises RestError with the API message on failure
    (the message keeps 'PerDay' / 'retry in Ns' hints so the caller's retry logic still works)."""
    url, params = _endpoint(model, "generateContent")
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature,
                                 **({"responseMimeType": "application/json"} if json_mode else {})}}
    r = httpx.post(url, params=params, json=body, timeout=timeout)
    if r.status_code != 200:
        raise RestError(f"{r.status_code}: {r.text[:600]}")
    d = r.json()
    try:
        parts = d["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError):
        raise RestError(f"no content in response: {str(d)[:300]}")
    u = d.get("usageMetadata", {})
    return text, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0)


def embed(model: str, texts: list[str], timeout: float = 120) -> list[list[float]]:
    prov, _, mid = model.partition("/")
    url, params = _endpoint(model, "batchEmbedContents")
    reqs = [{"model": f"models/{mid}", "content": {"parts": [{"text": t}]}} for t in texts]
    r = httpx.post(url, params=params, json={"requests": reqs}, timeout=timeout)
    if r.status_code != 200:
        raise RestError(f"{r.status_code}: {r.text[:400]}")
    return [e["values"] for e in r.json()["embeddings"]]
