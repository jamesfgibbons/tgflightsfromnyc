# Repository Guidelines

## Project Structure & Module Organization
- `src/` — FastAPI backend and core engine
  - `main.py` (API entry), `vibe_api.py` (Vibe Engine), `sonify_service.py` (orchestration), `arranger.py`, `earcons.py`, `storage.py`, `pipeline/` (batch + travel), `renderer.py`.
- `completed/` — domain algorithms (metrics, controls, MIDI transform, motif selection).
- `tests/` — pytest suite (`test_*.py`).
- `config/` — palettes and rules (`vibe_palettes.yaml`, `vibe_rules.yaml`).
- `scripts/` — utilities and smoke tests (e.g., `scripts/vibe_smoke.py`).
- `tools/` — helpers (e.g., `tools/seed_palettes.py`).

## Build, Test, and Development Commands
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run API: `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- Run pipeline: `python -m src.pipeline.run_pipeline --limit 24`
- Smoke tests: `make smoke` or `BASE=http://localhost:8000 python scripts/vibe_smoke.py`
- Tests: `pytest -q` or coverage `pytest --cov=src -q`
- Docker (optional): `docker build -t serpradio:latest . && docker run --rm --env-file .env -p 8000:8000 serpradio:latest`

## Coding Style & Naming Conventions
- Python 3.11+, PEP8, 4‑space indentation (use Black defaults).
- Use type hints; Pydantic v2 models for request/response.
- Filenames/modules: `snake_case.py`; classes: `PascalCase`; vars/functions: `snake_case`.
- Formatters/linters: `black`, `isort`, `mypy` (installed in `requirements.txt`).
  - Examples: `black src tests`, `isort src tests`.

## Testing Guidelines
- Framework: `pytest`; place tests under `tests/` as `test_*.py`.
- Keep unit tests close to modules (e.g., `tests/test_arranger.py`).
- Run locally with `pytest -q`; aim for meaningful coverage (`pytest --cov=src`).
- Prefer deterministic inputs (seeded where applicable); avoid network in unit tests.

## Commit & Pull Request Guidelines
- Commits: concise, imperative mood (e.g., "Add Vibe Engine palettes endpoint"). Group related changes.
- PRs: include purpose, scope, screenshots/logs of API responses, and links to issues. Note env/config changes (e.g., `VIBE_USE_SPOTIFY`, storage buckets).
- CI friendliness: keep changes minimal; don’t commit secrets or `.env`.

## Security & Configuration Tips
- Configure storage via env (`S3_BUCKET`/`SUPABASE_*`). Keep `ADMIN_SECRET` and API keys out of git.
- Spotify is optional; disable with `VIBE_USE_SPOTIFY=0`. MP3 rendering via `RENDER_MP3=1` requires Fluidsynth+FFmpeg.
- Public assets: serve via the public bucket/CDN; keep artifacts private.
