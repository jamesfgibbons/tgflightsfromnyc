# SERPRadio v4.0 — Clean Monorepo (Railway + Supabase + Vercel)

This v4 folder is a minimal, production-ready monorepo to deploy the FastAPI backend on Railway, seed Supabase, and ship a Vite (Vercel) split‑flap frontend. It’s a cleaned structure that keeps the MVP simple while leaving room to grow.

## Stack
- Backend: FastAPI on Railway (Supabase DB, optional xAI Grok)
- Frontend: Vite React on Vercel (split‑flap board + optional chat)
- Data: Supabase tables + views (routes, quotes, “latest quotes” view)

## Quick Start (TL;DR)

1) Supabase
- SQL Editor → run:
  - `v4/sql/travel_routes_schema.sql`
  - `v4/sql/price_quotes.sql`
  - `v4/sql/views_travel.sql`
- Seed a few rows (Table Editor or CSV import). Optional: use the existing repo seeders in `scripts/` at repo root.

2) Backend on Railway
- Push this repo to GitHub (root). In Railway → Deploy from GitHub (root).
- Build method: Nixpacks (uses `v4/backend/Procfile`) or Dockerfile (uses `v4/backend/Dockerfile`).
- Service variables:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`
  - `CORS_ORIGINS=https://<your-vite-app>.vercel.app,http://localhost:5173`
  - Optional: `XAI_API_KEY`, `OPENAI_API_KEY`, `INTAKE_TOKEN`
- Verify:
  - `bash v4/scripts/verify_backend.sh https://<backend>.up.railway.app`

3) Frontend on Vercel (Vite)
- Folder: `v4/frontend`
- Edit `v4/frontend/vercel.json` → replace `https://YOUR_BACKEND_HOST` with your Railway URL.
- Deploy folder to Vercel (Root Directory = `v4/frontend`).
- Open preview → split‑flap board should load.

## Backend Details
- App entry: `v4/backend/app/main.py`
- Endpoints:
  - `GET /api/healthz`
  - `GET /api/board/feed` (dataset-backed; sample under `v4/backend/data/`)
  - `GET /api/travel/routes_nyc`
  - `GET /api/travel/price_quotes_latest`
  - `GET /api/llm/grok_search` (optional xAI Grok)
- Config: `v4/backend/.env.example` (copy values to Railway Variables)

## Frontend Details
- Vite app with a minimal split‑flap component calling `/api/board/feed` via rewrites
- Optional: set `XAI_API_KEY` in Vercel to enable `/api/chat` (add later)

## Scripts
- `v4/scripts/verify_backend.sh` — probes the live backend endpoints

## Programmatic SEO + Agentic plan
- See `v4/AGENTS.md` for the aligned “agentic B2C demand gen + sonification” strategy and next steps.

---

Need help wiring your Railway domain or Vercel rewrites? Share the backend URL and I’ll patch `vercel.json` and run live checks.
