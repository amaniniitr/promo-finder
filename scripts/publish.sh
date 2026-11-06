#!/bin/sh
# One-shot publish: GitHub push -> Vercel secrets + production deploy -> links baked in -> final push.
# Run from Terminal:   cd /Users/aman/Desktop/kuku/promo-finder && sh scripts/publish.sh
# Keys are copied from .env to Vercel by the Vercel CLI; they are never printed, committed or typed into a browser.
set -e
cd "$(dirname "$0")/.."
TOKEN=$(grep "^VERCEL_TOKEN=" .env | head -1 | cut -d= -f2-)
VCL="npx --yes vercel@latest${TOKEN:+ --token $TOKEN}"
say() { printf "\n\033[1;33m==> %s\033[0m\n" "$1"; }

say "1/5 Secret check (blocks the push if a key or plaintext Kuku script would be published)"
.venv/bin/python scripts/check_secrets.py

say "2/5 Push to GitHub"
if ! git remote get-url origin >/dev/null 2>&1; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo create promo-finder --public --source=. --remote=origin --description "Kuku AI Generalist - Problem 1 - promo finder (Aman Kumar, 22322004)"
    REPO=$(gh repo view --json url -q .url)
  else
    printf "Paste the GitHub repo URL Aside created (e.g. https://github.com/USER/promo-finder): "
    read REPO
  fi
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "$REPO"
fi
REPO=$(git remote get-url origin | sed 's/\.git$//')
git push -u origin main

if [ -z "$TOKEN" ]; then
  printf "\n\033[1;36mNow give Aside PART 2 (import the repo into Vercel). Press Enter here when Vercel shows the project.\033[0m "
  read _
fi

say "3/5 Vercel: log in (browser opens once), link the project Aside imported, copy secrets"
$VCL whoami >/dev/null 2>&1 || $VCL login
$VCL link --yes --project promo-finder
for NAME in VERTEX_API_KEY GEMINI_API_KEY TYPESAFE_API_KEY RUN_PASSPHRASE; do
  VAL=$(grep "^$NAME=" .env | head -1 | cut -d= -f2-)
  [ -z "$VAL" ] && { echo "  skip $NAME (not in .env)"; continue; }
  $VCL env rm "$NAME" production --yes >/dev/null 2>&1 || true
  printf "%s" "$VAL" | $VCL env add "$NAME" production >/dev/null
  echo "  set $NAME"
done

say "4/5 Production deploy"
$VCL --prod --yes | tee /tmp/vercel_deploy.log
SITE=$(grep -oE "https://[a-z0-9.-]+\.vercel\.app" /tmp/vercel_deploy.log | grep -v -- "-[a-z0-9]\{9\}-" | head -1)
[ -z "$SITE" ] && SITE=$(grep -oE "https://[a-z0-9.-]+\.vercel\.app" /tmp/vercel_deploy.log | tail -1)
printf "Production URL detected: %s\nPress Enter to accept, or paste the production domain shown in Vercel: " "$SITE"
read ALT; [ -n "$ALT" ] && SITE="$ALT"

say "5/5 Bake links into the deck + site, push (Vercel redeploys automatically)"
printf "Branch to show next to your name (Enter to skip): "; read BRANCH
if [ -n "$BRANCH" ]; then .venv/bin/python scripts/set_links.py --repo "$REPO" --site "$SITE" --branch "$BRANCH"
else .venv/bin/python scripts/set_links.py --repo "$REPO" --site "$SITE"; fi
git add -A && git commit -qm "Add live links" && git push
curl -s "$SITE/api/run" || true

say "Done. Paste into the submission form:"
echo "  Name / roll no.: Aman Kumar, 22322004"
echo "  Problem:         Problem 1 - Find the Promos"
echo "  Solution doc:    deck/solution.pdf (upload the file)"
echo "  Prototype:       $SITE   (tab '▶ Try it live')"
echo "  Code:            $REPO"
echo "  Raw outputs:     $SITE  -> tab 'Kuku show' -> unlock -> All promos (CSV)"
echo "  Passphrase:      $(grep '^RUN_PASSPHRASE=' .env | cut -d= -f2-)   (give only in the form)"
