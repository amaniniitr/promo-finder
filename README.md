# Promo Finder (Kuku AI Generalist assignment, Problem 1)

Aman Kumar · 22322004 · **Live site:** see `links.json` (Vercel; full results unlock with the passphrase from the submission form) · **Deploy steps:** `DEPLOY.md`

Reads a folder of timestamped microdrama screenplays and returns ranked 20-60 s promos. Each promo has episode and start/end times for every segment, the hook, the cliffhanger, one line on why it works, and a week-1 posting plan.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-local.txt   # full toolkit (requirements.txt = minimal, used by Vercel)
cp .env.example .env        # add keys (see below)

.venv/bin/python run.py "<show folder>" --out runs/latest      # full pipeline
.venv/bin/python run.py "<show folder>" --episodes 1,2,3        # quick test
.venv/bin/python demo.py runs/new_show_test                     # no keys needed: view a saved run
.venv/bin/streamlit run app.py                                  # editor review UI (approve / reject)
.venv/bin/python tests/test_parser.py                           # parser format tests (no keys)
.venv/bin/python scripts/dev_server.py                          # the Vercel site + live-run API on localhost:3000
```

**Keys.** `GEMINI_API_KEY` (free, AI Studio) is enough to run everything with fallbacks. `VERTEX_API_KEY` moves tagging and notes to Vertex `gemini-3.5-flash`. `TYPESAFE_API_KEY` uses TypeSafe Jev for scoring and ranking; without it, LLM judges are used. Any LiteLLM model string can be set per role, e.g. `PROMO_TAG_MODEL=openai/gpt-5-mini`, `PROMO_RANK_MODEL=...`.

**Input.** One file per episode (`.txt`/`.md`/`.fountain`). The parser accepts `**LABEL:**` or `LABEL:` blocks, `NAME (Emotion):` dialogue, times as `Start: (mm:ss.ff) | End: (...)`, `[mm:ss.ff - mm:ss.ff]`, `mm:ss,ff --> mm:ss,ff`, `h:mm:ss` or `1.0s - 4.8s`, on the label line or the next line, `SCENE n` markers or `INT./EXT.` sluglines, and episode numbers from the header or the file name. If it finds nothing usable it raises a clear error instead of returning an empty run. `tests/fixtures/new_show/` is a 4-episode show in a different format (bracket times, no bold, no header fields) used to prove a fresh show runs end to end.

## Pipeline

```
parser      screenplay -> beats with IDs and times                                   code
tag         LLM marks HOOK and CLIFF beats by ID, 1 call per episode                 LLM
windows     every hook->cliff pair becomes a 20-60s clip (or 2-part teaser + run-up),
            plus cross-episode promos (hook from ep A, cliff from a later ep B)      code
screen      rubric scores per clip, asked with levels in both orders                 Jev / LLM
dedupe      same footage or same story (embeddings) -> keep the better one;
            MMR shortlist of 20                                                      code
rank        every shortlist pair, both orders, Bradley-Terry on P(a beats b)         Jev / LLM
notes       hook / cliffhanger / why + week-1 posting plan, written after ranking    LLM
review      editor approves / rejects in app.py; decisions saved as labels           human
```

The LLM never writes a timestamp or picks a length. Rule compliance (20-60 s, hook in the first 3 s) holds by construction.

## Layout

| path | what |
|---|---|
| `run.py`, `promo/pipeline_v2.py` | final pipeline |
| `promo/` | parser, moments (windows), jev, rerank, diversity, explain, llm (model routing + cache) |
| `run_v1.py`, `promo/pipeline.py` | v1 baseline, kept only for the before/after comparison |
| `runs/v3_final/` | full-pack output (**confidential, not in git; shared separately**) |
| `runs/new_show_test/` | output on the synthetic new show (in git) |
| `experiments/` | baseline, v1-vs-v2, Jev, blind audits, real-life tests, critical review |
| `tests/` | parser tests and the synthetic show |
| `web/` | static Vercel site (demo public; full-pack results AES-encrypted) built by `scripts/build_site.py` |
| `deck/build_deck.py` | builds the 2-page solution PDF from the run files |
| `scripts/check_secrets.py` | pre-push guard: blocks keys, `.env`, passphrase, plaintext script text |

## Evidence (details in `experiments/`)
- Picking: raw compliance 84% (v1, LLM picks boundaries) -> 100% (LLM tags, code builds clips). 0 invented beat IDs in 500 tags.
- Real-life tests (`REALWORLD_RESULTS*.md`, ground truth not from an LLM): 90% of planted shocking lines tagged as hooks, 0/29 neutral decoys; writers' episode-ending cliffhangers found in 82-94% of episodes vs 18-26% by chance.
- Ranking: shortlist order reproducible at split-half Spearman 0.75-0.90 with Jev vs 0.44 with the free LLM ranker; full judging ~20 s and ~$0.05 per show.
- Not proven: that people prefer these promos. Independent AI judges agree only at Spearman 0.26-0.49, and blind audits give conflicting verdicts. Editor labels from `app.py` are the next step.

## Prior work used
AI-Youtube-Shorts-Generator and deepclip (score + hook + reason; reviewer + second opinion), constrained candidate selection for timestamps (arXiv 2606.20890), Pairwise Ranking Prompting (Qin et al. 2023), "Coin Flip Judge" (arXiv 2606.13685), JEV-as-a-Judge (arXiv 2609.26550), MMR, LiteLLM.
