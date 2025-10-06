# 🎵 SERP Radio - The Market Movement Sonification Engine

**Hear the market move.** SERP Radio transforms live search reality into emotive, nostalgic music through an OpenAI-powered pipeline that creates **instant audio** for frontend consumption.

![SERP Radio Pipeline](https://img.shields.io/badge/Pipeline-OpenAI→Momentum→Audio-brightgreen)
![Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![Sound Packs](https://img.shields.io/badge/Sound%20Packs-Arena%20Rock%20|%208--Bit%20|%20Synthwave-blue)

## 🚀 Quick Start

This repo ships a full, production-ready stack:

- Backend: FastAPI (Railway), Supabase DB/Storage, xAI Grok integration
- Frontends: Vite React (Vercel) split‑flap board + optional Next.js dashboard
- Pipelines: Daily LLM + price parsing + VibeNet sonification (batch/preset and on‑the‑fly)

For an end‑to‑end MVP (board + data) using what’s already in this repo:

1) Supabase
- Apply schema: `supabase db remote commit --file sql/000_init_schema.sql`
  (or run each referenced SQL file manually in the Dashboard)
- Seed: `scripts/upsert_travel_routes_from_json.py`, `scripts/upsert_price_quotes_from_json.py`

2) Backend on Railway
- Deploy this repo (Dockerfile or Procfile)
- Env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`, `CORS_ORIGINS`, optional `XAI_API_KEY`
- Verify: `/api/healthz`, `/api/travel/routes_nyc`, `/api/travel/price_quotes_latest`, `/api/board/feed`, `/api/vibenet/runs`

3) Vite app on Vercel (`vite-react-user`)
- Set rewrites `vercel.json` to your backend host (Railway)
- Optional env: `XAI_API_KEY` (for `/api/chat`), `VITE_API_BASE`
- Deploy and open preview → split‑flap board live

See docs/AGENTIC_B2C_APP.md for the aligned “agentic B2C demand generation + sonification” architecture (Lovable.dev shell + Vercel/Vite UI + Railway + Supabase) and programmatic SEO plan.

### Environment Setup

**Option 1: Supabase Storage (Recommended)**
```bash
# Required environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_ANON_KEY=your-anon-key-here
export STORAGE_BUCKET=serpradio-artifacts
export PUBLIC_STORAGE_BUCKET=serpradio-public
export OPENAI_API_KEY=your_openai_key
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini_here
export ADMIN_SECRET=sr_admin_2025_secure_secret
```

**Option 2: AWS S3 (Alternative)**
```bash
export AWS_REGION=us-east-1
export S3_BUCKET=serpradio-artifacts-2025
export S3_PUBLIC_BUCKET=serpradio-public-2025
export KMS_KEY_ID=alias/serpradio-kms-2025
export OPENAI_API_KEY=your_openai_key
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini_here
export ADMIN_SECRET=sr_admin_2025_9hAqV3XbL2
```

### Local Development
```bash
# Python 3.11+
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Docker (Recommended)
```bash
docker build -t serpradio:2025 .
docker run --rm -it --env-file ./.env -p 8000:8000 serpradio:2025
```

### Health Check
```bash
curl -s http://localhost:8000/api/healthz
```

## 🎵 Core Features

### 🎯 Sonification Engine
- **Multi-format Output**: MIDI + MP3 with presigned URL delivery
- **Sound Pack System**: Arena Rock, 8-Bit, Synthwave with nostalgic mapping
- **Momentum-Driven**: Live momentum bands drive musical arrangement
- **Wow-Factor Features**: Earcons, arrangement, and audio mastering

## 🔁 How Data Becomes Vibes

- **Metrics → Controls**: CTR maps to `tempo`, impressions to `velocity`, rank (position) to `transpose`, clicks to `filter` (CC74), combined engagement to `reverb`. See `completed/map_to_controls.py`.
- **Labels → Motifs**: Either trained label selection (`completed/motif_selector.py`) or controls-based motif picking to build a musical palette.
- **Momentum → Sections**: Momentum bands drive keys and tempo per section. Positive → C Major, Negative → A Minor, Neutral → C Lydian. See `src/arranger.py`.
- **Earcons → Events**: SERP features (e.g., top-1, AI overview, volatility spikes) trigger short musical cues per sound pack. See `src/earcons.py`.
- **Render → Artifacts**: MIDI is always generated; MP3 rendering is optional via Fluidsynth + FFmpeg (`RENDER_MP3=1`). URLs are returned as presigned (S3) or signed (Supabase).

## 🧩 Defaults, Fallbacks, and Safety

- **Momentum Optional**: If no input MIDI is available or analysis fails, momentum is skipped and the engine proceeds with controls + motifs (no job failure).
- **Output Keys**: When not provided, the engine auto-creates safe per-job output keys under `tenant/midi_output/{uuid}`.
- **Storage Abstraction**: All reads/writes use a unified interface supporting S3 and Supabase. Job status now reads momentum JSON via this layer for both backends.
- **MP3 Rendering**: Disabled by default. Enable with `RENDER_MP3=1` and install `fluidsynth` + `ffmpeg`. A GM soundfont is auto-discovered (see `src/renderer.py`).
- **OpenAI Dependency**: Only required for the Travel pipeline (LLM analysis). Core `/api/sonify` demo works without OpenAI.

## 🧪 Quick Demo (Data → Vibes)

```bash
# Start API
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Minimal demo: provides metrics and returns job_id
curl -s -X POST http://localhost:8000/api/sonify \
  -H 'Content-Type: application/json' \
  -d '{
        "tenant":"demo_tenant",
        "source":"demo",
        "sound_pack":"Synthwave",
        "override_metrics":{"ctr":0.75, "impressions":0.6, "position":0.8, "clicks":0.5}
      }'

# Check job status (signed URLs when ready)
curl -s http://localhost:8000/api/jobs/{job_id}
```

### 🚀 Travel Pipeline (NEW)
- **OpenAI Integration**: Structured flight price analysis with GPT-4o-mini
- **Emotive Mapping**: Budget carriers → 8-Bit, Vegas → Synthwave, Legacy → Arena Rock
- **Daily Automation**: Generates 24+ audio tracks focused on NYC→LAS routes
- **Public Catalog**: Frontend-ready JSON with instant-play URLs

### 🔄 Real-time Processing
- **Background Jobs**: FastAPI BackgroundTasks with job persistence
- **S3 Integration**: Tenant-isolated storage with CDN delivery
- **Live Catalog**: Public S3 bucket serves frontend-consumable JSON

## 🛠️ Pipeline Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenAI GPT    │───▶│  Momentum Bands  │───▶│  Audio Engine   │
│  Flight Analysis│    │ Price→Sentiment  │    │ MIDI/MP3 Output │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ YAML Prompts    │    │ Nostalgia Pack   │    │   Public S3     │
│ Travel Library  │    │    Selection     │    │   Catalog       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📡 API Endpoints

### Core Sonification
- `POST /api/sonify` - Create sonification job
- `GET /api/jobs/{id}` - Get job status with presigned URLs
- `POST /api/demo` - Enhanced demo with wow-factor features
- `POST /api/preview` - Fast synchronous preview

### Pipeline Management
- `POST /api/pipeline/run` - Trigger travel pipeline (admin only)
- `GET /api/cache/catalog` - Get latest travel catalog
- `POST /api/adhoc/run` - Single prompt → LLM → sonification (admin optional)
- `GET /api/vibenet/runs` - List recent batch/ad-hoc runs (Supabase-backed)
- `GET /api/vibenet/items` - Inspect catalog entries for a run

### Data Management
- `POST /api/upload-csv` - Upload and analyze CSV datasets
- `GET /api/rules?tenant=acme` - Get sonification rules
- `PUT /api/rules` - Update tenant rules

### Hero Audio
- `GET /api/hero-status` - Check hero audio availability
- `POST /api/render-hero` - Render hero audio (admin only)

### Vibe Engine (NEW)
- `POST /api/vibe/screenshot` - Ingest Spotify Now Playing screenshot; OCR via OpenAI Vision, map to palette
- `POST /api/vibe/motif` - Upload a captured MIDI motif from the browser (events → MIDI)
- `POST /api/vibe/generate` - Generate a track from palette + optional momentum bands
- `GET /api/vibe/palettes` - List available vibe palettes (Supabase or config fallback)

### Screenshot‑Only Mode
- Disable Spotify: set `VIBE_USE_SPOTIFY=0` (leave Spotify creds blank).
- Call `/api/vibe/screenshot` with either a PNG `file` or `artist`+`title` form fields.
- Backend infers features via LLM + rules and normalizes to:
  `{"tempo_bpm":112, "valence_0_1":0.7, "energy_0_1":0.6, "mode":"major", "key_center":"C"}`.
- Test:
  `curl -s -X POST http://localhost:8000/api/vibe/screenshot -F artist="The Beach Boys" -F title="Kokomo"`

### System
- `GET /api/healthz` - Modern health check
- `GET /api/metrics` - System metrics and monitoring
- `/docs` - Interactive API documentation

## 🎵 Sound Pack System

### **Arena Rock** 🎸
- **Use Case**: Legacy carriers, major brands, flagship routes
- **Vibe**: Big, confident, established
- **Triggers**: Delta, American, United, Expedia-scale

### **8-Bit** 🎮
- **Use Case**: Budget carriers, frugal travel, playful discovery
- **Vibe**: Playful, retro, cost-conscious
- **Triggers**: Spirit, Frontier, Allegiant, budget keywords

### **Synthwave** 🌃
- **Use Case**: Vegas routes, nightlife, neon destinations
- **Vibe**: Neon shimmer, 80s nostalgia, excitement
- **Triggers**: Las Vegas, casino, resort, nightlife

## 🚀 Travel Pipeline Usage

### Run Pipeline Locally
```bash
# Run travel pipeline with 24 route combinations
bash scripts/run_travel_pipeline_local.sh
```

### Run via API
```bash
# Trigger pipeline remotely
curl -X POST https://your-api.com/api/pipeline/run \
  -H "X-Admin-Secret: sr_admin_2025_9hAqV3XbL2"
```

### Check Results
```bash
# View generated catalog
curl -s https://your-api.com/api/cache/catalog | jq '.total'

# Check S3 artifacts
aws s3 ls s3://serpradio-artifacts-2025 --recursive | head
aws s3 ls s3://serpradio-public-2025/catalog/travel/
```

## 🎯 Example Outputs

### Sonification Request
```python
{
  "tenant": "pipeline_travel",
  "source": "demo", 
  "sound_pack": "Synthwave",
  "total_bars": 32,
  "tempo_base": 120,
  "override_metrics": {
    "momentum_data": [
      {"t0": 0.0, "t1": 3.2, "label": "positive", "score": 0.8},
      {"t0": 3.2, "t1": 6.4, "label": "neutral", "score": 0.1},
      {"t0": 6.4, "t1": 9.6, "label": "negative", "score": -0.6}
    ]
  }
}
```

### Catalog Entry
```json
{
  "id": "uuid-here",
  "timestamp": "2025-08-16T12:00:00Z",
  "channel": "travel",
  "brand": "Spirit",
  "title": "JFK->LAS",
  "prompt": "Find cheapest Spirit flight JFK to Las Vegas next 45 days",
  "sound_pack": "8-Bit",
  "duration_sec": 28.8,
  "mp3_url": "https://s3.../presigned-url",
  "midi_url": "https://s3.../presigned-url",
  "momentum_json": [...],
  "label_summary": {"positive": 3, "neutral": 4, "negative": 3}
}
```

## 🔧 Configuration

### Environment Variables

**Supabase Storage (Recommended):**
```bash
# Mandatory
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public
ADMIN_SECRET=sr_admin_2025_secure_secret
OPENAI_API_KEY=your_openai_key
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini

# xAI Grok (preferred provider)
XAI_API_KEY=your_xai_key
XAI_MODEL=grok-beta

# Intake authentication (optional shared secret for /api/intake/*)
INTAKE_TOKEN=your_intake_token

# Runtime Knobs
APP_VERSION=1.0.0
OPENAPI_PUBLIC=0
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2
PRESIGNED_URL_TTL=600
TTL_DAYS=7
RL_IP_PER_MIN=60
RL_TENANT_PER_MIN=120
# Board feed dataset (optional override)
BOARD_DATASET_PATH=data/grok_tips_inspiration_dataset.json
```

**AWS S3 (Alternative):**
```bash
# Mandatory
AWS_REGION=us-east-1
S3_BUCKET=serpradio-artifacts-2025
S3_PUBLIC_BUCKET=serpradio-public-2025
KMS_KEY_ID=alias/serpradio-kms-2025
ADMIN_SECRET=sr_admin_2025_9hAqV3XbL2
OPENAI_API_KEY=your_openai_key
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini

# Optional CDN
PUBLIC_CDN_DOMAIN=your-cloudfront-domain.net
```

### Vibe Engine LLM Providers (xAI vs Groq vs OpenAI)
```bash
# Preferred for daily pipelines: xAI Grok
GROK_API_KEY=your_xai_key         # or XAI_API_KEY
GROK_MODEL=grok-beta

# OCR + Vision helpers: Groq or OpenAI SDKs (used in screenshot ingestion)
GROQ_API_KEY=your_groq_key        # Groq SDK
GROQ_TEXT_MODEL=llama-3.1-8b-instant
GROQ_VISION_MODEL=llama-3.2-11b-vision-preview
OPENAI_API_KEY=your_openai_key    # OpenAI SDK
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini

# Optional: Spotify audio features (set only if using Spotify)
VIBE_USE_SPOTIFY=0
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=


# Optional: direct Postgres connection (CLI/psql)
# Replace [YOUR-PASSWORD] with your DB password in Supabase
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.zkqgcksxvmhbryplppxy.supabase.co:5432/postgres

# Or pooled (PgBouncer): username includes project ref
SUPABASE_DB_URL_POOLED=postgresql://postgres.zkqgcksxvmhbryplppxy:[YOUR-PASSWORD]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
# Palettes and rules (paths are configurable)
VIBE_PALETTES_PATH=config/vibe_palettes.yaml
VIBE_RULES_PATH=config/vibe_rules.yaml
```

### Seed Palettes (optional)
```bash
python tools/seed_palettes.py  # reads config/vibe_palettes.yaml and inserts into Supabase
```

### YAML Prompt Library
```yaml
# src/pipeline/prompt_library/travel.yaml
channel: travel
focus: "NYC area to Las Vegas (LAS) and top domestic budget routes"
origins: [JFK, LGA, EWR, HPN, ISP, SWF]
destinations:
  - code: LAS
    name: Las Vegas
  - code: MIA  
    name: Miami
templates:
  - "Find absolute cheapest one-way flight from {origin} to {dest} next 45 days"
  - "Red-eye or early morning cheapest fares {origin} -> {dest}"
novelty_special:
  - "What's the cleverest sub-$75 routing from any NYC airport to Las Vegas?"
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# Basic health
curl -s http://localhost:8000/api/healthz

# Detailed metrics  
curl -s http://localhost:8000/api/metrics | jq
```

### Structured Logging
```json
{
  "timestamp": "2025-08-16T12:00:00Z",
  "level": "INFO", 
  "message": "Pipeline job completed: 24 tracks rendered"
}
```

### S3 Monitoring
- **Private Bucket**: MIDI/MP3 artifacts with presigned access
- **Public Bucket**: Catalogs with CDN caching
- **Lifecycle Policies**: Auto-cleanup after TTL_DAYS

## 🚀 Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Docker)
```bash
# Build image
docker build -t serpradio:latest .

# Run with environment
docker run -d --name serpradio \
  --env-file .env \
  -p 8000:8000 \
  serpradio:latest
```

### Daily Automation Options

**A) Render Cron Job**
```bash
curl -X POST "https://your-api.com/api/pipeline/run" \
  -H "X-Admin-Secret: sr_admin_2025_9hAqV3XbL2"
```

