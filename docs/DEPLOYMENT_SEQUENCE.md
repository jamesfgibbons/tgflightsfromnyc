# 🚀 SERPRadio - Complete Deployment Sequence

**This is your step-by-step playbook to get from zero to fully deployed.**

**Time Required:** 30-60 minutes
**Status:** All code complete, just needs deployment configuration

---

## ✅ Pre-Deployment Checklist

- [ ] Parallel API key: `HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe` ✅
- [ ] Supabase URL: `https://bulcmonhcvqljorhiqgk.supabase.co` ✅
- [ ] Supabase Service Role key: Get from dashboard ⏳
- [ ] Railway account: https://railway.app
- [ ] Lovable project: Ready for deployment

---

## 🔧 Phase 1: Supabase Setup (5 minutes)

### Step 1.1: Get Service Role Key

1. Go to: https://supabase.com/dashboard/project/bulcmonhcvqljorhiqgk
2. Click **Settings** (left sidebar)
3. Click **API**
4. Scroll to **service_role**
5. Click **Copy** (key starts with `eyJhbGci...`)
6. Save it - you'll need this multiple times

### Step 1.2: Apply SQL Migrations

In Supabase Dashboard → SQL Editor, run these **in order**:

```sql
-- 1. Base schema
-- Paste and run: sql/000_init_schema.sql

-- 2. Board feed
-- Paste and run: sql/board_feed_schema.sql

-- 3. Best-time booking
-- Paste and run: sql/best_time_schema.sql

-- 4. Notifications engine
-- Paste and run: sql/010_notification_engine.sql

-- 5. Deal awareness (CRITICAL)
-- Paste and run: sql/020_deal_awareness.sql

-- 6. Refresh helpers (CRITICAL)
-- Paste and run: sql/021_refresh_helpers.sql
```

### Step 1.3: Create Storage Buckets

In Supabase → Storage → New Bucket:

1. **Bucket name:** `serpradio-artifacts`
   - Public: **No** (private)
   - File size limit: 50 MB

2. **Bucket name:** `serpradio-public`
   - Public: **Yes**
   - File size limit: 50 MB

### Step 1.4: Verify

Run this in SQL Editor:

```sql
-- Should return 6 tables
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';

-- Should return 3 functions
SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public';
```

---

## 🚂 Phase 2: Deploy Backend API (10 minutes)

### Step 2.1: Connect Repository

1. Go to: https://railway.app/new
2. Click **Deploy from GitHub repo**
3. Select `jamesfgibbons/tgflightsfromnyc`
4. Railway auto-detects `Dockerfile` ✅

### Step 2.2: Configure Environment Variables

Railway → Service → Variables → **Raw Editor**

**Paste this** (update values in CAPS):

```env
# Database
SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_SERVICE_ROLE=YOUR_SERVICE_ROLE_KEY_HERE
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public

# Security
ADMIN_SECRET=YOUR_RANDOM_SECRET_HERE
CORS_ORIGINS=https://your-app.lovable.dev,http://localhost:5173

# Audio
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

# Config paths
DESTINATION_ONTOLOGY_PATH=config/destination_ontology.yaml
VIBE_PALETTES_PATH=config/vibe_palettes.yaml
VIBE_RULES_PATH=config/vibe_rules.yaml
```

**Generate ADMIN_SECRET:**
```bash
openssl rand -hex 32
# Or: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2.3: Deploy

1. Click **Deploy**
2. Wait 3-5 minutes for build
3. Copy your Railway URL: `https://YOUR-SERVICE.up.railway.app`

### Step 2.4: Test Backend

```bash
BASE=https://YOUR-SERVICE.up.railway.app

# Health check
curl "$BASE/api/healthz"
# Expected: {"status":"ok"}

# Board feed
curl "$BASE/api/board/feed?origins=JFK&limit=5"
# Expected: JSON with items array

# Deal health (will show "no data" until worker runs)
curl "$BASE/api/deals/health"
# Expected: {"status":"ok","worker_ready":false}
```

---

