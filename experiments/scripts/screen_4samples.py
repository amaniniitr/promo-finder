import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Samples 3 and 4 of the pointwise screen on the same 138 candidates (cache salts s2,s3),
# so avg(1,2) vs avg(3,4) measures whether averaging 2 samples improves reliability.
import json
from promo.config import DEFAULT_SHOW  # noqa: E402
from promo.models import BeatIndex, Promo
from promo.parser import parse_show
from promo import rerank
idx=BeatIndex(parse_show(DEFAULT_SHOW))
d=json.load(open("runs/v2_llm/diagnostics.json"))
C=[Promo(**p) for p in d["all_candidates"]]
r=rerank.screen(C, idx, samples=4, workers=4)   # samples 1-2 come from cache
json.dump(r["per_sample"], open("experiments/screen_4samples.json","w"))
print("done", [len(s) for s in r["per_sample"]])
