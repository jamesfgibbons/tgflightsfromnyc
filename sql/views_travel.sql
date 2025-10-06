-- Convenience views and optional context table for frontends and summarization

-- Latest price quote per (origin,destination)
create or replace view vw_latest_price_quotes as
select distinct on (origin, destination)
  origin,
  destination,
  window_days,
  price_low_usd,
  price_high_usd,
  typical_airlines,
  cited_websites,
  brands,
  notes,
  created_at
from price_quotes
order by origin, destination, created_at desc;

-- Top routes by origin (sorted by popularity_score desc)
create or replace view vw_routes_top_by_origin as
select origin, destination, destination_name, popularity_score
from travel_routes_nyc
where popularity_score is not null
order by origin, popularity_score desc;

-- Optional: normalized Grok/web context summaries per route
create table if not exists web_context_summaries (
  id uuid primary key default gen_random_uuid(),
  origin text,
  destination text,
  query text,
  summary text,
  citations jsonb,
  created_at timestamptz not null default now()
);

