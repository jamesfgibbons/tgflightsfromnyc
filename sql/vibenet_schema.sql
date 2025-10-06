-- VibeNet Supabase schema (runs + items)
create table if not exists vibenet_runs (
  id uuid primary key default gen_random_uuid(),
  theme text not null,
  sub_theme text,
  channel text,
  generated timestamptz not null default now(),
  total integer not null default 0,
  catalog_key text,
  notes text
);

create table if not exists vibenet_items (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references vibenet_runs(id) on delete cascade,
  entry_id text not null, -- source id
  timestamp timestamptz,
  channel text,
  theme text,
  sub_theme text,
  origin text,
  destination text,
  brand text,
  title text,
  prompt text,
  sound_pack text,
  duration_sec numeric,
  mp3_url text,
  midi_url text
);

