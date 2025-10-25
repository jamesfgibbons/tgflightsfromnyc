"""
Parallel API Price Fetcher Adapter (Flexible)

Fetches flight prices from Parallel API with support for both bulk and single request modes.
Configuration is driven entirely by environment variables, making it easy to adapt to
any API specification without code changes.

Environment Variables:
- PARALLEL_API_KEY: API authentication key (required)
- PARALLEL_ENDPOINT: API endpoint URL (required)
- PARALLEL_MODE: Request mode - 'bulk' or 'single' (default: bulk)
- PARALLEL_TIMEOUT_SECONDS: Request timeout (default: 60)
- PARALLEL_BATCH_SIZE: Max routes per batch in bulk mode (default: 100)
- MONTHS_AHEAD: Number of months to fetch (default: 6)
"""

import os
import datetime as dt
from typing import List, Dict, Any
import httpx
from .prices_base import PriceFetcher, PriceFetchError


def _iso(d):
    """Convert date to ISO string"""
    return d if isinstance(d, str) else d.isoformat()


def _windows_next_n_months(n=6) -> List[Dict[str, str]]:
    """
    Generate monthly date windows for the next N months.

    Args:
        n: Number of months ahead

    Returns:
        List of date windows with 'start' and 'end' keys
    """
    today = dt.date.today().replace(day=1)
    windows = []
    y, m = today.year, today.month

    for i in range(n):
        yy = y + (m - 1 + i) // 12
        mm = ((m - 1 + i) % 12) + 1
        start = dt.date(yy, mm, 1)
        # Use 28th as end guard (works for all months)
        end = dt.date(yy, mm, 28)
        windows.append({"start": str(start), "end": str(end)})

    return windows


