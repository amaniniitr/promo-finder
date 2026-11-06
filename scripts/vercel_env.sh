#!/bin/sh
# Copies the 4 server-side secrets from .env into the Vercel project (production), then redeploys.
# Keys go terminal -> Vercel directly; they never appear in the browser, the repo or a chat.
# Usage (from the promo-finder folder, after the project exists on Vercel):  sh scripts/vercel_env.sh
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "no .env here"; exit 1; }
npx --yes vercel@latest whoami >/dev/null 2>&1 || npx --yes vercel@latest login
npx --yes vercel@latest link --yes --project promo-finder
for NAME in VERTEX_API_KEY GEMINI_API_KEY TYPESAFE_API_KEY RUN_PASSPHRASE; do
  VAL=$(grep "^$NAME=" .env | head -1 | cut -d= -f2-)
  if [ -z "$VAL" ]; then echo "skip $NAME (not in .env)"; continue; fi
  npx --yes vercel@latest env rm "$NAME" production --yes >/dev/null 2>&1 || true
  printf "%s" "$VAL" | npx --yes vercel@latest env add "$NAME" production >/dev/null
  echo "set $NAME"
done
npx --yes vercel@latest --prod --yes
