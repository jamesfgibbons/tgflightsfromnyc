# Pricing API Setup Guide

This guide explains how to securely configure your Parallel API (or X API) credentials for the pricing pipeline.

**⚠️ SECURITY WARNING:** Never commit API keys to git. All `.env` files are gitignored.

---

## 🔑 API Key Configuration

You have a Parallel API key. Configure it in the appropriate environment:

### Option 1: Local Development

Create a `.env` file in the project root (gitignored):

```bash
# .env (DO NOT COMMIT)
PRICE_SOURCE=parallel
PARALLEL_API_KEY=your-key-here
PARALLEL_API_ENDPOINT=https://api.parallel.com/v1/flights/search

# Required for worker
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=your-service-role-key

# Optional configuration
REFRESH_INTERVAL_HOURS=6
NYC_ORIGINS=JFK,EWR,LGA
TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO
```

Then load it:

```bash
# Load environment variables
export $(cat .env | xargs)

# Test the connection
python scripts/test_parallel_api.py

# Run one-shot refresh
python -m src.worker_refresh --once
```

### Option 2: Railway Deployment

**For Main API Service:**
1. Go to Railway → Your Service → Variables
2. Add the following environment variables:

```
PRICE_SOURCE=parallel
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
PARALLEL_API_ENDPOINT=https://api.parallel.com/v1/flights/search
```

**For Worker Service (Separate):**
1. Create new Railway service: "SERPRadio Worker"
2. Set Dockerfile path: `Dockerfile.worker`
3. Add environment variables:

```
PRICE_SOURCE=parallel
PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=your-service-role-key
REFRESH_INTERVAL_HOURS=6
NYC_ORIGINS=JFK,EWR,LGA
TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL
```

### Option 3: GitHub Actions

Configure repository secrets for the scheduled price refresh job:

1. Go to GitHub → Settings → Secrets and variables → Actions
2. Add repository secrets:

```
PARALLEL_API_KEY = HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
SUPABASE_URL = https://your-project.supabase.co
SUPABASE_SERVICE_ROLE = your-service-role-key
```

The workflow (`.github/workflows/price_refresh.yml`) will automatically use these secrets.

**To trigger manually:**
1. Go to Actions → Price Refresh Worker
2. Click "Run workflow"
3. Select `parallel` as price source
4. Click "Run workflow"

---

## 🧪 Testing the API Connection

Before deploying, verify your API key works:

```bash
# Set environment variable (temporary, this session only)
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe

# Run test script
python scripts/test_parallel_api.py
```

**Expected output:**
```
🔍 Testing Parallel API Connection
============================================================
API Key: HKkalLeE...QEe

📡 Initializing Parallel API fetcher...
✅ Fetcher initialized
   Endpoint: https://api.parallel.com/v1/flights/search
   Batch size: 100

🛫 Testing minimal query: JFK → MIA, next 30 days
   Origins: ['JFK']
   Destinations: ['MIA']
   Window: 2025-10-24 to 2025-11-23

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

If the test fails, check:
- API key is correct
- Endpoint URL is reachable
- No rate limiting issues

---

## 🚀 Deployment Steps

### Step 1: Apply SQL Migrations

Connect to your Supabase database and run:

```bash
# Apply deal awareness schema
psql $DATABASE_URL -f sql/020_deal_awareness.sql

# Apply refresh helper functions
psql $DATABASE_URL -f sql/021_refresh_helpers.sql
```

Or via Supabase dashboard:
1. Go to Supabase → SQL Editor
2. Copy contents of `sql/020_deal_awareness.sql` and run
3. Copy contents of `sql/021_refresh_helpers.sql` and run

### Step 2: Choose Deployment Method

**Option A: Railway Worker Service (Recommended)**

Pros: Continuous operation, automatic restarts, integrated logging
Cons: Uses Railway resources 24/7

1. Create new Railway service
2. Connect to this repo
3. Set Dockerfile path: `Dockerfile.worker`
4. Add environment variables (see Option 2 above)
5. Deploy

**Option B: GitHub Actions Scheduled Job**

Pros: No server costs, runs 4x/day automatically
Cons: Logs in artifacts, manual trigger for testing

1. Add GitHub secrets (see Option 3 above)
2. Enable Actions in repo settings
3. Workflow runs automatically every 6 hours

**Option C: Hybrid Approach**

Use GitHub Actions for scheduled runs + Railway for on-demand:
- GitHub Actions: Scheduled 6-hour refresh
- Railway: Manual triggers or hourly refresh for high-frequency updates

### Step 3: Verify Deployment

After first run, check data:

```bash
# Count price observations
psql $DATABASE_URL -c "SELECT COUNT(*) FROM price_observation;"

