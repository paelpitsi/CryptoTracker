"""HTTP client for CryptoTracker backend API."""

from typing import Optional, Any
import httpx
from cryptotracker.common.config import settings
from cryptotracker.common.exceptions import ServerUnavailableError
from cryptotracker.common.logger import logger


class APIClient:
    """HTTP client for communicating with the CryptoTracker backend server."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or f"http://{settings.server_host}:{settings.server_port}"
        self.timeout = 30.0
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Make HTTP request to the backend server."""
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                )
                
                # Handle HTTP errors
                if response.status_code >= 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    raise ServerUnavailableError(f"Server error: {error_msg}")
                
                return response.json()
                
        except httpx.ConnectError:
            logger.error(f"Cannot connect to server at {self.base_url}")
            raise ServerUnavailableError(
                f"Cannot connect to CryptoTracker server at {self.base_url}. "
                "Please start the server first with: cryptotracker server"
            )
        except httpx.TimeoutException:
            logger.error(f"Request to {url} timed out")
            raise ServerUnavailableError(
                "Server request timed out. The server may be overloaded."
            )
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ServerUnavailableError(f"Request failed: {e}")
    
    async def get_health(self) -> dict[str, Any]:
        """Check server health."""
        return await self._request("GET", "/health")
    
    async def get_rates(
        self,
        base: str,
        targets: list[str],
        currency_type: str = "all"
    ) -> dict[str, Any]:
        """Get exchange rates."""
        params = {
            "base": base,
            "targets": ",".join(targets),
            "type": currency_type
        }
        return await self._request("GET", "/api/v1/rates", params=params)
    
    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        currency_type: str = "auto"
    ) -> dict[str, Any]:
        """Convert currency."""
        json_data = {
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
            "type": currency_type
        }
        return await self._request("POST", "/api/v1/convert", json_data=json_data)
    
    async def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        command_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> dict[str, Any]:
        """Get query history."""
        params = {
            "limit": limit,
            "offset": offset
        }
        if command_type:
            params["command_type"] = command_type
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        
        return await self._request("GET", "/api/v1/history", params=params)
    
    async def delete_history(
        self,
        older_than_days: Optional[int] = None,
        delete_all: bool = False
    ) -> dict[str, Any]:
        """Delete query history."""
        params = {}
        if older_than_days:
            params["older_than_days"] = older_than_days
        if delete_all:
            params["all"] = "true"
        
        return await self._request("DELETE", "/api/v1/history", params=params)
    
    async def get_watchlists(self) -> dict[str, Any]:
        """Get all watchlists."""
        return await self._request("GET", "/api/v1/watchlists")
    
    async def get_watchlist(self, watchlist_id: int) -> dict[str, Any]:
        """Get watchlist details."""
        return await self._request("GET", f"/api/v1/watchlists/{watchlist_id}")
    
    async def create_watchlist(
        self,
        name: str,
        description: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new watchlist."""
        json_data = {"name": name}
        if description:
            json_data["description"] = description
        
        return await self._request("POST", "/api/v1/watchlists", json_data=json_data)
    
    async def delete_watchlist(self, watchlist_id: int) -> dict[str, Any]:
        """Delete a watchlist."""
        return await self._request("DELETE", f"/api/v1/watchlists/{watchlist_id}")
    
    async def add_watchlist_item(
        self,
        watchlist_id: int,
        base_currency: str,
        target_currency: str,
        currency_type: str
    ) -> dict[str, Any]:
        """Add item to watchlist."""
        json_data = {
            "base_currency": base_currency,
            "target_currency": target_currency,
            "type": currency_type
        }
        return await self._request(
            "POST",
            f"/api/v1/watchlists/{watchlist_id}/items",
            json_data=json_data
        )
    
    async def remove_watchlist_item(
        self,
        watchlist_id: int,
        item_id: int
    ) -> dict[str, Any]:
        """Remove item from watchlist."""
        return await self._request(
            "DELETE",
            f"/api/v1/watchlists/{watchlist_id}/items/{item_id}"
        )
    
    async def get_currencies(
        self,
        currency_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> dict[str, Any]:
        """Get available currencies."""
        params = {}
        if currency_type:
            params["type"] = currency_type
        if search:
            params["search"] = search
        
        return await self._request("GET", "/api/v1/currencies", params=params)
    
    async def sync_currencies(self) -> dict[str, Any]:
        """Sync currencies from external APIs."""
        return await self._request("POST", "/api/v1/currencies/sync")
    
    async def export_history(
        self,
        format: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        command_type: Optional[str] = None
    ) -> tuple[str, str]:
        """Export history to file."""
        params = {"format": format}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if command_type:
            params["command_type"] = command_type
        
        url = f"{self.base_url}/api/v1/export/history"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                
                if response.status_code >= 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    raise ServerUnavailableError(f"Server error: {error_msg}")
                
                # Get filename from Content-Disposition header
                content_disposition = response.headers.get("Content-Disposition", "")
                filename = "export"
                if "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1].strip('"')
                
                return response.text, filename
                
        except httpx.ConnectError:
            raise ServerUnavailableError(
                f"Cannot connect to CryptoTracker server at {self.base_url}"
            )
    
    async def export_watchlist(
        self,
        watchlist_id: int,
        format: str,
        include_rates: bool = True
    ) -> tuple[str, str]:
        """Export watchlist to file."""
        params = {
            "format": format,
            "include_rates": str(include_rates).lower()
        }
        
        url = f"{self.base_url}/api/v1/export/watchlist/{watchlist_id}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                
                if response.status_code >= 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    raise ServerUnavailableError(f"Server error: {error_msg}")
                
                # Get filename from Content-Disposition header
                content_disposition = response.headers.get("Content-Disposition", "")
                filename = "export"
                if "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1].strip('"')
                
                return response.text, filename
                
        except httpx.ConnectError:
            raise ServerUnavailableError(
                f"Cannot connect to CryptoTracker server at {self.base_url}"
            )
