#!/usr/bin/env bash
# Acceptance test for Caribbean Kokomo pipeline - full workflow validation
set -euo pipefail

echo "🏝️🔊 Running Caribbean Kokomo Pipeline Acceptance Test..."

# Load environment variables
if [ -f creds.env.txt ]; then
    set -a
    source <(cat creds.env.txt | grep -v '^#' | grep -v '^$')
    set +a
else
    echo "❌ Error: creds.env.txt not found. Please create it from creds.env.example"
    exit 1
fi

# Full acceptance test parameters
DAYS=7
echo "📊 Acceptance test parameters:"
echo "  - Days: $DAYS (full week)"
echo "  - Routes: All NYC→Caribbean"
echo "  - Limit: None (full data)"

# Pre-flight checks
echo "🔍 Pre-flight validation..."

# Check required environment variables
REQUIRED_VARS=("OPENAI_API_KEY" "SUPABASE_URL" "SUPABASE_SERVICE_ROLE" "TEQUILA_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "❌ Error: $var not set in environment"
        exit 1
    fi
done
echo "✅ Environment variables validated"

# Check Python dependencies
python -c "import openai, supabase, boto3, requests, pandas, numpy" 2>/dev/null || {
    echo "❌ Error: Missing Python dependencies. Run: pip install -r requirements.txt"
    exit 1
}
echo "✅ Python dependencies validated"

# Step 1: Fetch offers (full dataset)
echo "1️⃣ Fetching flight offers (full week)..."
START_TIME=$(date +%s)
python -m src.pipeline.fetch_offers_nyc_caribbean --days $DAYS --nonstop-only
FETCH_TIME=$(($(date +%s) - START_TIME))
echo "   ⏱️  Fetch completed in ${FETCH_TIME}s"

# Step 2: Build visibility
echo "2️⃣ Building visibility stats..."
START_TIME=$(date +%s)
python -m src.pipeline.build_visibility --days $DAYS
VISIBILITY_TIME=$(($(date +%s) - START_TIME))
echo "   ⏱️  Visibility completed in ${VISIBILITY_TIME}s"

# Step 3: OpenAI enrichment
echo "3️⃣ Running OpenAI enrichment..."
START_TIME=$(date +%s)
python -m src.pipeline.openai_enrich --days $DAYS
ENRICH_TIME=$(($(date +%s) - START_TIME))
echo "   ⏱️  Enrichment completed in ${ENRICH_TIME}s"

# Step 4: Build momentum bands
echo "4️⃣ Building momentum bands..."
START_TIME=$(date +%s)
python -m src.pipeline.build_momentum --days $DAYS
MOMENTUM_TIME=$(($(date +%s) - START_TIME))
echo "   ⏱️  Momentum completed in ${MOMENTUM_TIME}s"

# Step 5: Publish catalog
echo "5️⃣ Publishing catalog..."
START_TIME=$(date +%s)
python -m src.pipeline.publish_catalog
PUBLISH_TIME=$(($(date +%s) - START_TIME))
echo "   ⏱️  Publish completed in ${PUBLISH_TIME}s"

# Comprehensive validation
echo "🔍 Running comprehensive validation..."

# Validate catalog structure
if [ -f "catalog.json" ]; then
    echo "✅ catalog.json created"
    python tools/validate_catalog.py catalog.json
else
    echo "❌ catalog.json not found"
    exit 1
fi

# Check track count
TRACK_COUNT=$(python -c "import json; data=json.load(open('catalog.json')); print(len(data.get('tracks', [])))")
if [ "$TRACK_COUNT" -ge 10 ]; then
    echo "✅ Catalog contains $TRACK_COUNT tracks (minimum 10 met)"
else
    echo "❌ Catalog contains only $TRACK_COUNT tracks (minimum 10 required)"
    exit 1
fi

# Validate audio files
echo "🎵 Validating audio files..."
python tools/reconcile_catalog.py catalog.json

# Check LUFS levels
echo "🔊 Checking audio levels..."
python tools/lufs_check.py catalog.json

# Data quality checks
echo "📊 Running data quality checks..."

# Check for Caribbean destinations
CARIBBEAN_COUNT=$(python -c "
import json
data = json.load(open('catalog.json'))
caribbean_routes = [t for t in data.get('tracks', []) if any(dest in t.get('route', '') for dest in ['STT', 'STI', 'STX', 'SJU', 'MBJ', 'CUR', 'AUA'])]
print(len(caribbean_routes))
")

if [ "$CARIBBEAN_COUNT" -gt 0 ]; then
    echo "✅ Found $CARIBBEAN_COUNT Caribbean routes"
else
    echo "❌ No Caribbean routes found"
    exit 1
fi

# Check price diversity
PRICE_RANGE=$(python -c "
import json
data = json.load(open('catalog.json'))
prices = [float(t.get('price', 0)) for t in data.get('tracks', []) if t.get('price')]
if prices:
    print(f'{min(prices):.0f}-{max(prices):.0f}')
else:
    print('0-0')
")

echo "✅ Price range: \$$PRICE_RANGE"

# Check for jackpot deals (< $85)
JACKPOT_COUNT=$(python -c "
import json
data = json.load(open('catalog.json'))
jackpots = [t for t in data.get('tracks', []) if float(t.get('price', 999)) < 85]
print(len(jackpots))
")

echo "✅ Found $JACKPOT_COUNT jackpot deals (< \$85)"

# Performance summary
TOTAL_TIME=$((FETCH_TIME + VISIBILITY_TIME + ENRICH_TIME + MOMENTUM_TIME + PUBLISH_TIME))
echo ""
echo "⏱️  Performance Summary:"
echo "   Fetch:      ${FETCH_TIME}s"
echo "   Visibility: ${VISIBILITY_TIME}s"
echo "   Enrichment: ${ENRICH_TIME}s"
echo "   Momentum:   ${MOMENTUM_TIME}s"
echo "   Publish:    ${PUBLISH_TIME}s"
echo "   Total:      ${TOTAL_TIME}s"

echo ""
echo "🎉 Acceptance test completed successfully!"
echo "📊 Pipeline metrics:"
echo "   - Tracks generated: $TRACK_COUNT"
echo "   - Caribbean routes: $CARIBBEAN_COUNT"
echo "   - Price range: \$$PRICE_RANGE"
echo "   - Jackpot deals: $JACKPOT_COUNT"
echo "   - Total runtime: ${TOTAL_TIME}s"
echo ""
echo "✅ Ready for production deployment!"
echo "🌐 Catalog available at: catalog.json"