**B) GitHub Actions**
```yaml
name: Travel Pipeline
on:
  schedule: [{ cron: "0 8 * * *" }]  # Daily 08:00 UTC
jobs:
  run:
    steps:
      - name: Trigger pipeline
        run: |
          curl -X POST "https://your-api.com/api/pipeline/run" \
            -H "X-Admin-Secret: sr_admin_2025_9hAqV3XbL2"

## 🧠 xAI (Grok) Daily LLM Pipeline

### Configure
```bash
export GROK_API_KEY=your_xai_key             # or XAI_API_KEY
export GROK_MODEL=grok-beta
export LLM_CACHE_DIR=serpradio_convo_cache   # default
export LLM_CACHE_TTL_HOURS=24                # optional (0 = no TTL)
```

### Run via CLI
```bash
python scripts/run_xai_daily.py --limit 50 --model grok-beta
```

### Run via API (Admin)
```bash
curl -s -X POST "$BASE/api/llm/run?limit=50&model=grok-beta" -H "X-Admin-Secret: $ADMIN_SECRET"
```

### Prompts Source
- Supabase `api_results` with `status=accepted` (from `/api/intake/prompt(s)`)
- Fallback: `config/daily_prompts.json` (array of strings)

### Persistence & Cache
- Results persisted to Supabase `llm_results` (best‑effort) with `{provider, model, prompt, response_raw, latency_ms, status}`
- File cache at `LLM_CACHE_DIR` to avoid refiring the same prompt; optional TTL via `LLM_CACHE_TTL_HOURS`

## ✈️ Top Routes (NYC Origins → Popular Destinations)

Generate and cache the top routes by volume/popularity for JFK/LGA/EWR, then query them via API or Supabase.

### Prepare Destinations CSV
Create `destinations_by_popularity.csv` with headers:
```
dest,name,score
LAX,Los Angeles,100000
MIA,Miami,95000
LAS,Las Vegas,92000
... up to ~1700 rows ...
```
The `score` can be pax volume, search volume, or a composite popularity signal.

### Publish to Supabase
```bash
python scripts/publish_top_routes.py --input destinations_by_popularity.csv --limit 5000 --source pax_volume
```
This writes `origin ∈ {JFK,LGA,EWR}` × `destination` rows to table `travel_routes_nyc`.

### Consume in Front‑End
```bash
curl -s "$BASE/api/travel/routes_nyc?origin=JFK&limit=5000" | jq '.total'
```

### Optional xAI Summaries
For each top route, queue prompts via `/api/intake/prompt` (e.g., “Best time to book JFK→LAX next 60 days; include fees/holidays”), then run the daily xAI pipeline to persist raw responses in `llm_results`.

## 🧳 OpenAI Pipeline – Best Time to Book (NYC Canonical Routes)

Use OpenAI for a massive, low‑cost pass over canonical NYC routes (JFK/LGA/EWR → many destinations).

### Prepare Routes
- From Supabase: ensure `travel_routes_nyc` is populated (see earlier section).
- Or from a local cache: build with `scripts/build_routes_cache.py`.

### Run Batch (OpenAI)
```bash
# From Supabase (requires OPENAI_API_KEY, SUPABASE_*):
python scripts/run_openai_routes_booking.py --limit 300 --origin JFK --window 60

