"""Base external API client."""

import asyncio
from typing import Any, Optional
import httpx
from cryptotracker.common.config import settings
from cryptotracker.common.logger import logger


class BaseAPIClient:
    """Base class for external API clients with retry logic."""
    
    def __init__(self, base_url: str, timeout: int):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = settings.max_retry_attempts
        self.retry_delay = settings.retry_base_delay
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        
        url = f"{self.base_url}{endpoint}"
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data
                    )
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit exceeded
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limit exceeded for {url}. "
                        f"Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
                    raise
                    
            except httpx.RequestError as e:
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Request error for {url}: {e}. "
                    f"Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay)
                last_exception = e
        
        # All retries exhausted
        logger.error(f"All {self.max_retries} retry attempts failed for {url}")
        raise last_exception
