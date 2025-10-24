# 🚀 Complete Launch Status & Action Plan

**Date:** October 21, 2025
**Goal:** Launch to Lovable + Railway with continuous deployment and daily price refresh
**Time to Launch:** 2-3 hours
**Status:** 85% Ready - Need pricing pipeline

---

## 📊 WHERE WE ARE AT (Current Status)

### ✅ COMPLETE & READY TO DEPLOY

| Component | Status | Files | Ready? |
|-----------|--------|-------|--------|
| **Backend API** | ✅ 100% | 40+ endpoints, FastAPI, Railway-ready | YES |
| **SQL Schema** | ✅ 100% | 8 migration files (000-020) | YES |
| **Deal Awareness** | ✅ 100% | SQL + API + Frontend + Tests | YES |
| **VibeNet Engine** | ✅ 100% | Scene planner, ontology, palettes | YES |
| **Board Feed API** | ✅ 100% | `/api/board/feed` + badges | YES |
| **Notifications** | ✅ 100% | Events + materialized views | YES |
| **Docker Setup** | ✅ 100% | Dockerfile + railway.json | YES |
| **Documentation** | ✅ 100% | 5 deployment guides | YES |

### 🟡 PARTIAL / NEEDS WORK

| Component | Status | What's Missing |
|-----------|--------|----------------|
| **Price Data** | 🔴 0% | NO data in `price_observation` table |
| **Daily Pipeline** | 🔴 0% | NO automated price collection |
| **Materialized View Refresh** | 🟡 50% | SQL ready, automation missing |
| **Lovable Connection** | 🟡 50% | Components ready, not wired yet |
| **Frontend Deployment** | 🟡 50% | Code ready, not deployed |

### 🔴 CRITICAL BLOCKERS (Must Fix Before Launch)

1. **NO PRICING DATA** - `price_observation` table is empty
2. **NO DAILY SCRAPER** - No automated price collection
3. **LOVABLE NOT DEPLOYED** - Frontend exists but not live
4. **RAILWAY NOT DEPLOYED** - Backend not running in production

---

## 🎯 THE PRICING DATA FLOW (How It Should Work)

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY PRICE PIPELINE                      │
└─────────────────────────────────────────────────────────────┘

Every 6 hours:

1️⃣ FETCH PRICES
   ├─ Kiwi API / Skyscanner / Google Flights
   ├─ Top 50 NYC routes (JFK/EWR/LGA → destinations)
   ├─ Next 90 days of departures
   └─ Store raw JSON

2️⃣ TRANSFORM & LOAD
   ├─ Parse provider responses
   ├─ Normalize to price_observation schema
   ├─ INSERT into Supabase
   └─ Log metrics (routes covered, prices collected)

3️⃣ REFRESH BASELINES
   ├─ REFRESH MATERIALIZED VIEW route_baseline_30d
   ├─ Update 30-day percentiles (P25/P50/P75)
   └─ Emit notifications for price drops

4️⃣ TRAIN MODEL (Future)
   ├─ Analyze user actions (BUY clicks vs WAIT)
   ├─ Adjust deal score thresholds
   ├─ Improve recommendation confidence
   └─ Update sweet-spot detection

┌─────────────────────────────────────────────────────────────┐
│                   NOTIFICATION LOOP                          │
└─────────────────────────────────────────────────────────────┘

When new prices arrive:

1. Compare to baseline (from route_baseline_30d)
2. If price ≤ P25 → Emit "price_drop" event
3. If in sweet-spot window → Emit "window_open" event
4. Board badges auto-update (materialized view refresh)
5. Users see lime/cyan/magenta pills on split-flap

As users interact:

1. Track: Which "BUY" recommendations led to clicks?
2. Track: Which "WAIT" recommendations were ignored?
3. Adjust: Deal score formula weights
4. Improve: Confidence levels per route
5. Iterate: Better recommendations over time
```

---

## 🚀 WHAT'S READY TO LAUNCH RIGHT NOW

### Backend (Railway)

```bash
# These files are production-ready:

