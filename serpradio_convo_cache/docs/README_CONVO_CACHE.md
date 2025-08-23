# SERP Radio – Conversational Cache (NYC → Caribbean)

This mini-bundle builds a **conversational+structured cache** by asking OpenAI like a human *and* appending a machine-readable `SIGNALS` YAML block. It also integrates **web search** (Tavily API) so each note can cite sources.

## 0) Install

```bash
cd serpradio_convo_cache
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 1) Create *minimal* tables in Supabase

Paste `sql/supabase_minimal.sql` into the Supabase SQL Editor and run.
This creates:

- `visibility_notes` – conversational text + citations
- `visibility_signals` – machine-friendly extracts

(We keep RLS simple: authenticated `select` only. Tighten later.)

## 2) Fill `creds.env.txt`

```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGciOi...   # service role (server-side only)
TAVILY_API_KEY=tvly-...              # optional; enables web search
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMP=0.2
OPENAI_MAX_TOKENS=700
# Set to 1 to generate mock responses without spend:
# OPENAI_MOCK=1
```

## 3) Run a conversational batch

```bash
./scripts/run_convo_cache.sh
# or control params
DAY_PHRASE="this weekend" MAX_DESTS=12 MAX_RESULTS=6 ./scripts/run_convo_cache.sh
```

Each destination produces:
- a short analyst note with inline citations like `[1]`
- a fenced YAML block; we parse it and upsert into tables

## 4) What you’ll see

- `visibility_notes.note_text` – the exact conversational paragraph
- `visibility_notes.citations` – `["https://...", ...]`
- `visibility_signals.price_low_est` etc. for your sonification engine

## 5) Frontend (Lovable)

Query both tables by `origin_metro='NYC'` and `asked_on=today`.
Use `note_text` for human copy, `visibility_signals` for charts/sonification.

## 6) Extend at scale

- Add more metros/destinations; or switch `DAY_PHRASE` to "next month".
- Add more search providers (Brave, SerpAPI) under `src/searchers/`.
- Schedule with GitHub Actions or Render cron.

> **Tip**: keep most runs on `gpt-4o-mini`; reserve `gpt-4o` for homepage weekly narratives.
