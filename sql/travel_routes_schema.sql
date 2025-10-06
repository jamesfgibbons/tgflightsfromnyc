-- Top NYC Routes schema (Supabase)
-- Stores top routes by popularity across JFK/LGA/EWR for training/caching

create table if not exists travel_routes_nyc (
  id uuid primary key default gen_random_uuid(),
  origin text not null,           -- JFK, LGA, EWR
  destination text not null,      -- IATA code (e.g., DEN, SLC)
  destination_name text,          -- Friendly name (e.g., Denver)
  popularity_score numeric,       -- Arbitrary score (search volume, pax, composite)
  source text default 'manual',   -- e.g., 'manual', 'seo_volume', 'pax', 'blend'
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_travel_routes_nyc_origin_dest 
  on travel_routes_nyc (origin, destination);

