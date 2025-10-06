-- Prompt Engine core schema: lists, items, runs, LLM results, enrichments, catalogs

-- 1) Prompt lists (scheduled, curated, ad hoc)
create table if not exists prompt_lists (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  kind text not null default 'curated',  -- curated | scheduled | ad_hoc
  description text,
  owner text,                             -- email/user id (optional)
  schedule_cron text,                     -- for kind=scheduled
  tags text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_prompt_lists_kind on prompt_lists (kind);

-- 2) Prompt list items (the concrete prompts to call)
create table if not exists prompt_list_items (
  id uuid primary key default gen_random_uuid(),
  list_id uuid references prompt_lists(id) on delete cascade,
  title text,
  prompt text not null,
  metadata jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_prompt_list_items_list on prompt_list_items (list_id);

-- 3) Prompt runs (each execution of a list)
create table if not exists prompt_runs (
  id uuid primary key default gen_random_uuid(),
  list_id uuid references prompt_lists(id) on delete set null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  status text not null default 'running',  -- running | completed | failed
  notes text
);
create index if not exists idx_prompt_runs_list on prompt_runs (list_id);
create index if not exists idx_prompt_runs_status on prompt_runs (status);

-- 4) LLM results (raw provider response per item)
create table if not exists llm_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references prompt_runs(id) on delete cascade,
  list_item_id uuid references prompt_list_items(id) on delete set null,
  provider text,                 -- xai | groq | openai
  model text,
  prompt text,
  response_raw jsonb,
  latency_ms integer,
  status text default 'completed',  -- completed | failed
  error text,
  created_at timestamptz not null default now()
);
create index if not exists idx_llm_results_run on llm_results (run_id);

-- 5) Enrichment results (normalized + derived fields for VibeNet)
create table if not exists enrichment_results (
  id uuid primary key default gen_random_uuid(),
  llm_result_id uuid references llm_results(id) on delete cascade,
  normalized jsonb,            -- normalized fields from raw llm
  vibe_features jsonb,         -- valence/energy/mode/key_center etc
  momentum jsonb,              -- array of bands
  label_summary jsonb,         -- {positive, neutral, negative}
  sound_pack text,
  created_at timestamptz not null default now()
);
create index if not exists idx_enrichment_llm on enrichment_results (llm_result_id);

-- 6) Catalog publish registry (optional bookkeeping)
create table if not exists catalogs (
  id uuid primary key default gen_random_uuid(),
  channel text,               -- e.g., travel
  theme text,                 -- e.g., flights_from_nyc
  sub_theme text,             -- e.g., ski_season
  catalog_key text not null,  -- storage key to latest.json
  total integer,
  generated timestamptz not null default now()
);
create index if not exists idx_catalogs_key on catalogs (catalog_key);

