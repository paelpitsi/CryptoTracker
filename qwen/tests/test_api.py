"""Tests for FastAPI server endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.models.currency import Currency


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    async def test_health_check_success(self, client: AsyncClient):
        """Test that health check returns ok status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert data["database"] == "connected"
        assert "timestamp" in data


@pytest.mark.asyncio
class TestCurrenciesEndpoint:
    """Tests for the /api/v1/currencies endpoint."""

    async def test_get_currencies_all(self, client: AsyncClient):
        """Test getting all currencies."""
        response = await client.get("/api/v1/currencies")
        assert response.status_code == 200
        data = response.json()
        assert "currencies" in data
        # We seeded 4 fiat + 2 crypto = 6 currencies
        assert len(data["currencies"]) == 6

    async def test_get_currencies_filter_fiat(self, client: AsyncClient):
        """Test filtering currencies by type=fiat."""
        response = await client.get("/api/v1/currencies", params={"type": "fiat"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["currencies"]) == 4
        for c in data["currencies"]:
            assert c["type"] == "fiat"

    async def test_get_currencies_filter_crypto(self, client: AsyncClient):
        """Test filtering currencies by type=crypto."""
        response = await client.get("/api/v1/currencies", params={"type": "crypto"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["currencies"]) == 2
        for c in data["currencies"]:
            assert c["type"] == "crypto"

    async def test_get_currencies_search(self, client: AsyncClient):
        """Test searching currencies by code."""
        response = await client.get("/api/v1/currencies", params={"search": "USD"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["currencies"]) >= 1
        assert any(c["code"] == "USD" for c in data["currencies"])


@pytest.mark.asyncio
class TestWatchlistsEndpoint:
    """Tests for the /api/v1/watchlists endpoints."""

    async def test_get_watchlists(self, client: AsyncClient):
        """Test getting all watchlists (should include seeded 'default')."""
        response = await client.get("/api/v1/watchlists")
        assert response.status_code == 200
        data = response.json()
        assert "watchlists" in data
        assert len(data["watchlists"]) >= 1
        names = [w["name"] for w in data["watchlists"]]
        assert "default" in names

    async def test_create_watchlist(self, client: AsyncClient):
        """Test creating a new watchlist."""
        response = await client.post(
            "/api/v1/watchlists",
            json={"name": "test_watchlist", "description": "A test watchlist"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_watchlist"
        assert data["description"] == "A test watchlist"
        assert data["items_count"] == 0
        assert "id" in data
        assert "created_at" in data

    async def test_create_duplicate_watchlist(self, client: AsyncClient):
        """Test creating a watchlist with a duplicate name returns 409."""
        # First create
        await client.post(
            "/api/v1/watchlists",
            json={"name": "duplicate_test"}
        )
        # Second create with same name
        response = await client.post(
            "/api/v1/watchlists",
            json={"name": "duplicate_test"}
        )
        assert response.status_code == 409
        data = response.json()
        # FastAPI wraps HTTPException detail in "detail" key
        error_data = data.get("detail", data)
        assert "error" in error_data
        assert error_data["error"]["code"] == "DUPLICATE_WATCHLIST"

    async def test_get_watchlist_detail(self, client: AsyncClient):
        """Test getting watchlist detail by ID."""
        # First get the default watchlist ID
        list_response = await client.get("/api/v1/watchlists")
        watchlists = list_response.json()["watchlists"]
        default_wl = next(w for w in watchlists if w["name"] == "default")
        watchlist_id = default_wl["id"]

        response = await client.get(f"/api/v1/watchlists/{watchlist_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert "items" in data

    async def test_get_watchlist_not_found(self, client: AsyncClient):
        """Test getting a non-existent watchlist returns 404."""
        response = await client.get("/api/v1/watchlists/99999")
        assert response.status_code == 404
        data = response.json()
        # FastAPI wraps HTTPException detail in "detail" key
        error_data = data.get("detail", data)
        assert error_data["error"]["code"] == "WATCHLIST_NOT_FOUND"

    async def test_delete_watchlist(self, client: AsyncClient):
        """Test deleting a watchlist."""
        # Create a watchlist to delete
        create_response = await client.post(
            "/api/v1/watchlists",
            json={"name": "to_delete"}
        )
        watchlist_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/watchlists/{watchlist_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower() or "successfully" in data["message"].lower()

    async def test_delete_watchlist_not_found(self, client: AsyncClient):
        """Test deleting a non-existent watchlist returns 404."""
        response = await client.delete("/api/v1/watchlists/99999")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestHistoryEndpoint:
    """Tests for the /api/v1/history endpoints."""

    async def test_get_history_empty(self, client: AsyncClient):
        """Test getting history when no queries exist."""
        response = await client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "queries" in data
        assert data["total"] == 0
        assert len(data["queries"]) == 0

    async def test_get_history_with_pagination(self, client: AsyncClient):
        """Test history endpoint with limit and offset parameters."""
        response = await client.get("/api/v1/history", params={"limit": 10, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_delete_history_requires_params(self, client: AsyncClient):
        """Test that delete history requires either older_than_days or all param."""
        response = await client.delete("/api/v1/history")
        assert response.status_code == 400

    async def test_delete_all_history(self, client: AsyncClient):
        """Test deleting all history."""
        response = await client.delete("/api/v1/history", params={"all": "true"})
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert "message" in data


@pytest.mark.asyncio
class TestRatesEndpoint:
    """Tests for the /api/v1/rates endpoint (requires external API mocking)."""

    async def test_rates_missing_params(self, client: AsyncClient):
        """Test that rates endpoint returns 422 when required params are missing."""
        response = await client.get("/api/v1/rates")
        assert response.status_code == 422

    async def test_rates_missing_targets(self, client: AsyncClient):
        """Test that rates endpoint returns 422 when targets param is missing."""
        response = await client.get("/api/v1/rates", params={"base": "USD"})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestConvertEndpoint:
    """Tests for the /api/v1/convert endpoint."""

    async def test_convert_missing_body(self, client: AsyncClient):
        """Test that convert endpoint returns 422 when body is missing."""
        response = await client.post("/api/v1/convert")
        assert response.status_code == 422

    async def test_convert_invalid_body(self, client: AsyncClient):
        """Test that convert endpoint returns 422 for invalid body."""
        response = await client.post(
            "/api/v1/convert",
            json={"amount": -1, "from": "USD", "to": "EUR"}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestExportEndpoint:
    """Tests for the /api/v1/export endpoints."""

    async def test_export_history_invalid_format(self, client: AsyncClient):
        """Test export history with invalid format returns 400."""
        response = await client.get(
            "/api/v1/export/history",
            params={"format": "xml"}
        )
        assert response.status_code == 400

    async def test_export_history_csv(self, client: AsyncClient):
        """Test export history in CSV format (empty history)."""
        response = await client.get(
            "/api/v1/export/history",
            params={"format": "csv"}
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "") or "csv" in response.headers.get("content-disposition", "")

    async def test_export_history_json(self, client: AsyncClient):
        """Test export history in JSON format (empty history)."""
        response = await client.get(
            "/api/v1/export/history",
            params={"format": "json"}
        )
        assert response.status_code == 200

    async def test_export_watchlist_not_found(self, client: AsyncClient):
        """Test export watchlist with non-existent ID returns 404."""
        response = await client.get(
            "/api/v1/export/watchlist/99999",
            params={"format": "csv"}
        )
        assert response.status_code == 404

    async def test_export_watchlist_invalid_format(self, client: AsyncClient):
        """Test export watchlist with invalid format returns 400."""
        # Get the default watchlist ID first
        list_response = await client.get("/api/v1/watchlists")
        watchlists = list_response.json()["watchlists"]
        default_wl = next(w for w in watchlists if w["name"] == "default")
        watchlist_id = default_wl["id"]

        response = await client.get(
            f"/api/v1/export/watchlist/{watchlist_id}",
            params={"format": "xml"}
        )
        assert response.status_code == 400