## ⚙️ Phase 3: Deploy Pricing Worker (10 minutes)

**Choose ONE option:**

### Option A: Railway Worker Service (Recommended)

#### Step 3A.1: Create New Service

1. Railway → Same project → **+ New** → **Empty Service**
2. Name: "SERPRadio Worker"

#### Step 3A.2: Connect Repository

1. Settings → Connect: `jamesfgibbons/tgflightsfromnyc`
2. Source → Dockerfile path: `Dockerfile.worker`

#### Step 3A.3: Configure Variables

```env
# Pricing API (FLEXIBLE - works with bulk or single mode)
PRICE_SOURCE=parallel
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
PARALLEL_ENDPOINT=https://api.parallel.com/v1/flights/search
PARALLEL_MODE=bulk
PARALLEL_TIMEOUT_SECONDS=60
PARALLEL_BATCH_SIZE=100
MONTHS_AHEAD=6

# Database (same as backend)
SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_SERVICE_ROLE=YOUR_SERVICE_ROLE_KEY_HERE

# Worker config
REFRESH_INTERVAL_HOURS=6
NYC_ORIGINS=JFK,EWR,LGA
TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL
```

#### Step 3A.4: Deploy & Monitor

1. Click **Deploy**
2. View logs:
   ```bash
   railway logs --service serpradio-worker
   ```

3. Watch for:
   - `"Initialized ParallelFetcher: endpoint=... mode=bulk"`
   - `"Starting price refresh cycle"`
   - `"Fetching prices: 60 routes × 6 windows = 360 queries"`
   - `"Fetched X price observations"`
   - `"Upserted X rows to price_observation table"`

### Option B: GitHub Actions (Free Alternative)

#### Step 3B.1: Add Repository Secrets

GitHub → Settings → Secrets and variables → Actions

Add these secrets:

```
PARALLEL_API_KEY = HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
SUPABASE_URL = https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_SERVICE_ROLE = your-service-role-key
```

#### Step 3B.2: Enable Workflow

1. Actions tab → Enable workflows
2. Workflow `.github/workflows/price_refresh.yml` runs every 6 hours

#### Step 3B.3: Manual Test

1. Actions → Price Refresh Worker
2. Click **Run workflow**
3. Select `parallel` as price source
4. Click **Run workflow**

---

## 🌱 Phase 4: Seed Initial Data (5 minutes)

**While waiting for first API refresh, seed test data:**

```bash
# Install dependencies
pip install supabase httpx

# Set environment
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-service-role-key

# Seed sample data (15 routes, 120 days of data)
python scripts/seed_sample_prices.py --routes 15

# Expected output:
# "Generated 18,000+ observations"
# "Successfully inserted 18,000 observations"
# "Materialized view refreshed"
```

---

## ✅ Phase 5: Verification (5 minutes)

### Step 5.1: Run Verification Script

```bash
export API_BASE=https://YOUR-SERVICE.up.railway.app
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-service-role-key

python scripts/verify_deployment.py
```

**Expected:** All 18 checks pass ✅

### Step 5.2: Manual API Tests

```bash
# Test deal evaluation
curl "$API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3"

# Expected response:
# {
#   "origin": "JFK",
#   "dest": "MIA",
#   "month": 3,
#   "has_data": true,
#   "recommendation": "BUY",
#   "deal_score": 85,
#   "current_low": 180.50,
#   "baseline": {"p25": 200.00, "p50": 240.00, "p75": 280.00}
# }
```

### Step 5.3: Check Database

```sql
-- Price observations
SELECT COUNT(*), source FROM price_observation GROUP BY source;
-- Should show 18,000+ from 'sample' or 'parallel'

-- Baselines
SELECT COUNT(*) FROM route_baseline_30d;
-- Should show 100+ route baselines

-- Recent prices
SELECT origin, dest, MIN(price_usd), MAX(price_usd), AVG(price_usd)
FROM price_observation
GROUP BY origin, dest
ORDER BY AVG(price_usd) DESC
LIMIT 10;
```

---

