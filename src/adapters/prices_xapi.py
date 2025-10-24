"""
X API Price Fetcher Adapter

Fetches flight prices from X API (Twitter/X flight data API).
Implements the PriceFetcher interface with X API-specific logic.

Environment Variables:
- XAPI_KEY: X API authentication key
- XAPI_ENDPOINT: Base URL for X API (default: https://api.twitter.com/2/...)
- XAPI_RATE_LIMIT: Max requests per minute (default: 30)
"""

import os
import httpx
from typing import List, Dict
from datetime import date, datetime, timedelta
import asyncio
from .prices_base import PriceFetcher, PriceFetchError


class XApiFetcher(PriceFetcher):
    """
    X API price fetcher implementation.

    Uses X API to fetch real-time flight price data.
    Handles rate limiting, batch requests, and data transformation.
    """

    def __init__(self, **kwargs):
        """
        Initialize X API fetcher.

        Environment variables:
        - XAPI_KEY: Required API key
        - XAPI_ENDPOINT: Optional custom endpoint
        - XAPI_RATE_LIMIT: Optional rate limit (requests/minute)
        """
        api_key = os.getenv("XAPI_KEY")
        if not api_key:
            raise ValueError("XAPI_KEY environment variable is required")

        super().__init__(api_key=api_key, **kwargs)

        self.endpoint = os.getenv(
            "XAPI_ENDPOINT",
            "https://api.twitter.com/2/flights/prices"  # Placeholder URL
        )
        self.rate_limit = int(os.getenv("XAPI_RATE_LIMIT", "30"))
        self.timeout = float(os.getenv("XAPI_TIMEOUT", "30.0"))

        self.logger.info(f"Initialized XApiFetcher with endpoint: {self.endpoint}")

    def fetch(
        self,
        origins: List[str],
        destinations: List[str],
        windows: List[Dict[str, date]],
        cabin: str = "economy"
    ) -> List[Dict]:
        """
        Fetch prices from X API.

        Args:
            origins: List of origin airport codes
            destinations: List of destination airport codes
            windows: List of date windows with 'start' and 'end'
            cabin: Cabin class

        Returns:
            List of standardized price dictionaries
        """
        self.logger.info(
            f"Fetching prices: {len(origins)} origins, {len(destinations)} dests, "
            f"{len(windows)} windows, cabin={cabin}"
        )

        # Build route combinations
        routes = []
        for origin in origins:
            for dest in destinations:
                if origin != dest:  # Skip same-origin/dest
                    routes.append((origin, dest))

        self.logger.info(f"Generated {len(routes)} unique routes")

        # Batch routes for rate limiting
        batches = self.batch_requests(routes, batch_size=50)

        # Fetch prices asynchronously
        all_prices = []
        for i, batch in enumerate(batches):
            self.logger.info(f"Processing batch {i+1}/{len(batches)}")

            try:
                batch_prices = asyncio.run(self._fetch_batch_async(batch, windows, cabin))
                all_prices.extend(batch_prices)

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

        Args:
            routes: List of (origin, dest) tuples
            windows: Date windows
            cabin: Cabin class

        Returns:
            List of price dictionaries
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = []

            for origin, dest in routes:
                for window in windows:
                    task = self._fetch_route_window(
                        client, origin, dest, window, cabin
                    )
                    tasks.append(task)

            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and filter out errors
        prices = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.warning(f"Route fetch failed: {result}")
                continue
            if isinstance(result, list):
                prices.extend(result)

        return prices

    async def _fetch_route_window(
        self,
        client: httpx.AsyncClient,
        origin: str,
        dest: str,
        window: Dict[str, date],
        cabin: str
    ) -> List[Dict]:
        """
        Fetch prices for a single route and date window.

        Args:
            client: httpx client
            origin: Origin airport code
            dest: Destination airport code
            window: Date window with 'start' and 'end'
            cabin: Cabin class

        Returns:
            List of price dictionaries for this route/window
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "origin": origin.upper(),
            "destination": dest.upper(),
            "depart_date_start": window["start"].isoformat(),
            "depart_date_end": window["end"].isoformat(),
            "cabin": cabin.lower()
        }

        try:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            # Transform X API response to standard format
            return self._transform_response(data, origin, dest, cabin)

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTP error for {origin}→{dest}: {e.response.status_code} - {e.response.text}"
            )
            raise PriceFetchError(f"HTTP {e.response.status_code}") from e

        except httpx.RequestError as e:
            self.logger.error(f"Request error for {origin}→{dest}: {e}")
            raise PriceFetchError(f"Request failed: {e}") from e

    def _transform_response(
        self,
        api_response: Dict,
        origin: str,
        dest: str,
        cabin: str
    ) -> List[Dict]:
        """
        Transform X API response to standardized format.

        Args:
            api_response: Raw response from X API
            origin: Origin airport code
            dest: Destination airport code
            cabin: Cabin class

        Returns:
            List of standardized price dictionaries
        """
        prices = []
        observed_at = datetime.now()

        # X API response format (example - adjust to actual API schema):
        # {
        #   "flights": [
        #     {
        #       "depart_date": "2025-03-15",
        #       "price": 234.50,
        #       "currency": "USD"
        #     },
        #     ...
        #   ]
        # }

        flights = api_response.get("flights", [])

        for flight in flights:
            try:
                # Parse date
                depart_date = datetime.strptime(
                    flight["depart_date"],
                    "%Y-%m-%d"
                ).date()

                # Extract price (convert to USD if needed)
                price_usd = float(flight["price"])
                currency = flight.get("currency", "USD")

                if currency != "USD":
                    # TODO: Implement currency conversion if needed
                    self.logger.warning(
                        f"Non-USD currency detected: {currency}. Skipping."
                    )
                    continue

                prices.append({
                    "origin": origin.upper(),
                    "dest": dest.upper(),
                    "cabin": cabin.lower(),
                    "depart_date": depart_date,
                    "price_usd": round(price_usd, 2),
                    "source": "xapi",
                    "observed_at": observed_at
                })

            except (KeyError, ValueError, TypeError) as e:
                self.logger.warning(f"Failed to parse flight data: {flight} - {e}")
                continue

        return prices

    def get_source_identifier(self) -> str:
        """Return source identifier for X API"""
        return "xapi"


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Initialize fetcher
    fetcher = XApiFetcher()

    # Define search parameters
    origins = ["JFK", "EWR", "LGA"]
    destinations = ["MIA", "LAX", "SFO"]

    # Next 3 months in monthly windows
    today = date.today()
    windows = []
    for month_offset in range(3):
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
        for price in prices[:5]:  # Show first 5
            print(price)

    except PriceFetchError as e:
        print(f"Failed to fetch prices: {e}")
