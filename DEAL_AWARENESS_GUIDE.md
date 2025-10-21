# 🎯 Deal Awareness Feature - Implementation Guide

**Status:** Ready to Deploy
**Time to Implement:** 30 minutes
**Difficulty:** Easy
**Dependencies:** Supabase, price_observation table

---

## 📋 What This Feature Does

The **Deal Awareness** feature adds "Where & When" functionality:

✅ **"Is this a good deal right now?"**
- Compares current prices to 30-day rolling baseline (P25/P50/P75)
- Returns BUY/TRACK/WAIT recommendation
- Shows % delta vs median price

✅ **"When is the best time to book?"**
- Identifies sweet-spot booking window
- Based on lead-time curve analysis
- Shows optimal days before departure

✅ **Explainable Logic**
- Deal score (0-100) based on percentile bands
- Confidence level for each recommendation
- Human-readable rationale

---

## 🏗️ Architecture

```
┌─────────────────┐
│ User Selects:   │
│ - Destination   │──┐
│ - Month         │  │
└─────────────────┘  │
                     ▼
              ┌──────────────────┐
              │ /api/deals/      │
              │   evaluate       │
              └──────────────────┘
                     │
                     ▼
              ┌──────────────────┐
              │ Supabase RPC:    │
              │ evaluate_deal()  │
              └──────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌───────────────────┐    ┌────────────────────┐
│ route_baseline_   │    │ route_current_low  │
│ 30d (materialized)│    │ (view)             │
└───────────────────┘    └────────────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
              ┌──────────────────┐
              │ Recommendation:  │
              │ BUY / TRACK /    │
              │ WAIT             │
              └──────────────────┘
                     │
                     ▼
              ┌──────────────────┐
              │ DealEvaluator    │
              │ Component        │
              └──────────────────┘
```

---

## 🚀 Implementation Steps

### Step 1: Apply SQL Migration (5 minutes)

```bash
# In Supabase Dashboard → SQL Editor
# Copy/paste: sql/020_deal_awareness.sql
```

**What it creates:**
- `route_depart_month` view - Normalizes prices by month
- `route_baseline_30d` materialized view - Rolling 30-day percentiles
- `route_current_low` view - Current cheapest prices
- `next_depart_month()` function - Month picker helper
- `evaluate_deal()` function - Core recommendation logic

**Verification:**
```sql
-- Check materialized view was created
SELECT COUNT(*) FROM route_baseline_30d;

-- Test the function
SELECT evaluate_deal('JFK', 'MIA', 3, 'economy');
```

---

### Step 2: Backend API (Already Done ✅)

Files created:
- `src/deals_api.py` - FastAPI router with `/api/deals/evaluate`
- `src/main.py` - Router mounted automatically

**Endpoints:**
- `GET /api/deals/evaluate?origin=JFK&dest=MIA&month=3`
- `POST /api/deals/batch` - Evaluate multiple routes
- `GET /api/deals/health` - Check service status

**No additional work needed** - Already integrated into main.py

---

### Step 3: Frontend Component (Already Done ✅)

Files created:
- `v4/frontend/src/lib/dealsApi.ts` - TypeScript API client
- `v4/frontend/src/components/DealEvaluator.tsx` - React component

**Usage in your app:**

```tsx
import { DealEvaluator } from '@/components/DealEvaluator';

function HomePage() {
  return (
    <div>
      {/* Other components */}

      <DealEvaluator
        defaultOrigin="JFK"
        defaultDest="MIA"
        defaultMonth={3}
      />
    </div>
  );
}
```

---

### Step 4: Seed Initial Data (15 minutes)

The feature requires `price_observation` table with data.

**Option A: Quick Manual Seed (5 min)**

```sql
-- Insert sample price observations for testing
INSERT INTO price_observation (origin, dest, cabin, depart_date, price_usd, provider, observed_at)
VALUES
  -- JFK → MIA (March departures)
  ('JFK', 'MIA', 'economy', '2026-03-15', 159.00, 'kayak', NOW() - INTERVAL '1 day'),
  ('JFK', 'MIA', 'economy', '2026-03-15', 172.00, 'expedia', NOW() - INTERVAL '2 days'),
  ('JFK', 'MIA', 'economy', '2026-03-15', 148.00, 'google', NOW() - INTERVAL '3 days'),
  ('JFK', 'MIA', 'economy', '2026-03-22', 165.00, 'kayak', NOW() - INTERVAL '1 day'),
  ('JFK', 'MIA', 'economy', '2026-03-22', 178.00, 'expedia', NOW() - INTERVAL '2 days'),

  -- JFK → LAX (June departures)
  ('JFK', 'LAX', 'economy', '2026-06-15', 289.00, 'kayak', NOW() - INTERVAL '1 day'),
  ('JFK', 'LAX', 'economy', '2026-06-15', 302.00, 'expedia', NOW() - INTERVAL '2 days'),
  ('JFK', 'LAX', 'economy', '2026-06-22', 276.00, 'google', NOW() - INTERVAL '3 days'),

  -- EWR → LAS (April departures)
  ('EWR', 'LAS', 'economy', '2026-04-10', 119.00, 'kayak', NOW() - INTERVAL '1 day'),
  ('EWR', 'LAS', 'economy', '2026-04-10', 132.00, 'expedia', NOW() - INTERVAL '2 days'),
  ('EWR', 'LAS', 'economy', '2026-04-17', 125.00, 'google', NOW() - INTERVAL '3 days');

-- Refresh the materialized view
REFRESH MATERIALIZED VIEW route_baseline_30d;
```

