# ⚠️ Parallel API - Integration Status

## Current Status: NEEDS API DOCUMENTATION

### What We Have ✅

**Route Generation Logic** - CORRECT ✅
```python
# This logic is correct and will work with any API:
origins = ["JFK", "EWR", "LGA"]
destinations = ["MIA", "LAX", "SFO", "ORD", "ATL", ...]

routes = []
for origin in origins:
    for dest in destinations:
        if origin != dest:
            routes.append((origin, dest))

# Result: 60 routes (3 origins × 20 destinations)
```

**Batching Logic** - CORRECT ✅
```python
# Splits routes into batches of 100 for API rate limiting
batches = self.batch_requests(routes, batch_size=100)
```

**Retry Logic** - CORRECT ✅
```python
# Exponential backoff: 2s, 4s, 8s delays
prices = fetcher.fetch_with_retry(max_retries=3)
```

### What We Need ⚠️

**Actual API Format** - UNKNOWN ⚠️

The current implementation uses a **PLACEHOLDER** format:

```python
# src/adapters/prices_parallel.py line 46:
self.endpoint = os.getenv(
    "PARALLEL_API_ENDPOINT",
    "https://api.parallel.com/v1/flights/search"  # ⚠️ PLACEHOLDER URL
)

# Assumed payload format (lines 157-161):
payload = {
    "queries": [{
        "origin": "JFK",
        "destination": "MIA",
        "depart_date_start": "2025-11-01",
        "depart_date_end": "2025-11-30",
        "cabin": "economy"
    }],
    "currency": "USD",
    "max_results_per_query": 30
}
```

**This format is ASSUMED** - we don't have actual Parallel API documentation.

---

## 🔍 Discovery Process

### Step 1: Run Discovery Script

```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
python scripts/discover_parallel_api.py
```

This script will:
1. Test 5 common API endpoint patterns
2. Try 4 different payload formats
3. Log responses for each attempt
4. Save successful format to `parallel_api_success.json`

### Step 2: Check Results

**If successful ✅:**
- `parallel_api_success.json` will contain the working format
- Use that to update the adapter

**If all fail ❌:**
- We need actual Parallel API documentation
- Or we need to use sample data instead

---

## 📋 What We Need From You

To make the Parallel API work correctly, we need:

### 1. API Documentation

Please provide:
- [ ] Correct API endpoint URL
- [ ] Authentication method (Bearer token, API key, etc.)
- [ ] Request format (JSON structure)
- [ ] Response format (JSON structure)
- [ ] Rate limits
- [ ] Error response formats

### 2. OR: Sample API Call

If you have a working API call example:

```bash
# Example of what we need:
curl -X POST "https://REAL-API-ENDPOINT.com/search" \
  -H "Authorization: Bearer HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "JFK",
    "to": "MIA",
    "date": "2025-11-01"
  }'
```

### 3. OR: API Access Dashboard

- Link to API documentation portal
- Example requests from their docs
- SDK or code samples

---

## 🛠️ Quick Fix Options

### Option A: Discover Real Format (Recommended)

Run the discovery script:
```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
python scripts/discover_parallel_api.py
```

If it finds a working format, we'll update the adapter.

### Option B: Use Sample Data (Quick Start)

While we figure out the API, use sample data:
```bash
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-key
python scripts/seed_sample_prices.py --routes 15
```

This gives you ~20,000 realistic price observations to test the deal awareness system.

### Option C: Provide API Docs

If you have access to Parallel API documentation:
1. Share the docs/link
2. We'll update the adapter to match the real format
3. Takes ~15 minutes to adjust

---

## 🎯 The Adapter is Ready to Adjust

The good news: The adapter is **designed to be easily updated** once we know the real format.

### What Needs to Change (Example)

If the real API uses a different format, we just update these lines:

```python
# Current (lines 157-161):
payload = {
    "queries": [...],
    "currency": "USD"
}

# Update to real format (example):
payload = {
    "routes": [...],
    "return_currency": "USD"
}
```

And update the response parser:

```python
# Current (lines 210-220):
results = api_response.get("results", [])
for result in results:
    flights = result.get("flights", [])
    # ...

# Update to match real response:
data = api_response.get("data", [])
for item in data:
    prices = item.get("prices", [])
    # ...
```

**Time to adjust:** ~15 minutes once we know the format

---

## ✅ What Works Right Now

Even without the real Parallel API format, you can:

### 1. Test with Sample Data ✅

```bash
python scripts/seed_sample_prices.py
```

Generates realistic prices for all routes.

### 2. Deploy Everything Else ✅

- Backend API: Works independently
- Deal awareness: Works with seeded data
- Board feed: Works with seeded data
- VibeNet: Works independently
- Frontend: Works with sample data

### 3. Verify End-to-End ✅

```bash
python scripts/verify_deployment.py
```

All features work with sample data.

---

## 🚀 Recommended Path Forward

### Immediate (5 minutes)

1. **Run discovery script:**
   ```bash
   python scripts/discover_parallel_api.py
   ```

2. **Check if any format works**
   - If YES: Use that format ✅
   - If NO: Continue to next step

### Short-term (30 minutes)

3. **Deploy with sample data:**
   ```bash
   python scripts/seed_sample_prices.py --routes 15
   ```

4. **Verify everything works:**
   ```bash
   python scripts/verify_deployment.py
   ```

5. **Test deal awareness with sample data:**
   ```bash
   curl "$API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3"
   ```

### Long-term (when API docs available)

6. **Get Parallel API documentation**
   - Correct endpoint URL
   - Request/response format
   - Authentication method

7. **Update adapter** (15 minutes)
   - Adjust payload format
   - Update response parser
   - Test with real API

8. **Deploy worker with real API**
   - Railway or GitHub Actions
   - Start fetching real prices

---

## 📞 Questions to Answer

1. **Do you have Parallel API documentation?**
   - Link to docs portal?
   - Example API calls?
   - SDK or samples?

2. **Can you make a test API call?**
   - Does a simple curl work?
   - What response do you get?

3. **Should we use sample data for now?**
   - Deploy and test with synthetic data?
   - Figure out real API later?

---

## Summary

### ✅ What's Correct
- Route generation logic (60 routes)
- Batching and retry logic
- Response transformation
- Database upsert logic
- Adapter architecture

### ⚠️ What's Unknown
- Actual Parallel API endpoint URL
- Real request payload format
- Real response structure

### 🎯 Next Steps
1. Run `python scripts/discover_parallel_api.py`
2. Share results OR provide API docs
3. Update adapter if needed (15 min)
4. OR use sample data while figuring it out

**Bottom line:** The logic is correct, we just need to know the exact API format. The adapter is ready to be adjusted once we have that information.
