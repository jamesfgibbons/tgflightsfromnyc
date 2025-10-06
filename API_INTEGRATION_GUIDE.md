# API Integration Guide (Lovable Front-End)

Updated: 2025-10-05. This guide provides paste-ready TypeScript for interacting with the SERPRadio backend.

## 1. Runtime Config

```ts
// src/lib/runtimeConfig.ts
export const apiBase = () => {
  const cfg = (window as any).__CONFIG__;
  return cfg?.FRONTEND_API_URL || import.meta.env.VITE_API_BASE || 'https://serpradio-backend-production.up.railway.app/api';
};
```

## 2. Type Definitions

```ts
// src/lib/types.ts
export type Origin = 'JFK' | 'EWR' | 'LGA';
export type Momentum = 'rising' | 'falling' | 'flat';
export type DealTier = 'BUY' | 'TRACK' | 'WAIT' | 'sweetSpot';

export interface BoardRow {
  id: string;
  origin: Origin;
  dest: string;
  city?: string;
  tempoBpm?: number;
  momentum?: Momentum;
  trend?: number[];
  dealScore?: number;
  priceMin?: number;
  priceMax?: number;
  deltaPct?: number;
  nonstop?: boolean;
  paxBucket?: 'sm' | 'md' | 'lg';
  seasonal?: boolean;
  palette?: string;
}

export interface BoardBadge {
  id: string;            // `${origin}-${dest}`
  labels?: string[];
  dropPct?: number;
  spikePct?: number;
  windowOpen?: boolean;
  newLow?: boolean;
  severity?: 'info' | 'watch' | 'alert' | 'urgent';
  lastSeen: string;
}

export interface BookingSummary {
  bwi?: number;
  sweet_spot_min?: number;
  sweet_spot_max?: number;
  recommendation?: DealTier;
  confidence?: number;
  todayPrice?: number;
  deltaPct?: number;
  trend?: Momentum;
  rationale?: string;
}

export interface LeadTimePoint {
  lead_days: number;
  q25: number;
  q50: number;
  q75: number;
  volatility?: number;
}

export interface LeadTimeCurve {
  points: LeadTimePoint[];
}

export interface NotificationEvent {
  event_type: 'price_drop' | 'price_spike' | 'new_low' | 'window_open' | 'window_close' | 'momentum_rising' | 'momentum_falling';
  origin: string;
  dest: string;
  deltaPct?: number;
  observed_at: string;
  severity?: 'low' | 'medium' | 'high';
  meta?: Record<string, unknown>;
}
```

## 3. API Client Functions

```ts
// src/lib/serpradioApi.ts
import { apiBase } from './runtimeConfig';

const json = (r: Response) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)));

export const getBoardFeed = (origins: string[], limit = 12) =>
  fetch(`${apiBase()}/board/feed?origins=${origins.join(',')}&limit=${limit}`).then(json);

export const getBoardBadges = (origins: string[]) =>
  fetch(`${apiBase()}/notifications/board?origins=${origins.join(',')}`).then(json);

export const getRouteBadges = (origin: string, dest: string, hours = 168) =>
  fetch(`${apiBase()}/notifications/route?origin=${origin}&dest=${dest}&hours=${hours}`).then(json);

export const getBestTimeSummary = (origin: string, dest: string, month = 3, cabin = 'economy') =>
  fetch(`${apiBase()}/book/summary?origin=${origin}&dest=${dest}&month=${month}&cabin=${cabin}`).then(json);

export const getLeadTimeCurve = (origin: string, dest: string, month = 3, cabin = 'economy') =>
  fetch(`${apiBase()}/book/lead_time_curve?origin=${origin}&dest=${dest}&month=${month}&cabin=${cabin}`).then(json);

export async function generateAutoVibe(
  data: number[],
  bars = 8,
  tempo = 112,
  meta: { origin: string; destination: string }
): Promise<string | null> {
  const base = apiBase().replace(/\/api$/, ''); // /vibenet lives at root
  const response = await fetch(`${base}/vibenet/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ data, controls: { bars, tempo_hint: tempo }, meta }),
  });
  if (!response.ok) throw new Error(`Vibe generation failed: ${response.status}`);
  const result = await response.json();
  return result?.mp3_url || result?.job?.mp3_url || null;
}

export async function generateExplicitVibe(
  data: number[],
  paletteSlug: string,
  bars = 8,
  tempo = 112
): Promise<string | null> {
  const response = await fetch(`${apiBase()}/vibe/generate_data`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ data, palette_slug: paletteSlug, total_bars: bars, tempo_hint: tempo }),
  });
  if (!response.ok) throw new Error(`Vibe generation failed: ${response.status}`);
  const result = await response.json();
  return result?.mp3_url || result?.job?.mp3_url || null;
}

