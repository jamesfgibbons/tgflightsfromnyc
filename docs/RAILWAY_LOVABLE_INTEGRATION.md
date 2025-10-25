# 🔌 Railway ↔ Lovable Integration Guide

**This document shows exactly how to connect your Lovable frontend to the Railway backend.**

Based on the frontend spec provided, here's what needs to be configured for seamless communication.

---

## ✅ Backend API Endpoints (Already Available)

All endpoints from the frontend spec are **already implemented** in the Railway backend:

### 1. Board Feed
```bash
GET /api/board/feed?origins=JFK,EWR,LGA&limit=24
```
**Status:** ✅ Available
**File:** `src/board_api.py`
**Returns:** Array of deal cards with all required fields

### 2. Best-Time Summary
```bash
GET /api/book/summary?origin=EWR&dest=LAX&month=4
```
**Status:** ✅ Available
**File:** `src/booking_api.py`
**Returns:** BWI, sweet spot, recommendation, confidence

### 3. Lead-Time Curve
```bash
GET /api/book/lead_time_curve?origin=EWR&dest=LAX&month=4
```
**Status:** ✅ Available
**File:** `src/booking_api.py`
**Returns:** q25/q50/q75 points across lead days

### 4. Notifications (Board)
```bash
GET /api/notifications/board?origins=JFK,EWR,LGA
```
**Status:** ✅ Available
**File:** `src/notifications_api.py`
**Returns:** Recent price drop/surge events for board badges

### 5. Notifications (Route)
```bash
GET /api/notifications/route?origin=EWR&dest=LAX&hours=168
```
**Status:** ✅ Available
**File:** `src/notifications_api.py`
**Returns:** Timeline events for specific route

### 6. Sonification
```bash
POST /vibenet/generate
Body: {
  "data": [0.2, 0.4, 0.6, 0.8],
  "controls": {"bars": 8, "tempo_hint": 112},
  "meta": {"origin": "EWR", "destination": "LAX"}
}
```
**Status:** ✅ Available
**File:** `src/vibe_api.py`
**Returns:** mp3_url, midi_url, analysis object

### 7. Health Check
```bash
GET /api/healthz
```
**Status:** ✅ Available
**File:** `src/main.py`

### 8. Deal Awareness (New Feature)
```bash
GET /api/deals/evaluate?origin=JFK&dest=MIA&month=3
GET /api/deals/health
POST /api/deals/batch
```
**Status:** ✅ Available
**File:** `src/deals_api.py`

---

## 🔧 Railway Configuration (Backend)

### Step 1: Deploy Backend to Railway

**Already documented in:** `docs/DEPLOYMENT_SEQUENCE.md`

### Step 2: Set CORS Origins

In Railway → Service → Variables:

```env
CORS_ORIGINS=https://your-app.lovable.dev,https://*.lovable.dev,http://localhost:5173
```

**Important:** Update `your-app.lovable.dev` with your actual Lovable URL.

### Step 3: Get Railway URL

After deployment, Railway gives you:
```
https://YOUR-SERVICE.up.railway.app
```

**Copy this URL** - you'll need it for Lovable configuration.

---

## 🎨 Lovable Configuration (Frontend)

### Step 1: Set API Base URL

In your Lovable project, create/update `public/config.json`:

```json
{
  "VITE_API_BASE": "https://YOUR-SERVICE.up.railway.app"
}
```

**OR** set environment variable in Lovable:
```
VITE_API_BASE=https://YOUR-SERVICE.up.railway.app
```

### Step 2: Verify Connection

In your Lovable dev console:

```javascript
const API_BASE = import.meta.env.VITE_API_BASE;
console.log('API Base:', API_BASE);

// Test health endpoint
fetch(`${API_BASE}/api/healthz`)
  .then(r => r.json())
  .then(d => console.log('Backend health:', d));
```

Expected: `{status: "ok"}`

---

## 📦 Integration Helpers (Drop-in Files)

### File 1: `src/lib/api.ts` (API Client)

