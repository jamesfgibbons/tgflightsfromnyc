# 🚀 SERP Radio Launch Checklist - One Button Ship

## 0) Pre-flight Verification

### ✅ What you already have:
- [x] Caribbean ETL that ingests Google keyword CSVs
- [x] NYC + Caribbean registries (airports, region/country maps)
- [x] Storage abstraction defaulting to `serpradio-artifacts` bucket
- [x] NYC airports: `JFK, LGA, EWR, HPN, ISP, SWF`
- [x] Caribbean airports: `SJU, STT, STX, SDQ, PUJ, POP, STI, MBJ, KIN, AUA, CUR, BON, BGI, ANU, SKB, EIS, DOM, GND, SXM, PTP, FDF, NAS, GGT, ELH, FPO, GCM, PLS`

## 1) One-time Setup

### 1.1 ✅ Fill in `creds.env.txt` (3 values to PASTE):
```bash
# Edit the file and paste from your dashboards:
nano creds.env.txt

# Fill these 3 lines:
SUPABASE_SERVICE_ROLE=<PASTE from Supabase Settings → API → service_role>
TEQUILA_API_KEY=<PASTE from Kiwi Tequila if using live prices>
# OpenAI key already filled
```

### 1.2 ✅ Supabase Schema Setup:
1. Open Supabase SQL Editor
2. Paste and run: `sql/schema_cache_tables.sql`
3. Paste and run: `sql/caribbean_view.sql`

### 1.3 ✅ Lovable Frontend Config:
- File `public/config.json` created ✅
- CORS origins configured ✅

## 2) ✅ Scripts Ready (exact contents created)

All scripts are created and executable:
- [x] `scripts/run_caribbean_etl.sh` - ETL with CSV support
- [x] `scripts/run_cache_builder.sh` - OpenAI cache with gpt-4o-mini
- [x] `scripts/run_travel_pipeline_local.sh` - Multi-theme pipeline

## 3) 🚀 Execute Pipeline (exact order)

```bash
# 0) Activate environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Caribbean ETL → writes JSONs + latest_summary.json to storage
./scripts/run_caribbean_etl.sh
# Optional: ./scripts/run_caribbean_etl.sh data/google_caribbean.csv

# 2) Build OpenAI cache → saves to cache_jobs
./scripts/run_cache_builder.sh

# 3) Generate audio catalogs (all 4 themes, incl. Kokomo)
./scripts/run_travel_pipeline_local.sh
```

## 4) ✅ Verification Steps

### 4.1 Storage Verification:
Check these files exist in your bucket:
- [ ] `etl/caribbean_kokomo/raw_caribbean_*.json`
- [ ] `etl/caribbean_kokomo/visibility_records_*.json`
- [ ] `catalog/travel/flights_from_nyc/caribbean_kokomo/latest_summary.json` ⭐ (frontend reads this)

### 4.2 Supabase Verification:
- [ ] `cache_jobs` table has rows with `status='succeeded'`
- [ ] `flight_visibility` table has Caribbean rows
- [ ] `vw_caribbean_visibility` view returns data

### 4.3 Audio Verification:
- [ ] MP3/MIDI files uploaded to `serpradio-public-2025/hero/...`
- [ ] 24 tracks total (6 per sub-theme)
- [ ] Caribbean Kokomo tracks use "Tropical Pop" sound pack

## 5) ✅ Lovable.dev Frontend Integration

### 5.1 Caribbean Tab (Kokomo):
- **Summary source**: `GET https://serpradio-public-2025.s3.amazonaws.com/catalog/travel/flights_from_nyc/caribbean_kokomo/latest_summary.json`
- **Data source**: Supabase `vw_caribbean_visibility` view
- **Audio**: Tropical Pop sound pack, BPM=104
- **Earcons**: Jackpot when `rock_bottom_price_usd < 85`

### 5.2 Lead Capture:
- **Table**: Supabase `email_leads`
- **Tag**: Caribbean leads with `source='kokomo_launch'`

## 6) ✅ Sonification Cues (Caribbean-specific)

Configure these in your audio renderer:
- **Lowest price of day** → steel-drum ping at segment start
- **Jackpot (NYC→Caribbean < $85)** → ascending marimba arpeggio + brightness increase
- **Volatility spike (IQR ↑ ≥15%)** → surf crash + tempo wobble ±6 BPM for 2 bars
- **Airline beats OTA** → bell chime
- **OTA beats airline** → crystal ping

## 7) ✅ Scheduling (GitHub Actions)

- **File**: `.github/workflows/serpradio_daily.yml` ✅
- **Schedule**: 
  - 09:00 UTC: Caribbean (Kokomo)
  - 12:00 UTC: Budget carriers  
  - 21:00 UTC: Red-eye
- **Secrets needed in GitHub repo**:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE` 
  - `OPENAI_API_KEY`

## 8) Operational Guardrails

- [x] OpenAI spend cap: Set in OpenAI dashboard
- [x] Batch calls: Using gpt-4o-mini for cost efficiency
- [x] Idempotency: `prompt_hash` prevents duplicate charges
- [x] Storage TTLs: 60-90 days for offers, 30-60 days for catalogs
- [x] S3 public: Only `/hero/*` prefix public
- [x] CORS: 5 origins whitelisted exactly

## 9) 🎯 Acceptance Test (run in order)

1. [ ] `./scripts/run_caribbean_etl.sh` finishes; check bucket for 4 files, especially `catalog/travel/flights_from_nyc/caribbean_kokomo/latest_summary.json`
2. [ ] `./scripts/run_cache_builder.sh` inserts row into `cache_jobs` with `status='succeeded'`
3. [ ] `./scripts/run_travel_pipeline_local.sh` uploads 24 tracks to public S3 bucket
4. [ ] Lovable Caribbean tab shows destinations, volumes, and Tropical Pop playback with steel-drum earcons
5. [ ] Lead capture writes into `email_leads`
6. [ ] (Optional) Test with real GSC CSV

## 10) Troubleshooting Quick Hits

- **No files written?** Check `STORAGE_BUCKET=serpradio-artifacts-2025` in creds.env.txt
- **NYC/Caribbean filters off?** Verify airport codes in geo registry
- **Frontend 403 on audio?** Check bucket policy: only `/hero/*` public with `Cache-Control: public,max-age=86400`
- **Earcons not firing?** Verify momentum JSON thresholds and jackpot rule (`price < 85`)

---

## 🎵 Ready to Ship!

Run the three scripts in order and open the Caribbean tab. You'll have a **living audio fabric**: Caribbean "Kokomo" insights cached via OpenAI, surfaced in charts and played as Tropical Pop with steel-drum earcons when NYC bargains hit.

**Next**: Press the button! 🚀