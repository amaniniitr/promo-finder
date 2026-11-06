"""Paths. The show folder is always an argument; this is only the default for scripts/UI.
Set PROMO_SHOW to point at another show."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHOW = Path(os.getenv("PROMO_SHOW", ROOT.parent / "I Married a Broken Soldier. He was a Duke"))
FINAL_RUN = ROOT / "runs" / "v3_final"
