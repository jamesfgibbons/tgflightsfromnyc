# VibeNet Architecture and Data Sonification Engine

This document provides a deep, technical overview of VibeNet and how it maps arbitrary data (time‑series/tabular) into musical output using the SERPRadio sonification engine embedded in this repository.

## Goals
- Deterministic, low‑latency generation of listenable, structured music from data.
- Config‑first design (palettes, rules, chord blocks) with modular ML upgrades.
- Clean separation between API, orchestration, domain logic, rendering, and storage.

## High‑Level Flow
1. Client submits numeric series or context (CSV/keywords/screenshots) to the API.
2. API normalizes data and derives momentum bands and tempo hints.
3. Sonification service fetches or computes metrics, maps to MIDI controls, selects motifs, and designs harmony.
4. MIDI is arranged and written, optional earcons are layered, then optionally rendered to MP3.
5. Artifacts are stored (S3 or Supabase) and presigned URLs are returned.

```
Request → Normalize/Segment → Controls → Motifs + Harmony → MIDI → (MP3) → Storage URLs
```

## Core Modules & Responsibilities

- API Surface
  - FastAPI app: `src/main.py:1` (service assembly, CORS, routers)
  - Vibe endpoints (generic and palette lists): `src/vibenet_api.py:1`
  - Additional utilities (screenshots/palettes/motifs): `src/vibe_api.py:1`, `src/board_api.py:1`, `src/travel_context_api.py:1`

- Orchestration
  - Sonification orchestrator: `src/sonify_service.py:41` — coordinates metrics, motif selection, MIDI creation, earcons, and rendering
  - Job tracking: `src/jobstore.py:1` (queued→running→done/error lifecycle)
  - Storage abstraction: `src/storage.py:1` — unified Supabase/S3 with presigned URLs and secure path handling

- Domain Logic (completed/)
  - Metrics → Controls: `completed/map_to_controls.py:36` — maps normalized metrics (ctr, impressions, position, clicks) to BPM, transpose, velocity, filter, reverb
  - Motif Catalog & Selection: `completed/motif_selector.py:157` — strategy‑based and label‑based selection (rules + optional FastAI predictor)
  - MIDI Transformation: `completed/transform_midi.py:16` — tempo scaling, pitch/velocity adjustments, motif arrangement, CC automation, mido compatibility check
  - Momentum Analysis: `completed/extract_bars.py:1`, `completed/tokenize_motifs.py:1`, `completed/classify_momentum.py:1` — bars→tokens→labels

- Rendering & Mastering
  - MIDI→MP3: `src/renderer.py:1` — FluidSynth + FFmpeg with dependency checks
  - Mastering chain (LUFS, compression): `src/mixing.py:1`

## Data → Vibes Mapping

### Normalization & Segmentation
- Normalizes series to 0..1 and splits into segments to derive momentum bands.
- Implementation: `_normalize` and `_segments_to_bands` in `src/vibenet_api.py:84`.
- Bands are provided back into the pipeline as a simple musical proxy for energy/momentum.

### Controls (Metrics → MIDI)
- `ctr` → `bpm` (higher CTR → faster tempo)
- `position` → `transpose` (better rank → higher pitch)
- `impressions` → `velocity` (more impressions → louder)
- `clicks` → `cc74_filter` (brightness)
- Combined engagement → `reverb_send`
- Implementation: `completed/map_to_controls.py:36` (see dataclass `Controls:13`).

### Motif Selection
- Strategy‑based: picks motifs by energy/brightness/darkness given controls (`_determine_selection_strategy`, `_select_by_strategy`).
- Label‑based: decides label by rules (`decide_label_from_metrics`) and filters catalog by that label (`select_motifs_by_label:435`).
- Optional learning: unlabeled motifs are auto‑labeled by a FastAI classifier if available (see “Training”).
- Implementation: `completed/motif_selector.py:157` and `completed/motif_selector.py:435`.

### Harmony & Chord Plans
- Key/mode choice: `src/harmony.py:9` via `choose_key_mode` based on vibe vector dimensions.
- Progressions: `build_progression` selects from pop/dorian/phrygian blocks with tasteful extensions and borrowed iv (`src/harmony.py:17`).
- Epic loop designer: `design_epic_harmony_from_palette` blends an anthemic intro block with a high‑energy drop loop for “deal drop” moments (`src/harmony.py:54`). Uses palette chord blocks (see “Vibe Space”).

## Vibe Space (Palettes & Rules)

### Palettes
- Defined in `config/vibe_palettes.yaml:1` with fields:
  - `slug`, `title`, `description`, `target_valence`, `target_energy`, `tempo_min/max`, `mode_preference`, `default_pack`
  - `instrumentation_json`: suggested instrument roles
  - `signature_rhythm_json`: pattern hints
  - `chord_blocks_json`: named chord sequences (e.g., `pop_sunshine`, `anthemic_lift`, `power_riff_mix`)
- Examples in this repo:
  - `caribbean_kokomo` — island/pop vibe for travel hero
  - `synthwave_midnight` — synthwave palette
  - `arena_anthem` — arena rock
  - `circle_of_life_travel` — anthemic pop‑orchestral progression for intros
  - `hammer_to_fall_drop` — power‑riff drop for epic reveals

### Palette Selection Rules
- Keyword mapping: `config/vibe_rules.yaml:1` routes text to `palette_slug`.
- API fallback: `_palette_to_sound_pack` in `src/vibenet_api.py:40` maps palette slug to default sound pack.

## MIDI Creation Pipeline

