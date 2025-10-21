-- =====================================================
-- Baseline Deal Awareness + "Where & When" Flow
-- =====================================================
-- Run after: sql/000_init_schema.sql, sql/best_time_schema.sql
--
-- This migration adds:
-- 1. Rolling 30-day baseline price distributions per route/month
-- 2. Deal evaluator function (BUY/TRACK/WAIT logic)
-- 3. Helper views for current prices
-- 4. Best-time window detection
--
-- Purpose: Enable "Is this a good deal?" and "When to book?" queries
-- =====================================================

-- 1) Normalize depart month for grouping
-- Aggregates price observations by route + departure month
CREATE OR REPLACE VIEW route_depart_month AS
SELECT
  origin,
  dest,
  cabin,
  DATE_TRUNC('month', depart_date)::DATE AS depart_month,
  price_usd,
  observed_at
FROM price_observation;

COMMENT ON VIEW route_depart_month IS
  'Normalizes price observations to month-level for baseline calculations';

-- 2) Rolling 30-day distribution (p25/50/75) for each (route, month, cabin)
-- Materialized for performance; refresh every 6 hours via cron
CREATE MATERIALIZED VIEW IF NOT EXISTS route_baseline_30d AS
SELECT
  origin,
  dest,
  cabin,
  depart_month,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_usd)::NUMERIC(10,2) AS p25_30d,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price_usd)::NUMERIC(10,2) AS p50_30d,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_usd)::NUMERIC(10,2) AS p75_30d,
  COUNT(*) AS n_samples,
  MAX(observed_at) AS last_updated
FROM route_depart_month
WHERE observed_at >= NOW() - INTERVAL '30 days'
GROUP BY origin, dest, cabin, depart_month;

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_baseline30_route
  ON route_baseline_30d(origin, dest, cabin, depart_month);

CREATE INDEX IF NOT EXISTS idx_baseline30_updated
  ON route_baseline_30d(last_updated DESC);

COMMENT ON MATERIALIZED VIEW route_baseline_30d IS
  'Rolling 30-day price percentiles (P25/P50/P75) per route/month. Refresh every 6h.';

-- 3) Helper: current cheapest price for each (route, month, cabin)
CREATE OR REPLACE VIEW route_current_low AS
SELECT
  origin,
  dest,
  cabin,
  DATE_TRUNC('month', depart_date)::DATE AS depart_month,
  MIN(price_usd)::NUMERIC(10,2) AS current_low,
  MAX(observed_at) AS last_seen
FROM price_observation
WHERE depart_date >= DATE_TRUNC('month', NOW())
  AND depart_date < DATE_TRUNC('month', NOW()) + INTERVAL '12 months'
GROUP BY origin, dest, cabin, depart_month;

COMMENT ON VIEW route_current_low IS
  'Current cheapest price for each route/month combo (next 12 months)';

-- 4) Helper function: next occurrence of a month number (1-12)
-- E.g., if today is Oct 2025 and month=3, returns 2026-03-01
CREATE OR REPLACE FUNCTION next_depart_month(month_num INT)
RETURNS DATE
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT DATE_TRUNC('month',
    MAKE_DATE(
      CASE
        WHEN EXTRACT(MONTH FROM NOW())::INT <= month_num
          THEN EXTRACT(YEAR FROM NOW())::INT
        ELSE (EXTRACT(YEAR FROM NOW())::INT + 1)
      END,
      month_num,
      1
    )
  )::DATE;
$$;

COMMENT ON FUNCTION next_depart_month IS
  'Returns the next future occurrence of a given month number (1-12)';

-- 5) Deal evaluator function
-- Compares current price to baseline + sweet-spot window
-- Returns BUY/TRACK/WAIT recommendation with confidence and rationale
CREATE OR REPLACE FUNCTION evaluate_deal(
  p_origin TEXT,
  p_dest TEXT,
  p_month INT,
  p_cabin TEXT DEFAULT 'economy'
)
RETURNS JSONB
LANGUAGE PLPGSQL
SECURITY DEFINER
AS $$
DECLARE
  v_month DATE := next_depart_month(p_month);
  v_base RECORD;
  v_now RECORD;
  v_delta_pct NUMERIC;
  v_deal_score INT;
  v_reco TEXT;
  v_conf INT := 70; -- default confidence
  v_ss_min INT := NULL;
  v_ss_max INT := NULL;
  v_rationale TEXT;