# From local cache:
python scripts/run_openai_routes_booking.py --input data/routes_nyc_cache.json --limit 300 --window 60
```
- Caching: results saved in `LLM_CACHE_DIR` and stored to Supabase `llm_results` (best‑effort).
- Model: defaults to `OPENAI_TEXT_MODEL` (e.g., gpt‑4o‑mini). Override via `--model`.

### Env
```bash
OPENAI_API_KEY=sk-...
OPENAI_TEXT_MODEL=gpt-4o-mini
LLM_CACHE_DIR=serpradio_convo_cache
LLM_CACHE_TTL_HOURS=24
OPENAI_BATCH_SLEEP_SEC=0.1
```

### Downstream
- Read `llm_results` to annotate split‑flap slices or feed VibeNet enrichment later.
- Mix with xAI daily runs (with web search) for periodic ground‑truth + citations.
```

## 🎵 Frontend Integration

### Public Catalog Access
```javascript
// Fetch latest travel catalog
const catalog = await fetch('https://your-api.com/api/cache/catalog')
  .then(r => r.json());

// Display tracks with instant play
catalog.items.forEach(track => {
  console.log(`${track.title}: ${track.sound_pack} (${track.duration_sec}s)`);
  
  // Play MP3 directly from presigned URL
  const audio = new Audio(track.mp3_url);
  audio.play();
});
```

