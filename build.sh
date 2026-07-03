#!/usr/bin/env bash
# build.sh — assemble ONLY the public web files into dist/ for Cloudflare Pages.
#
# The build scripts (scripts/), CI config (.github/), the Apache-only .htaccess,
# docs and the dev-only preview page are deliberately left OUT of the deployed
# output, so none of the source is ever publicly served.
#
# Cloudflare Pages project settings:
#   Build command:            bash build.sh
#   Build output directory:   dist
#
# Every push to main (including the daily deal-bot commits) re-runs this and
# redeploys automatically. dist/ is build output — it is git-ignored.
set -euo pipefail

# Fetch the self-hosted brand fonts (Sora + DM Sans) fresh on every deploy.
# They are intentionally NOT committed to git — this pulls them into fonts/ so
# the copy step below bundles them into dist/. Non-fatal by design: if the
# download ever fails, the deploy still succeeds and the site falls back to
# clean system fonts (exactly as it does today).
echo "Fetching brand fonts…"
bash scripts/get_fonts.sh || echo "⚠ Font fetch failed — deploying with system-font fallback."

rm -rf dist
mkdir dist

# Copy the whole tree into dist/, excluding source, CI, docs and dev artifacts.
# New daily-generated pages (deal-*.html, cat-*.html, feed.xml, sitemap.xml,
# data/deals.json) are pattern-matched automatically, so nothing is missed.
tar \
  --exclude='./dist' \
  --exclude='./.git' \
  --exclude='./scripts' \
  --exclude='./.github' \
  --exclude='./.memories' \
  --exclude='./node_modules' \
  --exclude='./.htaccess' \
  --exclude='./preview.html' \
  --exclude='./lobangking-site.zip' \
  --exclude='*.py' \
  --exclude='*.md' \
  --exclude='*.yml' \
  --exclude='*.yaml' \
  --exclude='*.toml' \
  --exclude='*.lock' \
  -cf - . | tar -xf - -C dist

echo "dist/ assembled — $(find dist -type f | wc -l) files served; source & CI excluded."
