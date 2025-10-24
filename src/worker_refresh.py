#!/usr/bin/env python3
"""
Price Refresh Worker

Scheduled worker that:
1. Fetches flight prices from configured API (X API or Parallel API)
2. Upserts prices to Supabase price_observation table
3. Refreshes route_baseline_30d materialized view
4. Emits notification events for significant price drops
5. Runs on a 6-hour schedule (4x per day)

Environment Variables:
- PRICE_SOURCE: "xapi" or "parallel" (default: "parallel")
- REFRESH_INTERVAL_HOURS: Hours between refreshes (default: 6)
- NYC_ORIGINS: Comma-separated origin codes (default: "JFK,EWR,LGA")
- TOP_DESTINATIONS: Comma-separated destination codes (default: top 20 US routes)
- SUPABASE_URL: Supabase project URL
- SUPABASE_SERVICE_ROLE: Supabase service role key
- XAPI_KEY or PARALLEL_API_KEY: Price API credentials

Usage:
    # Run once
    python -m src.worker_refresh --once

    # Run continuously on schedule
    python -m src.worker_refresh

    # Custom interval
    REFRESH_INTERVAL_HOURS=3 python -m src.worker_refresh
"""

import os
import sys
import time
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict
import argparse

# Supabase client
from supabase import create_client, Client

# Price fetcher adapters
from src.adapters import XApiFetcher, ParallelFetcher, PriceFetchError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/worker_refresh.log') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


# Configuration
PRICE_SOURCE = os.getenv("PRICE_SOURCE", "parallel")
REFRESH_INTERVAL_HOURS = int(os.getenv("REFRESH_INTERVAL_HOURS", "6"))
NYC_ORIGINS = os.getenv("NYC_ORIGINS", "JFK,EWR,LGA").split(",")

# Top 20 destinations from NYC
DEFAULT_DESTINATIONS = "MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL"
TOP_DESTINATIONS = os.getenv("TOP_DESTINATIONS", DEFAULT_DESTINATIONS).split(",")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
    logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE are required")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
logger.info(f"Connected to Supabase: {SUPABASE_URL}")


def get_price_fetcher():
    """
    Get the appropriate price fetcher based on PRICE_SOURCE.

    Returns:
        PriceFetcher instance
    """
    if PRICE_SOURCE == "xapi":
        logger.info("Using X API fetcher")
        return XApiFetcher()
    elif PRICE_SOURCE == "parallel":
        logger.info("Using Parallel API fetcher")
        return ParallelFetcher()
    else:
        raise ValueError(f"Unknown PRICE_SOURCE: {PRICE_SOURCE}. Must be 'xapi' or 'parallel'")


def get_date_windows(months_ahead: int = 6) -> List[Dict[str, date]]:
    """
    Generate monthly date windows for the next N months.

    Args:
        months_ahead: Number of months to look ahead

    Returns:
        List of date windows with 'start' and 'end'
    """
    windows = []
    today = date.today()

    for month_offset in range(months_ahead):
        # Start at beginning of month
        if month_offset == 0:
            start = today
        else:
            start = today + timedelta(days=30 * month_offset)
            start = start.replace(day=1)

        # End at end of month
        end = start + timedelta(days=30)

        windows.append({
            "start": start,
            "end": end
        })

    logger.info(f"Generated {len(windows)} date windows covering next {months_ahead} months")
    return windows


def upsert_prices(prices: List[Dict]) -> int:
    """
    Upsert prices to Supabase price_observation table.

    Uses idempotent upsert on (origin, dest, cabin, depart_date, source, observed_at)
    to avoid duplicates.

    Args:
        prices: List of price dictionaries

    Returns:
        Number of rows upserted
    """
    if not prices:
        logger.warning("No prices to upsert")
        return 0

    # Convert date objects to strings for JSON
    for price in prices:
        if isinstance(price.get("depart_date"), date):
            price["depart_date"] = price["depart_date"].isoformat()
        if isinstance(price.get("observed_at"), datetime):
            price["observed_at"] = price["observed_at"].isoformat()

    try:
        # Upsert to price_observation table
        # Note: Supabase upsert requires unique constraint on conflict columns
        result = supabase.table("price_observation").upsert(
            prices,
            on_conflict="origin,dest,cabin,depart_date,source,observed_at"
        ).execute()

        count = len(result.data) if result.data else 0
        logger.info(f"Upserted {count} price observations")
        return count

    except Exception as e:
        logger.error(f"Failed to upsert prices: {e}")
        raise