**Option B: Production Data Collection**

Use your existing price scraping pipeline:
1. Enable daily price collection for top NYC routes
2. Upsert to `price_observation` table
3. Refresh `route_baseline_30d` every 6 hours (via pg_cron)

---

### Step 5: Test End-to-End (5 minutes)

```bash
# Run the test script
./scripts/test_deal_awareness.sh https://your-service.up.railway.app

# Or test manually
BASE=https://your-service.up.railway.app

# Health check
curl "$BASE/api/deals/health"

# Evaluate a deal
curl "$BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3" | jq

# Expected response:
# {
#   "has_data": true,
#   "origin": "JFK",
#   "dest": "MIA",
#   "month": 3,
#   "current_price": 159.00,
#   "baseline": {
#     "p25": 148.00,
#     "p50": 165.00,
#     "p75": 178.00,
#     "samples": 8
#   },
#   "delta_pct": -3.6,
#   "deal_score": 70,
#   "recommendation": "TRACK",
#   "confidence": 70,
#   "rationale": "Price is 3.6% below median but may improve"
# }
```

---

## 📖 Recommendation Logic Explained

### Deal Score (0-100)

| Price vs Baseline | Score | Quality |
|-------------------|-------|---------|
| ≤ P25 (bottom 25%) | 90 | Excellent |
| ≤ P50 (median) | 70 | Good |
| ≤ P75 (top 25%) | 45 | Fair |
| > P75 | 20 | Poor |

### Recommendation Rules

**BUY:**
- Price ≤ P25 (excellent deal)
- OR (in sweet-spot window AND price ≤ P50)

**TRACK:**
- Price ≤ P50 (below median)
- OR deal_score ≥ 50 (decent)

**WAIT:**
- Price > P75 (expensive)
- OR deal_score < 50 (poor value)

### Sweet-Spot Window

Finds the contiguous lead-time range where median price (q50) is within 5% of its minimum.

Example:
- 60 days out: $289
- 45 days out: $245 ← minimum
- 30 days out: $251 (within 5% of $245)
- 14 days out: $298

**Sweet spot:** 30-60 days before departure

---

## 🔄 Maintaining Fresh Data

### Automated Refresh (Recommended)

Add to your existing data pipeline:

```bash
# Every 6 hours (in crontab or GitHub Actions)
0 */6 * * * psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;"
```

**OR** use pg_cron (if available in Supabase):

```sql
SELECT cron.schedule(
  'refresh-baselines',
  '0 */6 * * *',
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;$$
);
```

### Manual Refresh

```sql
-- Run as needed
REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;
```

---

## 🎨 Frontend Integration Examples

### Home Page

```tsx
import { DealEvaluator } from '@/components/DealEvaluator';

function HomePage() {
  return (
    <div className="container mx-auto p-6">
      <h1>Find Your Perfect Flight Deal</h1>

      {/* Deal Evaluator */}
      <DealEvaluator className="mt-6" />

      {/* Other components: Split-flap board, Featured Mixes, etc. */}
    </div>
  );
}
```

### Route Detail Page

```tsx
import { evaluateDeal } from '@/lib/dealsApi';
import { useEffect, useState } from 'react';

function RouteDetailPage({ origin, dest }) {
  const [deal, setDeal] = useState(null);
  const currentMonth = new Date().getMonth() + 1;

  useEffect(() => {
    evaluateDeal(origin, dest, currentMonth).then(setDeal);
  }, [origin, dest]);

  if (!deal || !deal.has_data) return null;

  return (
    <div className="rounded-lg border p-4">
      <h3>Current Deal Analysis</h3>
      <div className={`text-2xl font-bold ${
        deal.recommendation === 'BUY' ? 'text-green-500' :
        deal.recommendation === 'WAIT' ? 'text-red-500' :
        'text-yellow-500'
      }`}>
        {deal.recommendation}
      </div>
      <p className="text-sm text-gray-500">{deal.rationale}</p>

      <div className="mt-4">
        <span>Current: ${deal.current_price}</span>
        <span className="ml-4">
          Baseline: ${deal.baseline.p50}
        </span>
        <span className={`ml-4 ${
          deal.delta_pct <= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {deal.delta_pct > 0 ? '+' : ''}{deal.delta_pct}%
        </span>
      </div>
    </div>
  );
}
```

### Batch Evaluation (Compare Multiple Routes)

```tsx
import { batchEvaluateDeal } from '@/lib/dealsApi';

