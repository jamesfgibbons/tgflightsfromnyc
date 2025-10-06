# Agents Integration (Formatting & QA + Runners)

This repository includes a simple agent manifest (`agents/agent_manifest.yaml`) and a formatting/QA subagent (`agents/formatting_qa_agent.py`). These can be registered with an agent runner (e.g., `openai/openai-agents-python`) to orchestrate tasks.

## Agents
- `formatting_qa` — runs black/isort (check or fix), mypy, pytest; returns JSON summary; nonzero exit on failures.
- `smoke_runner` — executes API smoke (`scripts/vibenet_curl_smoke.sh`).
- `travel_batch_runner` — runs a small multi-subtheme batch and publishes catalog.
- `ski_batch_runner` — runs ad-hoc ski-season batch and publishes catalog.

## Register with openai-agents-python
1. Clone their runner (outside this repo):
   ```bash
   git clone https://github.com/openai/openai-agents-python
   ```
2. Create an agent spec (example):
   ```yaml
   # agents.yaml
   agents:
     - name: formatting_qa
       command: "python agents/formatting_qa_agent.py --mode check"
     - name: smoke_runner
       command: "bash scripts/vibenet_curl_smoke.sh"
     - name: travel_batch_runner
       command: "bash scripts/run_travel_test_batch.sh"
     - name: ski_batch_runner
       command: "python scripts/run_ski_pipeline.py --limit 100"
   env:
     BASE: "http://localhost:8000"
   ```
3. Configure environment variables (GROQ/OPENAI keys, storage, etc.) in the runner.
4. Invoke agents by name; collect JSON/status for dashboards.

## Local usage
- Formatting fix: `python agents/formatting_qa_agent.py --mode fix`
- Check only: `python agents/formatting_qa_agent.py --mode check`
- Smoke: `bash scripts/vibenet_curl_smoke.sh`
- Travel batch: `bash scripts/run_travel_test_batch.sh`
- Ski batch: `python scripts/run_ski_pipeline.py --limit 100`

## Notes
- Formatting/QA agent exits nonzero on failing checks; can be wired to CI/CD gates.
- Outputs of batch runners publish into `catalog/travel/...` (public bucket) for Lovable.
