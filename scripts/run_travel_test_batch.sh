#!/usr/bin/env bash
set -euo pipefail

echo "🎼 Running small travel test batch..."
python -m src.pipeline.run_pipeline \
  --vertical travel \
  --theme flights_from_nyc \
  --sub-themes non_brand_seo best_time_to_book hidden_city_hacks weekend_getaways caribbean_kokomo red_eye_deals \
  --tracks-per-theme 3 \
  --limit 18
echo "✅ Test batch finished. Try: curl -s http://localhost:8000/api/travel/subthemes | jq"

