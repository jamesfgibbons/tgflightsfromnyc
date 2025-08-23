# 🎵 SERP Radio Pipeline Integration Guide

## Overview

You now have TWO complementary approaches for building your Caribbean Kokomo cache:

1. **Structured Pipeline** (`serpradio-pipeline/`) - Strict JSON extraction for precise data
2. **Conversational Cache** (`serpradio_convo_cache/`) - Human-readable notes with YAML signals

Both write to the same Supabase instance and can be used together!

## 🚀 Quick Setup

### 1. Create ALL tables in Supabase

Run `sql/setup_supabase.sql` in your Supabase SQL Editor. This creates:

- `flight_price_data` - Raw offers from OpenAI
- `offers_enriched` - Optional enrichment details  
- `momentum_bands` - Audio player data
- `visibility_notes` - Conversational analyst notes
- `visibility_signals` - Machine-readable signals from notes
- Storage bucket `serpradio-public` with public read access

### 2. Update your credentials

Your Supabase URL has been updated to: `https://zkqgcksxvmhbryplppxy.supabase.co`

The `creds.env.txt` file in `serpradio-pipeline` already has this URL configured.

### 3. Test the structured pipeline

```bash
cd /Users/James/Documents/tg/src/serpradio-pipeline

# Load environment
export SUPABASE_URL="https://zkqgcksxvmhbryplppxy.supabase.co"
export SUPABASE_SERVICE_ROLE="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ1bGNtb25oY3ZxbGpvcmhpcWdrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTMwOTM5MiwiZXhwIjoyMDcwODg1MzkyfQ.72Xbm3GPhhD3-UkJq9PU9MuVe9A4yC_o9zWo1F7V5x0"
export OPENAI_API_KEY="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"
export DATA_SOURCE="openai"

# Run extraction
python3 -m src.pipeline.openai_extract_offers --days 1
```

### 4. Test the conversational cache

```bash
cd /Users/James/Documents/tg/serpradio_convo_cache

# Create environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create creds.env.txt with same credentials as above
# Then run:
./scripts/run_convo_cache.sh
```

## 🎯 When to Use Each Approach

### Use Structured Pipeline when you need:
- Precise price data for charts
- Consistent data format
- High-volume extraction
- Predictable schema

### Use Conversational Cache when you need:
- Human-readable summaries
- Voice-over content
- Web search citations
- Natural language insights

## 🔄 Hybrid Workflow

The best approach combines both:

1. **Morning**: Run conversational cache for human-friendly daily summaries
   ```bash
   cd serpradio_convo_cache && ./scripts/run_convo_cache.sh
   ```

2. **Throughout day**: Run structured extraction for precise data points
   ```bash
   cd serpradio-pipeline && python3 -m src.pipeline.openai_extract_offers --days 1
   ```

3. **Build momentum**: Combine both data sources for rich audio experiences
   ```bash
   # Uses data from both tables to create momentum_bands
   python3 -m src.pipeline.build_momentum --days 7
   ```

## 📊 Data Flow

```
Web Search → Conversational Cache → visibility_notes + visibility_signals
                                          ↓
                                    momentum_bands ← Audio Player
                                          ↑
OpenAI Structured → flight_price_data → enrichment → momentum calculation
```

## 🎵 Sonification Mapping

From `visibility_signals` (conversational):
- `price_low_est` → Jackpot earcon trigger
- `red_eye_share_est` → Tempo reduction
- `novelty_notes` → Accent motifs
- `confidence` → Reverb/brightness

From `flight_price_data` (structured):
- `price` → Exact pitch mapping
- `direct_flight` → Rhythm pattern
- `airline` → Instrument selection

## 🚨 Important Notes

1. **Both pipelines use the same Supabase** - They complement each other
2. **Service role key is for backend only** - Never expose in frontend
3. **Public read is enabled** - Lovable can read all tables with anon key
4. **Test with OPENAI_MOCK=1** - Both pipelines support mock mode

## 🔧 Troubleshooting

If you see "table doesn't exist":
1. Run the SQL file again
2. Check you're using the correct Supabase URL
3. Verify your service role key

If OpenAI extraction fails:
1. Check your API key is valid
2. Verify DATA_SOURCE="openai" is set
3. Try with OPENAI_MOCK=1 first

## 🎉 Next Steps

1. Set up daily cron jobs for both pipelines
2. Build a dashboard showing both data types
3. Create voice-overs from visibility_notes
4. Add more destinations beyond Caribbean

The combination of structured data + conversational insights gives you the best of both worlds!