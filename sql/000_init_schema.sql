-- SERP Radio consolidated Supabase schema
-- Run once on a fresh project. Uses IF NOT EXISTS guards for idempotency.

-- Extensions ---------------------------------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- API Logging --------------------------------------------------------------
\i sql/api_logging_schema.sql

-- Prompt Engine ------------------------------------------------------------
\i sql/prompt_engine_schema.sql

-- VibeNet Runs & Catalog ---------------------------------------------------
\i sql/vibenet_schema.sql

-- Board Feed / Webz.io events ---------------------------------------------
\i sql/board_feed_schema.sql

-- Travel data tables -------------------------------------------------------
\i sql/travel_routes_schema.sql
\i sql/travel_routes_ski.sql
\i sql/price_quotes.sql

-- Optional cache helpers ---------------------------------------------------
\i sql/schema_cache_tables.sql

-- Best-Time to Book --------------------------------------------------------
\i sql/best_time_schema.sql
