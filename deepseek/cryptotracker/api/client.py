"""
Base async HTTP client for external API communication.

Provides an httpx.AsyncClient configured with timeouts and consistent
User-Agent header. Retry logic is implemented per-call in the API modules.
"""

import asyncio
import logging
from typing import Optional

import httpx

from cryptotracker.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "CryptoTracker/1.0"


def build_client() -> httpx.AsyncClient:
    """Create a configured httpx AsyncClient for external API calls.

    Returns:
        httpx.AsyncClient with timeout and User-Agent set.
    """
    timeout = httpx.Timeout(
        connect=5.0,
        read=settings.request_timeout,
        write=5.0,
        pool=5.0,
    )
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs,
) -> httpx.Response:
    """Perform an HTTP request with exponential backoff retry logic.

    Retries on 5xx errors, network errors, and timeouts.
    For 429 (rate limit), waits 60 seconds and retries once.

    Args:
        client: Configured httpx.AsyncClient.
        method: HTTP method (GET, POST, etc.).
        url: Full URL to request.
        max_retries: Maximum number of retries. Defaults to settings.max_retries.
        **kwargs: Additional arguments passed to client.request().

    Returns:
        httpx.Response object.

    Raises:
        httpx.HTTPStatusError: For non-retryable HTTP errors (4xx except 429).
        httpx.RequestError: When all retries are exhausted.
    """
    if max_retries is None:
        max_retries = settings.max_retries

    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)

            # Handle rate limiting (429)
            if response.status_code == 429:
                if attempt < max_retries:
                    logger.warning(
                        "Rate limited by %s. Waiting 60s before retry...", url
                    )
                    await asyncio.sleep(60)
                    continue
                response.raise_for_status()

            # Retry on server errors
            if response.status_code >= 500:
                if attempt < max_retries:
                    wait = 2**attempt  # 1s, 2s, 4s
                    logger.warning(
                        "Server error %d from %s. Retrying in %ds "
                        "(attempt %d/%d)...",
                        response.status_code,
                        url,
                        wait,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()

            # Client errors (4xx except 429) — do not retry
            if response.status_code >= 400:
                response.raise_for_status()

            return response

        except (httpx.TimeoutException, httpx.NetworkError,
                httpx.RemoteProtocolError, httpx.ConnectError) as exc:
            last_exception = exc
            if attempt < max_retries:
                wait = 2**attempt
                logger.warning(
                    "Network error for %s: %s. Retrying in %ds "
                    "(attempt %d/%d)...",
                    url,
                    exc,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait)
                continue
            raise

    # If we exhaust all retries, raise the last exception
    if last_exception is not None:
        raise last_exception
    # Should not reach here, but safety fallback
    raise httpx.RequestError(f"All {max_retries} retries exhausted for {url}")
