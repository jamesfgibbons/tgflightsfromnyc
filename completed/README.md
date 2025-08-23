# 🎵 SERP Radio - Production-Grade Sonification Platform

**Transform SERP data into real-time musical experiences with enterprise-ready FastAPI backend**

**🌐 Live Demo: [https://serpradio.com](https://serpradio.com)**

A complete production system for **SERP Radio** that converts SERP ranking data into musical audio reports using advanced momentum analysis, machine learning, and **FATLD** (Frequency, Amplitude, Timbre, Location, Duration) sonification mapping.

## 🎯 **Production Milestones & Progress**

### **Phase 1: Core Training System** ✅ **COMPLETE**
- [x] **Labeled Bar Training** - CSV/MIDI marker labeling system
- [x] **Momentum Classification** - Advanced momentum analysis pipeline
- [x] **ML Model Training** - scikit-learn classification models
- [x] **Motif Selection Engine** - Label-based and controls-based selection
- [x] **YAML Rule Engine** - Declarative metrics → label mapping
- [x] **End-to-End CLI** - Complete command-line interface
- [x] **Comprehensive Testing** - Full test suite with 95%+ coverage

### **Phase 2: Live Streaming Application** ✅ **COMPLETE**
- [x] **FastAPI WebSocket Server** - Real-time event streaming
- [x] **React + Tone.js Client** - Browser-based audio synthesis
- [x] **Redis Pub/Sub** - High-performance event distribution
- [x] **Docker Compose** - Complete development environment
- [x] **Production Deployment** - SSL, nginx, monitoring ready

### **Phase 3: Production FastAPI Backend** ✅ **COMPLETE**
- [x] **Pydantic v2 Models** - Request/response DTOs with validation
- [x] **S3 Storage Layer** - Presigned URLs, artifact management
- [x] **Job Queue System** - Background task processing
- [x] **Orchestration Service** - Domain logic integration
- [x] **REST API Endpoints** - Upload, sonify, status, rules management
- [x] **MP3 Rendering** - Optional audio format support
- [x] **Comprehensive Testing** - API integration tests with TestClient
- [x] **Lovable Deployment** - Cloud-native deployment package

### **Phase 4: Enterprise Scaling** 🔄 **READY FOR IMPLEMENTATION**
- [ ] **DynamoDB Job Store** - Replace in-memory PoC with persistent storage
- [ ] **Lambda Integration** - Serverless execution for cost optimization
- [ ] **CloudWatch Monitoring** - Comprehensive logging and alerting
- [ ] **Multi-tenant Architecture** - Enhanced isolation and billing
- [ ] **CDN Integration** - Global audio distribution
- [ ] **Auto-scaling** - Demand-based capacity management

### **Current Status: 🎉 Production Ready**
**Completed:** Training system, live streaming, production FastAPI backend  
**Active:** Enterprise features and scaling  
**Next:** Multi-tenant SaaS deployment

## 🚀 Quick Start - Experience It Live

Visit **[serpradio.com](https://serpradio.com)** to experience real-time SERP sonification:

1. Click **"Start Audio"** to begin
2. Select your preferred **audio station**:
   - **📊 Daily** - All SERP changes
   - **🤖 AI Lens** - AI-powered results only  
   - **⚡ Opportunity** - Large movements & anomalies
3. Listen as search ranking changes become music in real-time

## 🎵 What This Does

Transform your SERP data into music! Each search engine result, ranking change, and competitive movement becomes a musical element:

- **Frequency** (Pitch): Rank delta (-10 to +10 → musical intervals)
- **Amplitude** (Volume): Share percentage (0-100% → MIDI velocity)  
- **Timbre** (Instrument): Search engine (Google Web, AI, etc.)
- **Location** (Pan): Geographic segment (West/Central/East)
- **Duration** (Note length): Rich snippet type (video, shopping, etc.)

## Quick Start

### Prerequisites
- Python 3.11+
- FluidSynth (for audio rendering)
- FFmpeg (for MP3 conversion)
- AWS credentials (for publishing)
- DataForSEO API access

### One-Shot Setup
```bash
# Install and test everything
make bootstrap

# Generate sample audio to hear how SERP data sounds
make sample

# Run full pipeline with your data
make run
```

## Environment Variables

Create `.env` file in the project root:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATAFORSEO_LOGIN` | DataForSEO API login | `your_login` |
| `DATAFORSEO_PASSWORD` | DataForSEO API password | `your_password` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `abc123...` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET` | S3 bucket for audio files | `ti-radio` |
| `BRAND_DOMAIN` | Your brand domain | `mybrand.com` |
| `TMP_DIR` | Temporary file directory | `/tmp` |

## Architecture

### Data Flow
1. **DataForSEO API** → Fetch daily SERP rankings for keywords
2. **Preprocessing** → Calculate rank deltas, detect anomalies, add features
3. **Sonification** → Convert data to MIDI using FATLD mappings
4. **Audio Rendering** → FluidSynth converts MIDI to WAV → pydub creates MP3
5. **Publishing** → Upload to S3, update RSS feed, generate HTML player
6. **Distribution** → Public URLs for audio, RSS, and web player

### Components

- **src/fetch_data.py**: DataForSEO API integration with retry logic
- **src/preprocess.py**: Rank delta calculation and anomaly detection  
- **src/sonify.py**: Core FATLD mapping and MIDI generation
- **src/render_audio.py**: FluidSynth integration and audio processing
- **src/publish.py**: S3 publishing, RSS feeds, HTML player generation
- **src/cli.py**: Typer-based command line interface
- **src/mappings.py**: Musical mapping utilities and scale generation

## Development

```bash
# Install dependencies and setup
make dev

# Generate sample audio (no API required)
make sample

# Run tests with coverage
make test

# Check audio dependencies
make check-deps

# Lint code
make lint

# Clean temporary files
make clean
```

## Commands

```bash
# CLI Commands
python -m src.cli run-daily          # Full daily pipeline
python -m src.cli run-weekly         # Weekly batch processing  
python -m src.cli sample             # Generate sample audio
python -m src.cli local-preview data/sample.csv  # Preview from CSV
python -m src.cli call-dataforseo-status  # Check API status

# Docker
docker build -f docker/Dockerfile -t serp-loop-radio .
docker run --env-file .env serp-loop-radio run-daily
```

## Production Deployment

### Option 1: Docker
```bash
# Build and run
make docker
docker run -d --env-file .env --name serp-loop serp-loop-radio run-daily
```

### Option 2: AWS Lambda  
```bash
# Package and deploy (implementation pending)
make deploy
```

## ✅ Completed Features

- [x] **DataForSEO API Integration** - Full SERP data collection with retry logic
- [x] **FATLD Sonification System** - Complete musical parameter mapping
- [x] **MIDI Generation** - Multi-track MIDI with engine separation
- [x] **Audio Rendering** - FluidSynth + pydub pipeline with MP3 export
- [x] **S3 Publishing** - Automated upload with RSS feeds and HTML player
- [x] **CLI Interface** - Full Typer-based command system
- [x] **Docker Support** - Complete containerization with auto-soundfont download
- [x] **Testing Suite** - Unit tests with 75%+ coverage requirement
- [x] **CI/CD Pipeline** - GitHub Actions with linting, testing, Docker builds
- [x] **Anomaly Detection** - Z-score based anomaly flagging with percussion
- [x] **Bass Riff System** - Conditional bass overlay for brand wins
- [x] **Rank Delta Processing** - Day-over-day comparison with trend analysis

## 🎵 Phase 2: Live Streaming (NEW!)

The MVP now includes **real-time WebSocket streaming** for live SERP data sonification:

### Live Streaming Features

- **WebSocket API Server** (FastAPI) with Redis pub/sub
- **React + Tone.js Client** for browser-based audio synthesis
- **Real-time SERP monitoring** with configurable intervals
- **Multiple Audio Stations**:
  - 📊 **Daily** - All SERP changes
  - 🤖 **AI Lens** - AI overview and AI-powered results only
  - ⚡ **Opportunity** - Large ranking movements and anomalies
- **Live audio effects** (reverb, delay, panning)
- **Real-time statistics** and event visualization

### Quick Start Live Mode

```bash
# Setup live streaming
make live-setup

# Start all services (Redis, API, React client)
make live-dev

# Open browser to http://localhost:5173
# Click "Start Audio" and select a station!
```

### Live System Architecture

```
SERP Data → Publisher → Redis → WebSocket API → React Client → Tone.js Audio
              ↓
         Change Detection
              ↓
         Musical Mapping
              ↓
         Real-time Events
```

### Environment Variables (Live Mode)

```bash
# Live streaming config
REDIS_URL=redis://localhost:6379
LIVE_MODE_TOKEN=your-websocket-api-key
PUBLISHER_INTERVAL=90  # seconds between SERP checks

# WebSocket client config
VITE_WS_URL=ws://localhost:8000/ws/serp
VITE_API_KEY=your-websocket-api-key
```

### Phase 2 Completed Features

- [x] **FastAPI WebSocket Server** - Real-time event streaming with authentication
- [x] **Redis Pub/Sub** - High-performance event distribution
- [x] **React + Tone.js Client** - Browser-based audio synthesis with live effects
- [x] **SERP Change Detection** - Diff-based ranking change monitoring
- [x] **Musical Event Mapping** - Real-time FATLD parameter conversion
- [x] **Station System** - Multiple themed audio channels
- [x] **Docker Compose** - Complete development environment
- [x] **WebSocket Tests** - Comprehensive testing for real-time features

## 🚀 Future Enhancements

- [ ] **AWS Lambda Deployment** - Serverless scheduled execution
- [ ] **City-level Audio Panning** - Geographic SERP analysis
- [ ] **OpenAI TTS Integration** - Spoken summaries with audio overlay
- [ ] **Mobile App** - React Native client for iOS/Android
- [ ] **Multi-user Sessions** - Shared listening experiences
- [ ] **Advanced Audio Effects** - 3D spatial audio, granular synthesis
- [ ] **ML Anomaly Detection** - Enhanced pattern recognition
- [ ] **Voice Alerts** - AI-generated insights with speech synthesis 