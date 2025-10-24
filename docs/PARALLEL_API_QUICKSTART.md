# 🚀 Parallel API - Quick Start Guide

**Your API Key:** `HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe`

This guide shows you exactly how to get Parallel API working correctly for the pricing pipeline.

---

## ⚡ Quick Test (2 minutes)

### Test the API connection RIGHT NOW:

```bash
# Set your API key
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe

# Run the test script
python scripts/test_parallel_api.py
```

**Expected Output:**
```
🔍 Testing Parallel API Connection
============================================================
API Key: HKkalLeE...QEe

📡 Initializing Parallel API fetcher...
✅ Fetcher initialized
   Endpoint: https://api.parallel.com/v1/flights/search
   Batch size: 100

🛫 Testing minimal query: JFK → MIA, next 30 days
⏳ Fetching prices...

============================================================
✅ SUCCESS!
============================================================
Fetched 15 price observations

Sample prices (first 5):
1. JFK → MIA
   Date: 2025-11-05
   Price: $234.50
   ...

🎉 Parallel API connection successful!
```

**If it fails**, see troubleshooting section below.

---

## 🔧 Configuration

### Environment Variables

The Parallel API adapter needs these environment variables:

```bash
# Required
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe

# Optional (with defaults)
PARALLEL_API_ENDPOINT=https://api.parallel.com/v1/flights/search
PARALLEL_BATCH_SIZE=100
PARALLEL_API_TIMEOUT=60.0
```

### Where to Set Them

**1. Local Development (.env file)**
```bash
# Create .env file (gitignored)
cat > .env <<EOF
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
PARALLEL_API_ENDPOINT=https://api.parallel.com/v1/flights/search
EOF

# Load it
export $(cat .env | xargs)
```

**2. Railway (for worker service)**
```
Service → Variables → Raw Editor

PRICE_SOURCE=parallel
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
PARALLEL_API_ENDPOINT=https://api.parallel.com/v1/flights/search
```

**3. GitHub Actions (for scheduled jobs)**
```
GitHub → Settings → Secrets → Actions → New repository secret

Name: PARALLEL_API_KEY
Value: HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
```

---

## 📡 How the Parallel API Works

### Request Format

The adapter sends bulk requests like this:

```json
{
  "queries": [
    {
      "origin": "JFK",
      "destination": "MIA",
      "depart_date_start": "2025-11-01",
      "depart_date_end": "2025-11-30",
      "cabin": "economy"
    },
    {
      "origin": "JFK",
      "destination": "LAX",
      "depart_date_start": "2025-11-01",
      "depart_date_end": "2025-11-30",
      "cabin": "economy"
    }
  ],
  "currency": "USD",
  "max_results_per_query": 30
}
```

### Response Format

Parallel API returns:

```json
{
  "results": [
    {
      "query_id": 0,
      "origin": "JFK",
      "destination": "MIA",
      "flights": [
        {
          "depart_date": "2025-11-05",
          "price": {
            "amount": 234.50,
            "currency": "USD"
          },
          "airline": "AA",
          "flight_number": "1234"
        }
      ]
    }
  ]
}
```

### What the Adapter Does

1. **Transforms request** → Parallel API format
2. **Sends bulk query** → Up to 100 routes per request
3. **Parses response** → Extracts prices
4. **Standardizes data** → Converts to our schema:

```python
{
    "origin": "JFK",
    "dest": "MIA",
    "cabin": "economy",
    "depart_date": date(2025, 11, 5),
    "price_usd": 234.50,
    "source": "parallel",
    "observed_at": datetime.now()
}
```

---

## 🧪 Testing Scenarios

### Test 1: Single Route (Minimal)

```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
python scripts/test_parallel_api.py
```

This tests: JFK → MIA, next 30 days

### Test 2: Manual Python Test

```python
import os
from datetime import date, timedelta
from src.adapters import ParallelFetcher

# Set API key
os.environ["PARALLEL_API_KEY"] = "HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe"

# Initialize fetcher
fetcher = ParallelFetcher()

# Fetch prices
prices = fetcher.fetch(
    origins=["JFK"],
    destinations=["MIA"],
    windows=[{
        "start": date.today(),
        "end": date.today() + timedelta(days=30)
    }],
    cabin="economy"
)

print(f"Fetched {len(prices)} prices")
for price in prices[:3]:
    print(f"{price['origin']}→{price['dest']}: ${price['price_usd']} on {price['depart_date']}")
```

### Test 3: Full Worker Run (One-Shot)

```bash
# Set environment
export PRICE_SOURCE=parallel
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-service-role-key

# Run worker once
python -m src.worker_refresh --once
```

Expected output:
```
🔍 Starting price refresh worker (PRICE_SOURCE=parallel)
Origins: ['JFK', 'EWR', 'LGA']
Destinations: ['MIA', 'LAX', 'SFO', ...]

============================================================
Starting price refresh cycle
============================================================
Fetching prices for 3 origins × 20 destinations × 6 windows
Fetched 5,234 price observations
Upserted 5,234 rows to price_observation table
Materialized view refreshed successfully
Emitted 12 price drop notifications
Price refresh cycle completed successfully
```

---

## 🔍 Verify It's Working

### Check 1: API Connection
```bash
python scripts/test_parallel_api.py
# Should return: "🎉 Parallel API connection successful!"
```

