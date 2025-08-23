-- Minimal tables for conversational cache + signals
-- Run this in Supabase SQL Editor (project database).

-- Extensions
create extension if not exists pgcrypto;

-- Notes: conversational text + citations
create table if not exists visibility_notes (
  id uuid primary key default gen_random_uuid(),
  origin_metro text not null,
  destination text not null,
  asked_on date not null,
  note_text text not null,
  citations jsonb,
  run_id text not null,
  created_at timestamptz default now()
);

-- Signals: machine-friendly fields extracted from notes
create table if not exists visibility_signals (
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

-- Lightweight read policies (optional; tighten later)
alter table visibility_notes enable row level security;
alter table visibility_signals enable row level security;

-- Allow authenticated reads
do $$ begin
  if not exists (select 1 from pg_policies where tablename='visibility_notes' and policyname='read_notes_authenticated') then
    create policy "read_notes_authenticated" on visibility_notes for select to authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='visibility_signals' and policyname='read_signals_authenticated') then
    create policy "read_signals_authenticated" on visibility_signals for select to authenticated using (true);
  end if;
end $$;