async function compareRoutes() {
  const routes = [
    { origin: 'JFK', dest: 'MIA', month: 3 },
    { origin: 'JFK', dest: 'LAX', month: 3 },
    { origin: 'JFK', dest: 'LAS', month: 3 }
  ];

  const results = await batchEvaluateDeal(routes);

  // Sort by deal_score descending
  const sorted = results
    .filter(r => r.has_data)
    .sort((a, b) => (b.deal_score || 0) - (a.deal_score || 0));

  return sorted; // Render top deals first
}
```

---

## 🐛 Troubleshooting

### "No baseline or current price for this route/month"

**Cause:** No data in `price_observation` for this route/month

**Fix:**
1. Seed data (see Step 4)
2. Ensure `observed_at` is recent (last 30 days)
3. Check `depart_date` is in the future (next 12 months)

### "Insufficient data: only X samples in last 30 days"

**Cause:** Less than 10 price observations in rolling 30-day window

**Fix:**
1. Add more historical data
2. Reduce minimum sample threshold in `evaluate_deal()` function
3. Wait for more data to accumulate

### Materialized View is Stale

**Cause:** `route_baseline_30d` not refreshed after new data inserted

**Fix:**
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;
```

Set up automatic refresh (see "Maintaining Fresh Data" section)

### API Returns 502 "Supabase RPC failed"

**Cause:** SUPABASE_URL or SUPABASE_SERVICE_ROLE not set correctly

**Fix:**
1. Check Railway environment variables
2. Verify Supabase credentials
3. Test RPC directly:
   ```bash
   curl -X POST "$SUPABASE_URL/rest/v1/rpc/evaluate_deal" \
     -H "apikey: $SUPABASE_SERVICE_ROLE" \
     -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE" \
     -H "Content-Type: application/json" \
     -d '{"p_origin":"JFK","p_dest":"MIA","p_month":3,"p_cabin":"economy"}'
   ```

---

## 📊 Success Metrics

**Feature is working when:**

✅ `/api/deals/evaluate` returns recommendations with confidence ≥65%
✅ Delta % calculations are accurate (vs P50 baseline)
✅ Sweet-spot windows appear for routes with curve data
✅ Recommendations change appropriately when prices fluctuate
✅ Frontend component displays all fields correctly

**Performance Targets:**

- Response time: <500ms for single evaluation
- Batch requests: <2s for 10 routes
- Baseline refresh: <10s for 1000 route/month combos
- Data freshness: ≤6 hours between refreshes

---

## 🎯 Next Steps After Implementation

### Immediate (This Week)

1. **Seed Production Data**
   - Enable price scraping for top 20 NYC routes
   - Target: 30+ observations per route/month

2. **Add to Home Page**
   - Place DealEvaluator below hero
   - A/B test placement vs engagement

3. **Monitor Usage**
   - Track `/api/deals/evaluate` requests
   - Measure conversion: view → evaluate → book

### Short Term (Next 2 Weeks)

4. **Enhance Rationale**
   - Add more context (e.g., "Lowest price in 30 days")
   - Include historical trends

5. **Email Alerts**
   - Let users subscribe to price drops
   - Notify when deal score > 80 (BUY recommended)

6. **Mobile Optimization**
   - Responsive month picker
   - Swipe gestures for quick comparison

### Medium Term (Next Month)

7. **ML Price Prediction**
   - Forecast next 7-14 days
   - Improve sweet-spot accuracy

8. **Personalization**
   - Remember user's favorite routes
   - Customize recommendation thresholds

9. **Deal Alerts Dashboard**
   - Show all BUY recommendations across routes
   - Filter by budget, month, airline

---

## 📚 Related Documentation

- `sql/020_deal_awareness.sql` - Database schema
- `src/deals_api.py` - Backend API
- `v4/frontend/src/components/DealEvaluator.tsx` - Frontend component
- `scripts/test_deal_awareness.sh` - E2E tests
- `RECOMMENDATIONS.md` - Full action plan

---

## ✅ Checklist

Before deploying to production:

- [ ] SQL migration applied to Supabase
- [ ] Materialized view refreshed
- [ ] At least 10 price observations per route/month
- [ ] Backend API tested (200 OK responses)
- [ ] Frontend component renders correctly
- [ ] E2E test script passes
- [ ] Automatic refresh scheduled (pg_cron or cron job)
- [ ] Monitoring/alerts configured
- [ ] User documentation written

---

**Estimated Implementation Time:** 30 minutes
**Estimated Value:** High (core MVP feature)
**Complexity:** Low (mostly SQL + thin API wrapper)

Ready to deploy! 🚀
