# 🚀 Deploy SERPRadio NOW - Complete Guide

**Goal:** Get SERPRadio fully deployed and operational in under 1 hour

**What you'll deploy:**
- ✅ Backend API (Railway)
- ✅ Pricing Worker (Railway or GitHub Actions)
- ✅ Database (Supabase)
- ✅ Frontend (Lovable)

---

## 📋 Prerequisites

**You need:**
- [x] Supabase URL: `https://bulcmonhcvqljorhiqgk.supabase.co` ✅
- [x] Parallel API Key: `HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe` ✅
- [ ] Supabase Service Role Key (get from Supabase dashboard)
- [ ] Railway account (https://railway.app)
- [ ] GitHub access to this repo

---

## ⚡ Quick Deploy (30 minutes)

### Phase 1: Database Setup (5 minutes)

1. **Go to Supabase Dashboard:**
   https://supabase.com/dashboard/project/bulcmonhcvqljorhiqgk

2. **Get Service Role Key:**
   - Settings → API → service_role (secret)
   - Copy the key starting with `eyJhbGci...`

3. **Apply SQL Migrations:**
   - SQL Editor → New Query
   - Copy/paste and run these files IN ORDER:
     - `sql/000_init_schema.sql`
     - `sql/board_feed_schema.sql`
     - `sql/best_time_schema.sql`
     - `sql/010_notification_engine.sql`
     - `sql/020_deal_awareness.sql` ⭐
     - `sql/021_refresh_helpers.sql` ⭐

4. **Create Storage Buckets:**
   - Storage → New Bucket → `serpradio-artifacts` (private)
   - Storage → New Bucket → `serpradio-public` (public)

### Phase 2: Deploy Backend API (10 minutes)

1. **Go to Railway:**
   https://railway.app/new

2. **Deploy from GitHub:**
   - Click "Deploy from GitHub repo"
   - Select `jamesfgibbons/tgflightsfromnyc`
   - Railway auto-detects `Dockerfile` and `railway.json`

3. **Set Environment Variables:**
   - Service → Variables → Raw Editor
   - Paste this (fill in your values):

```env
# Database (REQUIRED)
SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGci...YOUR_SERVICE_ROLE_KEY_HERE
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public

# Security
ADMIN_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=https://your-app.lovable.dev,http://localhost:5173

# Audio
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

# Config paths
DESTINATION_ONTOLOGY_PATH=config/destination_ontology.yaml
VIBE_PALETTES_PATH=config/vibe_palettes.yaml
VIBE_RULES_PATH=config/vibe_rules.yaml
```

4. **Deploy:**
   - Click "Deploy"
   - Wait 3-5 minutes
   - Copy your Railway URL: `https://YOUR-SERVICE.up.railway.app`

5. **Test Backend:**
```bash
curl https://YOUR-SERVICE.up.railway.app/api/healthz
# Should return: {"status":"ok"}
```

### Phase 3: Deploy Pricing Worker (10 minutes)

**Choose ONE option:**

#### Option A: Railway Worker (Recommended)

1. **Create new service in Railway:**
   - Same project → + New → Empty Service
   - Name: "SERPRadio Worker"

2. **Connect GitHub:**
   - Settings → Connect: `jamesfgibbons/tgflightsfromnyc`
   - Source → Dockerfile: `Dockerfile.worker`

3. **Set Variables:**
```env
# Pricing API
PRICE_SOURCE=parallel
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe

# Database (same as main service)
SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGci...YOUR_SERVICE_ROLE_KEY_HERE

# Worker config
REFRESH_INTERVAL_HOURS=6
NYC_ORIGINS=JFK,EWR,LGA
TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN
```

4. **Deploy & Verify:**
   - Click Deploy
   - Logs → Look for "Starting price refresh cycle"

#### Option B: GitHub Actions (Free)

1. **Add GitHub Secrets:**
   - GitHub → Settings → Secrets and variables → Actions
   - Add:
     - `PARALLEL_API_KEY` = `HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe`
     - `SUPABASE_URL` = `https://bulcmonhcvqljorhiqgk.supabase.co`
     - `SUPABASE_SERVICE_ROLE` = your-service-role-key

2. **Enable Actions:**
   - Actions tab → Enable workflows
   - Workflow runs every 6 hours automatically

3. **Manual Test:**
   - Actions → Price Refresh Worker → Run workflow

### Phase 4: Seed Sample Data (5 minutes)

**While waiting for first price refresh, seed test data:**

```bash
# Clone repo locally
git clone https://github.com/jamesfgibbons/tgflightsfromnyc.git
cd tgflightsfromnyc

# Install dependencies
pip install supabase

# Set environment
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-service-role-key

# Seed sample data (10 routes, 120 days of data)
python scripts/seed_sample_prices.py --routes 10
```

**Expected output:**
```
🌱 Seeding Sample Flight Prices
============================================================
Generated 12,000+ observations
Inserting in batches...
✅ Successfully inserted 12,000 observations
✅ Materialized view refreshed
🎉 Sample data seeded successfully!
```

### Phase 5: Deploy Frontend (Lovable)

1. **Update Lovable config:**
   - Create `public/config.json`:
```json
{
  "VITE_API_BASE": "https://YOUR-SERVICE.up.railway.app"
}
```

2. **Update Railway CORS:**
   - Add your Lovable URL to `CORS_ORIGINS`
   - Example: `https://your-app.lovable.dev,https://*.lovable.dev`

3. **Deploy Lovable:**
   - Lovable will auto-deploy on push
   - Check deployment URL

---

## ✅ Verify Everything Works

**Run automated verification:**

```bash
export API_BASE=https://YOUR-SERVICE.up.railway.app
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-service-role-key

python scripts/verify_deployment.py
```

**Expected output:**
```
🔍 SERPRadio Deployment Verification
======================================================================
  1. Environment Configuration
======================================================================
✅ API_BASE set
✅ SUPABASE_URL set
✅ SUPABASE_SERVICE_ROLE set

======================================================================
  2. Database Connection & Schema
======================================================================
✅ Supabase client initialized
✅ Table 'price_observation' exists
✅ Table 'route_baseline_30d' exists
✅ RPC function 'evaluate_deal' exists

======================================================================
  3. Price Data
======================================================================
✅ Price observations exist (Found 12,000+ observations)
✅ Baseline data exists (Found 100+ route baselines)

======================================================================
  4. API Endpoints
======================================================================
✅ Health endpoint (/api/healthz)
✅ Deals health check
✅ Deal evaluation
✅ Board feed endpoint

======================================================================
  5. Deal Awareness Feature
======================================================================
✅ Response structure valid
✅ Has baseline data (Recommendation: BUY, Score: 85)
✅ Baseline percentiles valid (P25=$180 P50=$220 P75=$280)

======================================================================
  Verification Summary
======================================================================
Total checks: 15
✅ Passed: 15
❌ Failed: 0
Success rate: 100.0%

🎉 All checks passed! Deployment is ready.
```

---

## 🎯 Manual Tests

### Test Deal Evaluation
```bash
curl "$API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3"
```

**Expected response:**
```json
{
  "origin": "JFK",
  "dest": "MIA",
  "month": 3,
  "cabin": "economy",
  "has_data": true,
  "recommendation": "BUY",
  "deal_score": 85,
  "current_low": 180.50,
  "baseline": {
    "p25": 200.00,
    "p50": 240.00,
    "p75": 280.00
  },
  "rationale": "Current price ($180.50) is below P25 baseline - excellent deal!",
  "sweet_spot_window": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  }
}
```

### Test Board Feed
```bash
curl "$API_BASE/api/board/feed?origins=JFK&limit=5"
```

### Test VibeNet Generation
```bash
curl -X POST "$API_BASE/vibenet/generate" \
  -H "content-type: application/json" \
  -d '{
    "data": [0.2, 0.4, 0.6, 0.8, 1.0],
    "controls": {"bars": 8, "tempo_hint": 112},
    "meta": {"origin": "JFK", "destination": "MIA"}
  }'
```

---

## 🔍 Monitor & Debug

### Railway Logs
```bash
# Backend API
railway logs --service serpradio

# Worker
railway logs --service serpradio-worker
```

### GitHub Actions Logs
- Actions → Price Refresh Worker → Latest run
- Download artifacts for detailed logs

### Database Metrics
```sql
-- Check price data
SELECT COUNT(*) FROM price_observation;
SELECT source, COUNT(*) FROM price_observation GROUP BY source;

-- Check baselines
SELECT COUNT(*) FROM route_baseline_30d;
SELECT * FROM route_baseline_30d ORDER BY p25_30d LIMIT 10;

-- Check notifications
SELECT * FROM notification_event ORDER BY created_at DESC LIMIT 10;
```

---

## 🐛 Troubleshooting

### No price data?
1. Check worker logs for errors
2. Verify Parallel API key is correct
3. Seed sample data: `python scripts/seed_sample_prices.py`

### Deal API returns "no data"?
1. Run: `SELECT COUNT(*) FROM price_observation;`
2. If empty, run worker or seed sample data
3. Refresh materialized view: `SELECT refresh_baselines_nonconcurrent();`

### CORS errors on frontend?
1. Check `CORS_ORIGINS` in Railway includes your Lovable URL
2. Format: `https://your-app.lovable.dev,https://*.lovable.dev`
3. Redeploy Railway service after CORS update

### Worker not running?
1. Railway: Check logs for errors
2. GitHub Actions: Check Actions tab for failed runs
3. Verify API key and Supabase credentials

---

## 📞 Support & Next Steps

**Deployment complete! 🎉**

### What's working:
- ✅ Backend API with 40+ endpoints
- ✅ Deal awareness with BUY/TRACK/WAIT recommendations
- ✅ Pricing pipeline (6-hour refresh cycle)
- ✅ Board feed with split-flap display data
- ✅ VibeNet audio sonification
- ✅ Notifications for price drops

### Next steps:
1. Wire DealEvaluator component into Lovable pages
2. Configure model training loop (track user actions)
3. Add more destinations (expand TOP_DESTINATIONS)
4. Setup monitoring and alerts
5. Generate featured mixes (6-10 pre-rendered MP3s)

### Documentation:
- **LAUNCH_PLAN.md** - Complete deployment status
- **PRICING_API_SETUP.md** - Price API configuration
- **DEAL_AWARENESS_GUIDE.md** - Deal feature details
- **RAILWAY_QUICKSTART.md** - Detailed Railway guide

---

## 🎯 Checklist

- [ ] Supabase migrations applied (6 files)
- [ ] Storage buckets created (serpradio-artifacts, serpradio-public)
- [ ] Backend deployed to Railway
- [ ] Worker deployed (Railway or GitHub Actions)
- [ ] Sample data seeded
- [ ] Verification script passes all checks
- [ ] Frontend connected to Railway URL
- [ ] CORS configured correctly
- [ ] Manual tests pass (deal evaluation, board feed)
- [ ] Worker logs show successful price refresh

**Once all checked:** Your SERPRadio deployment is LIVE! 🚀
