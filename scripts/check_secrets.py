"""Run before every push:  .venv/bin/python scripts/check_secrets.py
Fails (exit 1) if any file git would publish contains an API key, the .env file, the site passphrase,
the input pack, or verbatim script text from the input pack."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                       capture_output=True, text=True).stdout.split()
KEYS = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|AQ\.[0-9A-Za-z_\-]{30,}|apikey_[0-9a-f]{20,}|sk-[A-Za-z0-9]{20,}|jv_live_\w+")
env = {}
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if len(v.strip()) >= 8:
                env[k] = v.strip()
frags = set()
pack = ROOT.parent / "I Married a Broken Soldier. He was a Duke"
if pack.exists():
    for f in pack.glob("*.txt"):
        for line in f.read_text().splitlines():
            w = re.findall(r"[A-Za-z']+", line)
            if len(w) >= 8:
                frags |= {" ".join(w[i:i + 8]).lower() for i in range(len(w) - 7)}
bad = []
for f in files:
    p = ROOT / f
    if f == ".env" or f.startswith("I Married") or "/.env" in f:
        bad.append(f"{f}: secret/confidential file is tracked")
        continue
    try:
        t = p.read_text()
    except Exception:
        continue
    if KEYS.search(t):
        bad.append(f"{f}: looks like an API key")
    for k, v in env.items():
        if v in t:
            bad.append(f"{f}: contains the value of {k} from .env")
    w = re.findall(r"[A-Za-z']+", t)
    hits = sum(" ".join(w[i:i + 8]).lower() in frags for i in range(len(w) - 7))
    if hits:
        bad.append(f"{f}: {hits} verbatim 8-word runs from the confidential scripts")
print(f"checked {len(files)} files")
if bad:
    print("BLOCKED:\n  " + "\n  ".join(bad))
    sys.exit(1)
print("OK: no keys, no .env, no passphrase, no plaintext script text")
