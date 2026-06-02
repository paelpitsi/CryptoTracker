"""
CoinGecko API client for cryptocurrency prices.

Provides methods to fetch available cryptocurrencies and their prices.
Base URL: https://api.coingecko.com/api/v3
Free tier — no API key required (rate limited to 10-30 req/min).
"""

from datetime import datetime, timezone

from cryptotracker.api.client import build_client, request_with_retry
from cryptotracker.config import settings


class CoinGeckoClient:
    """Async client for the CoinGecko cryptocurrency API."""

    def __init__(self) -> None:
        self._base_url: str = settings.coingecko_url.rstrip("/")

    async def _get(self, path: str, **kwargs) -> dict | list:
        """Perform a GET request with retry logic.

        Args:
            path: API path (e.g., '/coins/list').
            **kwargs: Additional query parameters.

        Returns:
            Parsed JSON response (dict or list).

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

    async def get_coins_list(self) -> list[dict]:
        """Fetch the list of all available cryptocurrencies from CoinGecko.

        Returns:
            List of dicts with keys: id, symbol, name.
            Example: [{'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}, ...]
        """
        return await self._get("/coins/list")  # type: ignore[return-value]

    async def get_simple_price(
        self, coin_id: str, vs_currency: str
    ) -> dict:
        """Fetch the current price of a cryptocurrency in a target currency.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin').
            vs_currency: Target fiat currency code (e.g., 'usd').

        Returns:
            Dictionary with keys: base, target, rate, source, fetched_at.
            Rate is 0.0 if the price cannot be parsed.
        """
        data = await self._get(
            "/simple/price",
            ids=coin_id,
            vs_currencies=vs_currency,
        )
        prices: dict = data.get(coin_id, {})  # type: ignore[union-attr]
        rate = float(prices.get(vs_currency, 0.0))
        return {
            "base": coin_id,
            "target": vs_currency.lower(),
            "rate": rate,
            "source": "coingecko",
            "fetched_at": datetime.now(timezone.utc),
        }

    async def get_crypto_to_crypto_rate(
        self, base_id: str, target_id: str
    ) -> dict:
        """Calculate a crypto-to-crypto rate via USD.

        Fetches prices of both coins in USD and computes the cross-rate.

        Args:
            base_id: CoinGecko ID of the base cryptocurrency.
            target_id: CoinGecko ID of the target cryptocurrency.

        Returns:
            Dictionary with keys: base, target, rate, source, fetched_at.
        """
        # Fetch both prices in USD simultaneously
        async with build_client() as client:
            url = f"{self._base_url}/simple/price"
            import asyncio

            async def _fetch_one(coin: str) -> dict:
                resp = await request_with_retry(
                    client, "GET", url,
                    params={"ids": coin, "vs_currencies": "usd"},
                )
                return resp.json()

            base_data, target_data = await asyncio.gather(
                _fetch_one(base_id), _fetch_one(target_id)
            )

        base_usd = float(base_data.get(base_id, {}).get("usd", 0.0))
        target_usd = float(target_data.get(target_id, {}).get("usd", 0.0))

        rate = base_usd / target_usd if target_usd != 0 else 0.0

        return {
            "base": base_id,
            "target": target_id,
            "rate": rate,
            "source": "coingecko",
            "fetched_at": datetime.now(timezone.utc),
        }

    async def check_health(self) -> str:
        """Check if the CoinGecko API is reachable.

        Returns:
            'reachable' if healthy, 'unreachable' or 'rate_limited' otherwise.
        """
        try:
            async with build_client() as client:
                resp = await request_with_retry(
                    client, "GET", f"{self._base_url}/ping"
                )
                if resp.status_code == 200:
                    return "reachable"
                if resp.status_code == 429:
                    return "rate_limited"
                return "unreachable"
        except Exception:
            return "unreachable"


# Module-level singleton
coingecko_client = CoinGeckoClient()