class ParallelFetcher(PriceFetcher):
    """
    Flexible Parallel API adapter supporting both 'bulk' and 'single' modes.

    Bulk mode: Send all routes in a single request (efficient for APIs that support it)
    Single mode: One request per route+window combination (more compatible)

    The adapter normalizes responses to a standard format regardless of the API's
    response structure, making it easy to adjust to different providers.
    """

    def __init__(self, **kwargs):
        """
        Initialize Parallel API fetcher with environment-driven configuration.

        Raises:
            RuntimeError: If required environment variables are missing
        """
        super().__init__(**kwargs)

        self.base_endpoint = os.getenv("PARALLEL_ENDPOINT", "").strip()
        self.key = os.getenv("PARALLEL_API_KEY", "").strip()
        self.mode = os.getenv("PARALLEL_MODE", "bulk").strip().lower()
        self.timeout = int(os.getenv("PARALLEL_TIMEOUT_SECONDS", "60"))
        self.batch_size = int(os.getenv("PARALLEL_BATCH_SIZE", "100"))
        self.months_ahead = int(os.getenv("MONTHS_AHEAD", "6"))

        if not self.base_endpoint:
            raise RuntimeError("PARALLEL_ENDPOINT environment variable is required")
        if not self.key:
            raise RuntimeError("PARALLEL_API_KEY environment variable is required")

        self.logger.info(
            f"Initialized ParallelFetcher: endpoint={self.base_endpoint}, "
            f"mode={self.mode}, batch_size={self.batch_size}, timeout={self.timeout}s"
        )

    def _auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        return {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

    def fetch(
        self,
        origins: List[str],
        destinations: List[str],
        windows: List[Dict] = None,
        cabin: str = "economy"
    ) -> List[Dict]:
        """
        Fetch prices from Parallel API.

        Args:
            origins: List of origin airport codes
            destinations: List of destination airport codes
            windows: Optional list of date windows (generated if not provided)
            cabin: Cabin class (default: economy)

        Returns:
            List of standardized price dictionaries

        Raises:
            RuntimeError: If API requests fail
        """
        if not windows:
            windows = _windows_next_n_months(self.months_ahead)

        # Generate all route combinations (excluding same origin/dest)
        routes = [(o, d) for o in origins for d in destinations if o != d]

        self.logger.info(
            f"Fetching prices: {len(routes)} routes × {len(windows)} windows = "
            f"{len(routes) * len(windows)} queries (mode={self.mode})"
        )

        results: List[Dict[str, Any]] = []

        with httpx.Client(timeout=self.timeout) as client:
            if self.mode == "bulk":
                results = self._fetch_bulk(client, routes, windows, cabin)
            else:
                results = self._fetch_single(client, routes, windows, cabin)

        self.logger.info(f"Fetched {len(results)} price observations")
        return results

    def _fetch_bulk(
        self,
        client: httpx.Client,
        routes: List[tuple],
        windows: List[Dict],
        cabin: str
    ) -> List[Dict]:
        """
        Fetch prices using bulk request mode.

        Sends all routes in a single request (or batched if too many).
        """
        results = []

        # Build all queries
        queries = []
        for (origin, dest) in routes:
            for window in windows:
                queries.append({
                    "origin": origin,
                    "destination": dest,
                    "depart_date_start": window["start"],
                    "depart_date_end": window["end"],
                    "cabin": cabin,
                    "currency": "USD",
                })

        self.logger.info(f"Built {len(queries)} queries for bulk request")

        # Send in chunks to respect payload limits
        for i in range(0, len(queries), self.batch_size):
            chunk = queries[i:i + self.batch_size]
            payload = {"queries": chunk, "currency": "USD"}

            self.logger.debug(f"Sending bulk request with {len(chunk)} queries")

            try:
                response = client.post(
                    self.base_endpoint,
                    json=payload,
                    headers=self._auth_headers()
                )

                if response.status_code >= 400:
                    error_text = response.text[:500]
                    raise RuntimeError(
                        f"Parallel bulk request failed: {response.status_code} - {error_text}"
                    )

                batch_results = self._normalize_bulk_response(response.json())
                results.extend(batch_results)

                self.logger.info(
                    f"Bulk batch {i // self.batch_size + 1}: "
                    f"Got {len(batch_results)} prices"
                )

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error in bulk request: {e}")
                raise RuntimeError(f"Bulk request failed: {e}") from e

        return results

    def _fetch_single(
        self,
        client: httpx.Client,
        routes: List[tuple],
        windows: List[Dict],
        cabin: str
    ) -> List[Dict]:
        """
        Fetch prices using single request mode.

        One request per route+window combination (more compatible but slower).
        """
        results = []
        total_requests = len(routes) * len(windows)
        request_count = 0

        for (origin, dest) in routes:
            for window in windows:
                request_count += 1

                payload = {
                    "origin": origin,
                    "destination": dest,
                    "depart_date_start": window["start"],
                    "depart_date_end": window["end"],
                    "cabin": cabin,
                    "currency": "USD",
                }

                try:
                    response = client.post(
                        self.base_endpoint,
                        json=payload,
                        headers=self._auth_headers()
                    )

                    if response.status_code >= 400:
                        error_text = response.text[:200]
                        self.logger.warning(
                            f"Single request failed for {origin}-{dest} {window}: "
                            f"{response.status_code} - {error_text}"
                        )
                        continue

                    route_results = self._normalize_single_response(
                        response.json(), origin, dest, window
                    )
                    results.extend(route_results)

                    if request_count % 10 == 0:
                        self.logger.info(
                            f"Progress: {request_count}/{total_requests} requests, "
                            f"{len(results)} prices so far"
                        )

                except httpx.HTTPError as e:
                    self.logger.warning(
                        f"HTTP error for {origin}-{dest} {window}: {e}"
                    )
                    continue

        return results

    # --- Response normalizers (adjust these if API format differs) ---

    def _normalize_bulk_response(self, data: Dict[str, Any]) -> List[Dict]:
        """
        Normalize bulk API response to standard format.

        Expected bulk response shape (example):
        {
          "results": [
            {
              "origin": "JFK",
              "destination": "MIA",
              "date": "2025-03-14",
              "cabin": "economy",
              "price": 189.0
            },
            ...
          ]
        }

        Adjust the key names here if your API uses different field names.
        """
        results = data.get("results") or data.get("quotes") or data.get("data") or []
        normalized = []
        now = dt.datetime.utcnow().isoformat()

        for row in results:
            try:
                normalized.append({
                    "origin": (row.get("origin") or "").upper(),
                    "dest": (row.get("destination") or row.get("dest") or "").upper(),
                    "cabin": (row.get("cabin") or "economy").lower(),
                    "depart_date": row.get("date") or row.get("depart_date"),
                    "price_usd": float(
                        row.get("price") or row.get("usd") or
                        row.get("amount") or 0
                    ),
                    "source": "parallel",
                    "observed_at": now,
                })
            except (ValueError, TypeError, KeyError) as e:
                self.logger.warning(f"Failed to parse bulk result: {row} - {e}")
                continue

        return normalized

    def _normalize_single_response(
        self,
        data: Dict[str, Any],
        origin: str,
        dest: str,
        window: Dict[str, str]
    ) -> List[Dict]:
        """
        Normalize single-route API response to standard format.

        Expected single response shape (example):
        {
          "quotes": [
            {"date": "2025-03-14", "price": 189.0, "cabin": "economy"},
            {"date": "2025-03-15", "price": 195.0, "cabin": "economy"},
            ...
          ]
        }

        Adjust the key names here if your API uses different field names.
        """
        quotes = data.get("quotes") or data.get("results") or data.get("prices") or []
        normalized = []
        now = dt.datetime.utcnow().isoformat()

        for quote in quotes:
            try:
                normalized.append({
                    "origin": origin.upper(),
                    "dest": dest.upper(),
                    "cabin": (quote.get("cabin") or "economy").lower(),
                    "depart_date": quote.get("date") or quote.get("depart_date"),
                    "price_usd": float(
                        quote.get("price") or quote.get("usd") or
                        quote.get("amount") or 0
                    ),
                    "source": "parallel",
                    "observed_at": now,
                })
            except (ValueError, TypeError, KeyError) as e:
                self.logger.warning(f"Failed to parse single quote: {quote} - {e}")
                continue

        return normalized

    def get_source_identifier(self) -> str:
        """Return source identifier for Parallel API"""
        return "parallel"