### Real-time Sonification
```javascript
// Create custom sonification
const job = await fetch('/api/sonify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    tenant: 'my-company',
    sound_pack: 'Synthwave',
    total_bars: 32,
    override_metrics: { ctr: 0.85, volatility: 0.7 }
  })
}).then(r => r.json());

// Poll for completion
const result = await fetch(`/api/jobs/${job.job_id}`).then(r => r.json());
```

## 💛 Lovable.dev Build & Sub-Agent Guide (Split‑Flap + VibeNet)

This section documents how the Lovable.dev front‑end integrates the split‑flap visualization and VibeNet endpoints, including handshakes, payloads, optional scoring context, and pipeline triggers.

### Build Setup (Lovable)
- API base: set `VITE_API_BASE` to your backend (e.g., `http://localhost:8000`).
- Audio stack: Tone.js or WaveSurfer for playback; resume AudioContext on first user gesture.
- Polling: board feed refresh every 30–60s; debounce visibility changes.

### Handshake & Health
```ts
// On app boot
await fetch(`${VITE_API_BASE}/api/healthz`).then(r => r.json());
// Fetch initial board feed (keywords target)
const feed = await fetch(`${VITE_API_BASE}/api/board/feed?target=keywords&limit=12&lookback_days=30`).then(r => r.json());
```

