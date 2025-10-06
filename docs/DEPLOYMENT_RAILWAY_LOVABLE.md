# Deployment Plan (Railway + Supabase + Lovable)

North‑star: “Hear the fares.” Ship the NYC split‑flap board with playable mixes and Best‑Time pages. This doc details turning today’s code into a live stack on Railway (API), Supabase (data/storage), and Lovable (Vite React UI).

## 1) Prereqs

- Accounts: Railway, Supabase, Lovable (or Vercel), domain/DNS.
- Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE(_KEY)` or `SUPABASE_ANON_KEY`, optionally `AWS_*` if using S3; `CORS_ORIGINS`, `ADMIN_SECRET`.
- Node + Python build caches enabled on hosts where possible.

## 2) Supabase setup

1. Create project; note the URL, anon key, and service role key.
2. Storage: create buckets (e.g., `serpradio-artifacts`, `serpradio-public`). Mark public buckets appropriately.
3. Migrations: apply SQL from `sql/` in order:
   - `sql/000_init_schema.sql:1`
   - other modular files in `sql/` (board feeds, vibenet schema, views)
4. Tables to confirm:
   - price observations, vibenet_runs/items, momentum_bands, notification_events (see `sql/*`).

## 3) Backend on Railway

Option A: Using Dockerfile in repo (recommended)

- Railway → New project → Deploy from GitHub → pick this repo.
- Set service build to Docker; port `8000` exposed.
- Env vars:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE` (or `_KEY`)
  - `STORAGE_BUCKET` (e.g., `serpradio-artifacts`) and `PUBLIC_BUCKET` as needed
  - `CORS_ORIGINS` (comma‑separated, include your Lovable domain)
  - `ADMIN_SECRET` (random)
  - `RENDER_MP3=0` initially (skip fluidsynth/ffmpeg), or set `1` after adding those deps in Docker.
- Start command: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
- Health: `GET /health` (returns JSON; add path in Railway health checks).

Optional MP3 rendering

- Install `fluidsynth` and `ffmpeg` in the container or use a base image with them.
- Ensure a soundfont exists (`completed/GeneralUser.sf2` is present). `src/renderer.py:1` checks availability.

## 4) Frontend on Lovable

Repo path: `vite-react-user/`

1. Configure env:
   - `VITE_API_BASE` → `https://<railway-domain>` (no trailing slash)
2. Build and deploy from Lovable UI; confirm SSR/SPA settings as needed.
3. CORS: confirm `CORS_ORIGINS` on API allows the Lovable domain.
4. Smoke test components:
   - Board feed (GET `/api/board/feed`)
   - Best‑Time summary/curve
   - Sonify play (POST `/api/vibe/generate_data` or `/vibenet/generate`)

## 5) Data backfill + crons

1. Backfill price observations using your ETL pipeline or seed CSVs.
2. Schedule cron (Railway or Supabase) every 6 hours to compute deltas, slopes, and write `notification_events`.
3. Optionally add an admin endpoint `/api/pricing/refresh` to trigger ad‑hoc pulls for a few routes.

## 6) Pre‑render mixes for Featured rail

1. Use `/vibenet/generate` or `/api/vibe/generate_data` to render 6–10 short tracks.
2. Upload results to public bucket (e.g., `serpradio-public/mixes/…`); paste their URLs into the Lovable `FeaturedMixes` component.

## 7) Acceptance (go‑live)

- Home
  - Board rows show price + Δ%; click → MP3/MIDI plays in <5s.
  - Best‑Time Snapshot shows ≥5 routes with BUY/TRACK/WAIT.
  - Featured Mixes: ≥6 tracks play instantly.
- Route detail
  - Summary returns BWI, sweet‑spot, rec, confidence.
  - Curve renders ≥20 points; play sonifies q50.
  - JSON‑LD present; sitemap submitted.
- DNE
  - notification_events rows appear on drops/spikes/window transitions; badges visible on feed.
- Perf/A11y
  - Lighthouse ≥90 mobile; keyboard navigation supports board.

## 8) Troubleshooting

- CORS errors → verify `CORS_ORIGINS` and `VITE_API_BASE`.
- No audio → check `RENDER_MP3` and renderer availability; fall back to MIDI if needed.
- Missing data → backfill tables; confirm SQL views and Supabase RLS.
- 500s on storage → verify bucket names and service role key.

## 9) Useful cURL

```bash
# List palettes
curl -s https://<railway-domain>/vibenet/vibes | jq .

# Generate a track from normalized data
curl -sX POST https://<railway-domain>/vibenet/generate \
  -H 'content-type: application/json' \
  -d '{"vibe_slug":"circle_of_life_travel","data":[0.2,0.4,0.6,0.8],"controls":{"bars":16}}' | jq .

# Board feed
curl -s 'https://<railway-domain>/api/board/feed?origins=JFK,EWR,LGA&limit=10' | jq .
```

