#!/usr/bin/env bash
# Download the self-hosted brand fonts (Sora + DM Sans) into ../fonts with the
# stable filenames the site expects. Run once from the repo root:
#     bash scripts/get_fonts.sh
# Requires curl + unzip (standard on macOS/Linux; use Git Bash or WSL on Windows).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p fonts
API="https://gwfh.mranftl.com/api/fonts"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading Sora (600, 700, 800)…"
curl -fsSL "$API/sora?download=zip&subsets=latin&variants=600,700,800&formats=woff2" -o "$tmp/sora.zip"
unzip -oq "$tmp/sora.zip" -d "$tmp/sora"
for w in 600 700 800; do mv "$tmp"/sora/*"$w"*.woff2 "fonts/sora-$w.woff2"; done

echo "Downloading DM Sans (400, 500, 600, 700)…"
curl -fsSL "$API/dm-sans?download=zip&subsets=latin&variants=regular,500,600,700&formats=woff2" -o "$tmp/dm.zip"
unzip -oq "$tmp/dm.zip" -d "$tmp/dm"
mv "$tmp"/dm/*regular*.woff2 "fonts/dmsans-400.woff2"
for w in 500 600 700; do mv "$tmp"/dm/*"$w"*.woff2 "fonts/dmsans-$w.woff2"; done

echo "Done. Saved to ./fonts:"
ls -1 fonts