✅ Dockerfile - Builds with fluidsynth/ffmpeg
✅ railway.json - One-click Railway config
✅ src/main.py - 40+ API endpoints
✅ src/deals_api.py - Deal awareness endpoints
✅ src/board_api.py - Board feed
✅ src/vibe_api.py - VibeNet generation
✅ sql/*.sql - 8 migration files

# Missing:
❌ .env with real credentials
❌ Active Railway deployment
❌ Data in database
```

### Frontend (Lovable)

```bash
# These files are production-ready:

✅ v4/frontend/src/lib/dealsApi.ts - API client
✅ v4/frontend/src/components/DealEvaluator.tsx - UI component
✅ API_INTEGRATION_GUIDE.md - Integration docs
✅ vercel-app/ - Alternative Next.js frontend

# Missing:
❌ Deployed to Lovable hosting
❌ VITE_API_BASE configured to Railway
❌ Components wired into pages
```

### Data Pipeline

```bash
# These files exist:

⚠️ scripts/upsert_price_quotes_from_json.py - Writes to WRONG table
⚠️ .github/workflows/serpradio_daily.yml - Runs Caribbean ETL only

# Missing:
❌ scripts/fetch_prices_kiwi.py - Daily price scraper
❌ .github/workflows/price_refresh.yml - 6-hour schedule
❌ Cron job to refresh materialized views
```

---

## 📋 COMPLETE LAUNCH CHECKLIST (In Order)

### PHASE 1: Infrastructure (1 hour)

- [ ] **1.1 Supabase Setup** (15 min)
  ```bash
  # Apply all SQL migrations in order:
  1. sql/000_init_schema.sql
  2. sql/board_feed_schema.sql
  3. sql/best_time_schema.sql
  4. sql/010_notification_engine.sql
  5. sql/020_deal_awareness.sql

  # Create storage buckets:
  - serpradio-artifacts (private)
  - serpradio-public (public)

  # Copy credentials:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE
  ```

- [ ] **1.2 Railway Deployment** (15 min)
  ```bash
  # Deploy from GitHub:
  1. Connect jamesfgibbons/tgflightsfromnyc repo
  2. Set environment variables (see .env.railway.example)
  3. Deploy (auto-detects Dockerfile)
  4. Get URL: https://your-service.up.railway.app
  ```

- [ ] **1.3 Seed Sample Data** (30 min)
  ```bash
  # Option A: Quick manual seed (5 min)
  # Run seed script in LAUNCH_PLAN.md

  # Option B: Build price scraper (I'll do this - 30 min)
  # Fetch real prices from API
  ```

### PHASE 2: Frontend Connection (30 min)

- [ ] **2.1 Configure Lovable** (10 min)
  ```bash
  # Set environment variable:
  VITE_API_BASE=https://your-service.up.railway.app

  # Or create public/config.json:
  {
    "VITE_API_BASE": "https://your-service.up.railway.app"
  }
  ```

- [ ] **2.2 Wire Components** (20 min)
  ```tsx
  // In your Lovable Home.tsx:
  import { DealEvaluator } from '@/components/DealEvaluator';

  function HomePage() {
    return (
      <>
        {/* Hero section */}

        {/* Deal Evaluator - Where & When */}
        <DealEvaluator className="mt-8" />

        {/* Split-flap board */}
        {/* Featured mixes */}
      </>
    );
  }
  ```

- [ ] **2.3 Update CORS on Railway** (5 min)
  ```bash
  # Railway → Variables → Update:
  CORS_ORIGINS=https://your-app.lovable.dev,https://*.lovable.dev

  # Redeploy
  ```

### PHASE 3: Daily Pipeline (1 hour)

- [ ] **3.1 Price Scraper** (30 min)
  ```bash
  # I'll create this for you:
  scripts/fetch_prices_daily.py

  # Fetches from Kiwi/Skyscanner
  # Writes to price_observation
  # Configured for top 50 NYC routes
  ```

- [ ] **3.2 GitHub Actions Workflow** (15 min)
  ```yaml
  # .github/workflows/price_refresh.yml

  name: Price Refresh
  on:
    schedule:
      - cron: '0 */6 * * *'  # Every 6 hours

  jobs:
    refresh:
      runs-on: ubuntu-latest
      steps:
        - name: Fetch Prices
          run: python scripts/fetch_prices_daily.py

        - name: Refresh Baselines
          run: psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW route_baseline_30d"
  ```

- [ ] **3.3 Monitoring** (15 min)
  ```sql
  -- Create monitoring view:
  CREATE VIEW vw_data_health AS
  SELECT
    origin,
    destination,
    DATE_TRUNC('month', depart_date) as month,
    COUNT(*) as observations,
    MAX(captured_at) as last_updated,
    NOW() - MAX(captured_at) as staleness
  FROM price_observation
  GROUP BY 1,2,3
  HAVING COUNT(*) < 10  -- Alert if < 10 samples
     OR NOW() - MAX(captured_at) > INTERVAL '24 hours';  -- Alert if stale
  ```

### PHASE 4: Continuous Deployment (30 min)

- [ ] **4.1 Railway Auto-Deploy** (10 min)
  ```bash
  # Railway Settings:
  ✅ Enable: "Auto-deploy on push to main"
  ✅ Watch branch: main (or your preferred branch)

  # Now pushing to GitHub auto-deploys to Railway
  # 5-minute deploy cycle ✅
  ```

- [ ] **4.2 Lovable Hot Reload** (10 min)
  ```bash
  # Lovable automatically hot-reloads on file changes
  # No config needed

  # To deploy:
  1. Edit component in Lovable editor
  2. Save (Cmd+S / Ctrl+S)
  3. See changes instantly

  # Or push to GitHub:
  1. Commit changes
  2. Push to connected branch
  3. Lovable auto-deploys
  ```

- [ ] **4.3 Database Migrations** (10 min)
  ```bash
  # For schema changes:

  1. Add new .sql file: sql/021_new_feature.sql
  2. Test locally
  3. Run in Supabase production (SQL Editor)
  4. Update code to use new schema
  5. Deploy

  # Or use migration runner:
  scripts/run_migrations.sh
  ```

---

## 🔄 DAILY OPERATIONS (Once Launched)

### Morning (9:00 AM)

```bash
# Automated (GitHub Actions):
1. Fetch prices (6-hour schedule)
2. Refresh baselines (materialized view)
3. Emit notifications (price drops detected)
4. Board badges auto-update