### Check 2: Database Has Data
```bash
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-key

# Check price observations
psql $SUPABASE_URL -c "SELECT COUNT(*), source FROM price_observation GROUP BY source;"
```

Expected:
```
 count  | source
--------+----------
  5234  | parallel
```

### Check 3: Deal Evaluation Works
```bash
curl "$API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3"
```

Should return JSON with `has_data: true` and recommendation.

---

## ⚠️ Troubleshooting

### Error: "PARALLEL_API_KEY environment variable is required"

**Problem:** API key not set

**Solution:**
```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
```

Or add to Railway/GitHub Actions environment variables.

### Error: "HTTP 401" or "HTTP 403"

**Problem:** Invalid API key or unauthorized

**Solutions:**
1. Verify key is correct (no extra spaces)
2. Check Parallel API dashboard for account status
3. Verify API key has correct permissions

```bash
# Test key directly
curl -H "Authorization: Bearer HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe" \
     https://api.parallel.com/v1/flights/search \
     -d '{"queries":[{"origin":"JFK","destination":"MIA","depart_date_start":"2025-11-01","depart_date_end":"2025-11-30"}]}'
```

### Error: "Request failed" or "Timeout"

**Problem:** Network issue or API downtime

**Solutions:**
1. Worker has built-in retry logic (3 attempts)
2. Check Parallel API status page
3. Increase timeout:
   ```bash
   export PARALLEL_API_TIMEOUT=120.0
   ```

### Warning: "No prices fetched"

**Problem:** API returned empty results

**Possible causes:**
1. Test route not available (try different route)
2. Date range not supported
3. API rate limit reached

**Solutions:**
1. Try different origin/destination
2. Check API documentation for supported routes
3. Wait and retry (rate limits reset)

### Error: "Failed after 3 retries"

**Problem:** Persistent API failures

**Solutions:**
1. Check API key is active
2. Verify Parallel API service status
3. Review error logs for details
4. Contact Parallel API support

---

## 📊 Monitoring

### Railway Worker Logs

```bash
railway logs --service serpradio-worker
```

Look for:
```
✅ Fetcher initialized
✅ Fetched X price observations
✅ Upserted X rows to price_observation table
✅ Materialized view refreshed successfully
```

### GitHub Actions Logs

1. Go to: https://github.com/jamesfgibbons/tgflightsfromnyc/actions
2. Click: Price Refresh Worker
3. View latest run
4. Download artifacts for full logs

### Database Metrics

```sql
-- Total observations from Parallel API
SELECT COUNT(*) FROM price_observation WHERE source = 'parallel';

-- Latest observation
SELECT MAX(observed_at) FROM price_observation WHERE source = 'parallel';

-- Price range
SELECT origin, dest, MIN(price_usd), MAX(price_usd), AVG(price_usd)
FROM price_observation
WHERE source = 'parallel'
GROUP BY origin, dest
ORDER BY AVG(price_usd) DESC
LIMIT 10;
```

---

## 🚀 Production Setup

### Step 1: Configure Railway Worker

1. **Create Railway service:**
   - Same project as backend
   - Name: "SERPRadio Worker"
   - Dockerfile: `Dockerfile.worker`

2. **Set environment variables:**
   ```env
   PRICE_SOURCE=parallel
   PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
   SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
   SUPABASE_SERVICE_ROLE=your-key
   REFRESH_INTERVAL_HOURS=6
   NYC_ORIGINS=JFK,EWR,LGA
   TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO
   ```

3. **Deploy:**
   - Click Deploy
   - Monitor logs for first refresh

### Step 2: OR Configure GitHub Actions

1. **Add repository secrets:**
   ```
   PARALLEL_API_KEY = HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
   SUPABASE_URL = https://bulcmonhcvqljorhiqgk.supabase.co
   SUPABASE_SERVICE_ROLE = your-key
   ```

2. **Enable workflow:**
   - Actions → Price Refresh Worker
   - Runs every 6 hours automatically

3. **Manual trigger:**
   - Actions → Run workflow
   - Select `parallel` as source

### Step 3: Verify Production

```bash
# Check database has fresh data
psql $SUPABASE_URL -c "
  SELECT MAX(observed_at), COUNT(*)
  FROM price_observation
  WHERE source = 'parallel'
  AND observed_at >= NOW() - INTERVAL '1 hour'
"
```

Should show recent observations.

---

## 📞 Support

### Parallel API Issues

- **Documentation**: Check Parallel API docs for endpoint details
- **Support**: Contact Parallel API support with API key
- **Status**: Check Parallel API status page for outages

### Worker Issues

- **Test locally**: `python scripts/test_parallel_api.py`
- **Check logs**: Railway or GitHub Actions
- **Verify config**: Environment variables set correctly

### Database Issues

- **Run refresh**: `SELECT refresh_baselines_nonconcurrent();`
- **Check data**: `SELECT COUNT(*) FROM price_observation;`
- **Verify schema**: Migrations 020 and 021 applied

---

## ✅ Quick Checklist

- [ ] API key set in environment
- [ ] Test script passes
- [ ] Worker deployed (Railway or GitHub Actions)
- [ ] First refresh completed
- [ ] Database has price data
- [ ] Baselines calculated
- [ ] Deal API returns data

**All checked?** Parallel API is working correctly! 🎉

---

**Your API Key**: `HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe`
**Test Command**: `python scripts/test_parallel_api.py`
**Status**: Ready to use
