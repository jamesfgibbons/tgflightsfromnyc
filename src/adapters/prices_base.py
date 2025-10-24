"""
Price Fetcher Adapter - Base Interface

Abstract base class for price fetching adapters (X API, Parallel API, etc.)
All adapters must implement the fetch() method to return standardized price data.

The adapter pattern allows swapping between different price data providers
without changing the worker refresh logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class PriceFetchError(Exception):
    """Raised when price fetching fails"""
    pass


class PriceFetcher(ABC):
    """
    Abstract base class for flight price fetchers.

    Implementations must provide:
    - fetch() method that returns standardized price dictionaries
    - Retry logic with exponential backoff
    - Error handling and logging
    - Rate limiting compliance
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the price fetcher.

        Args:
            api_key: API key for the service (if required)
            **kwargs: Additional configuration options
        """
        self.api_key = api_key
        self.config = kwargs
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def fetch(
        self,
        origins: List[str],
        destinations: List[str],
        windows: List[Dict[str, date]],
        cabin: str = "economy"
    ) -> List[Dict]:
        """
        Fetch flight prices for given routes and date windows.

        Args:
            origins: List of origin airport codes (e.g., ["JFK", "EWR", "LGA"])
            destinations: List of destination airport codes
            windows: List of date windows, each with 'start' and 'end' keys
                Example: [{"start": date(2025, 3, 1), "end": date(2025, 3, 31)}]
            cabin: Cabin class (economy, premium, business, first)

        Returns:
            List of price dictionaries with standardized schema:
            [
                {
                    "origin": "JFK",
                    "dest": "MIA",
                    "cabin": "economy",
                    "depart_date": date(2025, 3, 15),
                    "price_usd": 234.50,
                    "source": "xapi",  # or "parallel" or other identifier
                    "observed_at": datetime.now()
                },
                ...
            ]

        Raises:
            PriceFetchError: If fetching fails after retries
        """
        raise NotImplementedError("Subclasses must implement fetch()")

    def fetch_with_retry(
        self,
        origins: List[str],
        destinations: List[str],
        windows: List[Dict[str, date]],
        cabin: str = "economy",
        max_retries: int = 3,
        backoff_base: float = 2.0
    ) -> List[Dict]:
        """
        Fetch prices with exponential backoff retry logic.

        Args:
            origins, destinations, windows, cabin: Same as fetch()
            max_retries: Maximum number of retry attempts
            backoff_base: Base for exponential backoff (seconds)

        Returns:
            List of price dictionaries

        Raises:
            PriceFetchError: If all retries fail
        """
        import time

        for attempt in range(max_retries + 1):
            try:
                return self.fetch(origins, destinations, windows, cabin)

            except Exception as e:
                if attempt == max_retries:
                    self.logger.error(f"Price fetch failed after {max_retries} retries: {e}")
                    raise PriceFetchError(f"Failed after {max_retries} retries: {e}") from e

                wait_time = backoff_base ** attempt
                self.logger.warning(
                    f"Price fetch failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

    def validate_price_data(self, price_data: List[Dict]) -> List[Dict]:
        """
        Validate and clean price data before returning.

        Args:
            price_data: Raw price data from API

        Returns:
            Validated and cleaned price data
        """
        validated = []

        for item in price_data:
            # Check required fields
            required = ["origin", "dest", "cabin", "depart_date", "price_usd", "source"]
            if not all(k in item for k in required):
                self.logger.warning(f"Skipping invalid price data: {item}")
                continue

            # Validate types
            try:
                if not isinstance(item["origin"], str) or len(item["origin"]) != 3:
                    continue
                if not isinstance(item["dest"], str) or len(item["dest"]) != 3:
                    continue
                if not isinstance(item["price_usd"], (int, float)) or item["price_usd"] <= 0:
                    continue

                # Ensure observed_at is set
                if "observed_at" not in item:
                    item["observed_at"] = datetime.now()

                validated.append(item)

            except (TypeError, ValueError) as e:
                self.logger.warning(f"Skipping invalid price data: {item} - {e}")
                continue

        self.logger.info(f"Validated {len(validated)}/{len(price_data)} price records")
        return validated

    def batch_requests(
        self,
        routes: List[tuple],
        batch_size: int = 50
    ) -> List[List[tuple]]:
        """
        Split routes into batches for API rate limiting.

        Args:
            routes: List of (origin, dest) tuples
            batch_size: Maximum routes per batch

        Returns:
            List of route batches
        """
        batches = []
        for i in range(0, len(routes), batch_size):
            batches.append(routes[i:i + batch_size])

        self.logger.info(f"Split {len(routes)} routes into {len(batches)} batches")
        return batches

    def get_source_identifier(self) -> str:
        """
        Get the source identifier for this adapter.

        Returns:
            Source string (e.g., "xapi", "parallel")
        """
        return self.__class__.__name__.lower().replace("fetcher", "")
