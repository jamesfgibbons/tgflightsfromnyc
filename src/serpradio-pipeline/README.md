# SERP Radio — Caribbean Kokomo Pipeline (Drop‑in Bundle)

This bundle gives you **ready-to-run Python** + **shell scripts** to:
1) fetch NYC→Caribbean flight offers from an API (Kiwi/Tequila),
2) compute visibility stats,
3) enrich with OpenAI (brand/novelty),
4) convert to momentum bands,
5) publish a public catalog JSON for your Lovable.dev frontend.

## 0) Setup

```bash
cd serpradio-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Add your secrets
cp creds.env.example creds.env.txt
nano creds.env.txt  # fill OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE, TEQUILA_API_KEY
```

Create tables in Supabase (SQL editor):

```sql
-- Paste this file:
-- sql/schema.sql
```

## 1) Run the full pipeline (Caribbean Kokomo)

```bash
source .venv/bin/activate
./scripts/run_all.sh
```

This will run, in order:
- `fetch_offers_nyc_caribbean` (14 days forward)
- `build_visibility` (quartiles, volatility, SOV)
- `openai_enrich` (GPT‑4o mini JSON classification)
- `build_momentum` (Tropical Pop momentum bands)
- `publish_catalog` (writes `catalog.json` to your public bucket)

## 2) Individual stages

```bash
./scripts/run_offers.sh          # DAYS=30 ./scripts/run_offers.sh
./scripts/run_visibility.sh
./scripts/run_enrich.sh
./scripts/run_momentum.sh
./scripts/run_publish.sh
```

## 3) Frontend (Lovable.dev) wiring

- Read `momentum_bands` (Supabase) or the published `catalog.json`.
- When theme = `caribbean_kokomo`, use **Tropical Pop** pack and enable “jackpot” earcons when `price_min < price_p25`.
- Use `/catalog/travel/flights_from_nyc/caribbean_kokomo/catalog.json` to list playable items.
- Show a **Leaderboard** from `flight_visibility` (min price by destination), and **Volatility** from `volatility` column.

## Notes

- Storage: This bundle includes a `UnifiedStorage` writer that uses **Supabase Storage** by default (falls back to **S3** if configured).
- Cost control: Enrichment model is **gpt‑4o‑mini** with strict JSON. Batch API is recommended for larger runs.
- Extend: Add more regions by updating `src/geo_registry.py` and reuse the same pipeline.

Generated: 2025-08-16T23:41:29.580452Z
