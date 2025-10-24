#!/usr/bin/env python3
"""
Seed Sample Flight Prices to Supabase

This script generates realistic sample flight price data for testing the
deal awareness system without waiting for the first API refresh.

It creates:
- price_observation records for popular NYC routes
- Realistic price distributions (economy cabin)
- 30 days of historical data + 90 days of future prices
- Multiple observations per route to enable baseline calculation

Usage:
    export SUPABASE_URL=https://your-project.supabase.co
    export SUPABASE_SERVICE_ROLE=your-service-role-key
    python scripts/seed_sample_prices.py

Options:
    --routes N       Number of routes to seed (default: 10)
    --days-back N    Days of historical data (default: 30)
    --days-forward N Days of future data (default: 90)
    --dry-run        Print sample data without inserting
"""

import os
import sys
import argparse
import random
from datetime import date, datetime, timedelta
from typing import List, Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ ERROR: supabase-py not installed")
    print("   Install with: pip install supabase")
    sys.exit(1)


# Popular NYC routes with realistic base prices (economy)
POPULAR_ROUTES = [
    ("JFK", "MIA", 180, 350),   # Miami
    ("JFK", "LAX", 250, 500),   # Los Angeles
    ("JFK", "SFO", 280, 550),   # San Francisco
    ("EWR", "ORD", 150, 300),   # Chicago
    ("LGA", "ATL", 140, 280),   # Atlanta
    ("JFK", "DEN", 200, 400),   # Denver
    ("EWR", "LAS", 180, 380),   # Las Vegas
    ("JFK", "SEA", 300, 600),   # Seattle
    ("LGA", "DCA", 120, 250),   # Washington DC
    ("EWR", "MCO", 160, 320),   # Orlando
    ("JFK", "PHX", 220, 440),   # Phoenix
    ("LGA", "BOS", 80, 180),    # Boston
    ("EWR", "SAN", 260, 520),   # San Diego
    ("JFK", "FLL", 170, 340),   # Fort Lauderdale
    ("LGA", "CLT", 130, 260),   # Charlotte
]


def generate_price_observations(
    routes: List[tuple],
    days_back: int = 30,
    days_forward: int = 90
) -> List[Dict]:
    """
    Generate realistic sample price observations.

    Args:
        routes: List of (origin, dest, min_price, max_price) tuples
        days_back: Days of historical data
        days_forward: Days of future data

    Returns:
        List of price observation dictionaries
    """
    observations = []
    today = date.today()

    # Generate date range (past and future)
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)

    current_date = start_date
    while current_date <= end_date:
        for origin, dest, min_price, max_price in routes:
            # Generate 2-5 observations per route per day (different sources/times)
            num_obs = random.randint(2, 5)

            for _ in range(num_obs):
                # Price varies based on:
                # 1. Day of week (weekends more expensive)
                # 2. Lead time (closer dates more expensive)
                # 3. Random variation

                is_weekend = current_date.weekday() >= 5
                weekend_multiplier = 1.2 if is_weekend else 1.0

                days_until = (current_date - today).days
                # Prices drop as departure gets closer (within reason)
                lead_time_multiplier = 1.0
                if 30 <= days_until <= 60:
                    lead_time_multiplier = 0.85  # Sweet spot
                elif days_until < 7:
                    lead_time_multiplier = 1.5   # Last minute surge

                base_price = random.uniform(min_price, max_price)
                final_price = base_price * weekend_multiplier * lead_time_multiplier

                # Add some random noise
                final_price *= random.uniform(0.95, 1.05)

                # Round to nearest dollar
                final_price = round(final_price, 2)

                # Random observation time (simulate different scrape times)
                obs_time = datetime.now() - timedelta(
                    days=random.randint(0, days_back),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )

                observations.append({
                    "origin": origin,
                    "dest": dest,
                    "cabin": "economy",
                    "depart_date": current_date.isoformat(),
                    "price_usd": final_price,
                    "source": random.choice(["sample", "seed", "test"]),
                    "observed_at": obs_time.isoformat()
                })

        current_date += timedelta(days=1)

    return observations


