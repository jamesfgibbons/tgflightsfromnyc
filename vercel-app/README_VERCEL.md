# VibeNet Vercel Concepts (Split‑Flap + Radio + Composer)

This Next.js app hosts three small concept UIs on Vercel, wired to the FastAPI backend in `src/`:

- Split‑Flap Board (`/embed`) → proxies `/api/board/feed` with KV caching
- Radio Tuner (`/radio`) → tunes through canonical NYC routes, fetches price quotes
- Deal Composer (`/composer`) → Vercel AI SDK chat with tools to fetch routes, price quotes, board feed, and Grok websearch

## Quick Deploy

1) Create a new Vercel project pointing to `vercel-app/`

2) Set Environment Variables (Project → Settings → Environment Variables):

- BACKEND_BASE_URL=https://YOUR-BACKEND.example.com
- ADMIN_SECRET=… (same as FastAPI ADMIN secret)
- INTAKE_TOKEN=… (same as backend intake)
- BOARD_FEED_TTL_SEC=45
- KV_REST_API_URL=… (from Vercel KV)
- KV_REST_API_TOKEN=…
- AI_PROVIDER=openai (or `xai`)
- OPENAI_API_KEY=… (if AI_PROVIDER=openai)
- XAI_API_KEY=… (if AI_PROVIDER=xai)
- BASIC_AUTH_USER=… (optional: protect internal front‑end)
- BASIC_AUTH_PASS=… (optional)

3) Add Cron (vercel.json included)

- Schedules `/api/cron/xai-daily` at 09:00 UTC → calls your backend `/api/llm/run`

4) CORS on FastAPI

- Add your Vercel domain to `CORS_ORIGINS` env (comma-separated)

5) Deploy

- `vercel` (or Auto Deploy from Git)

## Endpoints in this app

- GET `/api/board/feed` → KV-cached proxy to FastAPI board feed
- GET `/api/travel/routes` → proxy to `/api/travel/routes_nyc`
- GET `/api/travel/price_quotes` → proxy with query params `origin`, `destination`
- POST `/api/llm/run` and GET `/api/cron/xai-daily` → admin-triggered ML runs (use server-side only)
- POST `/api/intake/prompt` → forwards to backend intake with `x-client-token`
- POST `/api/chat` → Vercel AI SDK chat, with tools to call backend
  - Tools include: routes, price quotes, board feed, and `searchWeb` (Grok websearch summary with citations)

## Aligns with Integrated System Summary

- Front end captures configs (chat + tuner + split‑flap UI), feeds the decoupled backend intake and orchestration.
- Edge routes + KV reduce latency and load; cron triggers daily xAI cache fills.
- Chat tool calls map to row-based data endpoints (routes, prices, board) and can be extended to Webz.io summaries.
- Visual split‑flap metaphors show trends; tuner maps to canonical routes; composer streams “data stories”.

## Local Dev

```
cd vercel-app
pnpm i   # or npm i / yarn
pnpm dev # http://localhost:3000
```

Set a `.env.local` with BACKEND_BASE_URL and optionally OPENAI_API_KEY/XAI_API_KEY. KV is optional locally.
For Grok websearch in chat tools, set `XAI_API_KEY`. The `searchWeb` tool calls the backend Grok endpoint regardless of the chat provider.

## Notes

- The split‑flap effect is a lightweight CSS animation keyed off feed updates.
- To add ETag/Last-Modified support, propagate headers from the backend in `/api/board/feed`.
- To wire Webz.io, add a new tool `getNewsContext` and proxy to a backend endpoint.
