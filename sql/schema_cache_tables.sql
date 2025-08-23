-- ========== CORE PRICES ==========
create table if not exists flight_offers (
  offer_id text primary key,
  origin_airport text not null,
  origin_metro text not null,          -- NYC, BOS, LAX…
  dest_airport text not null,
  dest_region text not null,           -- Caribbean, West Coast…
  dest_country text not null,
  date_depart date not null,
  time_window text not null,           -- red_eye|am|pm
  nonstop boolean not null,
  stops int not null default 0,
  carrier text not null,               -- IATA, e.g., B6
  carrier_name text not null,
  fare_brand text,
  baggage_included int not null default 0,
  seller_type text not null,           -- airline|OTA|meta
  seller_name text not null,
  price_usd numeric(10,2) not null,
  currency text not null default 'USD',
  source text not null,                -- kiwi|amadeus|skyscanner
  found_at timestamptz not null default now(),
  raw jsonb
);

create index if not exists idx_offers_day_route on flight_offers (origin_metro, dest_airport, date_depart);
create index if not exists idx_offers_dest_region on flight_offers (dest_region, date_depart);
create index if not exists idx_offers_carrier on flight_offers (carrier);
create index if not exists idx_offers_seller on flight_offers (seller_type, seller_name);

-- Daily route statistics (Caribbean-first but general)
create table if not exists flight_visibility (
  id bigserial primary key,
  region text not null,                -- 'caribbean', 'west_coast', …
  origin text not null,                -- JFK,LGA,EWR,…
  destination text not null,           -- SJU,AUA,MBJ,…
  date_bucket date not null,
  price_min numeric,
  price_p25 numeric,
  price_median numeric,
  price_p75 numeric,
  price_max numeric,
  volatility numeric,                  -- stddev or normalized IQR
  sov_brand jsonb,                     -- {"JetBlue":0.32,"Delta":0.28,...}
  sample_size int default 0,
  src varchar(24) default 'openai_cache',
  created_at timestamptz default now()
);

-- Precomputed sonification (what your player reads)
create table if not exists momentum_bands (
  id bigserial primary key,
  region text not null,
  theme text not null,                 -- budget_carriers|legacy_airlines|red_eye_deals|caribbean_kokomo
  job_key text not null,
  momentum jsonb not null,             -- [{t0,t1,label,score},...]
  label_summary jsonb not null,        -- {positive_count,negative_count,neutral_count}
  duration_sec int not null,
  sound_pack text not null,            -- 8-Bit|Arena Rock|Synthwave|Tropical Pop
  created_at timestamptz default now()
);

-- OpenAI job + cache
create table if not exists cache_jobs (
  id bigserial primary key,
  prompt_key text not null,
  prompt_hash text not null unique,
  model text not null,
  tokens_in int default 0,
  tokens_out int default 0,
  cost_usd numeric default 0,
  status text not null check (status in ('queued','succeeded','failed')),
  payload jsonb,
  ttl_hours int default 168,
  created_at timestamptz default now(),
  refreshed_at timestamptz
);

-- ======== VIEWS (rock-bottom & volatility) =========
drop materialized view if exists v_daily_min_by_airport;
create materialized view v_daily_min_by_airport as
select
  origin_metro, origin_airport, dest_airport, date_depart,
  min(price_usd) as min_price_usd,
  (array_agg(offer_id order by price_usd asc))[1] as offer_id
from flight_offers
group by 1,2,3,4;

drop materialized view if exists v_daily_min_by_metro;
create materialized view v_daily_min_by_metro as
select
  origin_metro, dest_airport, date_depart,
  min(min_price_usd) as min_price_usd
from v_daily_min_by_airport
group by 1,2,3;

drop materialized view if exists v_volatility_7d;
create materialized view v_volatility_7d as
with series as (
  select distinct origin_metro, dest_airport from flight_offers
),
days as (
  select generate_series(min(date_depart), max(date_depart), interval '1 day')::date as d
  from flight_offers
)
select
  s.origin_metro, s.dest_airport, d.d as date_depart,
  stddev_samp(m.min_price_usd) over (
    partition by s.origin_metro, s.dest_airport
    order by d.d
    rows between 3 preceding and 3 following
  ) as vol_7d
from series s
cross join days d
left join v_daily_min_by_metro m
  on m.origin_metro = s.origin_metro
 and m.dest_airport = s.dest_airport
 and m.date_depart = d.d;

drop materialized view if exists v_brand_exposure;
create materialized view v_brand_exposure as
with winners as (
  select f.origin_metro, f.dest_airport, f.date_depart, f.seller_name, f.seller_type, f.carrier, f.carrier_name
  from flight_offers f
  join v_daily_min_by_metro m
    on m.origin_metro = f.origin_metro
   and m.dest_airport = f.dest_airport
   and m.date_depart = f.date_depart
   and f.price_usd = m.min_price_usd
)
select origin_metro, dest_airport, date_trunc('week', date_depart)::date as week,
       seller_type, seller_name, carrier, carrier_name, count(*) as wins
from winners
group by 1,2,3,4,5,6,7;

-- Helpful Caribbean view
create or replace view vw_caribbean_visibility as
select *
from flight_visibility
where lower(region) = 'caribbean';

-- (Optional) Public read for the view (keep raw tables protected)
-- alter publication supabase_realtime add table vw_caribbean_visibility;