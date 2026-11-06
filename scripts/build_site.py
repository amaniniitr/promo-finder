"""Export runs into the static Vercel site in web/.

  .venv/bin/python scripts/build_site.py

web/data/demo.json        synthetic show (tests/fixtures/new_show): public
web/data/kuku.enc.json    full-pack run + solution deck, AES-256-GCM encrypted with SITE_PASSPHRASE
                          from .env (PBKDF2-SHA256, 310k iterations). Decrypted in the browser.
No API key is read or written here except SITE_PASSPHRASE, which is never written to web/.
"""
import base64
import json
import os
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from promo.models import BeatIndex, Promo, clip_script  # noqa: E402
from promo.parser import parse_show  # noqa: E402

WEB = ROOT / "web"
(WEB / "data").mkdir(parents=True, exist_ok=True)
ITER = 310_000


def bundle(run: Path, show: Path, titles: dict | None = None) -> dict:
    meta = json.loads((run / "meta.json").read_text())
    promos = json.loads((run / "promos.json").read_text())["promos"]
    idx = BeatIndex(parse_show(show))
    out = []
    for p in promos:
        q = Promo(**p)
        j = p.get("judge") or {}
        out.append({"rank": p["rank"], "id": p["id"], "kind": p["kind"], "duration": p["duration"],
                    "title": (titles or {}).get(p["id"], ""),
                    "segments": [{"episode": s["episode"], "start": s["start"], "end": s["end"]} for s in p["segments"]],
                    "hook": p["hook"], "cliffhanger": p["cliffhanger"], "why": p["why"], "record": p.get("record", ""),
                    "bt": p.get("bt"), "screen": p.get("screen_score"),
                    "scores": {k: j.get(k) for k in ("hook", "cliffhanger", "standalone", "intensity", "spoiler_risk")},
                    "script": clip_script(q, idx)})
    keep = ["candidates", "rule_violations", "story_duplicates_removed", "ranked", "shortlist_size", "pairwise",
            "posting_plan", "episodes", "judge", "generated"]
    m = {k: meta.get(k) for k in keep}
    m["jev_cost_usd"] = (meta.get("jev_usage") or {}).get("cost_usd")
    return {"meta": m, "promos": out}


def encrypt(obj: dict, passphrase: str) -> dict:
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(passphrase.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, separators=(",", ":")).encode(), None)
    b = lambda x: base64.b64encode(x).decode()  # noqa: E731
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": b(salt), "iv": b(iv), "ct": b(ct)}


(WEB / "data" / "links.json").write_text((ROOT / "links.json").read_text())
demo = bundle(ROOT / "runs" / "new_show_test", ROOT / "tests" / "fixtures" / "new_show")
demo["meta"]["label"] = "Synthetic demo show (AI-written, different script format)"
(WEB / "data" / "demo.json").write_text(json.dumps(demo, separators=(",", ":")))
print(f"web/data/demo.json: {len(demo['promos'])} promos (public)")

pw = os.getenv("SITE_PASSPHRASE")
final = ROOT / "runs" / "v3_final"
if pw and final.exists():
    from promo.config import DEFAULT_SHOW
    tfile = ROOT / "deck" / "titles.json"
    kuku = bundle(final, DEFAULT_SHOW, json.loads(tfile.read_text()) if tfile.exists() else None)
    kuku["meta"]["label"] = "I Married a Broken Soldier. He was a Duke · all 50 episodes"
    pdf = ROOT / "deck" / "solution.pdf"
    if pdf.exists():
        kuku["deck_pdf_b64"] = base64.b64encode(pdf.read_bytes()).decode()
    kuku["csv"] = (final / "promos.csv").read_text()
    (WEB / "data" / "kuku.enc.json").write_text(json.dumps(encrypt(kuku, pw)))
    print(f"web/data/kuku.enc.json: {len(kuku['promos'])} promos + deck, encrypted")
else:
    print("SITE_PASSPHRASE or runs/v3_final missing: confidential bundle not built")
