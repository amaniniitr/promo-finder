# Deploy

The site is a static folder (`web/`) plus one Python function (`api/run.py`) on Vercel. `vercel.json` wires them together. The function runs the real pipeline on up to 5 episodes, with minimal dependencies from `requirements.txt` and a 300 s limit.

## What is published where

| Place | Contains | Never contains |
|---|---|---|
| GitHub | Code, tests, experiment write-ups, the synthetic demo run, `web/`, `docs/` images | `.env`, the licensed scripts, runs on them, the deck PDF |
| Vercel site | `web/`, including `web/data/kuku.json` (the 50-episode results, deck and CSV, served openly; git-ignored) | Keys |
| Vercel env vars | `VERTEX_API_KEY`, `GEMINI_API_KEY`, `TYPESAFE_API_KEY`, `RUN_PASSPHRASE` | |

`scripts/check_secrets.py` blocks a push if any file git would publish contains a key, the `.env` file, the passphrase or an 8-word run of text from the confidential scripts.

## Test locally

```bash
.venv/bin/python scripts/dev_server.py          # site + live-run API on http://localhost:3000
```

## Update and deploy

```bash
.venv/bin/python deck/build_deck.py             # deck/solution.pdf from runs/v3_final
.venv/bin/python scripts/build_docs.py          # README images in docs/
.venv/bin/python scripts/build_site.py          # writes results + deck into web/data/
.venv/bin/python scripts/check_secrets.py       # must print OK
git add -A && git commit -m "Update results" && git push
sh scripts/vercel_env.sh                        # first time only: copy the 4 secrets from .env to Vercel
npx vercel --prod                               # deploy
```

Keep Vercel's Deployment Protection off for production so reviewers aren't asked to log in. Rotate keys regularly.