### Split‑Flap Board (Engine Inputs vs Design Inputs)
- Engine inputs (fetched): `id, title, data_window, vibe{valence,arousal,tension}, tempo_bpm, momentum{positive,neutral,negative}, palette, last_updated, spark[]` from `GET /api/board/feed`.
- Design inputs (UI): columns, flap timing (55–75ms), row stagger (20–40ms), reduced‑motion fallback, a11y labels.

### Play a Slice (Sonification + Vibe)
Use the combined endpoint to get both audio artifacts and vibe sliders in one call.
```ts
const body = {
  data: sparkRawValues,           // e.g., last 30 days numeric series for the row
  palette_slug: 'synthwave_midnight',
  total_bars: 16,
  // Optional context: curated scores for analytics & future mapping
  context: {
    deal_score: 0.82,
    novelty_score: 0.35,
    brand_pref_score: 0.6,
    region_pref_score: 0.7
  }
};
const res = await fetch(`${VITE_API_BASE}/api/vibe/generate_data`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body)
}).then(r => r.json());

// res.job.mp3_url → play; res.vibe → render sliders (valence/arousal/tension/...)
```

Notes:
- The backend logs an analytics row (`vibe_board_events`) with `job_id`, `palette_slug`, `context`, `momentum` counts, and `tempo_bpm` (Supabase optional).
- Keep only one active player; add a small crossfade between slices for continuity.

