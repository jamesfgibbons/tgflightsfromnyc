# SERPRadio Production Spec (Lovable + Railway)

Updated: 2025-10-05

- Backend services follow the Audible Intelligence Fabric™ Codex (sound-pack DSL, scene planner, mastering chain).
- This spec bridges Railway (FastAPI), Supabase, and the Lovable front-end.

## 1. High-Level Architecture

- **FastAPI (Railway)**
  - `/api/board/feed`: split-flap rows (price, dealScore, sparkline data)
  - `/api/book/summary`, `/api/book/lead_time_curve`: best-time metrics
  - `/api/vibe/generate_data`, `/vibenet/generate`: sonification endpoints
  - `/api/notifications/board`, `/api/notifications/route`: Data-Notification Engine (DNE)
- **Supabase**
  - Stores price observations, notification_events, vibenet_runs/items, featured mixes metadata
  - `sql/010_notification_engine.sql` adds events table + `board_badges_live` materialized view
- **Lovable (Vite React)**
  - Split-flap board, Best-Time rail, route detail pages, embed widget
- **Audio Engine**
  - Scene planner (`src/scene_planner.py`) → verse/pre/chorus schedule
  - `completed/transform_midi.py` adds chorus ostinato (square lead) only for chorus bars
  - Optional MP3 rendering controlled by `RENDER_MP3` (fluidsynth + ffmpeg)

## 2. Notifications & Events

- Migration: apply `sql/010_notification_engine.sql`
  - `notification_events` (append-only)
  - `board_badges_live` (last 24h view)
  - Optional `pg_cron` job emits drop/spike/window events every 6h
- API contracts
  - `GET /api/notifications/board?origins=JFK,EWR,LGA`
    - Returns `{ items: [{ id:"JFK-MIA", labels:["18% drop","window open"], severity:"alert", lastSeen:"…" }] }`
  - `GET /api/notifications/route?origin=JFK&dest=MIA&hours=168`
    - Returns `{ events: [{ event_type:"price_drop", delta_pct:-15, observed_at:"…" }, …] }`
- UI mapping
  - Split-flap rows show lime/cyan/magenta pills for drop/spike/window
  - Route pages render timeline (7-day window) with same event set

## 3. Sonification Flow

`POST /vibenet/generate`
```json
{
  "data": [0.1, 0.3, 0.5, 0.8],
  "controls": { "bars": 16, "tempo_hint": 112 },
  "meta": { "origin": "JFK", "destination": "MIA" }
}
```

1. Palette selection
   - Explicit `vibe_slug` wins
   - Else `meta.destination` → `src/ontology.py` → `config/destination_ontology.yaml`
   - Fallback `meta.origin` → ontology, final fallback `synthwave_midnight`
2. Scene schedule
   - `build_scene_schedule` examines momentum bands
   - Positive momentum triggers pre → chorus; otherwise verse only
3. MIDI creation
   - `create_sonified_midi(..., scene_schedule=...)`
   - `_add_chorus_ostinato` adds 16th-note square lead in chorus bars
4. Storage
   - MIDI/MP3 uploaded via `put_bytes`
   - Presigned URLs returned in `JobResult`

Latency target: <8s for 16 bars. MP3 rendering optional.

## 4. Palettes & Ontology

- `config/vibe_palettes.yaml` (excerpt)
  - `circle_of_life_travel`: anthemic pop intro
  - `hammer_to_fall_drop`: arena-drop energy
  - `new_wave_hunt`: up-tempo new wave
  - `hoosier_heartland`: heartland rock
  - `king_of_pop_loop`: late-80s pop groove
  - `pacific_breeze`: How Bizarre-inspired NZ vibe
  - `philly_fight`: brass fight-song energy
- `config/destination_ontology.yaml`
  - Maps airport/city → `{ tags, default_palette }`
  - No demographic attributes used
- `config/vibe_rules.yaml`
  - Keyword map ensures palette selection when text includes city, team, or cultural cues

## 5. Front-End Integration Checklist

### Home (`/`)
- Split-flap board (tabs for JFK/EWR/LGA) using `useBoardData`
- Best-Time snapshot rail (5–8 routes) from `/api/book/summary`
- Featured Mixes rail (static MP3 list served via CDN)
- “How it works” strip + CTA

### Route (`/routes/[origin]/[dest]`)
- Hero stats: price, Δ%, recommendation badge
- `<BestTimeSummary>` with sweet-spot, BWI, confidence
- `<LeadTimeCurve>` (q25/q50/q75) with tooltips
- “Play the trend” button calling `generateAutoVibe` with q50 slice
- Timeline badges via `useRouteBadges`
- JSON-LD inserted using `generateRouteJsonLd`

### Deals (`/deals`)
- Filters (origin, nonstop) and tabs (Top / Trending / Seasonal / Weekend)
- Deal cards display badge pills, delta, play CTA

### Embed (`/embed`)
- Query params: `origins`, `limit`, `theme`
- Provides `postMessage` API (play/stop/next) for parent site control

## 6. Deployment & Ops

- Railway env vars:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE` (or `_KEY`)
  - `STORAGE_BUCKET`, `PUBLIC_STORAGE_BUCKET`
  - `CORS_ORIGINS`, `ADMIN_SECRET`
  - `RENDER_MP3` (0/1), `DESTINATION_ONTOLOGY_PATH` (optional override)
- Smoke tests:
  ```bash
  curl -s $BASE/health
  curl -s "$BASE/api/board/feed?origins=JFK,EWR,LGA&limit=10"
  curl -s "$BASE/api/notifications/board?origins=JFK,EWR,LGA"
  curl -s "$BASE/api/book/summary?origin=JFK&dest=MIA&month=3"
  curl -s -X POST "$BASE/vibenet/generate" -H 'content-type: application/json' \
       -d '{"data":[0.2,0.4,0.6],"meta":{"origin":"JFK","destination":"NZAA"}}'
  ```
- CDN (e.g., Supabase public bucket or Cloudflare R2) should host Featured Mixes MP3s.

## 7. Acceptance Criteria (MVP)

- Home renders 10+ live rows with badges; play starts in <5s
- Route detail pages respond with summary + curve + audio + badges
- Featured mixes playable instantly (no backend latency)
- Lighthouse ≥90 mobile, a11y ≥95
- No blocking 5xx responses from API

## 8. References

- `COMPLETE_ROADMAP.md`
- `API_INTEGRATION_GUIDE.md`
- `AUDIO_INTEGRATION.md`
- Audible Intelligence Fabric™ Codex (source of truth for audio DSL)

