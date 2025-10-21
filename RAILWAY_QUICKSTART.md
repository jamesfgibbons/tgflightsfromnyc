# 🚂 Railway Deployment - Quick Start

**Estimated time: 15 minutes**

This guide assumes you have:
- ✅ GitHub account with `jamesfgibbons/tgflightsfromnyc` repo
- ✅ Railway account (https://railway.app)
- ✅ Supabase project created

---

## Step 1: Prepare Supabase (5 minutes)

### A) Apply SQL Migrations

In Supabase Dashboard → SQL Editor, run these in order:

```sql
-- 1. Base schema
-- Paste contents of: sql/000_init_schema.sql

-- 2. Board feed schema
-- Paste contents of: sql/board_feed_schema.sql

-- 3. Best-time booking schema
-- Paste contents of: sql/best_time_schema.sql

-- 4. Notifications engine (badges + events)
-- Paste contents of: sql/010_notification_engine.sql
```

### B) Create Storage Buckets

Supabase → Storage → New Bucket:

1. **Bucket name**: `serpradio-artifacts`
   - Public: **No** (private)
   - File size limit: 50 MB

2. **Bucket name**: `serpradio-public`
   - Public: **Yes**
   - File size limit: 50 MB

### C) Copy Credentials

Supabase → Settings → API:
- Copy **Project URL** → This is your `SUPABASE_URL`
- Copy **service_role** secret key → This is `SUPABASE_SERVICE_ROLE`

---

## Step 2: Deploy to Railway (5 minutes)

### A) Create New Project

1. Go to https://railway.app/new
2. Click **Deploy from GitHub repo**
3. Select `jamesfgibbons/tgflightsfromnyc`
4. Railway will auto-detect `Dockerfile` and `railway.json`

### B) Set Environment Variables

Railway → Service → Variables → Raw Editor:

**Paste this template and fill in your values:**

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGci...your-service-role-key
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public
ADMIN_SECRET=generate-random-secret-here-min-32-chars
CORS_ORIGINS=https://your-app.lovable.dev

# Audio
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

# Paths
DESTINATION_ONTOLOGY_PATH=config/destination_ontology.yaml
VIBE_PALETTES_PATH=config/vibe_palettes.yaml
VIBE_RULES_PATH=config/vibe_rules.yaml

# Optional: Add OpenAI/xAI keys if you need LLM features
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...
```

**Generate ADMIN_SECRET:**
```bash
# On your local machine:
openssl rand -hex 32
# Or:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### C) Deploy

1. Click **Deploy**
2. Wait 3-5 minutes for build
3. Railway will give you a public URL: `https://your-service.up.railway.app`

---

## Step 3: Verify Deployment (5 minutes)

### A) Quick Smoke Tests

Replace `BASE` with your Railway URL:

```bash
BASE=https://your-service.up.railway.app

# 1. Health check
curl "$BASE/health"
# Expected: {"ok": true}

# 2. Board feed
curl "$BASE/api/board/feed?origins=JFK,EWR,LGA&limit=5"
# Expected: JSON with "items" array

# 3. VibeNet palettes
curl "$BASE/vibenet/vibes"
# Expected: Array of palette objects

# 4. Generate audio
curl -X POST "$BASE/vibenet/generate" \
  -H "content-type: application/json" \
  -d '{
    "data":[0.2,0.4,0.6,0.8],
    "controls":{"bars":8,"tempo_hint":112},
    "meta":{"origin":"JFK","destination":"MIA"}
  }'
# Expected: Job object with mp3_url or midi_url
```

### B) Check Logs

Railway → Deployments → View Logs

Look for:
```
✓ Starting uvicorn on port 8000
✓ Application startup complete
✓ Uvicorn running on http://0.0.0.0:8000
```

---

## Step 4: Connect Frontend (Lovable)

### In Your Lovable Project:

**Create or update `public/config.json`:**
```json
{
  "VITE_API_BASE": "https://your-service.up.railway.app"
}
```

**Or set environment variable:**
```
VITE_API_BASE=https://your-service.up.railway.app
```

**Update CORS on Railway:**
```env
CORS_ORIGINS=https://your-actual-app.lovable.dev,https://*.lovable.dev
```

Redeploy Railway service after CORS update.

---

## Step 5: Seed Initial Data (Optional)

### If Board Feed Returns Empty:

You need to populate `travel_routes_nyc` and `price_quotes` tables.

**Option A: Use Scripts**

```bash
# Clone repo locally
git clone https://github.com/jamesfgibbons/tgflightsfromnyc.git
cd tgflightsfromnyc

# Create .env with Supabase creds
cp .env.railway.example .env
# Edit .env with your values

# Install dependencies
pip install -r requirements.txt

# Publish routes
python scripts/publish_top_routes.py --input destinations_by_popularity.csv --limit 5000

# Upsert price quotes
python scripts/upsert_price_quotes_from_json.py
```

**Option B: Manual Insert**

Supabase → SQL Editor:

```sql
-- Insert sample routes
INSERT INTO travel_routes_nyc (origin, dest, city, rank, source)
VALUES
  ('JFK', 'MIA', 'Miami', 1, 'manual'),
  ('JFK', 'LAX', 'Los Angeles', 2, 'manual'),
  ('JFK', 'LAS', 'Las Vegas', 3, 'manual'),
  ('EWR', 'MIA', 'Miami', 1, 'manual'),
  ('LGA', 'MIA', 'Miami', 1, 'manual');

-- Insert sample price quotes
INSERT INTO price_quotes (origin, dest, provider, price_usd, observed_at)
VALUES
  ('JFK', 'MIA', 'kayak', 159.00, NOW()),
  ('JFK', 'LAX', 'kayak', 289.00, NOW()),
  ('JFK', 'LAS', 'expedia', 119.00, NOW());
```

---

## Troubleshooting

### Build Fails: "Could not build wheels for midiutil"
✅ **Already fixed** - Dockerfile installs gcc/g++ and builds packages correctly

### Health Check Fails
1. Check Railway logs for errors
2. Verify PORT is not hardcoded (should use $PORT from Railway)
3. Check `/api/healthz` endpoint (not just `/health`)

### CORS Errors in Browser
1. Add your Lovable domain to `CORS_ORIGINS`
2. Include protocol: `https://` (not just domain)
3. For preview URLs, use wildcard: `https://*.lovable.dev`

### No Audio Generated
- Check `RENDER_MP3=1` is set
- Verify soundfont exists: Railway → Shell → `ls /usr/share/sounds/sf2/`
- Try `RENDER_MP3=0` for MIDI-only mode

### Empty Board Feed
- Run data seeding scripts (Step 5)
- Check Supabase tables have data
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE` are correct

---

## Next Steps After Deployment

1. **Generate Featured Mixes** (6-10 hero MP3s)
   - Caribbean routes ×3
   - West Coast ×2
   - Europe ×2
   - Upload to `serpradio-public` bucket

2. **Setup Daily Automation**
   - Configure GitHub Actions secrets
   - Enable `.github/workflows/serpradio_daily.yml`

3. **Wire Lovable Components**
   - Split-flap board → `/api/board/feed` + `/api/notifications/board`
   - Route pages → `/api/book/summary` + `/api/book/lead_time_curve`
   - Play buttons → `/vibenet/generate`

4. **SEO & Analytics**
   - Generate route pages for top 50 NYC pairs
   - Add JSON-LD structured data
   - Setup analytics tracking

---

## Success Checklist

- [ ] Railway service shows "Active" status
- [ ] All smoke tests return 200 OK
- [ ] Logs show no errors
- [ ] Board feed returns data (after seeding)
- [ ] Audio generation completes in <10s
- [ ] Lovable frontend connects successfully
- [ ] Split-flap board animates with live data
- [ ] Play buttons generate and play audio

**Estimated total time: 15-20 minutes** ⚡

---

## Support

- Railway docs: https://docs.railway.app
- Supabase docs: https://supabase.com/docs
- Issues: https://github.com/jamesfgibbons/tgflightsfromnyc/issues
