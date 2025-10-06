## VibeNet: Data → Vibes (Aligned with SERPRadio POC)

### 1) Overview
- Goal: Turn arbitrary data (time‑series/tabular) into coherent musical vibes that are informative and emotive.
- Strategy: Hybrid algorithmic composition (rules + music theory) with optional ML stylization, bound by a curated vibe space.
- Alignment: Extends SERPRadio’s engine and Vibe APIs (`src/vibe_api.py`, `src/sonify_service.py`) to generic data inputs.

### 2) Current POC Mapping → VibeNet
- API: FastAPI (`src/main.py`), Vibe endpoints (`/api/vibe/*`), job store, storage presigners.
- Rendering: MIDI assembly (completed/), FluidSynth+FFmpeg in `src/renderer.py` (opt‑in via `RENDER_MP3=1`).
- Vibes: `config/vibe_palettes.yaml` (Synthwave, Arena Rock, Tropical Pop), `config/vibe_rules.yaml` (keyword mapping).
- Vibes: `config/vibe_palettes.yaml` (Synthwave, Arena Rock, Tropical Pop, Circle of Life – Travel), `config/vibe_rules.yaml` (keyword mapping).
- Screenshot→Palette: `src/vibe_api.py` (LLM‑only by default; Spotify optional).
- Batch: `src/pipeline/*` (catalog + publishing) — reuse for scheduled VibeNet jobs.

### 3) Vibe Space (Config‑First; Embedding Later)
- Palettes (tempo, instruments, chord blocks, signature rhythms) in `config/vibe_palettes.yaml`.
- Rules (keyword→palette, theory nudges like IV→iv) in `config/vibe_rules.yaml`.
- Future: Vibe embedding via MusicVAE (latent interpolation) for smooth style blends.

### 4) API Surface (VibeNet)
- `GET /vibenet/vibes` → list palettes (Supabase or config fallback).
- `POST /vibenet/generate` → { data:[…] | csv_id, vibe_slug, controls } → { job_id, midi_url, mp3_url, momentum_json }.
- New: `POST /api/vibe/embed` → { data:[…], palette? } → { vibe: V }.
- New: `POST /api/vibe/train` (admin) → labeled takes for future finetune.
- Reuse: `POST /api/vibe/screenshot` (image or artist/title → palette), `POST /api/vibe/motif` (motif library).

Example body:
```json
{ "vibe_slug": "circle_of_life_travel", "data": [0.12,0.3,0.5,0.72], "controls": {"bars": 16, "tempo_hint": 112} }
```

### 5) Data → Music Pipeline (Rule‑Based Core)
- Preprocess: normalize (0..1), resample to beats, smooth outliers.
- Melody: values→scale degrees (palette key); clamp leaps; volatility→note density.
- Harmony: palette chord blocks (e.g., I‑V‑vi‑IV); data windows select chord/inversion; nostalgia rules (IV→iv cadence).
- Rhythm & Dynamics: volatility→tempo/density; amplitude→velocity; earcons on peaks/spikes.
- Assembly: assign tracks (lead/pad/bass/drums) from sound packs; export MIDI/MP3; store + sign URLs.
- Optional ML: stylize melody via MusicVAE/seq2seq (feature‑flagged, later phase).

### 6) Sub‑Agents (MCP) & Responsibilities
- Requirements Analyst: stories, API contracts, acceptance criteria.
- Sonification Engineer: mapping funcs (melody/harmony/rhythm), theory rules, unit tests.
- ML Specialist (opt): dataset curation, MusicVAE/seq2seq pipelines, model APIs.
- Audio Integration: MIDI assembly, instrument programs/CCs, FluidSynth/FFmpeg mastering.
- Backend Engineer: `/vibenet/*` endpoints, validation, storage, rate limits, OpenAPI.
- Frontend Dev (Lovable): data upload, vibe picker, controls, player, momentum viz; admin motif capture.
- QA/Release: smoke + E2E, LUFS checks, artifact integrity, latency/error SLOs.
- Docs/Ops: envs, runbooks, CI/CD, cost/logging.

### 7) Build Phases & Deliverables
- Phase 0 – Groundwork: palettes + rules, rendering path, storage wiring, Vibe endpoints.
- Phase 1 – MVP (2–3 weeks): rule‑based generator for arrays; 3 palettes; frontend flow; Kokomo hero.
  - DoD: <6s P95 for 16 bars; signed URLs; unit + E2E passing.
