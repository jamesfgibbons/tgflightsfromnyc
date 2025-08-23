
-- SERP Radio core schema (Supabase/Postgres)
-- Safe to run in a fresh project; use IF NOT EXISTS guards.

create extension if not exists "uuid-ossp";

-- =======================
-- PROFILES
-- =======================
create table if not exists public.profiles (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_profiles_email on public.profiles(email);

-- =======================
-- EMAIL LEADS
-- =======================
create table if not exists public.email_leads (
  id uuid primary key default uuid_generate_v4(),
  email text not null,
  source text default 'website',
  utm jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_email_leads_email on public.email_leads(email);

-- =======================
-- SONIFICATION PROJECTS
-- =======================
create table if not exists public.sonification_projects (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid references public.profiles(id) on delete set null,
  name text not null,
  vertical text not null,           -- e.g., 'travel'
  theme text not null,              -- e.g., 'flights_from_nyc'
  sub_theme text,                   -- e.g., 'budget_carriers'
  sound_pack text not null,         -- 'Arena Rock' | '8-Bit' | 'Synthwave'
  status text not null default 'ready',  -- 'ready'|'processing'|'done'|'error'
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_projects_vertical on public.sonification_projects(vertical, theme);

-- =======================
-- DEMO DATASETS
-- =======================
create table if not exists public.demo_datasets (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  description text,
  vertical text not null,
  source text default 'openai',
  created_at timestamptz not null default now()
);

-- =======================
-- FLIGHT PRICE DATA (analysis results from OpenAI)
-- =======================
create table if not exists public.flight_price_data (
  id uuid primary key default uuid_generate_v4(),
  origin text not null,            -- airport code (JFK, LGA, etc.)
  origin_region text not null,     -- NYC, Northeast, Caribbean, etc.
  destination text not null,       -- code or city (LAS, LAX, etc.)
  destination_region text not null,
  prompt text not null,
  estimated_price_min numeric,
  estimated_price_max numeric,
  best_booking_window integer,
  routing_strategy text,           -- direct|connecting|hidden-city|multi-city
  novelty_score integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_flight_price_pair on public.flight_price_data(origin, destination);
create index if not exists idx_flight_region on public.flight_price_data(origin_region, destination_region);

-- =======================
-- SONIFICATION INVENTORY (what the frontend lists/plays)
-- =======================
create table if not exists public.sonification_inventory (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references public.sonification_projects(id) on delete cascade,
  brand text,                       -- brand or airline
  route_label text,                 -- human label like "JFK → LAS"
  audio_mp3_url text,
  midi_url text,
  momentum_json jsonb,
  label_summary jsonb,
  duration_sec integer,
  sound_pack text,
  created_at timestamptz not null default now()
);

create index if not exists idx_inventory_project on public.sonification_inventory(project_id);

-- =======================
-- INVENTORY ↔ FLIGHT DATA (traceability)
-- =======================
create table if not exists public.inventory_flight_data (
  inventory_id uuid references public.sonification_inventory(id) on delete cascade,
  flight_id uuid references public.flight_price_data(id) on delete cascade,
  primary key (inventory_id, flight_id)
);

-- =======================
-- OPTIONAL: SIMPLE VIEW for dashboard
-- =======================
create or replace view public.v_visibility_by_region as
select
  destination_region as region,
  count(*) as routes,
  avg((coalesce(estimated_price_min,0)+coalesce(estimated_price_max,0))/2.0) as avg_est_price
from public.flight_price_data
group by 1
order by 1;
