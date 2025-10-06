# Agentic B2C Web App for Demand Generation & Sonification

This document aligns the stack and strategy for a consumer‑facing SERPRadio experience that turns live travel data into immersive visuals (split‑flap board, maps) and audio (VibeNet), while driving organic acquisition via programmatic SEO.

## Overview

- Lovable.dev hosts the SERPRadio.com landing shell (no‑code fast iteration)
- Vercel hosts the UI apps:
  - Vite React split‑flap board (MVP visual + chat overlays)
  - Optional Next.js dashboard (routes + latest quotes + embeds)
- Railway hosts the FastAPI backend (core orchestration + VibeNet + Grok)
- Supabase stores routes, quotes, logs, optional context summaries
- Pipelines populate Supabase (OpenAI parsing), enrich with Grok (xAI), and generate preset audio with VibeNet

## Architecture (Aligned)

- Front Door (MVP Shell): Lovable.dev (SERPRadio.com)
  - Embeds Vercel components via iframe or links (board, maps, tools)
  - Collects email/intake (optional) → `/api/intake/prompt(s)`

- UI (Vercel)
  - Vite app (`vite-react-user`): split‑flap board, context overlays, chat (Vercel AI SDK)
  - Next app (`vercel-app`): dashboard/table views, /embed board, API proxies, KV cache
  - Both apps call backend via rewrites or env (`VITE_API_BASE`, `BACKEND_BASE_URL`)

- Backend (Railway)
  - FastAPI (`src/main.py`) exposes:
    - `/api/board/feed` (dataset‑driven board rows)
    - `/api/travel/routes_nyc`, `/api/travel/price_quotes[_latest]`
    - `/api/llm/grok_search`, `/api/llm/run_summary`, `/api/intake/*`
    - `/api/travel/context` (summaries/citations from artifacts or Supabase)
  - VibeNet endpoints (`/api/vibe/*`) for on‑the‑fly sonification

- Data (Supabase)
  - Tables: `travel_routes_nyc`, `price_quotes`, `api_results`, `llm_results`
  - Views: `vw_latest_price_quotes`, `vw_routes_top_by_origin`
  - Optional: `web_context_summaries` for curated Grok summaries/citations

## Deploy (MVP)

1) Supabase
- Supabase schema: `supabase db remote commit --file sql/000_init_schema.sql`
- Seed: `scripts/upsert_travel_routes_from_json.py`, `scripts/upsert_price_quotes_from_json.py`
- RLS (optional public read): enable RLS then `create policy ... using (true)` for `select`

2) Backend on Railway
- Use Dockerfile or Nixpacks (Procfile: `web: uvicorn src.main:app --host 0.0.0.0 --port $PORT`)
- Env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`, `CORS_ORIGINS`, optional `XAI_API_KEY`
- Verify `GET /api/healthz` then travel and board routes

3) Vite on Vercel
- `vite-react-user/vercel.json`: set backend destination to Railway domain
- Env (optional): `XAI_API_KEY` (Edge `/api/chat`), `VITE_API_BASE`
- Deploy → Board live

4) Next on Vercel (optional)
- Set `BACKEND_BASE_URL` and deploy for dashboard + /embed

5) Lovable.dev
- Embed Vercel board/map as iframe on SERPRadio.com landing
- Link to tools (dashboard, chat) hosted on Vercel

## Programmatic SEO (2025 Playbook)

- Targets: route pages (e.g., `/routes/jfk-lax`), city hubs, deal guides, tools
- Generation:
  - Templates + Supabase data pull
  - Optional LLM assist (Grok/OpenAI) via Vercel AI SDK (server actions or build step)
- Rendering strategies:
  - Next.js (recommended): SSG/ISR for SEO pages, CSR for tools
  - Vite: prerender with `vite-plugin-ssr` or static export for key pages
- Enhancers: schema.org (FAQ, Article), sitemaps, breadcrumbs, canonical tags
- Performance: edge caching, KV warmed endpoints, small JS, image/CDN hygiene

## Sonification Modes

- Preset (batch): railway cron runs VibeNet, stores MP3/MIDI in Supabase Storage, used by SEO pages and embeds for instant playback
- On‑the‑fly: UI calls `/api/vibe/*`, generates MIDI in realtime, plays via Web Audio/Tone.js

## Data & Pipelines

- Route seeding: run JSON upserts → `travel_routes_nyc`
- Price parsing: OpenAI batch → parse → upsert `price_quotes`
- Grok context: xAI search summaries → artifact and/or upsert `web_context_summaries`
- Board dataset: `scripts/build_grok_viz_dataset.py` → consumed by `/api/board/feed`

## Ops & Security

- CORS allowlist: Vercel domains + localhost
- RLS: anon `select` (read‑only), service‑role for server writes
- Caching: KV for `/api/board/feed`, ETag/TTL where appropriate
- Observability: logs on Railway, Vercel analytics, simple Prom metrics endpoint

## Env Summary

Backend (Railway):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`, `CORS_ORIGINS`
- Optional: `XAI_API_KEY`, `OPENAI_API_KEY`, `INTAKE_TOKEN`

Vercel Vite:
- Rewrites → backend; optional `XAI_API_KEY`, `VITE_API_BASE`

Vercel Next:
- `BACKEND_BASE_URL`, optional KV

## Roadmap

- Context overlays with citations in Vite board
- `web_context_summaries` population + backend `/api/travel/context` first‑class
- Explore map: arcs, route chips, audio cues
- Annotations table + moderation UI
- Programmatic SEO rollout: route hubs, dynamic deal pages, tools directory
