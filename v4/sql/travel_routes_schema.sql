create table if not exists travel_routes_nyc (
  id uuid primary key default gen_random_uuid(),
  origin text not null,
  destination text not null,
  destination_name text,
  popularity_score numeric,
  source text default 'manual',
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_travel_routes_nyc_origin_dest on travel_routes_nyc (origin, destination);
