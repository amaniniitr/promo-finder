"""Check a run's promos against the screenplays, without trusting the run.

Re-parses the scripts and checks every promo:
  - each segment's hook and cliff beat IDs exist in that episode;
  - every in time is some beat's start and every out time some beat's end, so no time was
    invented and no cut lands mid-line;
  - total length is 20-60 s;
  - the hook beat sits inside the first segment and starts within 3 s of it;
  - ranks are 1..N with no gaps.

Usage: python scripts/verify_outputs.py <screenplay folder> [run dir, default runs/v3_final]
Exits 1 if any check fails.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from promo.parser import parse_show  # noqa: E402


def main(pack: str, run: str = "runs/v3_final") -> int:
    beats = {b.id: b for ep in parse_show(pack) for b in ep.beats}
    starts, ends = {}, {}
    for b in beats.values():
        starts.setdefault(b.episode, set()).add(round(b.start, 2))
        ends.setdefault(b.episode, set()).add(round(b.end, 2))
    promos = json.loads((Path(run) / "promos.json").read_text())["promos"]
    fails, counts = [], {"ids": 0, "times": 0, "length": 0, "hook": 0}

    for p in promos:
        segs, ok = p["segments"], True
        for s in segs:
            a, b = beats.get(s["start_beat"]), beats.get(s["end_beat"])
            if not (a and b and a.episode == b.episode == s["episode"]):
                fails.append(f"{p['id']}: bad beat IDs {s['start_beat']}..{s['end_beat']}")
                ok = False
                continue
            counts["ids"] += 1
            e = s["episode"]
            if round(s["start"], 2) not in starts[e] or round(s["end"], 2) not in ends[e]:
                fails.append(f"{p['id']}: {s['start']}-{s['end']} is not on beat boundaries")
            else:
                counts["times"] += 1
        dur = sum(s["end"] - s["start"] for s in segs)
        if 20 - 0.01 <= dur <= 60 + 0.01:
            counts["length"] += 1
        else:
            fails.append(f"{p['id']}: length {dur:.1f} s")
        h, s0 = beats.get(p.get("hook_beat") or ""), segs[0]
        if ok and h and h.episode == s0["episode"] and s0["start"] <= h.start <= s0["start"] + 3.0 + 0.01:
            counts["hook"] += 1
        else:
            fails.append(f"{p['id']}: hook beat {p.get('hook_beat')} not in the first 3 s")

    ranks = sorted(p["rank"] for p in promos)
    if ranks != list(range(1, len(promos) + 1)):
        fails.append("ranks are not 1..N")

    n, nseg = len(promos), sum(len(p["segments"]) for p in promos)
    print(f"{n} promos, {nseg} segments, {len(beats):,} beats re-parsed")
    print(f"  beat IDs exist:        {counts['ids']}/{nseg}")
    print(f"  on beat boundaries:    {counts['times']}/{nseg}")
    print(f"  length 20-60 s:        {counts['length']}/{n}")
    print(f"  hook in first 3 s:     {counts['hook']}/{n}")
    for f in fails:
        print("  FAIL", f)
    print("OK" if not fails else f"{len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:3]))
