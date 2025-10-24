"""
Price Fetcher Adapters

This package provides adapters for fetching flight price data from various APIs.

Available adapters:
- XApiFetcher: Fetches prices from X API (Twitter/X)
- ParallelFetcher: Fetches prices from Parallel API (bulk aggregator)

Usage:
    from src.adapters import XApiFetcher, ParallelFetcher

    # Choose adapter based on config
    if os.getenv("PRICE_SOURCE") == "xapi":
        fetcher = XApiFetcher()
    else:
        fetcher = ParallelFetcher()

    # Fetch prices
    prices = fetcher.fetch_with_retry(
        origins=["JFK", "EWR"],
        destinations=["MIA", "LAX"],
        windows=[{"start": date.today(), "end": date.today() + timedelta(days=30)}],
        cabin="economy"
    )
"""

from .prices_base import PriceFetcher, PriceFetchError
from .prices_xapi import XApiFetcher
from .prices_parallel import ParallelFetcher

__all__ = [
    "PriceFetcher",
    "PriceFetchError",
    "XApiFetcher",
    "ParallelFetcher"
]
