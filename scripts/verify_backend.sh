#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-}"
if [ -z "$BASE_URL" ]; then
  echo "Usage: $0 https://your-backend-host" >&2
  exit 2
fi

echo "== Checking $BASE_URL =="
echo "-- /api/healthz --"
curl -fsS -m 20 "$BASE_URL/api/healthz" || true
echo

echo "-- /api/board/feed --"
curl -fsS -m 20 "$BASE_URL/api/board/feed?target=keywords&limit=5&lookback_days=30" || true
echo

echo "-- /api/travel/routes_nyc --"
curl -fsS -m 20 "$BASE_URL/api/travel/routes_nyc?origin=JFK&limit=5" || true
echo

echo "-- /api/travel/price_quotes_latest --"
curl -fsS -m 20 "$BASE_URL/api/travel/price_quotes_latest?origin=JFK&limit=5" || true
echo

echo "Done."