### Intake & LLM (Optional)
To queue Grok/Groq/OpenAI analysis or summaries from the client, use intake endpoints (guarded by `INTAKE_TOKEN`).
```bash
curl -s -X POST "$BASE/api/intake/prompt" \
  -H 'Content-Type: application/json' \
  -H "X-Client-Token: $INTAKE_TOKEN" \
  -d '{
        "source":"lovable.board",
        "prompt":"Analyze latest travel slice trends and propose board annotations.",
        "metadata": {"vertical":"travel","lookback_days":30},
        "config": {"provider":"grok","model":"grok-beta"}
      }'
```

### Pipeline Initiation (Core vs Ad‑Hoc)
- Core runs (Lovable admin) → launch with `X-Admin-Secret`:
```bash
curl -s -X POST "$BASE/api/pipeline/run" -H "X-Admin-Secret: $ADMIN_SECRET"
curl -s -X POST "$BASE/api/vibenet/run?vertical=travel&theme=flights_from_nyc&limit=24" -H "X-Admin-Secret: $ADMIN_SECRET"
```
- Ad‑hoc runs (scripts/ops) → `scripts/run_ski_pipeline.py` or `src/pipeline/run_pipeline` may be invoked from CI or local.

### Supabase Data Logging
- Board events: automatically inserted by `/api/vibe/generate_data` (if Supabase configured) into `vibe_board_events`.
- Intake prompts: `api_results` table via `/api/intake/prompt(s)`.
- Catalogs/runs: `vibenet_runs` / `vibenet_items` via batch pipelines.

