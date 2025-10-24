"""
Parallel API Price Fetcher Adapter

Fetches flight prices from Parallel API (or similar aggregator service).
Implements the PriceFetcher interface with Parallel API-specific logic.

Environment Variables:
- PARALLEL_API_KEY: Parallel API authentication key
- PARALLEL_API_ENDPOINT: Base URL for Parallel API
- PARALLEL_BATCH_SIZE: Max routes per batch request (default: 100)
"""

import os
import httpx
from typing import List, Dict
from datetime import date, datetime, timedelta
import asyncio
from .prices_base import PriceFetcher, PriceFetchError


class ParallelFetcher(PriceFetcher):
    """
    Parallel API price fetcher implementation.

    Uses Parallel API to fetch bulk flight price data efficiently.
    Supports batch requests and handles API-specific response formats.
    """

    def __init__(self, **kwargs):
        """
        Initialize Parallel API fetcher.

        Environment variables:
        - PARALLEL_API_KEY: Required API key
        - PARALLEL_API_ENDPOINT: Optional custom endpoint
        - PARALLEL_BATCH_SIZE: Optional batch size
        """
        api_key = os.getenv("PARALLEL_API_KEY")
        if not api_key:
            raise ValueError("PARALLEL_API_KEY environment variable is required")

        super().__init__(api_key=api_key, **kwargs)

        self.endpoint = os.getenv(
            "PARALLEL_API_ENDPOINT",
            "https://api.parallel.com/v1/flights/search"  # Placeholder URL
        )
        self.batch_size = int(os.getenv("PARALLEL_BATCH_SIZE", "100"))
        self.timeout = float(os.getenv("PARALLEL_API_TIMEOUT", "60.0"))

        self.logger.info(
            f"Initialized ParallelFetcher with endpoint: {self.endpoint}, "
            f"batch_size: {self.batch_size}"
        )

    def fetch(
        self,
        origins: List[str],
        destinations: List[str],
        windows: List[Dict[str, date]],
        cabin: str = "economy"
    ) -> List[Dict]:
        """
        Fetch prices from Parallel API.

        Parallel API supports bulk batch requests, making it efficient
        for fetching many routes at once.

        Args:
            origins: List of origin airport codes
            destinations: List of destination airport codes
            windows: List of date windows with 'start' and 'end'
            cabin: Cabin class

        Returns:
            List of standardized price dictionaries
        """
        self.logger.info(
            f"Fetching prices via Parallel API: {len(origins)} origins, "
            f"{len(destinations)} dests, {len(windows)} windows, cabin={cabin}"
        )

        # Build route combinations
        routes = []
        for origin in origins:
            for dest in destinations:
                if origin != dest:
                    routes.append((origin, dest))

        self.logger.info(f"Generated {len(routes)} unique routes")

        # Batch routes for API limits
        batches = self.batch_requests(routes, batch_size=self.batch_size)

        # Fetch prices asynchronously
        all_prices = []
        for i, batch in enumerate(batches):
            self.logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} routes)")

            try:
                batch_prices = asyncio.run(
                    self._fetch_batch_async(batch, windows, cabin)
                )
                all_prices.extend(batch_prices)

                self.logger.info(f"Batch {i+1} returned {len(batch_prices)} prices")

            except Exception as e:
                self.logger.error(f"Failed to fetch batch {i+1}: {e}")
                # Continue with other batches
                continue

        # Validate and return
        validated = self.validate_price_data(all_prices)
        self.logger.info(f"Successfully fetched {len(validated)} price records")

        return validated

    async def _fetch_batch_async(
        self,
        routes: List[tuple],
        windows: List[Dict[str, date]],
        cabin: str
    ) -> List[Dict]:
        """
        Fetch a batch of routes asynchronously.

        Parallel API supports bulk requests, so we can send all routes
        in a single API call.

        Args:
            routes: List of (origin, dest) tuples
            windows: Date windows
            cabin: Cabin class

        Returns:
            List of price dictionaries
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build bulk request payload
        # Parallel API accepts array of route queries
        queries = []
        for origin, dest in routes:
            for window in windows:
                queries.append({
                    "origin": origin.upper(),
                    "destination": dest.upper(),
                    "depart_date_start": window["start"].isoformat(),
                    "depart_date_end": window["end"].isoformat(),
                    "cabin": cabin.lower()
                })

        payload = {
            "queries": queries,
            "currency": "USD",
            "max_results_per_query": 30  # Limit results per route
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                )

                response.raise_for_status()
                data = response.json()

            # Transform response to standard format
            return self._transform_response(data, cabin)

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise PriceFetchError(f"HTTP {e.response.status_code}") from e

        except httpx.RequestError as e:
            self.logger.error(f"Request error: {e}")
            raise PriceFetchError(f"Request failed: {e}") from e

    def _transform_response(
        self,
        api_response: Dict,
        cabin: str
    ) -> List[Dict]:
        """
        Transform Parallel API response to standardized format.

        Args:
            api_response: Raw response from Parallel API
            cabin: Cabin class

        Returns:
            List of standardized price dictionaries
        """
        prices = []
        observed_at = datetime.now()

        # Parallel API response format (example - adjust to actual API schema):
        # {
        #   "results": [
        #     {
        #       "query_id": 0,
        #       "origin": "JFK",
        #       "destination": "MIA",
        #       "flights": [
        #         {
        #           "depart_date": "2025-03-15",
        #           "price": {"amount": 234.50, "currency": "USD"},
        #           "airline": "AA",
        #           "flight_number": "1234"
        #         },
        #         ...
        #       ]
        #     },
        #     ...
        #   ]
        # }

        results = api_response.get("results", [])

        for result in results:
            origin = result.get("origin", "").upper()
            dest = result.get("destination", "").upper()
            flights = result.get("flights", [])

            for flight in flights:
                try:
                    # Parse date
                    depart_date_str = flight.get("depart_date")
                    if not depart_date_str:
                        continue

                    depart_date = datetime.strptime(
                        depart_date_str,
                        "%Y-%m-%d"
                    ).date()

                    # Extract price
                    price_obj = flight.get("price", {})
                    price_amount = price_obj.get("amount")
                    currency = price_obj.get("currency", "USD")

                    if not price_amount or currency != "USD":
                        continue

                    price_usd = float(price_amount)

                    prices.append({
                        "origin": origin,
                        "dest": dest,
                        "cabin": cabin.lower(),
                        "depart_date": depart_date,
                        "price_usd": round(price_usd, 2),
                        "source": "parallel",
                        "observed_at": observed_at
                    })

                except (KeyError, ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to parse flight: {flight} - {e}")
                    continue

        return prices

    def get_source_identifier(self) -> str:
        """Return source identifier for Parallel API"""
        return "parallel"


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Initialize fetcher
    fetcher = ParallelFetcher()

    # Define search parameters
    origins = ["JFK", "EWR", "LGA"]
    destinations = ["MIA", "LAX", "SFO", "ORD", "ATL"]

    # Next 6 months in monthly windows
    today = date.today()
    windows = []
    for month_offset in range(6):
        start = today + timedelta(days=30 * month_offset)
        end = start + timedelta(days=30)
        windows.append({"start": start, "end": end})

    # Fetch prices
    try:
        prices = fetcher.fetch_with_retry(
            origins=origins,
            destinations=destinations,
            windows=windows,
            cabin="economy"
        )

        print(f"Fetched {len(prices)} price records")

        # Group by route
        routes_count = {}
        for price in prices:
            route = f"{price['origin']}→{price['dest']}"
            routes_count[route] = routes_count.get(route, 0) + 1

        print("\nPrices per route:")
        for route, count in sorted(routes_count.items()):
            print(f"  {route}: {count} observations")

    except PriceFetchError as e:
        print(f"Failed to fetch prices: {e}")
