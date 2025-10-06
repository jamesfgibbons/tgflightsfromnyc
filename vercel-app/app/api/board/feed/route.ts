export const runtime = 'edge';

import { kv } from '@vercel/kv';

export async function GET(req: Request) {
  const url = new URL(req.url);
  const target = url.searchParams.get('target') ?? 'keywords';
  const limit = url.searchParams.get('limit') ?? '12';
  const lookback = url.searchParams.get('lookback_days') ?? '30';
  const palette = url.searchParams.get('palette_slug') ?? '';
  const dataset = url.searchParams.get('dataset');
  const key = `board:${target}:${limit}:${lookback}:${palette}:${dataset ?? ''}`;

  try {
    const cached = await kv.get<string>(key);
    if (cached) {
      return new Response(cached, { headers: { 'content-type': 'application/json', 'x-cache': 'HIT' } });
    }
  } catch (_) {
    // KV optional; continue
  }

  const backend = process.env.BACKEND_BASE_URL!;
  const qs = new URLSearchParams({ target, limit, lookback_days: lookback, palette_slug: palette });
  if (dataset) qs.set('dataset', dataset);
  const res = await fetch(`${backend}/api/board/feed?${qs.toString()}`, { headers: { accept: 'application/json' } });
  const body = await res.text();
  if (!res.ok) return new Response(body, { status: 502 });

  try {
    const ttl = parseInt(process.env.BOARD_FEED_TTL_SEC ?? '45', 10);
    await kv.set(key, body, { ex: ttl });
  } catch (_) {}

  return new Response(body, {
    headers: { 'content-type': 'application/json', 'cache-control': 's-maxage=45, stale-while-revalidate=60' },
  });
}

