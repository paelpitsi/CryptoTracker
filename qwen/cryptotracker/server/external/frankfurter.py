"""Frankfurter API client."""

from typing import Optional
from cryptotracker.server.external.base import BaseAPIClient
from cryptotracker.common.config import settings
from cryptotracker.common.exceptions import FrankfurterUnavailableError, CurrencyNotFoundError
from cryptotracker.common.logger import logger


class FrankfurterClient(BaseAPIClient):
    """Client for Frankfurter API (fiat currencies)."""
    
    def __init__(self):
        super().__init__(
            base_url=settings.frankfurter_base_url,
            timeout=settings.frankfurter_timeout
        )
    
    async def get_latest_rates(
        self,
        base: str,
        targets: list[str]
    ) -> dict[str, float]:
        """Get latest exchange rates for fiat currencies."""
        
        try:
            params = {
                "from": base,
                "to": ",".join(targets)
            }
            
            response = await self._request("GET", "/latest", params=params)
            
            if "rates" not in response:
                raise FrankfurterUnavailableError("Invalid response from Frankfurter API")
            
            return response["rates"]
            
        except Exception as e:
            logger.error(f"Failed to get rates from Frankfurter: {e}")
            raise FrankfurterUnavailableError(f"Frankfurter API error: {e}")
    
    async def get_available_currencies(self) -> dict[str, str]:
        """Get list of all available fiat currencies."""
        
        try:
            response = await self._request("GET", "/currencies")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get currencies from Frankfurter: {e}")
            raise FrankfurterUnavailableError(f"Frankfurter API error: {e}")
    
    async def get_historical_rate(
        self,
        date: str,
        base: str,
        target: str
    ) -> Optional[float]:
        """Get historical exchange rate for a specific date."""
        
        try:
            params = {
                "from": base,
                "to": target
            }
            
            response = await self._request("GET", f"/{date}", params=params)
            
            if "rates" not in response or target not in response["rates"]:
                return None
            
            return response["rates"][target]
            
        except Exception as e:
            logger.error(f"Failed to get historical rate from Frankfurter: {e}")
            raise FrankfurterUnavailableError(f"Frankfurter API error: {e}")
