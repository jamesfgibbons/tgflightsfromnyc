-- =====================================================
-- Refresh Helper Functions
-- =====================================================
-- Run after: sql/020_deal_awareness.sql
--
-- This migration adds helper functions for the worker refresh system:
-- 1. refresh_baselines() - Refresh materialized views (concurrent)
-- 2. refresh_baselines_nonconcurrent() - Fallback non-concurrent refresh
-- 3. detect_price_drops() - Emit notifications for significant price drops
--
-- These functions are called by src/worker_refresh.py
-- =====================================================

-- 1) Concurrent refresh of route_baseline_30d
-- Requires unique index on materialized view (already created in 020_deal_awareness.sql)
CREATE OR REPLACE FUNCTION refresh_baselines()
RETURNS VOID
LANGUAGE PLPGSQL
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;
END;
$$;

COMMENT ON FUNCTION refresh_baselines IS
  'Refresh route_baseline_30d materialized view (concurrent, non-blocking)';

-- 2) Non-concurrent refresh (fallback if concurrent fails)
CREATE OR REPLACE FUNCTION refresh_baselines_nonconcurrent()
RETURNS VOID
LANGUAGE PLPGSQL
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW route_baseline_30d;
END;
$$;

COMMENT ON FUNCTION refresh_baselines_nonconcurrent IS
  'Refresh route_baseline_30d materialized view (non-concurrent, locks table)';

-- 3) Detect and emit price drop notifications
-- Finds routes where current price dropped below P25 baseline
-- Inserts notification_event records for the board feed
CREATE OR REPLACE FUNCTION detect_price_drops()
RETURNS TABLE(
  origin TEXT,
  dest TEXT,
  cabin TEXT,
  depart_month DATE,
  old_price NUMERIC,
  new_price NUMERIC,
  drop_pct NUMERIC
)
LANGUAGE PLPGSQL
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  WITH price_drops AS (
    SELECT
      rcl.origin,
      rcl.dest,
      rcl.cabin,
      rcl.depart_month,
      rb.p25_30d AS baseline_p25,
      rcl.current_low AS new_price,
      rb.p50_30d AS baseline_median,
      ROUND(
        ((rcl.current_low - rb.p25_30d) / rb.p25_30d) * 100.0,
        1
      ) AS drop_pct
    FROM route_current_low rcl
    INNER JOIN route_baseline_30d rb
      ON rcl.origin = rb.origin
      AND rcl.dest = rb.dest
      AND rcl.cabin = rb.cabin
      AND rcl.depart_month = rb.depart_month
    WHERE
      -- Price dropped below P25 (excellent deal)
      rcl.current_low < rb.p25_30d
      -- Only consider recent observations (within last hour)
      AND rcl.last_seen >= NOW() - INTERVAL '1 hour'
      -- Ensure baseline is fresh
      AND rb.last_updated >= NOW() - INTERVAL '12 hours'
  ),
  inserted AS (
    INSERT INTO notification_event (
      origin,
      dest,
      cabin,
      depart_month,
      event_type,
      delta_pct,
      price_usd,
      baseline_p50,
      created_at
    )
    SELECT
      pd.origin,
      pd.dest,
      pd.cabin,
      pd.depart_month,
      'price_drop' AS event_type,
      pd.drop_pct AS delta_pct,
      pd.new_price AS price_usd,
      pd.baseline_median AS baseline_p50,
      NOW() AS created_at
    FROM price_drops pd
    -- Avoid duplicate notifications (check if we already emitted for this route/month today)
    WHERE NOT EXISTS (
      SELECT 1
      FROM notification_event ne
      WHERE ne.origin = pd.origin
        AND ne.dest = pd.dest
        AND ne.cabin = pd.cabin
        AND ne.depart_month = pd.depart_month
        AND ne.event_type = 'price_drop'
        AND ne.created_at >= NOW() - INTERVAL '24 hours'
    )
    RETURNING
      notification_event.origin,
      notification_event.dest,
      notification_event.cabin,
      notification_event.depart_month,
      notification_event.price_usd,
      notification_event.delta_pct
  )
  SELECT
    i.origin,
    i.dest,
    i.cabin,
    i.depart_month,
    NULL::NUMERIC AS old_price,  -- Not tracked, use baseline instead
    i.price_usd AS new_price,
    i.delta_pct AS drop_pct
  FROM inserted i;
END;
$$;

COMMENT ON FUNCTION detect_price_drops IS
  'Detect significant price drops and emit notification events. Returns list of new notifications.';

-- Grant permissions for worker (uses service_role key)
GRANT EXECUTE ON FUNCTION refresh_baselines() TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION refresh_baselines_nonconcurrent() TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION detect_price_drops() TO anon, authenticated, service_role;

-- =====================================================
-- Migration complete
-- =====================================================

-- Verify installation:
-- SELECT refresh_baselines();
-- SELECT * FROM detect_price_drops();
