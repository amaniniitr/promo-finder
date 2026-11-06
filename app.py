"""Editor review UI. Run: streamlit run app.py

Human-in-the-loop: the tool proposes, the editor approves/rejects. Decisions are
saved to <runs/v1>/decisions.json, which doubles as labelled data to tune prompts.
"""
import json
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from promo.parser import fmt, parse_show

st.set_page_config(page_title="Promo Finder", layout="wide")
st.title("Promo Finder: microdrama screenplays")

from promo.config import DEFAULT_SHOW  # noqa: E402

with st.sidebar:
    st.header("Source")
    mode = st.radio("Load", ["Existing runs/v1", "Run on a new show"])
    out_dir = st.text_input("Outputs folder", "runs/v3_final")
    if mode == "Run on a new show":
        up = st.file_uploader("Zip of episode .txt files", type="zip")
        folder = st.text_input("...or folder path", str(DEFAULT_SHOW))
        eps = st.text_input("Episodes (blank = all, e.g. 1,2,3)", "")
        per_ep = st.slider("Candidates per episode", 1, 5, 3)
        n_st = st.slider("Stitched promos", 0, 10, 6)
        version = st.radio("Pipeline", ["v2 (tag -> windows -> pairwise rank)", "v1 (baseline)"])
        judge_choice = st.radio("Judge (v2)", ["auto", "jev", "llm"], help="jev = TypeSafe Jev; auto uses Jev if TYPESAFE_API_KEY is set")
        if st.button("Run pipeline", type="primary"):
            from promo.pipeline import run
            from promo.pipeline_v2 import run_v2
            from promo.report import write_outputs
            from promo.report_v2 import write_v2
            if up:
                tmp = Path(tempfile.mkdtemp())
                zipfile.ZipFile(up).extractall(tmp)
                txts = list(tmp.rglob("*.txt"))
                folder = str(txts[0].parent) if txts else str(tmp)
            log_box = st.empty()
            lines = []

            def log(msg):
                lines.append(str(msg))
                log_box.code("\n".join(lines[-15:]))

            with st.spinner("Running (free-tier rate limits make this slow; results are cached)..."):
                sel = [int(x) for x in eps.split(",")] if eps.strip() else None
                if version.startswith("v2"):
                    res = run_v2(folder, per_ep, episodes_filter=sel, log=log, judge=judge_choice)
                    write_v2(res, out_dir)
                else:
                    res = run(folder, per_ep, n_st, 4, sel, log=log)
                    write_outputs(res, out_dir)
                (Path(out_dir) / "source.txt").write_text(folder)
            st.success(f"Done: {len(res['ranked'])} promos")

out = Path(out_dir)
if not (out / "promos.json").exists():
    st.info("No runs/v1 yet. Run the pipeline from the sidebar or `python run_v1.py <folder>`.")
    st.stop()

data = json.loads((out / "promos.json").read_text())
promos, meta = data["promos"], data["meta"]
EMPTY = {"hook": 0, "cliffhanger": 0, "standalone": 0, "intensity": 0, "spoiler_risk": 0,
         "would_post": False, "verdict": "", "issues": ""}
for p in promos:
    p["judge"] = p.get("judge") or EMPTY
src = Path((out / "source.txt").read_text()) if (out / "source.txt").exists() else DEFAULT_SHOW
episodes = {e.number: e for e in parse_show(src)} if src.exists() else {}
dec_file = out / "decisions.json"
decisions = json.loads(dec_file.read_text()) if dec_file.exists() else {}

if meta.get("version") == "v2":
    judge = (f"judge TypeSafe {meta['jev_usage']['model']} (${meta['jev_usage']['cost_usd']:.3f})"
             if meta.get("judge") == "jev" else f"models used {meta['models_actually_used']}")
    st.caption(f"v2 | {judge} | {meta['candidates']} candidate windows, "
               f"{meta['rule_violations']} rule violations, {meta['story_duplicates_removed']} story duplicates removed | "
               f"top {meta['shortlist_size']} ordered by pairwise tournament "
               f"(position consistency {meta['pairwise'].get('position_consistency')})")