# Manual checks:
- View monitoring dashboard (data health)
- Check error logs in Railway
- Verify materialized view refreshed
```

### Evening (9:00 PM)

```bash
# Automated:
1. Another price fetch cycle
2. Baseline refresh
3. Notifications emitted

# Weekly review:
- Analyze which routes get most traffic
- Review recommendation accuracy
- Adjust deal score thresholds if needed
```

---

## 🎓 MODEL TRAINING LOOP (Continuous Improvement)

### Phase 1: Collect Signals (Week 1-2)

```sql
-- Track user actions
CREATE TABLE user_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT,
  action TEXT,  -- 'view_deal', 'click_buy', 'dismiss'
  origin TEXT,
  dest TEXT,
  month INT,
  recommendation TEXT,  -- 'BUY', 'TRACK', 'WAIT'
  deal_score INT,
  current_price NUMERIC,
  delta_pct NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analyze conversion rates
SELECT
  recommendation,
  COUNT(*) as total_shown,
  SUM(CASE WHEN action = 'click_buy' THEN 1 ELSE 0 END) as conversions,
  ROUND(100.0 * SUM(CASE WHEN action = 'click_buy' THEN 1 ELSE 0 END) / COUNT(*), 2) as conversion_rate
FROM user_actions
GROUP BY recommendation;

-- Expected results:
-- BUY:   40-60% conversion (high intent)
-- TRACK: 10-20% conversion (monitoring)
-- WAIT:  <5% conversion (correctly deterred)
```

### Phase 2: Adjust Thresholds (Week 3-4)

```sql
-- If BUY recommendations have LOW conversion:
-- → Recommendation is too aggressive
-- → Raise the threshold

-- Update evaluate_deal() function:
-- Change this:
  WHEN v_now.current_low <= v_base.p25_30d THEN 'BUY'
-- To this (more conservative):
  WHEN v_now.current_low <= v_base.p25_30d * 0.95 THEN 'BUY'  -- 5% below P25

-- If WAIT recommendations show HIGH conversion:
-- → Users ignore warnings
-- → Make WAIT threshold stricter

-- Change this:
  ELSE 'WAIT'
-- To this:
  WHEN v_now.current_low > v_base.p75_30d * 1.1 THEN 'WAIT'  -- 10% above P75
  ELSE 'TRACK'