def refresh_materialized_views():
    """
    Refresh materialized views:
    - route_baseline_30d (rolling 30-day percentiles)

    Note: REFRESH MATERIALIZED VIEW CONCURRENTLY requires unique index
    """
    try:
        logger.info("Refreshing route_baseline_30d materialized view...")

        # Execute refresh via Supabase RPC or direct SQL
        # Option 1: Use RPC function (recommended)
        supabase.rpc("refresh_baselines").execute()

        # Option 2: Execute raw SQL (if RPC not available)
        # supabase.postgrest.rpc("query", {
        #     "query": "REFRESH MATERIALIZED VIEW CONCURRENTLY route_baseline_30d"
        # }).execute()

        logger.info("Materialized view refreshed successfully")

    except Exception as e:
        # Try non-concurrent refresh as fallback
        logger.warning(f"Concurrent refresh failed: {e}. Trying non-concurrent...")

        try:
            # Non-concurrent refresh (locks table)
            supabase.rpc("refresh_baselines_nonconcurrent").execute()
            logger.info("Materialized view refreshed (non-concurrent)")

        except Exception as e2:
            logger.error(f"Failed to refresh materialized views: {e2}")
            # Don't raise - continue with next cycle


def emit_notifications():
    """
    Emit notification events for significant price drops.

    Checks for prices that dropped below P25 baseline and emits
    notification_event records.
    """
    try:
        logger.info("Checking for price drop notifications...")

        # Call Supabase RPC function to detect and emit notifications
        result = supabase.rpc("detect_price_drops").execute()

        count = len(result.data) if result.data else 0
        logger.info(f"Emitted {count} price drop notifications")

    except Exception as e:
        logger.warning(f"Failed to emit notifications: {e}")
        # Don't raise - notifications are non-critical


def run_refresh_cycle():
    """
    Run a single price refresh cycle.

    Steps:
    1. Fetch prices from API
    2. Upsert to database
    3. Refresh materialized views
    4. Emit notifications

    Returns:
        True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("Starting price refresh cycle")
    logger.info("=" * 60)

    try:
        # 1. Get price fetcher
        fetcher = get_price_fetcher()

        # 2. Generate date windows
        windows = get_date_windows(months_ahead=6)

        # 3. Fetch prices
        logger.info(
            f"Fetching prices for {len(NYC_ORIGINS)} origins × "
            f"{len(TOP_DESTINATIONS)} destinations × {len(windows)} windows"
        )

        prices = fetcher.fetch_with_retry(
            origins=NYC_ORIGINS,
            destinations=TOP_DESTINATIONS,
            windows=windows,
            cabin="economy",
            max_retries=3
        )

        logger.info(f"Fetched {len(prices)} price observations")

        if not prices:
            logger.warning("No prices fetched. Skipping upsert.")
            return False

        # 4. Upsert to database
        count = upsert_prices(prices)
        logger.info(f"Upserted {count} rows to price_observation table")

        # 5. Refresh materialized views
        refresh_materialized_views()

        # 6. Emit notifications
        emit_notifications()

        logger.info("Price refresh cycle completed successfully")
        return True

    except PriceFetchError as e:
        logger.error(f"Price fetch failed: {e}")
        return False

    except Exception as e:
        logger.error(f"Refresh cycle failed: {e}", exc_info=True)
        return False


def run_worker(run_once: bool = False):
    """
    Run the price refresh worker.

    Args:
        run_once: If True, run a single cycle and exit.
                  If False, run continuously on schedule.
    """
    logger.info(f"Starting price refresh worker (PRICE_SOURCE={PRICE_SOURCE})")
    logger.info(f"Origins: {NYC_ORIGINS}")
    logger.info(f"Destinations: {TOP_DESTINATIONS}")
    logger.info(f"Refresh interval: {REFRESH_INTERVAL_HOURS} hours")

    if run_once:
        logger.info("Running in one-shot mode")
        success = run_refresh_cycle()
        sys.exit(0 if success else 1)

    # Continuous mode
    logger.info("Running in continuous mode. Press Ctrl+C to stop.")

    cycle_count = 0
    while True:
        cycle_count += 1
        logger.info(f"\nCycle #{cycle_count}")

        try:
            run_refresh_cycle()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down...")
            break

        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)

        # Sleep until next cycle
        sleep_seconds = REFRESH_INTERVAL_HOURS * 3600
        next_run = datetime.now() + timedelta(seconds=sleep_seconds)

        logger.info(f"Sleeping for {REFRESH_INTERVAL_HOURS} hours. Next run at {next_run}")
        time.sleep(sleep_seconds)

    logger.info("Worker stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Price refresh worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing or cron jobs)"
    )
    args = parser.parse_args()

    run_worker(run_once=args.once)
