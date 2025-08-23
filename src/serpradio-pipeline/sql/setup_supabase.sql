-- =========================
-- BASIC TABLES (minimal)
-- =========================

-- 1) Raw offers from OpenAI (simple & stable for experiments)
create table if not exists public.flight_price_data (
  id            text primary key,      -- deterministic hash you generate client-side
  origin        text not null,         -- e.g., JFK, LGA, EWR (IATA)
  destination   text not null,         -- e.g., SJU, AUA (IATA)
  departure_date date not null,        -- YYYY-MM-DD
  airline       text not null,         -- canonical brand, e.g., "JetBlue"
  price         numeric not null,      -- USD dollars (e.g., 78.00)
  currency      text not null default 'USD',
  direct_flight boolean not null default true,
  data_source   text not null default 'openai',
  created_at    timestamptz not null default now()
);

-- 2) Optional enrichment table (LLM adds detail here)
create table if not exists public.offers_enriched (
  id              text primary key references public.flight_price_data(id) on delete cascade,
  seller_name     text,
  seller_type     text check (seller_type in ('airline','OTA','meta','unknown')) default 'unknown',
  routing         text check (routing in ('direct','connecting','red_eye','positioning','unknown')) default 'unknown',
  novelty_score   numeric check (novelty_score >= 0 and novelty_score <= 10),
  novelty_reasons text[],
  kokomo_hint     text,           -- e.g., 'steel_drums','marimba','wind_chimes'
  enriched_at     timestamptz not null default now()
);

-- 3) Momentum bands the player consumes (already wired in your FE)
create table if not exists public.momentum_bands (
  id            bigserial primary key,
  region        text not null default 'caribbean',
  theme         text not null,   -- 'budget_carriers','legacy_airlines','red_eye_deals','caribbean_kokomo'
  job_key       text not null,   -- e.g., 'nyc-sju-2025-09-08'
  momentum      jsonb not null,  -- [{t0,t1,label,score}, ...]
  label_summary jsonb not null,  -- { positive_count, negative_count, neutral_count }
  duration_sec  int not null default 45,
  sound_pack    text not null,   -- '8-Bit','Arena Rock','Synthwave','Tropical Pop'
  created_at    timestamptz not null default now()
);

-- =========================
-- CONVERSATIONAL CACHE TABLES
-- =========================

-- Extensions
create extension if not exists pgcrypto;

-- 4) Notes: conversational text + citations
create table if not exists public.visibility_notes (
  id uuid primary key default gen_random_uuid(),
  origin_metro text not null,
  destination text not null,
  asked_on date not null,
  note_text text not null,
  citations jsonb,
  run_id text not null,
  created_at timestamptz default now()
);

-- 5) Signals: machine-friendly fields extracted from notes
create table if not exists public.visibility_signals (
  id uuid primary key default gen_random_uuid(),
  origin_metro text not null,
  destination text not null,
  asked_on date not null,
  price_low_est numeric,
  price_typical_est numeric,
  price_high_est numeric,
  red_eye_share_est numeric,
  carriers jsonb,
  sellers jsonb,
  novelty_notes jsonb,
  confidence numeric,
  run_id text not null,
  created_at timestamptz default now()
);

-- =========================
-- RLS + SIMPLE PUBLIC READ
-- =========================
alter table public.flight_price_data enable row level security;
alter table public.offers_enriched   enable row level security;
alter table public.momentum_bands    enable row level security;
alter table public.visibility_notes  enable row level security;
alter table public.visibility_signals enable row level security;

-- Public read policies (Lovable can read with anon key)
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='flight_price_data' and policyname='Public read flight_price_data'
  ) then
    create policy "Public read flight_price_data"
      on public.flight_price_data for select
      to anon
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='offers_enriched' and policyname='Public read offers_enriched'
  ) then
    create policy "Public read offers_enriched"
      on public.offers_enriched for select
      to anon
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='momentum_bands' and policyname='Public read momentum_bands'
  ) then
    create policy "Public read momentum_bands"
      on public.momentum_bands for select
      to anon
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='visibility_notes' and policyname='Public read visibility_notes'
  ) then
    create policy "Public read visibility_notes"
      on public.visibility_notes for select
      to anon
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='visibility_signals' and policyname='Public read visibility_signals'
  ) then
    create policy "Public read visibility_signals"
      on public.visibility_signals for select
      to anon
      using (true);
  end if;
end$$;

-- No insert policies needed for writes from your service role (it bypasses RLS).
-- If you want authenticated client inserts later, we can add insert policies then.

-- =========================
-- STORAGE BUCKET
-- =========================
-- Create a public bucket for audio & catalogs
insert into storage.buckets (id, name, public)
values ('serpradio-public','serpradio-public', true)
on conflict (id) do update set public = true;

-- Public read of objects in that bucket
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname='storage' and tablename='objects' and policyname='Public read on serpradio-public'
  ) then
    create policy "Public read on serpradio-public"
      on storage.objects for select
      to anon
      using (bucket_id = 'serpradio-public');
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='storage' and tablename='objects' and policyname='Auth read on serpradio-public'
  ) then
    create policy "Auth read on serpradio-public"
      on storage.objects for select
      to authenticated
      using (bucket_id = 'serpradio-public');
  end if;

  -- Optional: allow authenticated uploads (clients). Service role already bypasses RLS.
  if not exists (
    select 1 from pg_policies
    where schemaname='storage' and tablename='objects' and policyname='Auth write on serpradio-public'
  ) then
    create policy "Auth write on serpradio-public"
      on storage.objects for insert
      to authenticated
      with check (bucket_id = 'serpradio-public');
  end if;
end$$;