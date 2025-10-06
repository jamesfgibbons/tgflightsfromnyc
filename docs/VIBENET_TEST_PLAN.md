# VibeNet Test Plan (API + Batch)

## Quick Smoke (local)
- Pre-req: `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- Env: `VIBE_USE_SPOTIFY=0`, `GROQ_API_KEY=...` (or `OPENAI_API_KEY`)

1) List palettes
- `curl -s http://localhost:8000/vibenet/vibes | jq` → `{ items: [...], source: "..." }`

2) Screenshot-only (form fields)
- `curl -s -X POST http://localhost:8000/api/vibe/screenshot -F artist="The Beach Boys" -F title="Kokomo" | jq`
- Expect: `palette_slug=caribbean_kokomo`, `features_normalized` present

3) Generate from numeric data
- `curl -s -X POST http://localhost:8000/vibenet/generate -H 'Content-Type: application/json' \
  -d '{"vibe_slug":"caribbean_kokomo","data":[0.1,0.4,0.7,0.3,0.8,0.2],"controls":{"bars":16}}' | jq`
- Expect: `mp3_url` or `midi_url`, `momentum_json`, `sound_pack`

## Travel Batch (small)
- Run: `bash scripts/run_travel_test_batch.sh`
- Verify:
  - `curl -s http://localhost:8000/api/travel/subthemes | jq`
 - `curl -s 'http://localhost:8000/api/travel/catalog?sub_theme=non_brand_seo&origin=JFK&destination=LAS&limit=10' | jq`
- `curl -s 'http://localhost:8000/api/vibenet/runs?limit=5' | jq`
- `curl -s 'http://localhost:8000/api/vibenet/items?run_id=<uuid>&limit=5' | jq`

## Agent Responsibilities for Test
- Requirements Analyst: Confirms inputs and acceptance criteria match; updates this plan if needed.
- Sonification Engineer: Ensures VibeDoc fields coherent; validates scale/chords; fixes mapping edge-cases.
- Backend Engineer: API contracts; storage/presign; `/vibenet/*` + catalog endpoints.
- Audio Integration: Rendering path healthy; LUFS/peak checked; earcon headroom.
- QA Auditor: Runs smoke + asserts: presence of URLs, momentum bands, VibeDoc (if exposed), LUFS bounds.
- Docs/Ops: Records results, updates runbooks, captures sample responses for demos.

## Acceptance
- “First call” success: screenshot form → palette + normalized features
- “Generate” success: returns playable URL + momentum + pack
- “Medium batch” success: subthemes route counts non-zero; filtered catalog returns items
- No errors in API logs; generation < 6s for 16 bars (local, non-ML)
