#!/usr/bin/env bash
# Smoke test for Caribbean Kokomo pipeline - fast validation with constrained parameters
set -euo pipefail

echo "🏝️ Running Caribbean Kokomo Pipeline Smoke Test..."

# Load environment variables
if [ -f creds.env.txt ]; then
    set -a
    source <(cat creds.env.txt | grep -v '^#' | grep -v '^$')
    set +a
else
    echo "❌ Error: creds.env.txt not found. Please create it from creds.env.example"
    exit 1
fi

# Smoke test parameters (constrained for speed)
DAYS=1
THROTTLE=0.1  # Faster for testing

echo "📊 Smoke test parameters:"
echo "  - Days: $DAYS (minimal data)"
echo "  - Throttle: ${THROTTLE}s (faster for testing)"
echo "  - Routes: All NYC→Caribbean (limited by short timeframe)"

# Change to the serpradio-pipeline directory (but keep environment loaded)
cd src/serpradio-pipeline
# Copy creds file to this directory so environment loads correctly
cp ../../creds.env.txt ./creds.env.txt

# Step 1: Fetch offers (constrained)
echo "1️⃣ Fetching flight offers..."
python3 -m src.pipeline.fetch_offers_nyc_caribbean --days $DAYS --nonstop-only --throttle $THROTTLE

# Step 2: Build visibility
echo "2️⃣ Building visibility stats..."
python3 -m src.pipeline.build_visibility --days $DAYS

# Step 3: OpenAI enrichment (limited scope)
echo "3️⃣ Running OpenAI enrichment..."
python3 -m src.pipeline.openai_enrich --days $DAYS

# Step 4: Build momentum bands
echo "4️⃣ Building momentum bands..."
python3 -m src.pipeline.build_momentum --days $DAYS

# Step 5: Publish catalog
echo "5️⃣ Publishing catalog..."
python3 -m src.pipeline.publish_catalog

# Return to original directory
cd ../..

# Validation checks
echo "🔍 Running validation checks..."

# Check if catalog.json was created
if [ -f "catalog.json" ]; then
    echo "✅ catalog.json created"
    
    # Run catalog validation
    python3 tools/validate_catalog.py catalog.json
    
    # Check catalog has at least 1 track
    TRACK_COUNT=$(python3 -c "import json; data=json.load(open('catalog.json')); print(len(data.get('tracks', [])))")
    if [ "$TRACK_COUNT" -gt 0 ]; then
        echo "✅ Catalog contains $TRACK_COUNT tracks"
    else
        echo "❌ Catalog is empty"
        exit 1
    fi
else
    echo "❌ catalog.json not found"
    exit 1
fi

# Run audio reconciliation
echo "🎵 Checking audio files..."
python3 tools/reconcile_catalog.py catalog.json

echo "🎉 Smoke test completed successfully!"
echo "📂 Check catalog.json for results"
echo "🎯 Ready for acceptance testing"