else:
    st.caption(f"Picker `{meta['picker_model']}` | Judge `{meta['judge_model']}` | {meta['episodes']} episodes | "
               f"{meta['promos_ranked']} ranked, {meta['rejected']} rejected by rules, "
               f"{meta['duplicates_removed']} duplicates removed")

c1, c2, c3 = st.columns(3)
kind = c1.multiselect("Kind", ["single", "stitched"], ["single", "stitched"])
min_score = c2.slider("Min score", 0.0, 10.0, 0.0, 0.5)
only_post = c3.checkbox("Judge says 'would post' only")


def segs(p):
    return " + ".join(f"Ep{s['episode']} {fmt(s['start'])}-{fmt(s['end'])}" for s in p["segments"])


rows = [p for p in promos if p["kind"] in kind and p["final_score"] >= min_score
        and (p["judge"]["would_post"] or not only_post)]
st.dataframe(pd.DataFrame([{
    "rank": p["rank"], "id": p["id"], "title": p["title"], "segments": segs(p),
    "len_s": round(p["duration"], 1), "score": p["final_score"], "hook": p["judge"]["hook"],
    "cliff": p["judge"]["cliffhanger"], "standalone": p["judge"]["standalone"],
    "post?": p["judge"]["would_post"], "pairwise W-L-T": p.get("record", ""),
    "editor": decisions.get(p["id"], {}).get("status", ""),
} for p in rows]), hide_index=True, width="stretch")

st.divider()
for p in rows:
    j = p["judge"]
    status = decisions.get(p["id"], {}).get("status", "")
    with st.expander(f"#{p['rank']}  {p['id']}  {p['title']}  |  {segs(p)}  |  {p['duration']:.0f}s  |  "
                     f"score {p['final_score']}  {('[' + status + ']') if status else ''}"):
        a, b = st.columns([3, 2])
        with a:
            st.markdown(f"**Hook:** {p['hook']}\n\n**Cliffhanger:** {p['cliffhanger']}\n\n**Why:** {p['why']}")
            st.markdown(f"**Judge:** {j['verdict']}" + (f"  \n**Issue:** _{j['issues']}_" if j["issues"] else ""))
            if p.get("record"):
                st.caption(f"Pairwise tournament: {p['record']} (wins-losses-ties), BT strength {p['bt']:+.2f}; "
                           f"screen samples {p.get('screen_samples')}")
            if p["fixes"]:
                st.caption("Auto-fixes: " + "; ".join(p["fixes"]))
            if p["flags"]:
                st.caption("Flags: " + ", ".join(p["flags"]))
        with b:
            st.bar_chart(pd.Series({k: j[k] for k in ["hook", "cliffhanger", "standalone", "intensity",
                                                      "spoiler_risk"]}), height=180)
        for n, s in enumerate(p["segments"]):
            ep = episodes.get(s["episode"])
            if not ep:
                continue
            st.markdown(f"**Segment {n + 1}: Episode {s['episode']}, {fmt(s['start'])} to {fmt(s['end'])}**")
            lines = []
            for bt in ep.beats:
                if bt.end < s["start"] - 4 or bt.start > s["end"] + 4:
                    continue
                inside = bt.start >= s["start"] - 0.01 and bt.end <= s["end"] + 0.01
                who = f"{bt.speaker} ({bt.emotion}): \"{bt.text}\"" if bt.speaker else f"[{bt.type.upper()}] {bt.text}"
                lines.append(f"{'  ' if inside else '× '}{fmt(bt.start)} {who}")
            st.code("\n".join(lines), language=None)
        st.caption("Lines marked × are context just outside the cut.")
        d1, d2, d3 = st.columns([1, 1, 4])
        note = d3.text_input("Note", decisions.get(p["id"], {}).get("note", ""), key=f"n{p['id']}")
        for col, label in ((d1, "approve"), (d2, "reject")):
            if col.button(label.capitalize(), key=f"{label}{p['id']}"):
                decisions[p["id"]] = {"status": label, "note": note}
                dec_file.write_text(json.dumps(decisions, indent=2))
                st.rerun()
