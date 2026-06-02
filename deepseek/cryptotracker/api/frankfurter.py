"""
Frankfurter API client for fiat currency exchange rates.

Provides methods to fetch available currencies and exchange rates.
Base URL: https://api.frankfurter.app
No authentication required.
"""

from datetime import datetime, timezone

from cryptotracker.api.client import build_client, request_with_retry
from cryptotracker.config import settings


class FrankfurterClient:
    """Async client for the Frankfurter foreign exchange rate API."""

    def __init__(self) -> None:
        self._base_url: str = settings.frankfurter_url.rstrip("/")

    async def _get(self, path: str, **kwargs) -> dict:
        """Perform a GET request with retry logic.

        Args:
            path: API path (e.g., '/currencies').
            **kwargs: Additional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
            httpx.RequestError: On network failures after all retries.
        """
        async with build_client() as client:
            response = await request_with_retry(
                client,
                "GET",
                f"{self._base_url}{path}",
                params=kwargs if kwargs else None,
            )
            return response.json()

    async def get_currencies(self) -> dict[str, str]:
        """Fetch the list of available fiat currencies.

        Returns:
            Dictionary mapping currency codes to names,
            e.g. {'EUR': 'Euro', 'USD': 'United States Dollar'}.
        """
        data = await self._get("/currencies")
        # The response is a dict where the key list may vary by date.
        # Standard keys: 'AUD', 'BGN', 'BRL', 'CAD', 'CHF', 'CNY', ...
        result: dict[str, str] = {}
        for key, value in data.items():
            if key != "AUD" and not isinstance(value, str):
                # Skip non-currency keys if any
                continue
            result[key] = value
        # If the API changed its format, return the raw data
        return result if result else data

    async def get_rate(self, base: str, target: str) -> dict:
        """Fetch the latest exchange rate for a currency pair.

        Args:
            base: Base currency code (e.g., 'usd').
            target: Target currency code (e.g., 'eur').

        Returns:
            Dictionary with keys: base, target, rate, source, fetched_at.
        """
        data = await self._get(
            "/latest",
            **{"from": base.upper(), "to": target.upper()},
        )
        rates: dict = data.get("rates", {})
        rate = rates.get(target.upper(), 0.0)
        return {
            "base": base.lower(),
            "target": target.lower(),
            "rate": float(rate),
            "source": "frankfurter",
            "fetched_at": datetime.now(timezone.utc),
        }

    async def check_health(self) -> str:
        """Check if the Frankfurter API is reachable.

        Returns:
            'reachable' if healthy, 'unreachable' otherwise.
        """
        try:
            await self._get("/currencies")
            return "reachable"
        except Exception:
            return "unreachable"


# Module-level singleton
frankfurter_client = FrankfurterClient()