```typescript
/**
 * API client for SERPRadio backend
 * Handles all communication with Railway-hosted API
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export type BoardRow = {
  origin: string;
  dest: string;
  priceMin: number;
  deltaPct: number;
  dealScore: number;
  recommendation: 'BUY' | 'TRACK' | 'WAIT';
  trend: number[];
  tempoBpm?: number;
  nonstop?: boolean;
  palette?: string;
};

export type BestTimeSummary = {
  bwi: number;
  sweet_spot_min?: number;
  sweet_spot_max?: number;
  recommendation: 'BUY' | 'TRACK' | 'WAIT';
  confidence: number;
  todayPrice?: number;
  deltaPct: number;
  trend: 'falling' | 'rising' | 'flat';
};

export type LeadTimePoint = {
  lead_days: number;
  q25: number;
  q50: number;
  q75: number;
  volatility: number;
};

export type NotificationEvent = {
  origin: string;
  dest: string;
  event_type: 'price_drop' | 'price_surge' | 'window_open' | 'window_close';
  delta_pct?: number;
  timestamp: string;
  message: string;
};

export type AudioAnalysis = {
  contour: 'descending' | 'ascending' | 'flat' | 'mixed';
  spike_count: number;
  smoothness: number;
  brightness: number;
};

export type VibeResult = {
  mp3_url?: string;
  midi_url?: string;
  analysis?: AudioAnalysis;
};

/**
 * Fetch board feed (top deals)
 */
export async function getBoardFeed(
  origins: string[] = ['JFK', 'EWR', 'LGA'],
  limit: number = 24
): Promise<BoardRow[]> {
  const url = new URL(`${API_BASE}/api/board/feed`);
  url.searchParams.set('origins', origins.join(','));
  url.searchParams.set('limit', String(limit));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Board feed failed: ${response.status}`);

  const data = await response.json();
  return data.items || [];
}

/**
 * Fetch best-time summary for a route
 */
export async function getBestTimeSummary(
  origin: string,
  dest: string,
  month?: number
): Promise<BestTimeSummary> {
  const url = new URL(`${API_BASE}/api/book/summary`);
  url.searchParams.set('origin', origin.toUpperCase());
  url.searchParams.set('dest', dest.toUpperCase());
  if (month) url.searchParams.set('month', String(month));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Summary failed: ${response.status}`);

  return response.json();
}

/**
 * Fetch lead-time curve for a route
 */
export async function getLeadTimeCurve(
  origin: string,
  dest: string,
  month?: number
): Promise<{ points: LeadTimePoint[] }> {
  const url = new URL(`${API_BASE}/api/book/lead_time_curve`);
  url.searchParams.set('origin', origin.toUpperCase());
  url.searchParams.set('dest', dest.toUpperCase());
  if (month) url.searchParams.set('month', String(month));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Curve failed: ${response.status}`);

  return response.json();
}

/**
 * Fetch board notifications (recent price events)
 */
export async function getBoardNotifications(
  origins: string[] = ['JFK', 'EWR', 'LGA']
): Promise<NotificationEvent[]> {
  const url = new URL(`${API_BASE}/api/notifications/board`);
  url.searchParams.set('origins', origins.join(','));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Notifications failed: ${response.status}`);

  const data = await response.json();
  return data.events || [];
}

/**
 * Fetch route-specific notifications
 */
export async function getRouteNotifications(
  origin: string,
  dest: string,
  hours: number = 168
): Promise<NotificationEvent[]> {
  const url = new URL(`${API_BASE}/api/notifications/route`);
  url.searchParams.set('origin', origin.toUpperCase());
  url.searchParams.set('dest', dest.toUpperCase());
  url.searchParams.set('hours', String(hours));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Route notifications failed: ${response.status}`);

  const data = await response.json();
  return data.events || [];
}

/**
 * Generate sonification (vibe) from price data
 */
export async function generateVibe(
  data: number[],
  meta: { origin: string; destination: string },
  controls: { bars?: number; tempo_hint?: number } = {}
): Promise<VibeResult> {
  const payload = {
    data,
    meta,
    controls: {
      bars: controls.bars || 8,
      tempo_hint: controls.tempo_hint || 112,
    },
  };

  const response = await fetch(`${API_BASE}/vibenet/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`Vibe generation failed: ${response.status}`);

  return response.json();
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/api/healthz`);
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);

  return response.json();
}
```

### File 2: `src/lib/vibePlayer.ts` (Audio Player)

```typescript
/**
 * Global audio player with beat sync
 * Manages playback and emits beat events for UI pulse animations
 */

export type VibeMeta = {
  origin: string;
  destination: string;
  tempo?: number;
  bars?: number;
  palette?: string;
};

export type PlayerEvent = 'play' | 'pause' | 'beat' | 'stop';

export class VibePlayer {
  private audio = new Audio();
  private beatTimer?: number;
  private listeners = new Set<(event: PlayerEvent) => void>();

  constructor() {
    // Preload audio element for faster playback
    this.audio.preload = 'auto';
  }