### Security & Auth (Frontend)
- Intake: set and send `X-Client-Token` only to `/api/intake/*` routes.
- Admin: never embed `ADMIN_SECRET` in public clients; use Lovable admin panel/server to proxy admin calls.
- Storage: MP3/MIDI URLs are short‑lived; don’t persist beyond session without re‑signing.

### Event Flow (Sub‑Agent Checklist)
- Handshake: GET `/api/healthz` (retry with backoff on fail).
- Fetch feed: GET `/api/board/feed` (30–60s cadence; pause when tab hidden).
- Play slice: POST `/api/vibe/generate_data` with optional `context` scores; play `job.mp3_url` and render `vibe`.
- Share: read share token or generate via existing share endpoints (if enabled).
- Telemetry: emit client analytics to your own endpoint or `/api/intake/prompt` (summaries only, with `INTAKE_TOKEN`).

### React Types (SplitFlapBoard)
```ts
export type VibeChip = { valence: number; arousal: number; tension: number };
export type MomentumCounts = { positive: number; neutral: number; negative: number };

export type BoardFeedRow = {
  id: string;
  title: string;
  data_window?: string;
  vibe: VibeChip;
  tempo_bpm: number;
  momentum: MomentumCounts;
  palette: string;
  last_updated?: string;
  spark: number[];         // normalized 0..1 values for flap + sparkline
};

export type SplitFlapBoardProps = {
  items: BoardFeedRow[];
  onPlay?: (row: BoardFeedRow) => void;
  onAddToStream?: (row: BoardFeedRow) => void;
  flapDurationMs?: number;    // per-flap frame duration (55–75ms)
  rowStaggerMs?: number;      // stagger between row flips (20–40ms)
  reducedMotion?: boolean;    // prefers-fReducedMotion fallback
  className?: string;
};

// Example usage
function SplitFlapBoard({ items, onPlay, onAddToStream, flapDurationMs = 65, rowStaggerMs = 30 }: SplitFlapBoardProps) {
  // render rows, map vibe→color, animate flaps via CSS transforms
  return null;
}
```

## 🔌 Webz.io Integration (Firehose → Board + VibeNet)

Integrate live Webz.io Firehose streams as a data source for the split‑flap board and VibeNet.

### Repo & Consumer
- Reference repo: GitHub Webhose/webzio-firehose-api-consumer (use as implementation reference).
- This project ships a minimal consumer: `scripts/run_webzio_consumer.py` using `src/webzio_integration.py`.

### Environment
```bash
WEBZIO_API_TOKEN=your_webzio_token
WEBZIO_FIREHOSE_URL=https://webz.io/fhose            # default
WEBZIO_FILTER="site_type:news language:english"     # optional query
WEBZIO_OUTPUT_DATASET_PATH=data/webzio_board_dataset.json
BOARD_DATASET_PATH=data/grok_tips_inspiration_dataset.json  # default board dataset
BOARD_FEED_TTL_SEC=45
VIBE_CONTEXT_NUDGE=1  # enable context→vibe adjustments in generate_data
```

### Run Consumer
```bash
python scripts/run_webzio_consumer.py
```
- Streams events, writes `webzio_events` (Supabase if configured), and updates `WEBZIO_OUTPUT_DATASET_PATH` every ~10 events.
- The board can point at this dataset: `GET /api/board/feed?dataset=data/webzio_board_dataset.json`.

### Mapping to Scores & Vibes
- The consumer computes placeholder `novelty_score`, `brand_pref_score`, `region_pref_score`, `deal_score`; extend with domain logic.
- When playing a slice from the board, pass `context` to `/api/vibe/generate_data` for analytics:
```json
{
  "data": [ ... ],
  "palette_slug": "synthwave_midnight",
  "context": {
    "novelty_score": 0.6,
    "brand_pref_score": 0.7,
    "region_pref_score": 0.5,
    "deal_score": 0.8
  }
}
```