```

### Phase 3: Personalize (Month 2+)

```sql
-- Track per-user preferences
CREATE TABLE user_preferences (
  user_id UUID,
  avg_budget NUMERIC,  -- Average price they click on
  risk_tolerance NUMERIC,  -- How often they take TRACK vs WAIT
  preferred_routes TEXT[],  -- Routes they search most
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Adjust recommendations per user:
CREATE OR REPLACE FUNCTION evaluate_deal_personalized(
  p_origin TEXT,
  p_dest TEXT,
  p_month INT,
  p_cabin TEXT,
  p_user_id UUID  -- New parameter
)
RETURNS JSONB AS $$
DECLARE
  v_base_result JSONB;
  v_user_prefs RECORD;
BEGIN
  -- Get base recommendation
  v_base_result := evaluate_deal(p_origin, p_dest, p_month, p_cabin);

  -- Get user preferences
  SELECT * INTO v_user_prefs FROM user_preferences WHERE user_id = p_user_id;

  -- Adjust based on user budget
  IF v_base_result->>'current_price' > v_user_prefs.avg_budget * 1.2 THEN
    -- Price is 20% above their usual budget
    -- Downgrade BUY → TRACK, TRACK → WAIT
    v_base_result := jsonb_set(v_base_result, '{recommendation}',
      CASE v_base_result->>'recommendation'
        WHEN 'BUY' THEN '"TRACK"'
        WHEN 'TRACK' THEN '"WAIT"'
        ELSE '"WAIT"'
      END::JSONB
    );
  END IF;

  RETURN v_base_result;
END;
$$ LANGUAGE PLPGSQL;
```

---

## ⚡ 5-MINUTE DEPLOY CYCLE (How It Works)

```
┌─────────────────────────────────────────────────────────┐
│         CONTINUOUS DEPLOYMENT WORKFLOW                   │
└─────────────────────────────────────────────────────────┘

CODE CHANGE → PRODUCTION (5 minutes)

1️⃣ Developer makes change (30 sec)
   ├─ Edit src/deals_api.py
   ├─ Add new feature
   └─ Test locally

2️⃣ Commit & Push (30 sec)
   ├─ git add .
   ├─ git commit -m "feat: improve deal scoring"
   └─ git push origin main

3️⃣ Railway Auto-Build (3 min)
   ├─ Detects push to main
   ├─ Pulls latest code
   ├─ Builds Docker image
   ├─ Runs health checks
   └─ Deploys new version

4️⃣ Automatic Rollback (if needed) (1 min)
   ├─ Health check fails?
   ├─ Auto-rollback to previous version
   └─ Alert developer

5️⃣ Live in Production (5 min total)
   └─ New feature available to users

┌─────────────────────────────────────────────────────────┐
│         LOVABLE FRONTEND (Even Faster)                   │
└─────────────────────────────────────────────────────────┘

COMPONENT CHANGE → LIVE (30 seconds)

1️⃣ Edit in Lovable (10 sec)
   └─ Change DealEvaluator styling

2️⃣ Save (Cmd+S) (1 sec)
   └─ Auto-saves

3️⃣ Hot Reload (5 sec)
   └─ Changes visible instantly in preview

4️⃣ Deploy (15 sec)
   └─ Click "Deploy" button
   └─ Live in production

Total: 30 seconds from edit to production ✅
```

---

## 🎯 ACTION PLAN: LAUNCH IN 2-3 HOURS

### Hour 1: Infrastructure

**What YOU do:**
1. Apply SQL migrations in Supabase (copy/paste 5 files)
2. Create storage buckets (2 clicks)
3. Deploy to Railway (connect GitHub repo)
4. Copy Railway URL

**What I do:**
- Stand by to help with any errors
- Verify endpoints are working

### Hour 2: Price Pipeline

**What I do:**
1. Build `scripts/fetch_prices_daily.py` (Kiwi API integration)
2. Create `.github/workflows/price_refresh.yml`
3. Create seed script for initial data
4. Test end-to-end

**What YOU do:**
- Provide Kiwi API key (or I'll use sample data for now)
- Review and approve

### Hour 3: Frontend Connection

**What YOU do:**
1. Set `VITE_API_BASE` in Lovable
2. Wire `<DealEvaluator />` into Home page
3. Deploy to Lovable
4. Test end-to-end

**What I do:**
- Provide exact code snippets
- Debug any CORS issues
- Verify recommendations working

---

## 🚀 READY TO LAUNCH?

**Tell me your preference:**

**Option A: Full Launch Today (3 hours)**
- I build the price pipeline NOW
- You deploy everything
- We go live by end of day

**Option B: Phased Launch (1 hour + 1 week)**
- Deploy with sample data TODAY (1 hour)
- Build real pipeline next week
- Full launch when ready

**Option C: Wait for Everything (1 week)**
- Build complete pipeline first
- Then deploy everything
- Guaranteed smooth launch

**My recommendation: Option A**

**What do you want to do?** Let me know and I'll start building! 🔨
