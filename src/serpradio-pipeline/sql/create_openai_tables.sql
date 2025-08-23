-- Create tables for OpenAI-first Caribbean Kokomo pipeline
-- Run this in Supabase SQL editor

-- 1. Create flight_offers table if it doesn't exist (for compatibility)
CREATE TABLE IF NOT EXISTS flight_offers (
  offer_id text PRIMARY KEY,
  origin_airport text NOT NULL,
  origin_metro text NOT NULL,
  dest_airport text NOT NULL,
  dest_region text NOT NULL,
  dest_country text NOT NULL,
  date_depart date NOT NULL,
  time_window text NOT NULL DEFAULT 'anytime',
  nonstop boolean NOT NULL DEFAULT true,
  stops int NOT NULL DEFAULT 0,
  carrier text NOT NULL,
  carrier_name text NOT NULL,
  fare_brand text,
  baggage_included int NOT NULL DEFAULT 0,
  seller_type text NOT NULL DEFAULT 'online',
  seller_name text NOT NULL DEFAULT 'openai',
  price_usd numeric(10,2) NOT NULL,
  currency text NOT NULL DEFAULT 'USD',
  source text NOT NULL DEFAULT 'openai_generated',
  found_at timestamptz NOT NULL DEFAULT now(),
  raw jsonb
);

CREATE INDEX IF NOT EXISTS idx_offers_day_route ON flight_offers (origin_metro, dest_airport, date_depart);
CREATE INDEX IF NOT EXISTS idx_offers_dest_region ON flight_offers (dest_region, date_depart);

-- 2. Create visibility tables for the pipeline
CREATE TABLE IF NOT EXISTS flight_visibility (
  id bigserial PRIMARY KEY,
  region text NOT NULL,
  origin text NOT NULL,
  destination text NOT NULL,
  date_bucket date NOT NULL,
  price_min numeric,
  price_p25 numeric,
  price_median numeric,
  price_p75 numeric,
  price_max numeric,
  volatility numeric,
  sov_brand jsonb,
  sample_size int DEFAULT 0,
  src varchar(24) DEFAULT 'openai_cache',
  created_at timestamptz DEFAULT now(),
  UNIQUE(region, origin, destination, date_bucket)
);

CREATE TABLE IF NOT EXISTS visibility_enrichment (
  region text NOT NULL,
  origin text NOT NULL,
  destination text NOT NULL,
  date_bucket date NOT NULL,
  brand_seller text,
  seller_type text,
  routing text,
  novelty_score numeric,
  novelty_reasons jsonb,
  kokomo_hint text,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY(region, origin, destination, date_bucket)
);

-- 3. Create momentum_bands table if it doesn't exist
CREATE TABLE IF NOT EXISTS momentum_bands (
  id bigserial PRIMARY KEY,
  region text NOT NULL,
  theme text NOT NULL,
  job_key text NOT NULL,
  momentum jsonb NOT NULL,
  label_summary jsonb NOT NULL,
  duration_sec int NOT NULL,
  sound_pack text NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(region, theme, job_key)
);

-- 4. Create catalogs table
CREATE TABLE IF NOT EXISTS catalogs (
  id bigserial PRIMARY KEY,
  theme text NOT NULL,
  region text NOT NULL,
  catalog_json jsonb NOT NULL,
  storage_url text,
  created_at timestamptz DEFAULT now()
);

-- Grant access if needed
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;