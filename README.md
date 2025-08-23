# 🎵 SERP Radio - The Market Movement Sonification Engine

**Hear the market move.** SERP Radio transforms live search reality into emotive, nostalgic music through an OpenAI-powered pipeline that creates **instant audio** for frontend consumption.

![SERP Radio Pipeline](https://img.shields.io/badge/Pipeline-OpenAI→Momentum→Audio-brightgreen)
![Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![Sound Packs](https://img.shields.io/badge/Sound%20Packs-Arena%20Rock%20|%208--Bit%20|%20Synthwave-blue)

## 🚀 Quick Start

### Environment Setup

**Option 1: Supabase Storage (Recommended)**
```bash
# Required environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_ANON_KEY=your-anon-key-here
export STORAGE_BUCKET=serpradio-artifacts
export PUBLIC_STORAGE_BUCKET=serpradio-public
export OPENAI_API_KEY=your_openai_key_here
export ADMIN_SECRET=sr_admin_2025_secure_secret
```

**Option 2: AWS S3 (Alternative)**
```bash
export AWS_REGION=us-east-1
export S3_BUCKET=serpradio-artifacts-2025
export S3_PUBLIC_BUCKET=serpradio-public-2025
export KMS_KEY_ID=alias/serpradio-kms-2025
export OPENAI_API_KEY=your_openai_key_here
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

# Runtime Knobs
APP_VERSION=1.0.0
OPENAPI_PUBLIC=0
RENDER_MP3=1
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2
PRESIGNED_URL_TTL=600
TTL_DAYS=7
RL_IP_PER_MIN=60
RL_TENANT_PER_MIN=120
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

# Optional CDN
PUBLIC_CDN_DOMAIN=your-cloudfront-domain.net
```

### Vibe Engine (OpenAI + Spotify)
```bash
# Required for screenshot OCR
OPENAI_API_KEY=your_openai_key

# Optional: Spotify audio features (set only if using Spotify)
VIBE_USE_SPOTIFY=0
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

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