### Operational Model
- Core pipelines: launched via `/api/pipeline/run` or `/api/vibenet/run` (Lovable admin/server only).
- Ad‑hoc runs: invoke consumer scripts anywhere; push to Supabase; board reads from dataset path.
- Supabase tables suggested: `webzio_events`, `vibe_board_events`, `api_results`, `vibenet_runs`, `vibenet_items`.

### Notes
- Do not embed tokens in public clients. Run consumers server-side or via CI/cron.
- The board feed caches responses; change `BOARD_FEED_TTL_SEC` for poll cadence.

## 🚀 Vercel Concepts (AI SDK) — Split‑Flap + Radio + Composer

- A ready-to-deploy Next.js app lives under `vercel-app/` and uses the Vercel AI SDK and Edge runtime to host:
  - Split‑Flap board (`/embed`) with KV caching proxying `/api/board/feed`
  - Radio Tuner (`/radio`) browsing canonical NYC routes and price quotes
  - Deal Composer chat (`/composer`) with tool-calling for routes, quotes, and board feed
- See `vercel-app/README_VERCEL.md` for env setup and deploy. Ensure your FastAPI `CORS_ORIGINS` includes your Vercel domain.


## 🏗️ Project Structure

```
/
├── src/
│   ├── main.py              # FastAPI application
│   ├── pipeline/            # NEW: OpenAI→Audio pipeline
│   │   ├── schemas.py       # Pydantic models
│   │   ├── openai_client.py # GPT-4o-mini wrapper
│   │   ├── travel_pipeline.py # Route analysis logic
│   │   ├── sonify_batch.py  # Batch rendering
│   │   ├── nostalgia.py     # Brand→SoundPack mapping
│   │   └── prompt_library/  # YAML prompt templates
│   ├── sonify_service.py    # Core sonification engine
│   ├── arranger.py          # Musical arrangement
│   ├── earcons.py           # Audio effects
│   ├── storage.py           # S3 operations
│   └── soundpacks.py        # Sound pack definitions
├── scripts/
│   └── run_travel_pipeline_local.sh
├── tests/                   # Comprehensive test suite
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container definition
└── README.md               # This file
```

## 🎯 Use Cases

### **Travel Discovery** ✈️
- Daily NYC→LAS bargain hunting with audio feedback
- Budget carrier analysis with 8-Bit playfulness
- Vegas route discovery with Synthwave excitement

### **Market Intelligence** 📊
- SERP position changes sonified as musical momentum
- CTR volatility translated to rhythm and earcons
- Brand performance mapped to nostalgic sound packs

### **Demo & Presentation** 🎪
- Instant audio generation for live demos
- Hero audio for marketing and product showcases
- Real-time sonification for interactive experiences

## 📞 Support & Contributing

### Documentation
- **API Docs**: `/docs` (Swagger UI)
- **Health Status**: `/api/healthz`
- **Metrics**: `/api/metrics`

### Issues & Enhancement
- Report bugs via GitHub Issues
- Feature requests welcome
- Contribution guidelines in CONTRIBUTING.md

---

**🎉 SERP Radio: Where search data becomes music, and market movement gets a soundtrack.**

*Built with FastAPI, OpenAI GPT-4o-mini, AWS S3, and a passion for turning data into audio experiences.*
### Provider Differences
- xAI (Grok): endpoint `https://api.x.ai/v1/chat/completions` with `GROK_API_KEY` or `XAI_API_KEY`. Used by our cached daily LLM pipeline (`src/llm_xai.py`, `/api/llm/run`).
- Groq: high‑performance LLM via Groq SDK (`groq` package), configured with `GROQ_API_KEY`. Used by screenshot OCR/vision helpers.
- OpenAI: fallback provider for OCR/vision (`OPENAI_API_KEY`).

Tip: Don’t confuse `GROK_API_KEY` (xAI) with `GROQ_API_KEY` (Groq). Both can be set; they serve different roles in this codebase.
