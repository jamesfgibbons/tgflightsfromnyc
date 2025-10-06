#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-http://localhost:8000}

echo "== List vibes =="
curl -s "$BASE/vibenet/vibes" | jq '.items | length'

echo "== Screenshot-only (form fields) =="
curl -s -X POST "$BASE/api/vibe/screenshot" \
  -F artist="The Beach Boys" \
  -F title="Kokomo" | jq '{palette_slug,features_normalized}'

echo "== Generate from numeric data =="
curl -s -X POST "$BASE/vibenet/generate" -H 'Content-Type: application/json' \
  -d '{"vibe_slug":"caribbean_kokomo","data":[0.1,0.4,0.7,0.3,0.8,0.2],"controls":{"bars":16}}' \
  | jq '{job_id, sound_pack, mp3_url, midi_url, duration_sec}'

echo "== Subthemes summary =="
curl -s "$BASE/api/travel/subthemes" | jq

echo "== Filtered catalog: non_brand_seo JFK→LAS =="
curl -s "$BASE/api/travel/catalog?sub_theme=non_brand_seo&origin=JFK&destination=LAS&limit=5" | jq '{total, items: [.items[] | {title, sound_pack, mp3_url}]}'

echo "✓ Smoke complete"