# Check baseline data
psql $DATABASE_URL -c "SELECT * FROM route_baseline_30d LIMIT 5;"

# Test deal evaluation API
curl "$API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3"
```

Expected results:
- `price_observation`: Thousands of rows
- `route_baseline_30d`: Percentile data for routes
- Deal API: Returns recommendation with `has_data: true`

---

## 📊 Monitoring

### Railway Logs
```bash
railway logs --service serpradio-worker
```

Watch for:
- "Starting price refresh cycle"
- "Fetched X price observations"
- "Upserted X rows to price_observation table"
- "Materialized view refreshed successfully"

### GitHub Actions Logs

1. Go to Actions → Price Refresh Worker
2. Click on latest run
3. View "Fetch and Update Prices" job
4. Download artifacts for full logs

### Database Metrics

```sql
-- Total observations
SELECT COUNT(*) FROM price_observation;

-- Observations by source
SELECT source, COUNT(*) FROM price_observation GROUP BY source;

-- Latest observation time
SELECT MAX(observed_at) FROM price_observation;

-- Routes with baseline data
SELECT COUNT(*) FROM route_baseline_30d;

-- Recent notifications
SELECT * FROM notification_event ORDER BY created_at DESC LIMIT 10;
```

---

## 🔧 Troubleshooting

### Error: "PARALLEL_API_KEY environment variable is required"

**Solution:** API key not set. Add to environment variables in Railway/GitHub or export locally.

### Error: "HTTP 401" or "HTTP 403"

**Solution:** Invalid API key. Verify the key is correct and has proper permissions.

### Error: "Request failed" or "Timeout"

**Solution:** Network issue or API downtime. The worker has retry logic (3 attempts with exponential backoff).

### Warning: "No prices fetched. Skipping upsert."

**Solution:** API returned empty results. Could be:
- Test route not available in API
- Date range not supported
- API limit reached

Check API documentation for supported routes and date ranges.

### Error: "Failed to refresh materialized views"

**Solution:** Database lock or missing index. Try:
1. Verify unique index exists on `route_baseline_30d`
2. Worker will fallback to non-concurrent refresh automatically
3. Check Supabase logs for details

---

## 🔒 Security Best Practices

1. **Never commit API keys to git**
   - All `.env` files are gitignored
   - Use environment variables or secrets management

2. **Use service role key for worker**
   - Worker needs full database access
   - Use `SUPABASE_SERVICE_ROLE`, not `SUPABASE_ANON_KEY`

3. **Rotate keys periodically**
   - Generate new Parallel API key every 90 days
   - Update in all environments (Railway, GitHub, local)

4. **Monitor API usage**
   - Track requests per day
   - Set up alerts for rate limiting
   - Optimize batch sizes if needed

5. **Audit logs regularly**
   - Review Railway/GitHub Actions logs
   - Check for failed requests or errors
   - Monitor database growth

---

## 📞 Support

**Parallel API Issues:**
- Check API documentation
- Contact Parallel API support
- Verify API status page

**Worker Issues:**
- Check logs (Railway or GitHub Actions)
- Review LAUNCH_PLAN.md for deployment details
- Test locally with `python -m src.worker_refresh --once`

**Database Issues:**
- Check Supabase logs
- Verify migrations applied correctly
- Run manual SQL queries to debug

---

## ✅ Quick Start Checklist

- [ ] API key added to environment (Railway/GitHub/local)
- [ ] SQL migrations applied (020 and 021)
- [ ] Test script passes (`python scripts/test_parallel_api.py`)
- [ ] Worker deployed (Railway or GitHub Actions)
- [ ] First refresh completed successfully
- [ ] Database has price observations
- [ ] Materialized views populated
- [ ] Deal evaluation API returns data
- [ ] Monitoring setup (logs, metrics)

Once all items are checked, your pricing pipeline is fully operational!
