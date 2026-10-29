#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs
python3 -I src/analysis.py data/cookie_cats.csv src/metrics.sql outputs > outputs/analysis_log.txt
python3 -I src/make_charts.py outputs/results.json outputs
python3 -I src/build_docs.py outputs/results.json .
echo "Done. See README.md, memo.md and outputs/."
