#!/usr/bin/env bash
# Downloads the public Cookie Cats A/B dataset (from a GitHub mirror) into data/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data
curl -sSL -o data/cookie_cats.csv \
  "https://raw.githubusercontent.com/robguilarr/ab_testing_cookie_cats/main/datasets/cookie_cats.csv"
lines=$(wc -l < data/cookie_cats.csv)
if [ "$lines" -lt 90000 ]; then
  echo "Unexpected file size ($lines lines). Download may have failed." >&2
  exit 1
fi
echo "Downloaded data/cookie_cats.csv ($lines lines)"
