-- Price quotes parsed from OpenAI results
create table if not exists price_quotes (
  id uuid primary key default gen_random_uuid(),
  origin text not null,
  destination text not null,
  window_days integer,
  price_low_usd numeric,
  price_high_usd numeric,
  typical_airlines text[],
  cited_websites text[],
  brands text[],
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_price_quotes_route on price_quotes (origin, destination);

