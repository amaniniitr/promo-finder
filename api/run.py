"""Vercel serverless function: run the real pipeline on a few episodes from the browser.

POST /api/run  {"passphrase": "...", "files": [{"name": "ep1.txt", "text": "..."}]}
GET  /api/run  -> health (which judge/models are configured; never the keys)

Keys live only in Vercel environment variables (VERTEX_API_KEY / GEMINI_API_KEY, TYPESAFE_API_KEY).
RUN_PASSPHRASE gates every run, so nobody can spend the keys without it. Input is capped
(5 episodes, 30k characters each) so a run fits Vercel Hobby's 300 s limit.
"""
import hmac
import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PROMO_CACHE", "/tmp/promo-cache")
os.environ.setdefault("PROMO_EMBED_TRIES", "2")
os.environ.setdefault("PROMO_EMBED_WAIT", "3")

MAX_FILES, MAX_CHARS = 5, 30_000


def _reset_counters():
    from promo import jev, llm, pipeline
    llm.CALLS.clear()
    llm.TOKENS.clear()
    pipeline.FAILED.clear()
    for k in jev.USAGE:
        jev.USAGE[k] = 0 if k != "seconds" else 0.0


def _models():
    from promo.llm import model_for
    return {r: model_for(r) for r in ("tag", "explain")} | {
        "judge": "TypeSafe Jev" if os.getenv("TYPESAFE_API_KEY") else model_for("rank")}


def run(files):
    from promo.export import bundle
    from promo.pipeline_v2 import run_v2
    from promo.report_v2 import write_v2
    tmp = Path(tempfile.mkdtemp(prefix="show-"))
    try:
        for i, f in enumerate(files):
            name = re.sub(r"[^A-Za-z0-9._-]", "_", str(f.get("name") or f"episode-{i + 1:02d}.txt"))[:80]
            if not name.lower().endswith((".txt", ".md", ".fountain")):
                name += ".txt"
            (tmp / name).write_text(str(f["text"]), encoding="utf-8")
        log = []
        t0 = time.time()
        res = run_v2(str(tmp), per_episode=4, shortlist=8, rounds=3, screen_samples=2, workers=6,
                     log=lambda m: log.append(str(m)), judge="auto", cross=6, notes=10)
        out = tmp / "out"
        write_v2(res, out)
        meta = json.loads((out / "meta.json").read_text())
        promos = json.loads((out / "promos.json").read_text())["promos"]
        b = bundle(meta, promos, res["index"])
        b["meta"]["label"] = f"Live run · {len(files)} uploaded episode(s)"
        b["meta"]["run_seconds"] = round(time.time() - t0, 1)
        b["meta"]["models"] = _models()
        b["meta"]["llm_tokens"] = meta.get("llm_tokens_by_model")
        b["log"] = [l for l in log if not l.strip().startswith("[llm]")][-40:]
        return b
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        ok = bool(os.getenv("VERTEX_API_KEY") or os.getenv("GEMINI_API_KEY"))
        self._send(200, {"ok": ok, "live_runs_enabled": ok and bool(os.getenv("RUN_PASSPHRASE")),
                         "models": _models() if ok else {}, "limits": {"files": MAX_FILES, "chars_per_file": MAX_CHARS}})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_FILES * MAX_CHARS * 2 + 10_000:
                return self._send(413, {"error": "request too large"})
            req = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "body must be JSON"})
        want = os.getenv("RUN_PASSPHRASE", "")
        if not want or not hmac.compare_digest(str(req.get("passphrase", "")).strip().encode(), want.encode()):
            time.sleep(1.5)                      # slow down guessing
            return self._send(401, {"error": "wrong passphrase"})
        files = req.get("files") or []
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
            return self._send(400, {"error": f"send 1-{MAX_FILES} episode files"})
        if any(not isinstance(f, dict) or not isinstance(f.get("text"), str) or len(f["text"]) > MAX_CHARS for f in files):
            return self._send(400, {"error": f"each file must be text, at most {MAX_CHARS:,} characters"})
        try:
            _reset_counters()
            return self._send(200, run(files))
        except Exception as e:
            from promo.parser import ScriptFormatError
            if isinstance(e, ScriptFormatError):
                return self._send(400, {"error": str(e)})
            traceback.print_exc()
            return self._send(500, {"error": f"{type(e).__name__}: {str(e)[:300]}"})