BEGIN
  -- Normalize inputs
  p_origin := UPPER(TRIM(p_origin));
  p_dest := UPPER(TRIM(p_dest));
  p_cabin := LOWER(TRIM(p_cabin));

  -- Get baseline (30d rolling) for the requested month
  SELECT * INTO v_base
  FROM route_baseline_30d
  WHERE origin = p_origin
    AND dest = p_dest
    AND cabin = p_cabin
    AND depart_month = v_month;

  -- Get current cheapest for that month
  SELECT * INTO v_now
  FROM route_current_low
  WHERE origin = p_origin
    AND dest = p_dest
    AND cabin = p_cabin
    AND depart_month = v_month;

  -- Check if we have sufficient data
  IF v_base IS NULL OR v_now IS NULL THEN
    RETURN JSONB_BUILD_OBJECT(
      'has_data', FALSE,
      'message', FORMAT('No baseline or current price for %s→%s in %s (month %s)',
        p_origin, p_dest, TO_CHAR(v_month, 'Mon YYYY'), p_month),
      'origin', p_origin,
      'dest', p_dest,
      'month', p_month,
      'cabin', p_cabin
    );
  END IF;

  -- Check for insufficient samples
  IF v_base.n_samples < 10 THEN
    RETURN JSONB_BUILD_OBJECT(
      'has_data', FALSE,
      'message', FORMAT('Insufficient data: only %s samples in last 30 days', v_base.n_samples),
      'origin', p_origin,
      'dest', p_dest,
      'month', p_month,
      'cabin', p_cabin
    );
  END IF;

  -- Delta vs rolling median (P50)
  v_delta_pct := ROUND(
    ((v_now.current_low - v_base.p50_30d) / v_base.p50_30d) * 100.0,
    1
  );

  -- Deal score: map delta vs P50/P25 bands into 0-100 scale
  -- <= P25 = excellent (85-95)
  -- <= P50 = good (65-75)
  -- <= P75 = fair (40-50)
  -- > P75 = poor (10-25)
  v_deal_score := GREATEST(0, LEAST(100,
    CASE
      WHEN v_now.current_low <= v_base.p25_30d THEN 90
      WHEN v_now.current_low <= v_base.p50_30d THEN 70
      WHEN v_now.current_low <= v_base.p75_30d THEN 45
      ELSE 20
    END
  ));

  -- Sweet-spot window from lead_time_curves
  -- Find the contiguous lead-time band where q50 is within 5% of its minimum
  SELECT MIN(lead_days), MAX(lead_days)
  INTO v_ss_min, v_ss_max
  FROM (
    SELECT
      lead_days,
      q50,
      MIN(q50) OVER () AS q50_min,
      (q50 <= MIN(q50) OVER () * 1.05) AS in_band
    FROM lead_time_curves
    WHERE origin = p_origin
      AND dest = p_dest
      AND cabin = p_cabin
      AND depart_month = v_month
  ) t
  WHERE in_band IS TRUE;

  -- Recommendation logic with rationale
  IF v_now.current_low <= v_base.p25_30d THEN
    -- Excellent deal: below 25th percentile
    v_reco := 'BUY';
    v_conf := 85;
    v_rationale := FORMAT('Price is %.1f%% below median and in the lowest 25%% of recent prices',
      ABS(v_delta_pct));

  ELSIF v_ss_min IS NOT NULL AND v_now.current_low <= v_base.p50_30d THEN
    -- Good deal: inside sweet-spot window and near/below median
    v_reco := 'BUY';
    v_conf := 80;
    v_rationale := FORMAT('In optimal booking window (%s-%s days out) and %.1f%% vs median',
      v_ss_min, v_ss_max, v_delta_pct);

  ELSIF v_now.current_low <= v_base.p50_30d THEN
    -- Decent: below median but not in sweet-spot
    v_reco := 'TRACK';
    v_conf := 70;
    v_rationale := FORMAT('Price is %.1f%% below median but may improve',
      ABS(v_delta_pct));

  ELSIF v_deal_score >= 50 THEN
    -- Fair: near median
    v_reco := 'TRACK';
    v_conf := 65;
    v_rationale := 'Price is near typical levels; monitor for drops';

  ELSE
    -- Poor: above 75th percentile
    v_reco := 'WAIT';
    v_conf := 70;
    v_rationale := FORMAT('Price is %.1f%% above median and in the highest 25%% recently',
      v_delta_pct);
  END IF;

  -- Return complete evaluation
  RETURN JSONB_BUILD_OBJECT(
    'has_data', TRUE,
    'origin', p_origin,
    'dest', p_dest,
    'month', p_month,
    'cabin', p_cabin,
    'depart_month', v_month,
    'current_price', v_now.current_low,
    'baseline', JSONB_BUILD_OBJECT(
      'p25', v_base.p25_30d,
      'p50', v_base.p50_30d,
      'p75', v_base.p75_30d,
      'samples', v_base.n_samples,
      'last_updated', v_base.last_updated
    ),
    'delta_pct', v_delta_pct,
    'deal_score', v_deal_score,
    'sweet_spot', CASE
      WHEN v_ss_min IS NOT NULL
        THEN JSONB_BUILD_OBJECT('min_days', v_ss_min, 'max_days', v_ss_max)
      ELSE NULL
    END,
    'recommendation', v_reco,
    'confidence', v_conf,
    'rationale', v_rationale,
    'last_seen', v_now.last_seen
  );
END;
$$;

COMMENT ON FUNCTION evaluate_deal IS
  'Evaluates deal quality and best-time recommendation for a route/month. Returns BUY/TRACK/WAIT with confidence.';

-- Grant permissions for PostgREST (Supabase RPC)
GRANT EXECUTE ON FUNCTION evaluate_deal(TEXT, TEXT, INT, TEXT)
  TO anon, authenticated, service_role;

-- 6) Optional: pg_cron job to refresh baselines every 6 hours
-- Uncomment if pg_cron extension is available:
/*
SELECT cron.schedule(
  'refresh-baselines',
  '0 */6 * * *',
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;$$
);
*/

-- Manual refresh command (run as needed):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d;

-- =====================================================
-- Migration complete
-- =====================================================

-- Verify installation:
-- SELECT evaluate_deal('JFK', 'MIA', 3, 'economy');