export async function fetchWithRetry<T>(fn: () => Promise<T>, retries = 3, delay = 1000): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (retries === 0) throw err;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return fetchWithRetry(fn, retries - 1, delay * 2);
  }
}
```

## 4. Hooks

### useBoardData

```ts
// src/hooks/useBoardData.ts
import { useEffect, useState } from 'react';
import type { BoardRow, BoardBadge } from '@/lib/types';
import { getBoardFeed, getBoardBadges } from '@/lib/serpradioApi';

export function useBoardData(origins: string[] = ['JFK','EWR','LGA'], limit = 12) {
  const [rows, setRows] = useState<BoardRow[]>([]);
  const [badges, setBadges] = useState<Record<string, BoardBadge>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const [feed, badgePayload] = await Promise.all([
          getBoardFeed(origins, limit),
          getBoardBadges(origins),
        ]);
        if (cancelled) return;
        const feedRows: BoardRow[] = feed?.items || feed || [];
        const badgeMap: Record<string, BoardBadge> = {};
        (badgePayload?.items || badgePayload || []).forEach((b: any) => {
          badgeMap[b.id] = b;
        });
        setRows(feedRows);
        setBadges(badgeMap);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error('Board fetch failed'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [origins.join(','), limit]);

  return { rows, badges, loading, error };
}
```

### useRouteBadges

```ts
// src/hooks/useRouteBadges.ts
import { useEffect, useState } from 'react';
import type { NotificationEvent } from '@/lib/types';
import { getRouteBadges } from '@/lib/serpradioApi';

export function useRouteBadges(origin: string, dest: string, hours = 168) {
  const [events, setEvents] = useState<NotificationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!origin || !dest) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const payload = await getRouteBadges(origin, dest, hours);
        if (cancelled) return;
        setEvents(payload?.events || payload || []);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error('Route badges failed'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [origin, dest, hours]);

  return { events, loading, error };
}
```

## 5. SEO Helpers

```ts
// src/lib/seo.ts
export function generateRouteJsonLd(origin: string, destination: string, medianPrice: number, summary?: any) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: `${origin} to ${destination} Flight Prices (NYC)`,
    description: `Real-time price tracking for ${origin} → ${destination}. Includes booking window guidance and trend data.`,
    measurementTechnique: 'Lead-time price curve (q25/q50/q75), Best Window Index (BWI)',
    variableMeasured: ['q25','q50','q75','volatility','BWI','sweet_spot'],
    keywords: ['best time to book','flight prices','NYC flights',`${origin} to ${destination}`],
    isAccessibleForFree: true,
    distribution: [{
      '@type': 'DataDownload',
      encodingFormat: 'application/json',
      contentUrl: `/api/book/lead_time_curve?origin=${origin}&dest=${destination}`,
    }],
    additionalProperty: [
      { '@type': 'PropertyValue', name: 'medianPriceUSD', value: medianPrice },
      ...(summary?.bwi ? [{ '@type': 'PropertyValue', name: 'BWI', value: summary.bwi }] : []),
    ],
  };
}
```

## 6. Usage Example – Route Detail

```tsx
import { useEffect, useState } from 'react';
import { getBestTimeSummary, getLeadTimeCurve, generateAutoVibe } from '@/lib/serpradioApi';
import { BestTimeSummary } from '@/components/BestTimeSummary';
import { LeadTimeCurve } from '@/components/LeadTimeCurve';

export function RouteDetail({ origin, dest }: { origin: string; dest: string }) {
  const [summary, setSummary] = useState<any>(null);
  const [curve, setCurve] = useState<any>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    Promise.all([
      getBestTimeSummary(origin, dest, 3),
      getLeadTimeCurve(origin, dest, 3),
    ]).then(([s, c]) => {
      setSummary(s);
      setCurve(c);
    });
  }, [origin, dest]);

  const playTrend = async () => {
    if (!curve?.points) return;
    const vals = curve.points.map((p: any) => p.q50).filter(Boolean);
    if (vals.length === 0) return;
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const data = vals.slice(0, 16).map((v: number) => (v - min) / Math.max(1, max - min));
    setPlaying(true);
    try {
      const url = await generateAutoVibe(data, 16, 112, { origin, destination: dest });
      if (url) {
        const audio = new Audio(url);
        await audio.play();
      }
    } finally {
      setPlaying(false);
    }
  };

  return (
    <div>
      {summary && <BestTimeSummary summary={summary} />}
      {curve && <LeadTimeCurve curve={curve} />}
      <button onClick={playTrend} disabled={playing}>
        {playing ? 'Playing…' : 'Play the Trend'}
      </button>
    </div>
  );
}
```

## 7. Testing Checklist

- All endpoints respond 200 with expected JSON shape
- CORS headers include Lovable domain
- Audio generation completes < 8s for 16 bars
- Loading/error states render gracefully
- Badges display correctly in board and timeline
- `generateRouteJsonLd` output validates in Google Rich Results tester

## 8. References

- `PRODUCTION_SPEC.md`
- `COMPLETE_ROADMAP.md`
- `SIGNATURE_POLISH.md`
- Audible Intelligence Fabric™ Codex

