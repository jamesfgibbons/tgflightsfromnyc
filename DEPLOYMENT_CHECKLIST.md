# 🚀 Railway Deployment Checklist

## Pre-Deployment (Do Once)

### 1. GitHub Setup
- [x] Git tree is clean (no nested repos)
- [x] Remote configured: `jamesfgibbons/tgflightsfromnyc`
- [ ] Push latest changes to GitHub
- [ ] Connect Railway to GitHub repo

### 2. Supabase Setup
- [ ] Apply SQL migrations in order:
  1. `sql/000_init_schema.sql`
  2. `sql/board_feed_schema.sql`
  3. `sql/best_time_schema.sql`
  4. `sql/vibenet_schema.sql` (optional)
  5. `sql/010_notification_engine.sql`
  6. `sql/storage_policies.sql` (if using Supabase Storage)

- [ ] Create storage buckets:
  - `serpradio-artifacts` (private)
  - `serpradio-public` (public)

- [ ] Copy these from Supabase Dashboard:
  - [ ] `SUPABASE_URL` (Settings → API → Project URL)
  - [ ] `SUPABASE_SERVICE_ROLE` (Settings → API → service_role key)

### 3. Railway Environment Variables

Set these in Railway → Variables:

```bash
# === Core (Required) ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=eyJ...your-service-role-key
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public
ADMIN_SECRET=generate-long-random-string-here

# === CORS (Required) ===
CORS_ORIGINS=https://your-lovable-app.lovable.dev,http://localhost:5173

# === Audio Rendering ===
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

# === Configuration Paths ===
DESTINATION_ONTOLOGY_PATH=config/destination_ontology.yaml
VIBE_PALETTES_PATH=config/vibe_palettes.yaml
VIBE_RULES_PATH=config/vibe_rules.yaml

# === Optional: AI Providers ===
OPENAI_API_KEY=sk-...
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini

XAI_API_KEY=xai-...
XAI_MODEL=grok-beta

# === Server ===
PORT=8000
APP_VERSION=1.0.0
```

## Deployment

### Option A: Procfile (Recommended - Easier)

Railway will auto-detect `Procfile` at root:
```
web: uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Requirements:**
- `requirements.txt` must install cleanly
- System dependencies (fluidsynth, ffmpeg) need to be in Dockerfile or buildpack

### Option B: Dockerfile (Recommended - Full Control)

Use the enhanced Dockerfile (see root `Dockerfile`):
- Installs fluidsynth + ffmpeg
- Pins Python 3.11
- Sets soundfont path
- Handles all dependencies

Railway → Settings → Deploy:
- **Build Method**: Dockerfile
- **Dockerfile Path**: `./Dockerfile`

## Post-Deployment Verification

### 1. Smoke Tests

```bash
# Set your Railway URL
BASE=https://your-service.up.railway.app

# Health check
curl "$BASE/health"

# Board feed
curl "$BASE/api/board/feed?origins=JFK,EWR,LGA&limit=12"

# Notifications
curl "$BASE/api/notifications/board?origins=JFK,EWR,LGA"

# Best-time booking
curl "$BASE/api/book/summary?origin=JFK&dest=MIA&month=4"
curl "$BASE/api/book/lead_time_curve?origin=JFK&dest=MIA&month=4"

# VibeNet palettes
curl "$BASE/vibenet/vibes"

# VibeNet generate
curl -X POST "$BASE/vibenet/generate" \
  -H "content-type: application/json" \
  -d '{
    "data":[0.2,0.4,0.6,0.8],
    "controls":{"bars":8,"tempo_hint":112},
    "meta":{"origin":"JFK","destination":"MIA"}
  }'
```

Expected results:
- ✅ All return 200 OK
- ✅ JSON responses match documented schemas
- ✅ `/vibenet/generate` returns `mp3_url` (or `midi_url` if `RENDER_MP3=0`)

### 2. Frontend Connection (Lovable)

Update your Lovable project:

**public/config.json:**
```json
{
  "VITE_API_BASE": "https://your-service.up.railway.app"
}
```

**Or set environment variable:**
```bash
VITE_API_BASE=https://your-service.up.railway.app
```

### 3. Acceptance Criteria

- [ ] `/health` returns `{ok: true}`
- [ ] Board feed returns ≥10 routes for NYC origins
- [ ] Notifications show badges for routes (after seeding)
- [ ] Best-time endpoints return BWI + sweet-spot data
- [ ] VibeNet generate completes in <10s
- [ ] MP3 URLs are playable (signed, not expired)
- [ ] Lovable frontend loads split-flap board
- [ ] "Play trend" button generates audio

## Troubleshooting

### Issue: Dependencies fail to install
**Solution:** Use Dockerfile (Option B) instead of Procfile

### Issue: No soundfont found
**Check:** `SOUNDFONT_PATH` points to `/usr/share/sounds/sf2/FluidR3_GM.sf2`
**Verify:** `ls -la /usr/share/sounds/sf2/` in Railway shell

### Issue: CORS errors in Lovable
**Check:** `CORS_ORIGINS` includes your Lovable domain
**Regex support:** `https://.+\.lovable\.dev` works for preview domains

### Issue: Empty board feed
**Check:**
1. Supabase migrations applied?
2. Data seeded in `travel_routes_nyc`, `price_quotes`?
3. Run ingestion scripts: `scripts/upsert_price_quotes_from_json.py`

### Issue: MP3 generation fails
**Options:**
1. Set `RENDER_MP3=0` (MIDI-only mode)
2. Verify fluidsynth installed: `which fluidsynth`
3. Check logs for soundfont errors

## Next Steps After Deployment

1. **Seed Initial Data**
   ```bash
   # NYC routes
   python scripts/publish_top_routes.py --input destinations_by_popularity.csv

   # Price quotes
   python scripts/upsert_price_quotes_from_json.py
   ```

2. **Generate Featured Mixes** (6-10 MP3s)
   - Caribbean ×3
   - West Coast ×2
   - Europe ×2
   - Asia-Pacific ×2
   - Upload to `PUBLIC_STORAGE_BUCKET/featured/`
   - Update `public/featured_mixes.json`

3. **Setup Daily Automation**
   - Configure GitHub Actions secrets (see `.github/workflows/serpradio_daily.yml`)
   - Or use Railway Cron (if available)

4. **Wire Lovable Frontend**
   - Home: Split-flap board + Best-Time rail + Featured Mixes
   - Route pages: Summary + Curve + Play button
   - Embed widget: `/embed?origins=JFK,EWR&limit=12`

## Success Metrics

**MVP Launch Ready When:**
- ✅ All smoke tests pass
- ✅ Lovable frontend displays live data
- ✅ Audio generation works end-to-end
- ✅ Lighthouse score ≥90 mobile
- ✅ No 5xx errors in Railway logs

**Current Status:** Backend code ready, needs deployment + frontend wiring
