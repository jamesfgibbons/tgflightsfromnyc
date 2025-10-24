#!/usr/bin/env python3
"""
Test Parallel API Connection

Quick script to verify Parallel API credentials and test basic price fetching.
Fetches a small sample of prices to ensure the adapter is working correctly.

Usage:
    export PARALLEL_API_KEY=your-key-here
    python scripts/test_parallel_api.py
"""

import os
import sys
from datetime import date, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters import ParallelFetcher, PriceFetchError


def test_parallel_api():
    """Test Parallel API connection with minimal request"""

    # Check for API key
    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key:
        print("❌ ERROR: PARALLEL_API_KEY environment variable not set")
        print("\nUsage:")
        print("  export PARALLEL_API_KEY=your-key-here")
        print("  python scripts/test_parallel_api.py")
        sys.exit(1)

    print("🔍 Testing Parallel API Connection")
    print("=" * 60)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    try:
        # Initialize fetcher
        print("📡 Initializing Parallel API fetcher...")
        fetcher = ParallelFetcher()
        print(f"✅ Fetcher initialized")
        print(f"   Endpoint: {fetcher.endpoint}")
        print(f"   Batch size: {fetcher.batch_size}")
        print()

        # Test with minimal query (1 route, 1 month)
        print("🛫 Testing minimal query: JFK → MIA, next 30 days")

        origins = ["JFK"]
        destinations = ["MIA"]

        today = date.today()
        windows = [{
            "start": today,
            "end": today + timedelta(days=30)
        }]

        print(f"   Origins: {origins}")
        print(f"   Destinations: {destinations}")
        print(f"   Window: {windows[0]['start']} to {windows[0]['end']}")
        print()

        print("⏳ Fetching prices...")
        prices = fetcher.fetch_with_retry(
            origins=origins,
            destinations=destinations,
            windows=windows,
            cabin="economy",
            max_retries=2
        )

        # Display results
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"Fetched {len(prices)} price observations")
        print()

        if prices:
            print("Sample prices (first 5):")
            for i, price in enumerate(prices[:5], 1):
                print(f"\n{i}. {price['origin']} → {price['dest']}")
                print(f"   Date: {price['depart_date']}")
                print(f"   Price: ${price['price_usd']:.2f}")
                print(f"   Cabin: {price['cabin']}")
                print(f"   Source: {price['source']}")
                print(f"   Observed: {price['observed_at']}")

            if len(prices) > 5:
                print(f"\n... and {len(prices) - 5} more")

        else:
            print("⚠️  No prices returned (API might be empty or test route unavailable)")

        print()
        print("🎉 Parallel API connection successful!")
        print("   You can now deploy the worker to fetch prices for all routes.")
        print()

        return True

    except PriceFetchError as e:
        print()
        print("=" * 60)
        print("❌ PRICE FETCH FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Possible issues:")
        print("  - Invalid API key")
        print("  - API endpoint not reachable")
        print("  - Rate limit exceeded")
        print("  - Network connectivity issues")
        print()
        print("Check the error message above for details.")
        print()
        return False

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    success = test_parallel_api()
    sys.exit(0 if success else 1)
