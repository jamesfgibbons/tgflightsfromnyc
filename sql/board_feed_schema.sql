-- Board feed + Webz.io supplemental schema

-- Logs board playback/generation events for analytics
create table if not exists vibe_board_events (
  id uuid primary key default gen_random_uuid(),
  job_id text,
  event text,                      -- e.g., 'generate_data'
  palette_slug text,
  context jsonb,                   -- deal_score, novelty_score, brand_pref_score, region_pref_score, etc.
  momentum jsonb,                  -- {positive, neutral, negative}
  tempo_bpm integer,
  created_at timestamptz not null default now()
);
create index if not exists idx_vibe_board_events_job on vibe_board_events(job_id);

-- Stores normalized Webz.io firehose items + derived scores
create table if not exists webzio_events (
  id uuid primary key default gen_random_uuid(),
  title text,
  url text,
  site text,
  published_at timestamptz,
  country text,
  language text,
  rating jsonb,
  entities jsonb,
  categories jsonb,
  source text default 'webzio',
  scores jsonb,                    -- novelty_score, brand_pref_score, region_pref_score, deal_score, etc.
  raw jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_webzio_events_site on webzio_events(site);
create index if not exists idx_webzio_events_published on webzio_events(published_at);