  /**
   * Subscribe to player events
   */
  on(listener: (event: PlayerEvent) => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(event: PlayerEvent) {
    this.listeners.forEach((fn) => fn(event));
  }

  /**
   * Play audio from URL with beat sync
   */
  async playFrom(url: string, tempoBpm: number = 112) {
    this.stop();
    this.audio.src = url;

    try {
      await this.audio.play();
      this.emit('play');

      // Start beat timer
      const beatMs = 60000 / tempoBpm;
      this.beatTimer = window.setInterval(() => this.emit('beat'), beatMs);
    } catch (error) {
      console.error('Playback failed:', error);
      throw error;
    }
  }

  /**
   * Pause playback
   */
  pause() {
    if (!this.audio.paused) {
      this.audio.pause();
      this.emit('pause');
    }

    if (this.beatTimer) {
      clearInterval(this.beatTimer);
      this.beatTimer = undefined;
    }
  }

  /**
   * Stop playback and reset
   */
  stop() {
    if (!this.audio.paused) {
      this.audio.pause();
    }

    this.audio.currentTime = 0;

    if (this.beatTimer) {
      clearInterval(this.beatTimer);
      this.beatTimer = undefined;
    }

    this.emit('stop');
  }

  /**
   * Check if currently playing
   */
  get isPlaying(): boolean {
    return !this.audio.paused;
  }

  /**
   * Get current playback time
   */
  get currentTime(): number {
    return this.audio.currentTime;
  }

  /**
   * Get total duration
   */
  get duration(): number {
    return this.audio.duration;
  }
}

// Global singleton instance
export const vibePlayer = new VibePlayer();
```

### File 3: `src/lib/useBeatPulse.ts` (React Hook)

```typescript
/**
 * React hook for beat-synchronized animations
 * Returns a tick that increments on each beat
 */

import { useEffect, useState } from 'react';
import { vibePlayer } from './vibePlayer';

export function useBeatPulse(): number {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const unsubscribe = vibePlayer.on((event) => {
      if (event === 'beat') {
        setTick((t) => t + 1);
      }
    });

    return unsubscribe;
  }, []);

  return tick;
}

/**
 * Example usage:
 *
 * function DealCard() {
 *   const beat = useBeatPulse();
 *
 *   return (
 *     <div className={beat % 2 === 0 ? 'scale-100' : 'scale-105'}>
 *       Deal content
 *     </div>
 *   );
 * }
 */
```

### File 4: `src/lib/narrative.ts` (Data-Driven Copy)

```typescript
/**
 * Generate data-driven narratives for route pages
 * Creates contextual copy based on pricing analysis
 */

import type { AudioAnalysis } from './api';

export type RouteSummary = {
  bwi: number;
  recommendation: 'BUY' | 'TRACK' | 'WAIT';
  confidence: number;
  deltaPct: number;
  trend: 'falling' | 'rising' | 'flat';
  sweet_spot_min?: number;
  sweet_spot_max?: number;
};

/**
 * Build narrative text for route sonification panel
 */
export function buildNarrative(
  summary: RouteSummary,
  analysis?: AudioAnalysis
): string {
  const parts: string[] = [];

  // Lead sentence based on recommendation
  const lead =
    summary.recommendation === 'BUY'
      ? `Strong buy signal today: fares sit **${Math.abs(summary.deltaPct).toFixed(0)}%** ${summary.deltaPct < 0 ? 'below' : 'above'} the 30-day median.`
      : summary.recommendation === 'WAIT'
      ? `Hold off for now: fares are **${Math.abs(summary.deltaPct).toFixed(0)}%** ${summary.deltaPct > 0 ? 'above' : 'below'} the 30-day median and momentum is unfavorable.`
      : `Track this route: pricing is near trend with mixed momentum.`;
  parts.push(lead);

  // Sweet spot window
  if (summary.sweet_spot_min && summary.sweet_spot_max) {
    parts.push(
      `Historically, the best booking window lands **${summary.sweet_spot_min}–${summary.sweet_spot_max} days** before departure.`
    );
  }

  // Audio-aware sentence (if analysis available)
  if (analysis) {
    const shape =
      analysis.contour === 'descending'
        ? 'smooth, descending line'
        : analysis.contour === 'ascending'
        ? 'slow, rising line'
        : analysis.contour === 'flat'
        ? 'steady, low-motion line'
        : 'mixed contours with a few bends';

    const spikes =
      analysis.spike_count > 0
        ? ` You'll hear **${analysis.spike_count} noticeable spike${analysis.spike_count > 1 ? 's' : ''}**.`
        : '';

    parts.push(
      `In audio, this becomes a **${shape}**; higher brightness means stronger short-term movement.${spikes}`
    );
  } else {
    // Fallback based on trend
    if (summary.trend === 'falling') {
      parts.push(
        `Expect a smoother, downward musical contour—an ear-level indicator that prices are easing.`
      );
    }
    if (summary.trend === 'rising') {
      parts.push(
        `Expect a brighter, upward contour—an audible sign of pressure on fares.`
      );
    }
  }

  // Confidence
  parts.push(
    `Signal confidence: **${summary.confidence.toFixed(0)}%** (BWI ${summary.bwi.toFixed(0)}).`
  );

  return parts.join(' ');
}

/**
 * Format sweet spot range as text
 */