## 🌐 Phase 6: Connect Frontend (5 minutes)

### Step 6.1: Update Lovable Configuration

In your Lovable project, create/update `public/config.json`:

```json
{
  "VITE_API_BASE": "https://YOUR-SERVICE.up.railway.app"
}
```

**OR** set environment variable:
```
VITE_API_BASE=https://YOUR-SERVICE.up.railway.app
```

### Step 6.2: Update CORS

In Railway backend environment variables:

```env
CORS_ORIGINS=https://your-actual-app.lovable.dev,https://*.lovable.dev,http://localhost:5173
```

Redeploy Railway service after CORS update.

### Step 6.3: Deploy Lovable

1. Push changes to Lovable
2. Lovable auto-deploys
3. Get deployment URL

### Step 6.4: Test Frontend

1. Open: `https://your-app.lovable.dev`
2. Check browser console (no CORS errors)
3. Navigate to pages:
   - Home (board feed)
   - Deals page
   - Route pages (e.g., `/routes/jfk-to-mia`)

---

## 🎯 Final Validation Checklist

- [ ] Backend deployed and responding
- [ ] Worker deployed and running
- [ ] Database has price data (18,000+ rows)
- [ ] Baselines calculated (100+ routes)
- [ ] Deal API returns recommendations with `has_data: true`
- [ ] Board feed returns route data
- [ ] Frontend loads without CORS errors
- [ ] Frontend connects to Railway backend
- [ ] Manual tests pass (deal evaluation, board feed)
- [ ] Verification script passes 100%

---

## 📊 What's Working

Once all phases complete:

✅ **Backend API** - 40+ endpoints live
✅ **Pricing Worker** - Fetching prices every 6 hours
✅ **Deal Awareness** - BUY/TRACK/WAIT recommendations
✅ **Board Feed** - Split-flap display data
✅ **VibeNet** - Audio sonification
✅ **Frontend** - Connected to Railway
✅ **Database** - Price observations + baselines

---

## 🔧 Troubleshooting

### Worker Logs Show "PARALLEL_ENDPOINT is required"

**Fix:** Set `PARALLEL_ENDPOINT` in worker environment variables:
```
PARALLEL_ENDPOINT=https://api.parallel.com/v1/flights/search
```

### Worker Logs Show "bulk request failed: 400"

**Fix:** Try single mode:
```
PARALLEL_MODE=single
```

### Worker Logs Show "401 Unauthorized"

**Fix:** Verify API key is correct:
```
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
```

### Deal API Returns "no data"

**Cause:** No price observations yet

**Fix:**
1. Check worker logs for errors
2. OR seed sample data: `python scripts/seed_sample_prices.py`
3. Refresh materialized view: `SELECT refresh_baselines();`

### Frontend CORS Errors

**Fix:** Update Railway `CORS_ORIGINS` to include Lovable URL and redeploy

---

## 🎉 Success!

When all phases complete, you have:
- ✅ 60 NYC routes tracked
- ✅ Prices refreshed every 6 hours
- ✅ Deal recommendations working
- ✅ Frontend connected and live
- ✅ Full end-to-end pipeline operational

**Next Steps:**
1. Monitor worker logs for successful refreshes
2. Check deal recommendations improve as more data arrives
3. Add more routes via environment variables if desired
4. Configure alerts/monitoring
5. Generate featured mixes (optional)

---

## 📞 Quick Commands Reference

```bash
# Test backend
curl https://YOUR-SERVICE.up.railway.app/api/healthz

# Test deals
curl "https://YOUR-SERVICE.up.railway.app/api/deals/evaluate?origin=JFK&dest=MIA&month=3"

# Seed data
python scripts/seed_sample_prices.py --routes 15

# Verify deployment
python scripts/verify_deployment.py

# Check worker logs
railway logs --service serpradio-worker

# Refresh baselines manually
psql $SUPABASE_URL -c "SELECT refresh_baselines();"
```

---

**You're ready to deploy!** Follow this sequence step-by-step and you'll be live in under an hour. 🚀