def seed_database(
    supabase: Client,
    observations: List[Dict],
    batch_size: int = 500,
    dry_run: bool = False
):
    """
    Insert observations into Supabase.

    Args:
        supabase: Supabase client
        observations: List of observations to insert
        batch_size: Number of rows per batch
        dry_run: If True, print sample without inserting
    """
    if dry_run:
        print("=" * 60)
        print("DRY RUN - Sample data (first 10 observations):")
        print("=" * 60)
        for i, obs in enumerate(observations[:10], 1):
            print(f"\n{i}. {obs['origin']} → {obs['dest']}")
            print(f"   Date: {obs['depart_date']}")
            print(f"   Price: ${obs['price_usd']:.2f}")
            print(f"   Source: {obs['source']}")
            print(f"   Observed: {obs['observed_at']}")

        print(f"\n... and {len(observations) - 10} more")
        print(f"\nTotal observations: {len(observations)}")
        print("\nTo actually insert, run without --dry-run")
        return

    print(f"Inserting {len(observations)} observations in batches of {batch_size}...")

    inserted_count = 0
    for i in range(0, len(observations), batch_size):
        batch = observations[i:i + batch_size]

        try:
            result = supabase.table("price_observation").upsert(
                batch,
                on_conflict="origin,dest,cabin,depart_date,source,observed_at"
            ).execute()

            batch_count = len(result.data) if result.data else len(batch)
            inserted_count += batch_count

            print(f"  Batch {i//batch_size + 1}: Inserted {batch_count} rows")

        except Exception as e:
            print(f"  ❌ Batch {i//batch_size + 1} failed: {e}")
            continue

    print(f"\n✅ Successfully inserted {inserted_count} observations")


def main():
    parser = argparse.ArgumentParser(description="Seed sample flight prices")
    parser.add_argument("--routes", type=int, default=10, help="Number of routes")
    parser.add_argument("--days-back", type=int, default=30, help="Days of historical data")
    parser.add_argument("--days-forward", type=int, default=90, help="Days of future data")
    parser.add_argument("--dry-run", action="store_true", help="Print without inserting")
    args = parser.parse_args()

    # Check environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE")

    if not supabase_url or not supabase_key:
        print("❌ ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE required")
        print("\nSet environment variables:")
        print("  export SUPABASE_URL=https://your-project.supabase.co")
        print("  export SUPABASE_SERVICE_ROLE=your-service-role-key")
        sys.exit(1)

    print("🌱 Seeding Sample Flight Prices")
    print("=" * 60)
    print(f"Supabase URL: {supabase_url}")
    print(f"Routes: {args.routes}")
    print(f"Date range: {args.days_back} days back to {args.days_forward} days forward")
    print()

    # Select routes
    selected_routes = POPULAR_ROUTES[:args.routes]
    print(f"Selected routes:")
    for origin, dest, min_p, max_p in selected_routes:
        print(f"  {origin} → {dest} (${min_p}-${max_p})")
    print()

    # Generate observations
    print("Generating sample data...")
    observations = generate_price_observations(
        selected_routes,
        days_back=args.days_back,
        days_forward=args.days_forward
    )
    print(f"Generated {len(observations)} observations")
    print()

    if args.dry_run:
        seed_database(None, observations, dry_run=True)
        return

    # Connect to Supabase
    print("Connecting to Supabase...")
    supabase = create_client(supabase_url, supabase_key)
    print("Connected ✅")
    print()

    # Insert data
    seed_database(supabase, observations)
    print()

    # Refresh materialized view
    print("Refreshing materialized views...")
    try:
        supabase.rpc("refresh_baselines_nonconcurrent").execute()
        print("✅ Materialized view refreshed")
    except Exception as e:
        print(f"⚠️  Failed to refresh view: {e}")
        print("   You may need to run this manually:")
        print("   SELECT refresh_baselines_nonconcurrent();")

    print()
    print("🎉 Sample data seeded successfully!")
    print()
    print("Next steps:")
    print("  1. Verify data: SELECT COUNT(*) FROM price_observation;")
    print("  2. Check baselines: SELECT * FROM route_baseline_30d LIMIT 5;")
    print("  3. Test API: curl $API_BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3")


if __name__ == "__main__":
    main()
