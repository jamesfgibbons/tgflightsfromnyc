# Repository Guidelines

## Project Structure & Module Organization
- `src/` – FastAPI backend, VibeNet engine, providers, and pipelines (`src/main.py`, `src/vibe_api.py`, `src/pipeline/*`).
- `vite-react-user/` – Vite/React split‑flap UI (Lovable/Vercel friendly).
- `sql/` – Supabase migrations (`000_init_schema.sql` + modular SQL files).
- `tests/` – pytest suites (storage, job store, audio, APIs).
- `docs/` – runbooks and deployment notes; `data/`, `catalog/` – generated assets.

## Build, Test, and Development Commands
- Backend install: `pip install -r requirements.txt`
- Run API: `uvicorn src.main:app --reload` (http://127.0.0.1:8000)
- Tests: `pytest --maxfail=1 -q` (unit/integration)
- Frontend: `cd vite-react-user && npm install && npm run dev`
- Pipelines (demo): `bash scripts/run_travel_pipeline_local.sh`
- Docker (optional): `docker build -t serpradio:dev . && docker run --rm -p 8000:8000 serpradio:dev`

## Coding Style & Naming Conventions
- Python: PEP 8; type hints for new code. Use `ruff` (if configured) or `black` + `isort`. Files: `snake_case.py`; classes: `PascalCase`; funcs/vars: `snake_case`.
- React: ESNext + Prettier (2‑space). Components in `PascalCase` (e.g., `SplitFlapBoard.tsx`).
- SQL: zero‑padded migration filenames (e.g., `000_init_schema.sql`).

## Testing Guidelines
- Framework: `pytest`; tests under `tests/` named `test_*.py`.
- Mock external deps (Supabase, S3, LLMs). Avoid live network in unit tests.
- Add tests for new routes/services; run `pytest --maxfail=1` before PRs.

## Commit & Pull Request Guidelines
- Commits: conventional, imperative (e.g., `feat: add best-time summary endpoint`).
- PRs: include purpose, key changes, run output (pytest, curl), and any env/config updates. Link issues when applicable.
- Screenshots/console for UI/API changes (split‑flap preview, `/api/vibe/generate_data` result). Keep PRs scoped.

## Security & Configuration Tips
- Secrets only in env (`.env`/platform vars). Never commit keys.
- Key envs: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`, `CORS_ORIGINS`, `ADMIN_SECRET`, storage (`STORAGE_BUCKET`/`S3_*`), frontend `VITE_API_BASE`.
- Admin routes require `X-Admin-Secret`; set CORS to your frontend domains.
