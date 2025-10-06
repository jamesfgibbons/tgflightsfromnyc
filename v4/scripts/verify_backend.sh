#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-}"
if [ -z "$BASE_URL" ]; then
  echo "Usage: $0 https://your-backend" >&2
  exit 2
fi

echo "== Checking $BASE_URL =="
for path in   "/api/healthz"   "/api/board/feed?target=keywords&limit=3&lookback_days=30"   "/api/travel/routes_nyc?origin=JFK&limit=3"   "/api/travel/price_quotes_latest?origin=JFK&limit=3"; do
  echo "
-- $path --"
  curl -fsS -m 25 "$BASE_URL$path" || true
  echo
done

echo "Done."