export function formatSweetSpot(min?: number, max?: number): string {
  if (!min && !max) return '—';
  if (min === max) return `${min}d`;
  return `${min}–${max}d`;
}

/**
 * Format price delta
 */
export function formatDelta(deltaPct: number): string {
  const sign = deltaPct > 0 ? '+' : '';
  return `${sign}${deltaPct.toFixed(0)}%`;
}
```

---

## 🧪 Testing the Integration

### Test 1: Health Check

```bash
curl https://YOUR-SERVICE.up.railway.app/api/healthz
```

Expected: `{"status":"ok"}`

### Test 2: Board Feed

```bash
curl "https://YOUR-SERVICE.up.railway.app/api/board/feed?origins=JFK,EWR,LGA&limit=5"
```

Expected: JSON array with deal cards

### Test 3: From Lovable Dev Console

```javascript
import { checkHealth, getBoardFeed, generateVibe } from '@/lib/api';

// Test health
await checkHealth();

// Test board feed
const deals = await getBoardFeed(['JFK', 'EWR', 'LGA'], 10);
console.log('Deals:', deals);

// Test sonification
const vibe = await generateVibe(
  [0.2, 0.4, 0.6, 0.8],
  { origin: 'JFK', destination: 'MIA' },
  { bars: 8, tempo_hint: 112 }
);
console.log('Vibe:', vibe);
```

### Test 4: Check CORS

In browser console on your Lovable app:

```javascript
fetch('https://YOUR-SERVICE.up.railway.app/api/healthz')
  .then((r) => console.log('CORS works!', r.status))
  .catch((e) => console.error('CORS error:', e));
```

If you see "CORS error", update `CORS_ORIGINS` in Railway.

---

## ✅ Integration Checklist

- [ ] Railway backend deployed and running
- [ ] Railway URL copied: `https://YOUR-SERVICE.up.railway.app`
- [ ] CORS configured in Railway with Lovable URL
- [ ] `VITE_API_BASE` set in Lovable (public/config.json or env var)
- [ ] Created `src/lib/api.ts` in Lovable project
- [ ] Created `src/lib/vibePlayer.ts` in Lovable project
- [ ] Created `src/lib/useBeatPulse.ts` in Lovable project
- [ ] Created `src/lib/narrative.ts` in Lovable project
- [ ] Tested health endpoint from browser
- [ ] Tested board feed from browser
- [ ] No CORS errors in browser console
- [ ] Audio playback works
- [ ] Beat pulse animations work

---

## 🐛 Troubleshooting

### "Failed to fetch" or CORS Error

**Problem:** Frontend can't reach backend

**Fix:**
1. Check `VITE_API_BASE` is correct
2. Update Railway `CORS_ORIGINS` to include your Lovable URL
3. Redeploy Railway service after CORS change
4. Hard refresh browser (Ctrl+Shift+R)

### "404 Not Found" on API Calls

**Problem:** Endpoint doesn't exist

**Fix:**
1. Verify endpoint path is correct (check `/api/` prefix)
2. Check Railway logs for errors
3. Verify backend deployment succeeded

### Audio Doesn't Play

**Problem:** MP3 URL not returned or invalid

**Fix:**
1. Check `RENDER_MP3=1` in Railway env vars
2. Verify `SOUNDFONT_PATH` is set
3. Check Railway logs for audio generation errors
4. Test sonification endpoint directly

### No Data Returned

**Problem:** Database is empty

**Fix:**
1. Seed sample data: `python scripts/seed_sample_prices.py`
2. OR wait for worker to complete first refresh
3. Check worker logs for errors

---

## 📞 Quick Reference

**Railway Backend URL Format:**
```
https://YOUR-SERVICE-NAME.up.railway.app
```

**Lovable Config Location:**
```
public/config.json
```

**Lovable Config Content:**
```json
{
  "VITE_API_BASE": "https://YOUR-SERVICE-NAME.up.railway.app"
}
```

**Test Commands:**
```bash
# Health
curl $RAILWAY_URL/api/healthz

# Board feed
curl "$RAILWAY_URL/api/board/feed?origins=JFK&limit=5"

# Best time
curl "$RAILWAY_URL/api/book/summary?origin=JFK&dest=MIA"
```

---

## 🎉 You're Ready!

Once you:
1. ✅ Deploy Railway backend
2. ✅ Set CORS_ORIGINS
3. ✅ Drop in the 4 integration files
4. ✅ Set VITE_API_BASE in Lovable

Your frontend will have **full access** to all backend features:
- ✅ Real-time board feed
- ✅ Best-time analysis
- ✅ Lead-time curves
- ✅ Notifications/badges
- ✅ Audio sonification
- ✅ Deal recommendations

**The frontend spec is now fully supported by the backend!** 🚀
