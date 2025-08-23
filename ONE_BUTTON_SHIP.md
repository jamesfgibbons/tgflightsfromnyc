# 🚀 SERP Radio - ONE BUTTON SHIP

**Ready-to-run Caribbean Kokomo pipeline with turnkey components integrated!**

## ✅ What's Been Built (Production-Ready)

### **🎵 Complete Turnkey Pipeline**
- **✅ Fetch**: NYC→Caribbean offers via official APIs (Kiwi Tequila, extensible to Amadeus/Duffel)
- **✅ Aggregate**: Quartiles, volatility, share-of-voice analysis  
- **✅ Enrich**: OpenAI GPT-4o-mini JSON classification (brand/seller/novelty/Kokomo hints)
- **✅ Sonify**: Momentum band generator with Tropical Pop mapping
- **✅ Publish**: Catalog.json to public bucket/CDN for Lovable.dev consumption

### **📁 Integrated Components**
```
✅ Pipeline Modules (src/pipeline/):
   - fetch_offers_nyc_caribbean.py    # API fetching with normalization
   - build_visibility.py              # Statistical aggregation  
   - openai_enrich.py                 # GPT-4o-mini enrichment
   - build_momentum.py                # 45s Tropical Pop momentum bands
   - publish_catalog.py               # Public catalog for frontend
   - run_all.py                       # Orchestrator

✅ Executive Scripts (scripts/):
   - run_all.sh                       # ONE BUTTON: Complete pipeline
   - run_offers.sh                    # Stage 1: Fetch flight data
   - run_visibility.sh                # Stage 2: Compute statistics  
   - run_enrich.sh                    # Stage 3: OpenAI enrichment
   - run_momentum.sh                  # Stage 4: Sonification prep
   - run_publish.sh                   # Stage 5: Catalog publishing

✅ Database Schema:
   - sql/caribbean_pipeline_schema.sql # Turnkey Supabase tables
   - sql/caribbean_view.sql           # Frontend-ready views
```

## 🚀 ONE BUTTON EXECUTION

### **Step 1: Setup (One-time)**
```bash
# 1. Fill 3 API keys in creds.env.txt
nano creds.env.txt
# PASTE: SUPABASE_SERVICE_ROLE, TEQUILA_API_KEY (OpenAI already filled)

# 2. Create Supabase tables (SQL Editor)
# PASTE: sql/caribbean_pipeline_schema.sql
# PASTE: sql/caribbean_view.sql

# 3. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### **Step 2: Press The Button** 🔴
```bash
source .venv/bin/activate
./scripts/run_all.sh
```

**That's it!** This runs the complete Caribbean Kokomo pipeline:

1. **Fetch** (14 days NYC→Caribbean offers)
2. **Aggregate** (price quartiles, volatility, SOV)  
3. **Enrich** (OpenAI brand/novelty classification)
4. **Sonify** (45-second Tropical Pop momentum bands)
5. **Publish** (catalog.json to public bucket)

## 🏝️ What You Get (Caribbean Kokomo Features)

### **Smart Data Pipeline**
- **NYC Airports**: JFK, LGA, EWR, HPN, ISP, SWF
- **Caribbean Destinations**: SJU, STT, STX, SDQ, PUJ, POP, STI, MBJ, KIN, AUA, CUR, BON, BGI, ANU, SKB, EIS, DOM, GND, SXM, PTP, FDF, NAS, GGT, ELH, FPO, GCM, PLS
- **Kiwi Tequila API**: Live flight pricing with normalization
- **14-day Forward Scan**: Real-time offers with competitive analysis

### **OpenAI Enhancement** 
- **Model**: GPT-4o-mini (cost-effective, structured JSON)
- **Classification**: `brand_seller`, `seller_type`, `routing`, `novelty_score`, `kokomo_hint`
- **Kokomo Hints**: steel_drums, marimba, wind_chimes, none
- **Cost Control**: Idempotent caching, batch-ready design

### **Sonification Engine**
- **Sound Pack**: Tropical Pop @ 104 BPM
- **Duration**: 45 seconds with 4 momentum segments
- **Earcons**: Jackpot (< $85), volatility spikes, airline vs OTA wins
- **Bargain Detection**: Positive segments when `price_min` << `price_median`

### **Frontend Integration**
- **Catalog Endpoint**: `catalog/travel/flights_from_nyc/caribbean_kokomo/catalog.json`
- **Live Data**: Supabase `vw_caribbean_visibility` view
- **Audio Files**: Pre-generated MP3/MIDI in public bucket
- **Charts**: Leaderboards, volatility heatmaps, SOV breakdowns

## 📊 Verification Checklist

After running `./scripts/run_all.sh`, verify:

### **✅ Supabase Tables Populated**
- [ ] `flight_offers`: NYC→Caribbean rows for next 14 days
- [ ] `flight_visibility`: Price quartiles, volatility by route/day
- [ ] `visibility_enrichment`: OpenAI classifications with Kokomo hints
- [ ] `momentum_bands`: 45-second Tropical Pop tracks ready for playback

### **✅ Public Catalog Published**
- [ ] `catalog/travel/flights_from_nyc/caribbean_kokomo/catalog.json` in bucket
- [ ] Playable audio files uploaded to public bucket `/hero/*` path
- [ ] Frontend can fetch catalog via CDN/S3 public URL

### **✅ Lovable.dev Ready**
- [ ] Caribbean tab reads from `vw_caribbean_visibility` view
- [ ] Audio player loads Tropical Pop tracks with steel drum earcons
- [ ] Jackpot triggers fire when NYC deals < $85
- [ ] Lead capture writes to `email_leads` with `source='kokomo_launch'`

## ⚡ Stage-by-Stage Execution (Optional)

If you want to run stages individually for testing:

```bash
./scripts/run_offers.sh          # Fetch 14 days of flight data
./scripts/run_visibility.sh      # Compute price statistics  
./scripts/run_enrich.sh          # OpenAI brand/novelty analysis
./scripts/run_momentum.sh        # Generate momentum bands
./scripts/run_publish.sh         # Publish catalog to bucket
```

## 🔄 Automated Scheduling

**GitHub Actions**: `.github/workflows/serpradio_daily.yml`
- **09:00 UTC**: Caribbean (Kokomo) refresh
- **12:00 UTC**: Budget carriers refresh  
- **21:00 UTC**: Red-eye deals refresh

## 🎯 Why This "Sounds Like Wow"

1. **Hear Bargains**: Positive segments surge when `price_min` < 85% of `price_median`
2. **Hear Volatility**: Rhythmic "jitter" when market volatility spikes ≥15%
3. **Hear Novelty**: High novelty scores → brighter, syncopated musical moments
4. **Hear Islands**: Steel drums fire on jackpot deals, marimba on price drops, wind chimes on new routes

## 🚀 Ready to Ship!

**Press the button and open the Caribbean tab in Lovable.dev!**

You'll have a living audio fabric: Caribbean "Kokomo" insights cached via OpenAI, surfaced in real-time charts, and played as Tropical Pop with steel-drum earcons when NYC bargains hit jackpot territory.

---

### 🔧 Extend It
- **Add Vegas**: Update `geo_registry.py` with West Coast airports
- **Add Red-Eye**: Same pipeline with time-window filters
- **Add Providers**: Swap Kiwi for Amadeus/Duffel in `flights_provider.py`
- **Batch OpenAI**: Port `openai_enrich.py` to Batch API for volume discounts