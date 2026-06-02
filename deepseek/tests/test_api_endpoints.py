"""
API endpoint tests for CryptoTracker.

Tests FastAPI endpoints with an in-memory SQLite database and mocked
external API clients (Frankfurter, CoinGecko).

Minimum 7 tests covering: server status, currencies, rate, convert,
watchlist CRUD, history, export.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — reset per-module caches between tests
# ---------------------------------------------------------------------------


def _clear_currencies_cache():
    """Reset the in-memory caches inside the currencies router module."""
    import cryptotracker.server.routers.currencies as cur_mod

    cur_mod._fiat_cache = None
    cur_mod._fiat_cache_time = 0.0
    cur_mod._crypto_cache = None
    cur_mod._crypto_cache_time = 0.0


def _clear_rates_cache():
    """Reset the in-memory caches inside the rates router module."""
    import cryptotracker.server.routers.rates as rates_mod

    rates_mod._fiat_currencies_cache = None
    rates_mod._crypto_symbol_to_id.clear()
    rates_mod._crypto_id_to_symbol.clear()


@pytest.fixture(autouse=True)
def _clear_module_caches():
    """Clear router-level caches before every API test."""
    _clear_currencies_cache()
    _clear_rates_cache()
    yield


# ---------------------------------------------------------------------------
# Mock API clients for the *server* layer
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_server_apis():
    """Patch the API client singletons used by server routers."""
    mock_ff = AsyncMock()
    mock_ff.get_currencies.return_value = {
        "EUR": "Euro",
        "USD": "United States Dollar",
        "GBP": "British Pound",
    }
    mock_ff.get_rate.return_value = {
        "base": "usd",
        "target": "eur",
        "rate": 0.92,
        "source": "frankfurter",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock_ff.check_health.return_value = "reachable"

    mock_cg = AsyncMock()
    mock_cg.get_coins_list.return_value = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
    ]
    mock_cg.get_simple_price.return_value = {
        "base": "bitcoin",
        "target": "usd",
        "rate": 67500.0,
        "source": "coingecko",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock_cg.get_crypto_to_crypto_rate.return_value = {
        "base": "bitcoin",
        "target": "ethereum",
        "rate": 18.5,
        "source": "coingecko",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock_cg.check_health.return_value = "reachable"

    with patch(
        "cryptotracker.api.frankfurter.frankfurter_client", mock_ff
    ), patch(
        "cryptotracker.api.coingecko.coingecko_client", mock_cg
    ):
        yield mock_ff, mock_cg


# ---------------------------------------------------------------------------
# Test 1 — GET /api/server/status
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_server_status(async_client):
    """``GET /api/server/status`` returns 200 with status='ok'."""
    response = await async_client.get("/api/server/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "external_apis" in data


# ---------------------------------------------------------------------------
# Test 2 — GET /api/currencies (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_currencies(async_client, mock_server_apis):
    """``GET /api/currencies`` returns the mocked fiat currencies list."""
    _clear_currencies_cache()
    response = await async_client.get("/api/currencies")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "frankfurter"
    assert "EUR" in data["currencies"]
    assert "USD" in data["currencies"]
    assert data["count"] > 0


# ---------------------------------------------------------------------------
# Test 3 — GET /api/rate: same base/target → 400
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_rate_same_currency_error(async_client):
    """``GET /api/rate?base=usd&target=usd`` must return 400."""
    response = await async_client.get(
        "/api/rate", params={"base": "usd", "target": "usd"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test 4 — POST /api/convert: negative amount → 422
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_convert_negative_amount(async_client):
    """``POST /api/convert`` with amount <= 0 must return 422."""
    response = await async_client.post(
        "/api/convert",
        params={"profile": "testprofile"},
        json={"base": "usd", "target": "eur", "amount": -10},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 5 — POST /api/watch: add pair → 201
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_watch_add_pair(async_client, mock_server_apis):
    """``POST /api/watch`` creates a watchlist entry and returns 201."""
    _clear_rates_cache()

    response = await async_client.post(
        "/api/watch",
        params={"profile": "testprofile"},
        json={"base": "btc", "target": "usd"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["base"] == "btc"
    assert data["target"] == "usd"
    assert "pair_type" in data


# ---------------------------------------------------------------------------
# Test 6 — POST /api/watch: duplicate → 409
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_watch_duplicate_pair(async_client, mock_server_apis):
    """Adding the same pair twice must return 409 Conflict."""
    _clear_rates_cache()

    await async_client.post(
        "/api/watch",
        params={"profile": "testprofile"},
        json={"base": "btc", "target": "usd"},
    )
    response = await async_client.post(
        "/api/watch",
        params={"profile": "testprofile"},
        json={"base": "btc", "target": "usd"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Test 7 — GET /api/watch: list watchlist
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_watch_list(async_client, mock_server_apis):
    """``GET /api/watch`` lists tracked pairs."""
    _clear_rates_cache()

    await async_client.post(
        "/api/watch",
        params={"profile": "testprofile"},
        json={"base": "btc", "target": "usd"},
    )
    response = await async_client.get(
        "/api/watch", params={"profile": "testprofile"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    pairs = data["pairs"]
    assert any(p["base"] == "btc" for p in pairs)


# ---------------------------------------------------------------------------
# Test 8 — DELETE /api/watch/{id}: remove pair
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_watch_delete(async_client, mock_server_apis):
    """``DELETE /api/watch/{id}`` removes a watchlist entry."""
    _clear_rates_cache()

    add_resp = await async_client.post(
        "/api/watch",
        params={"profile": "testprofile"},
        json={"base": "btc", "target": "usd"},
    )
    watch_id = add_resp.json()["id"]

    response = await async_client.delete(
        f"/api/watch/{watch_id}", params={"profile": "testprofile"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True
    assert data["id"] == watch_id


# ---------------------------------------------------------------------------
# Test 9 — DELETE /api/watch/{id}: non-existent → 404
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_watch_delete_not_found(async_client):
    """Deleting a non-existent watchlist entry returns 404."""
    response = await async_client.delete(
        "/api/watch/99999", params={"profile": "testprofile"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 10 — GET /api/history: empty for fresh profile
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_history_empty(async_client):
    """``GET /api/history`` returns an empty list for a new profile."""
    response = await async_client.get(
        "/api/history", params={"profile": "newprofile"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Test 11 — GET /api/export: JSON format
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_json(async_client):
    """``GET /api/export?format=json`` returns a valid JSON export."""
    response = await async_client.get(
        "/api/export",
        params={"profile": "testprofile", "format": "json", "dataset": "all"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "testprofile"
    assert "data" in data
    assert "exported_at" in data


# ---------------------------------------------------------------------------
# Test 12 — GET /api/export: CSV format
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_csv(async_client):
    """``GET /api/export?format=csv`` returns ``text/csv`` content."""
    response = await async_client.get(
        "/api/export",
        params={"profile": "testprofile", "format": "csv", "dataset": "all"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
