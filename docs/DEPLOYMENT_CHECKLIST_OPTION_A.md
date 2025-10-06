# Option A Deployment Checklist (Railway API + Static Frontend)

This checklist hardens security and gets the stack live without Vercel. Use alongside README.md and sql/000_init_schema.sql.

## 1) Supabase Security & Schema
- Run schema: `sql/000_init_schema.sql` in Supabase SQL Editor (or via CLI).
- Apply storage bucket policies (public read only for public assets): run `sql/storage_policies.sql` in SQL Editor.
- Confirm RLS is ON by default for project tables; do not create permissive policies beyond what’s in `000_init_schema.sql`.

## 2) Storage Buckets
- Private artifacts: `serpradio-artifacts` (private bucket)
- Public assets: `serpradio-public` (public bucket, read-only to the world)
- Backend writes both via service role; clients only read from `serpradio-public` over signed or public URLs.

## 3) Backend (Railway)
- Procfile present: `web: uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- Required env:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`
  - `STORAGE_BUCKET=serpradio-artifacts`, `PUBLIC_STORAGE_BUCKET=serpradio-public`
  - `CORS_ORIGINS=https://<frontend-domain>,http://localhost:5173`
  - `ADMIN_SECRET=<random>`
  - Providers: `GROK_API_KEY` or `XAI_API_KEY` (xAI), plus optional `OPENAI_API_KEY`, `GROQ_API_KEY`
  - Optional: `BOARD_DATASET_PATH=data/grok_tips_inspiration_dataset.json`
- Verify:
  - `GET /api/healthz`
  - `GET /api/board/feed`
  - `POST /api/vibe/generate_data`

## 4) Frontend (Static Host: Cloudflare Pages/Netlify/Railway Static)
- Build Vite app: `cd vite-react-user && npm install && npm run build`
- Configure `VITE_API_BASE=https://<railway-backend>` for dev/prod
- Ensure backend `CORS_ORIGINS` contains frontend domain(s)
- Smoke test split‑flap: loads `/api/board/feed`, plays audio via `/api/vibe/generate_data`

## 5) Supabase Edge Functions (if used)
If you proxy or enrich via Edge Functions, ensure CORS matches the Railway backend and allows custom headers.

Example `functions/_shared/cors.ts` (Deno):
```ts
export const ALLOWED_ORIGINS = [
  'https://<frontend-domain>',
  'http://localhost:5173',
];
export const ALLOWED_HEADERS = 'authorization,content-type,x-client-token,x-admin-secret';
export const ALLOWED_METHODS = 'GET,POST,PUT,OPTIONS';

export function withCORS(origin: string | null, res: Response): Response {
  const allowed = origin && ALLOWED_ORIGINS.includes(origin) ? origin : '*';
  const headers = new Headers(res.headers);
  headers.set('Access-Control-Allow-Origin', allowed);
  headers.set('Access-Control-Allow-Headers', ALLOWED_HEADERS);
  headers.set('Access-Control-Allow-Methods', ALLOWED_METHODS);
  headers.set('Access-Control-Max-Age', '86400');
  headers.append('Vary', 'Origin');
  return new Response(res.body, { status: res.status, headers });
}
```

Example usage in an Edge Function:
```ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { withCORS, ALLOWED_HEADERS, ALLOWED_METHODS } from '../_shared/cors.ts';

serve(async (req) => {
  const origin = req.headers.get('origin');
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': origin ?? '*',
        'Access-Control-Allow-Headers': ALLOWED_HEADERS,
        'Access-Control-Allow-Methods': ALLOWED_METHODS,
        'Access-Control-Max-Age': '86400',
        'Vary': 'Origin',
      },
    });
  }
  // ... your handler ...
  const res = new Response(JSON.stringify({ ok: true }), {
    headers: { 'content-type': 'application/json' },
  });
  return withCORS(origin, res);
});
```

## 6) API Authentication
- Admin endpoints require header `X-Admin-Secret: <ADMIN_SECRET>` (do not use from public clients).
- Intake endpoints (optional) require `X-Client-Token: <INTAKE_TOKEN>`; set only on trusted clients or server tasks.
- Ensure backend CORS `allow_headers` covers `x-admin-secret` and `x-client-token` (it is `*` by default in `src/main.py`).

## 7) Storage Policy Strategy
- Public: only read access for `serpradio-public` to `anon`/`authenticated` (anyone); writes via server only.
- Private: no read/write for clients on `serpradio-artifacts`; all access via server/service role & signed URLs.

## 8) CI/CD Tips
- Before deploy: `pytest --maxfail=1`
- After deploy: run `scripts/verify_backend.sh` and `scripts/vibenet_curl_smoke.sh`
- Consider a single GitHub Action: tests → Railway deploy → CF Pages deploy