- Phase 2 – Alpha (3–4 weeks): ML stylization behind flag; WebAudio MIDI option; streaming PoC.
  - DoD: audible improvement in listening tests; stable API.
- Phase 3 – Beta: more palettes; CSV role mapper; autoscale; analytics; daily batches on serpradio.com.

### 8) Testing & Acceptance
- Unit: scale conformance, chord validity, deterministic mapping with seeds.
- Integration: API contract (httpx), artifact presence, renderer availability.
- Audio: duration bounds, silence detection, LUFS target; MIDI diff tools for regressions.
- UX: end‑to‑end smoke (`scripts/vibe_smoke.py`), Lovable flows verified.

### 9) Env & Security
- Disable Spotify by default: `VIBE_USE_SPOTIFY=0`; require `OPENAI_API_KEY`.
- Storage: `S3_BUCKET`/`SUPABASE_*`; public vs private buckets; TTLs & lifecycle.
- Secrets: never commit `.env`; admin routes guarded by `ADMIN_SECRET`.

### 10) Roadmap Alignment (serpradio.com)
- Short‑term: Caribbean “Kokomo” hero, Synthwave/Arena demos, travel tie‑in, public catalog playback.
- Mid‑term: generic data uploads (CSV/JSON), vibe picker + controls, shareable links.
- Long‑term: learned vibe embeddings, real‑time streams, vertical packs (finance, weather, ecommerce).

### 11) Success Metrics
- Musicality: listener MOS, vibe match rate.
- Performance: P50/P95 generation, job success rate.
- Adoption: plays per track, repeat usage, palette popularity.

### 12) FastAI Training Loop (New)
- Repo: cloned locally under `fastai/` via `git clone --depth 1 https://github.com/fastai/fastai.git` (treated as a vendor dependency).
- Script: `python -m src.training.vibenet_fastai --epochs 5 --bs 64` trains a tabular classifier on `completed/motifs_catalog.json` using FastAI and exports a learner into `models/vibenet_fastai_motif.pkl`.
- Purpose: generates a supervised helper to predict motif labels from metadata, providing data-driven priors for the VibeNet motif selector. At runtime set `VIBENET_FASTAI_MODEL` (defaults to `models/vibenet_fastai_motif.pkl`) and the selector will auto-label unlabeled motifs using the exported learner.
- Next steps: wire the exported learner into `SonificationService` as an optional backfill when rule-based selection is inconclusive.

Implementation notes: endpoints extend existing FastAPI app; use `config/vibe_*` for palettes/rules; keep ML optional; maintain backward compatibility with current SERPRadio flows.

---

## Deep Spec (Vibe Space + Bindings)

This repository adopts a formal Vibe Space and bindings as described in AGENTS.md.
Key highlights implemented now:
- V (VibeVector) axes: valence, arousal, tension, brightness, warmth, density, syncopation, harm_complexity (+ palette, meter).
- Rule-first encoder `src/vibe_encoder.py` maps series → V.
- Harmony designer `src/harmony.py` chooses key/mode and chord grid.
- IRs in `src/vibe_ir.py` keep modules swappable and testable.
- New endpoints `/api/vibe/embed` and `/api/vibe/train` wire IRs to the existing stack.

Future extensions (planned): learned head for V, stylizer, motif graph orchestrator, DSL bindings per palette (mapping.yaml).

---

## Further Reading

- Full architecture deep‑dive, module references, and design rationale: `docs/VIBENET_ARCHITECTURE.md`

---

## Local MIDI Remix (POC)

- Purpose: remix a local MIDI (e.g., from an electric piano) using flight price metrics as the pattern driver, without requiring S3/Supabase.
- Command:
  - `python -m src.pipeline.remix_midi_from_csv --input-midi JMX-2025-Oct-05-1.11.6.pm.mid --csv seed_flight_price_data.csv --origin JFK --out-dir data/remixes --bars 16`
- What it does:
  - Reads `seed_flight_price_data.csv`, derives a series from median prices, maps volatility to tempo and bands, converts flight columns to SERP-like metrics, selects motifs, and writes a remixed MIDI using your input as a base template.
- Output: a `.mid` file under `data/remixes` with a timestamped name.
