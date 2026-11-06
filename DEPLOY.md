# Deploy: GitHub + Vercel

**Fast path:** `sh scripts/publish.sh` runs every Terminal step. The browser steps are in `../ASIDE_TASK.md` (for the Aside agent). The notes below explain what happens.

Architecture: `vercel.json` (repo root) serves `web/` as a static site, plus one Python function `api/run.py` (300 s, minimal deps in `requirements.txt`) that runs the real pipeline on up to 5 episodes. Keys live only in Vercel environment variables; `RUN_PASSPHRASE` gates every live run. Test the whole thing locally with `.venv/bin/python scripts/dev_server.py` → http://localhost:3000


What gets published:
- **GitHub:** code, tests, experiment write-ups, the synthetic demo run, and `web/` (the Vercel site). It does **not** include `.env` (your keys), the Kuku input pack, the full-pack runs or the deck PDF. `.gitignore` excludes them, and a pre-push hook (`scripts/check_secrets.py`) blocks the push if a key, the passphrase or plaintext Kuku script text slips in.
- **Vercel:** only the `web/` folder, a static site with no server and no keys. The 50-episode results and the deck PDF are inside `web/data/kuku.enc.json`, AES-256 encrypted. Viewers unlock them in the browser with the passphrase. The synthetic demo show is public.

All commands run from this folder:
```bash
cd /Users/aman/Desktop/kuku/promo-finder
```

## 1. Check that nothing secret will be published
```bash
.venv/bin/python scripts/check_secrets.py
git status --short          # should print nothing
```

## 2. Push to a private GitHub repo
1. In the browser, open https://github.com/new
   - Name: `promo-finder` · Visibility: **Private** · leave every "Initialize" box unticked · **Create repository**.
2. Paste in Terminal, replacing `YOUR_GITHUB_USERNAME`:
```bash
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/promo-finder.git
git push -u origin main
```
If Git asks for a password, use a GitHub personal access token (https://github.com/settings/tokens → "Generate new token (classic)" → tick `repo`), not your account password.

## 3. Deploy on Vercel (browser)
1. Open https://vercel.com/new and sign in with GitHub.
2. Click **Import** next to `promo-finder`. If it's not listed, click "Adjust GitHub App Permissions" and give Vercel access to that one repo.
3. Configure:
   - **Root Directory:** leave `./` (repo root; `vercel.json` points the site at `web/`)
   - **Framework Preset:** Other
   - **Build Command / Output Directory / Install Command:** leave empty
   - **Environment Variables:** none here; `scripts/publish.sh` copies `VERTEX_API_KEY`, `GEMINI_API_KEY`, `TYPESAFE_API_KEY`, `RUN_PASSPHRASE` from `.env` with the Vercel CLI
4. Click **Deploy**. You get a URL like `https://promo-finder-xxxx.vercel.app`.
5. Leave **Settings → Deployment Protection → Vercel Authentication** OFF for production. If it's on, reviewers would be asked to log in to Vercel.

Alternative without the dashboard: put `VERCEL_TOKEN=...` in `.env` and run `sh scripts/publish.sh`, which deploys with the CLI.

## 4. Put the links into the deck and the site, then redeploy
```bash
.venv/bin/python scripts/set_links.py --repo https://github.com/YOUR_GITHUB_USERNAME/promo-finder --site https://YOUR-PROJECT.vercel.app
git add -A && git commit -m "Add public links" && git push
```
Vercel redeploys automatically on every push. Add `--video <loom url>` once you record the walkthrough.

## 5. Get the passphrase for the submission form
```bash
grep SITE_PASSPHRASE .env
```
Put it in the form next to the site link, e.g. "Full 50-episode results: open the site, tab 'Kuku show', passphrase …". Don't put it in the repo, the deck or the video.

## 6. What to submit
| Form item | What to give |
|---|---|
| Solution doc (PDF) | `deck/solution.pdf` (upload the file; also downloadable from the site after unlocking) |
| Prototype link | the Vercel URL (works for anyone; the full results need the passphrase) |
| Raw outputs | the Vercel URL → unlock → **All promos (CSV)**. Or zip `runs/v3_final/` and share it via a restricted Google Drive link |
| Code | GitHub repo. **Note:** a private repo does not open for reviewers. Either add them as collaborators, or make the repo public (Settings → General → Change visibility). That's safe: keys and plaintext Kuku content are not in it. |

## 7. After the assignment
Rotate the Gemini, Vertex and TypeSafe keys. They appeared in a chat log, never in the repo.

## Updating later
After a new run: `.venv/bin/python deck/build_deck.py && .venv/bin/python scripts/build_site.py && git add -A && git commit -m "Update results" && git push`.
