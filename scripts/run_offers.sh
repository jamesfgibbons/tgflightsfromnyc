#!/usr/bin/env bash
set -euo pipefail
export $(cat creds.env.txt | grep -v '^#' | xargs)
python -m src.pipeline.fetch_offers_nyc_caribbean --days ${DAYS:-14} --nonstop-only
