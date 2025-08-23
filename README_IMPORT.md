
# SERP Radio Seeds – Import Guide

## What you have
- `schema.sql` – run once in Supabase SQL editor
- CSV seeds for `profiles`, `email_leads`, `sonification_projects`, `demo_datasets`, `flight_price_data`, `sonification_inventory`
- JSON libraries: prompt templates, sonification mapping, theme catalog

## How to import (Supabase)
1) Open **Supabase Dashboard → SQL** and run **schema.sql** (copy-paste or upload).
2) Go to **Table editor** for each table → **Import data** → choose the matching CSV:
   - seed_profiles.csv → `profiles`
   - seed_email_leads.csv → `email_leads`
   - seed_sonification_projects.csv → `sonification_projects`
   - seed_demo_datasets.csv → `demo_datasets`
   - seed_flight_price_data.csv → `flight_price_data`
   - seed_sonification_inventory.csv → `sonification_inventory`
3) Optional: create a **Storage** bucket `serpradio-public` for hosting public mp3/midi (if not using S3/CDN).

## Regions & Theming
- `flight_price_data` contains `destination_region` including **Caribbean** (NAS, MBJ, SJU, CUR).
- Use `v_visibility_by_region` view to power your region charts.
- The **Kokomo** theme is represented in `theme_catalog_travel.json` and inventory rows labeled “NYC → Caribbean”.

## Frontend wiring (Lovable.dev)
- Set ENV:
  - `VITE_API_BASE=https://serpradio-api-2025.onrender.com`
  - `VITE_SUPABASE_URL=...`
  - `VITE_SUPABASE_ANON_KEY=...`
- Load `theme_catalog_travel.json` into your app’s config loader to show tabs for sub-themes.
- Use `sonification_mapping_config.json` to drive earcon rules and pack selection.

## Next pipeline run (Claude/Backend)
- Ensure OPENAI key + Supabase creds set.
- Run: `bash scripts/run_travel_pipeline_local.sh`
- This will generate entries with NYC + Caribbean focus (Kokomo), suitable for playback.

Generated: 2025-08-16T16:23:50.262327
