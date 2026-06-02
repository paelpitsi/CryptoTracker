"""CoinGecko API client."""

from typing import Optional
from cryptotracker.server.external.base import BaseAPIClient
from cryptotracker.common.config import settings
from cryptotracker.common.exceptions import CoinGeckoUnavailableError
from cryptotracker.common.logger import logger


class CoinGeckoClient(BaseAPIClient):
    """Client for CoinGecko API (cryptocurrencies)."""
    
    def __init__(self):
        super().__init__(
            base_url=settings.coingecko_base_url,
            timeout=settings.coingecko_timeout
        )
    
    async def get_simple_price(
        self,
        ids: list[str],
        vs_currencies: list[str],
        include_24h_change: bool = True
    ) -> dict[str, dict[str, float]]:
        """Get current prices for cryptocurrencies."""
        
        try:
            params = {
                "ids": ",".join(ids),
                "vs_currencies": ",".join(vs_currencies),
                "include_24hr_change": str(include_24h_change).lower()
            }
            
            response = await self._request("GET", "/simple/price", params=params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get prices from CoinGecko: {e}")
            raise CoinGeckoUnavailableError(f"CoinGecko API error: {e}")
    
    async def get_coins_list(self) -> list[dict[str, str]]:
        """Get list of all available cryptocurrencies."""
        
        try:
            response = await self._request("GET", "/coins/list")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get coins list from CoinGecko: {e}")
            raise CoinGeckoUnavailableError(f"CoinGecko API error: {e}")
    
    async def get_coin_details(
        self,
        coin_id: str,
        localization: bool = False,
        tickers: bool = False,
        market_data: bool = True,
        community_data: bool = False,
        developer_data: bool = False
    ) -> dict:
        """Get detailed information about a cryptocurrency."""
        
        try:
            params = {
                "localization": str(localization).lower(),
                "tickers": str(tickers).lower(),
                "market_data": str(market_data).lower(),
                "community_data": str(community_data).lower(),
                "developer_data": str(developer_data).lower()
            }
            
            response = await self._request("GET", f"/coins/{coin_id}", params=params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get coin details from CoinGecko: {e}")
            raise CoinGeckoUnavailableError(f"CoinGecko API error: {e}")
