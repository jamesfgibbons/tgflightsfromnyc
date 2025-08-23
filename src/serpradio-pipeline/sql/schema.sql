-- Core tables
create table if not exists flight_offers (
  offer_id text primary key,
  origin_airport text not null,
  origin_metro text not null,
  dest_airport text not null,
  dest_region text not null,
  dest_country text not null,
  date_depart date not null,
  time_window text not null,
  nonstop boolean not null,
  stops int not null default 0,
  carrier text not null,
  carrier_name text not null,
  fare_brand text,
  baggage_included int not null default 0,
  seller_type text not null,
  seller_name text not null,
  price_usd numeric(10,2) not null,
  currency text not null default 'USD',
  source text not null,
  found_at timestamptz not null default now(),
  raw jsonb
);

create index if not exists idx_offers_day_route on flight_offers (origin_metro, dest_airport, date_depart);
create index if not exists idx_offers_dest_region on flight_offers (dest_region, date_depart);

create table if not exists flight_visibility (
  id bigserial primary key,
  region text not null,
  origin text not null,
  destination text not null,
  date_bucket date not null,
  price_min numeric,
  price_p25 numeric,
  price_median numeric,
  price_p75 numeric,
  price_max numeric,
  volatility numeric,
  sov_brand jsonb,
  sample_size int default 0,
  src varchar(24) default 'openai_cache',
  created_at timestamptz default now(),
  unique(region,origin,destination,date_bucket)
);

create table if not exists visibility_enrichment (
  region text not null,
  origin text not null,
  destination text not null,
  date_bucket date not null,
  brand_seller text,
  seller_type text,
  routing text,
  novelty_score numeric,
  novelty_reasons jsonb,
  kokomo_hint text,
  created_at timestamptz default now(),
  primary key(region,origin,destination,date_bucket)
);

create table if not exists momentum_bands (
  id bigserial primary key,
  region text not null,
  theme text not null,
  job_key text not null,
  momentum jsonb not null,
  label_summary jsonb not null,
  duration_sec int not null,
  sound_pack text not null,
  created_at timestamptz default now(),
  unique(region,theme,job_key)
);