1. Controls and motifs are computed (`map_metrics_to_controls`, `motif_selector`).
2. Harmony plan is designed (standard or epic intro→drop).
3. MIDI builder arranges instruments and patterns:
   - `completed/transform_midi.py:139` adds instrument tracks and arranges motif patterns (`_arrange_motif_pattern:163`).
   - Applies pitch transpose and velocity scaling (`_apply_pitch_transpose:101`, `_apply_velocity_scaling:114`).
   - Adds CC automation (filter/reverb) (`_add_control_changes:204`).
   - Writes file and verifies mido round‑trip (`_verify_midi_compatibility:180`).
4. Earcons (optional) are layered on momentum transitions (`src/sonify_service.py:260`).
5. Optional headroom applied for earcon layering (`_apply_earcon_headroom:292`).
6. MP3 rendering (optional) via FluidSynth + FFmpeg (`src/renderer.py:15`, `render_midi_to_mp3:24`).

## Momentum Analysis
- Bars are extracted from input MIDI (if provided), tokenized, and classified into momentum labels for earcon triggers and structural decisions.
- Key modules: `completed/extract_bars.py:1`, `completed/tokenize_motifs.py:1`, `completed/classify_momentum.py:1`.
- In `src/sonify_service.py:195`, the momentum pipeline runs when `input_midi_key` is provided or when `override_metrics` supplies momentum.

## Training (Optional, FastAI)

### Supervised Training
- Data: labeled motifs in `completed/motifs_catalog.json` (each with `metadata` and an optional `label`).
- Trainer: `src/training/vibenet_fastai.py:1` — builds FastAI Tabular learner (categorify/fillmissing/normalize), trains, and exports `models/vibenet_fastai_motif.pkl`.
- Invocation:
  - `python -m src.training.vibenet_fastai --epochs 5 --bs 64 --catalog completed/motifs_catalog.json --export models/vibenet_fastai_motif.pkl`

### Runtime Inference
- Helper: `src/training/fastai_runtime.py:1` — lazily loads the exported learner (path via `VIBENET_FASTAI_MODEL`, defaults to `models/vibenet_fastai_motif.pkl`).
- Selector integration: unlabeled motifs are predicted and promoted if they match the target label (`completed/motif_selector.py:452`).

## API Contracts

- List palettes: `GET /vibenet/vibes` → palette array (Supabase or config fallback) (`src/vibenet_api.py:59`).
- Generate sonification: `POST /vibenet/generate` with:
  - `data: number[]`, `vibe_slug: string`, `controls: { bars, tempo_hint? }`
  - Produces `JobResult` with signed URLs, label summary, momentum JSON, and logs (`src/vibenet_api.py:121`).
- Supporting models: `src/api_models.py:1`, `src/models.py:1` (`SonifyRequest`, `JobResult`).

## Storage, URLs, and Security

- Unified storage: `src/storage.py:1` chooses Supabase vs S3 based on env; presigned URLs via `UnifiedStorage.get_public_url`.
- Write helpers: `put_bytes`, `write_json` with encryption on private buckets (`src/storage.py:100`).
- Safeguards: tenant prefixes (`ensure_tenant_prefix:...`), traversal checks (`_has_path_traversal:...`).
- Key env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE(_KEY)`, `S3_BUCKET`/`AWS_*`, `CORS_ORIGINS`, `ADMIN_SECRET`, `RENDER_MP3`, `VIBENET_FASTAI_MODEL`.

## Rendering & Mastering

- Rendering availability check: `src/renderer.py:116`.
- Mastering chain (optional) for MP3 post‑processing: fades, EQ, multiband compression, LUFS normalization, peak limiting (`src/mixing.py:21`).

## Local POCs & Pipelines

- Remix a local piano MIDI with travel price patterns:
  - `src/pipeline/remix_midi_from_csv.py:1`
  - `python -m src.pipeline.remix_midi_from_csv --input-midi <file.mid> --csv seed_flight_price_data.csv --origin JFK --out-dir data/remixes --bars 16`
  - Uses your MIDI as base template and layers motif arrangement driven by metrics.

- Batch/publishing examples under `src/pipeline/*` and `scripts/*` for travel themes.

## Testing & Quality

- Unit tests: `tests/` with pytest; mock external services (Supabase, S3, LLMs).
- Recommendations: verify MIDI integrity (mido round‑trip), LUFS targets (`src/mixing.py:150`), and API contracts via httpx.

## Extensibility Guidelines

- Add a palette:
  1) Append a block to `config/vibe_palettes.yaml` with tempo ranges, instrument hints, and `chord_blocks_json`.
  2) Optionally add keywords in `config/vibe_rules.yaml`.
  3) Map `slug → sound_pack` in `_palette_to_sound_pack` if needed (`src/vibenet_api.py:40`).

- Add a motif category or labels:
  - Extend the motif catalog (`completed/motifs_catalog.json`) and retrain the FastAI classifier.

- Integrate new data sources:
  - Supply series/CSV to `/vibenet/generate` or add a pipeline under `src/pipeline/` that transforms your data into normalized metrics.

## Appendix: Selected File Index

- API: `src/vibenet_api.py:1`, `src/vibe_api.py:1`, `src/main.py:1`
- Orchestration: `src/sonify_service.py:41`, `src/jobstore.py:1`, `src/storage.py:1`
- Domain: `completed/map_to_controls.py:36`, `completed/motif_selector.py:157`, `completed/transform_midi.py:16`
- Harmony: `src/harmony.py:9`, `src/harmony.py:54`
- Rendering/Mastering: `src/renderer.py:1`, `src/mixing.py:1`
- Training: `src/training/vibenet_fastai.py:1`, `src/training/fastai_runtime.py:1`
- Palettes & Rules: `config/vibe_palettes.yaml:1`, `config/vibe_rules.yaml:1`

