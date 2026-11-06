"""Fill in the public links once you have them, then rebuild the deck and the site.
.venv/bin/python scripts/set_links.py --repo https://github.com/USER/promo-finder --site https://promo-finder.vercel.app [--video URL] [--outputs URL]"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
for k in ("repo", "site", "video", "outputs", "branch"):
    ap.add_argument(f"--{k}")
a = ap.parse_args()
L = json.loads((ROOT / "links.json").read_text())
L.update({k: v for k, v in vars(a).items() if v})
(ROOT / "links.json").write_text(json.dumps(L, indent=2) + "\n")
print("links.json:", L)
py = sys.executable
subprocess.run([py, str(ROOT / "deck" / "build_deck.py")], check=True)
subprocess.run([py, str(ROOT / "scripts" / "build_site.py")], check=True)
