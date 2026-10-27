#!/usr/bin/env bash
set -euo pipefail

cd /home/bvb/bvb-data-worker
source .venv/bin/activate

echo "[$(date '+%F %T')] Starting BVB daily pipeline"

python src/fetch_bvb.py
python src/metrics_generator.py
python scripts/publish_strategy.py

echo "[$(date '+%F %T')] BVB daily pipeline finished"
