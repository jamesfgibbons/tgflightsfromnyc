-- Ski routes table with regional metadata

create table if not exists travel_routes_ski (
  id uuid primary key default gen_random_uuid(),
  origin text not null,              -- JFK, LGA, EWR
  destination text not null,         -- IATA code
  destination_name text,
  region text,                       -- e.g., Rockies, Wasatch, Sierras, PNW, Northeast, Canada
  subregion text,                    -- e.g., Colorado, Utah, Tahoe, BC, Alberta, Vermont
  country text,                      -- e.g., US, CA
  state_province text,               -- e.g., CO, UT, CA, BC
  popularity_score numeric,
  source text default 'manual',
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_travel_routes_ski_origin_dest 
  on travel_routes_ski (origin, destination);

