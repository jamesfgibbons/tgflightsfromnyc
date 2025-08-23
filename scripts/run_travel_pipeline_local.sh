#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "🎵 SERP Radio — Multi-theme NYC Flights Pipeline"
export $(grep -v '^#' creds.env.txt | xargs)

python -m src.pipeline.run_pipeline \
  --vertical travel \
  --theme flights_from_nyc \
  --sub-themes budget_carriers legacy_airlines red_eye_deals caribbean_kokomo \
  --tracks-per-theme 6 \
  --limit 24