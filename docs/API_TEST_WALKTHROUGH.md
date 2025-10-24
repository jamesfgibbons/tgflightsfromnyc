# 🧪 Parallel API Testing - Step-by-Step Walkthrough

**Goal:** Discover if our current Parallel API payload format is correct

**Time:** 2-5 minutes

---

## Step 1: Set Your API Key (30 seconds)

```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
```

**Verify it's set:**
```bash
echo $PARALLEL_API_KEY
# Should output: HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
```

---

## Step 2: Run the Discovery Script (2 minutes)

```bash
python scripts/discover_parallel_api.py
```

**What you'll see:**

```
🔍 Parallel API Discovery Tool
======================================================================
API Key: HKkalLeE...QEe

🎯 Testing Endpoint/Format Combinations
This will help us discover the correct API format.

======================================================================
Testing: Format 1 (Bulk queries array)
Endpoint: https://api.parallel.com/v1/flights/search
======================================================================

📤 Request Payload:
{
  "queries": [{
    "origin": "JFK",
    "destination": "MIA",
    "depart_date_start": "2025-10-24",
    "depart_date_end": "2025-11-23",
    "cabin": "economy"
  }],
  "currency": "USD",
  "max_results_per_query": 10
}

📊 Status Code: ???
```

The script will test multiple combinations. **Watch for:**

---

## Step 3: Interpret Results

### ✅ Success Case

If you see this:

```
📊 Status Code: 200
✅ SUCCESS!

📥 Response:
{
  "results": [
    {
      "origin": "JFK",
      "destination": "MIA",
      "flights": [...]
    }
  ]
}

💾 Saved successful format to: parallel_api_success.json

======================================================================
🎉 FOUND WORKING FORMAT!
======================================================================

Endpoint: https://api.parallel.com/v1/flights/search
Format: Format 1 (Bulk queries array)

Check 'parallel_api_success.json' for details
```

**This means:** ✅ Our current implementation is CORRECT!

**Next steps:**
1. Check the file: `cat parallel_api_success.json`
2. Verify response structure matches our expectations
3. Proceed with deployment (no changes needed)

---

### ❌ All Tests Fail

If you see this:

```
Testing: Format 1 (Bulk queries array)
📊 Status Code: 401
❌ UNAUTHORIZED - API key may be invalid

Testing: Format 2 (Single query)
📊 Status Code: 404
⚠️  NOT FOUND - Endpoint doesn't exist

[More tests...]

======================================================================
❌ NO WORKING FORMAT FOUND
======================================================================

Possible issues:
1. API key is invalid or expired
2. API endpoint is different than expected
3. API requires different authentication
4. API payload format is different
```

**This means:** We need more information about the Parallel API.

**Next steps:** (See Step 4 below)

---

### ⚠️ Partial Success (Some 400 errors)

If you see:

```
📊 Status Code: 400
⚠️  BAD REQUEST - Payload format incorrect
Response: {"error": "Missing required field: departure_date"}
```

**This means:** We're close! The endpoint works, but the payload format is slightly different.

**Next steps:** The error message tells us what to fix.

---

## Step 4: What to Do Based on Results

### Case A: ✅ Success (Status 200)

```bash
# View the successful format
cat parallel_api_success.json | jq

# The adapter is correct! Deploy as-is
# See: docs/DEPLOY_NOW.md
```

**I'll help you deploy immediately.**

---

### Case B: ❌ 401 Unauthorized

**Problem:** API key is invalid or not recognized

**Actions:**
1. Double-check the API key is correct
2. Verify it's for the right environment (dev vs prod)
3. Check if API key needs to be activated
4. Contact Parallel API support to verify key status

**Question for you:**
- Where did you get this API key?
- Is it from a Parallel API account dashboard?
- Do you have access to the API documentation portal?

---

### Case C: ❌ 404 Not Found (All endpoints)

**Problem:** The API endpoints we're testing don't exist

**Actions:**
1. We need the real Parallel API endpoint URL
2. Check Parallel API documentation for correct URL
3. OR check your API dashboard for endpoint information

**Question for you:**
- Do you have a link to Parallel API docs?
- Can you access their developer portal?
- Do they provide example API calls?

---

### Case D: ⚠️ 400 Bad Request

**Problem:** Endpoint works, but payload format is wrong

**Actions:**
1. Look at the error message - it often tells us what's wrong
2. Check which fields are missing or incorrect
3. I'll update the adapter based on the error

**Share with me:**
- The exact error message from the response
- Any hints about the correct format

---

## Step 5: Share Results

**Copy and paste the output here.** Specifically:

1. **Status codes** you saw (200, 401, 404, 400, etc.)
2. **Any successful responses** (even partial)
3. **Error messages** that might give us hints

**Example of what to share:**

```
Format 1: Status 400 - "Missing field: from_airport"
Format 2: Status 404
Format 3: Status 401 - "Invalid API key"
```

Or just paste the full output from the script!

---

## Quick Reference

### If Success ✅
```bash
cat parallel_api_success.json
# Review the working format
# Proceed with deployment
```

### If Failure ❌
```bash
# Check if you have API docs
# Look for:
# - Developer portal link
# - Example API calls
# - Authentication guide
# - Request/response formats
```

### Alternative: Use Sample Data
```bash
# Deploy with synthetic data while figuring out API
export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
export SUPABASE_SERVICE_ROLE=your-key
python scripts/seed_sample_prices.py --routes 15
```

---

## Ready? Let's Do This!

**Run this command:**
```bash
export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
python scripts/discover_parallel_api.py
```

**Then share the results with me!**

I'll be watching for:
- ✅ Status 200 (success!)
- ❌ Status 401 (auth issue)
- ❌ Status 404 (wrong endpoint)
- ⚠️ Status 400 (wrong format - but we can fix!)

**Go ahead and run it - paste the output here when done!**
