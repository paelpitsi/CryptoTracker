"""
Pytest configuration and shared fixtures for CryptoTracker tests.

Provides:
- Temporary in-memory SQLite database via aiosqlite
- Mocked external API clients (Frankfurter, CoinGecko)
- FastAPI TestClient with overridden DB dependency
- Reset of global singletons between tests
"""

import asyncio
import contextlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_db_singletons(monkeypatch, tmp_path):
    """Before every test: point DB at a temp file and reset engine singletons.

    This fixture is ``autouse`` so every test gets a clean, isolated database.
    """
    db_path = tmp_path / "test_cryptotracker.db"
    # Patch settings *before* any other module accesses it
    monkeypatch.setattr(
        "cryptotracker.config.settings.db_path", str(db_path)
    )

    import cryptotracker.server.database as db_mod

    # Dispose old engine if one exists
    if db_mod._engine is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(db_mod.close_db())
            else:
                loop.run_until_complete(db_mod.close_db())
        except Exception:
            pass
    db_mod._engine = None
    db_mod._async_session_factory = None

    yield db_path

    # Teardown
    if db_mod._engine is not None:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop.run_until_complete(db_mod.close_db())
        except Exception:
            pass
    db_mod._engine = None
    db_mod._async_session_factory = None


# ---------------------------------------------------------------------------
# Mock external API clients
# ---------------------------------------------------------------------------


def _make_frankfurter_mock():
    """Create a reusable Frankfurter AsyncMock with sensible defaults."""
    mock = AsyncMock()
    mock.get_currencies.return_value = {
        "EUR": "Euro",
        "USD": "United States Dollar",
        "GBP": "British Pound",
        "RUB": "Russian Ruble",
        "JPY": "Japanese Yen",
    }
    mock.get_rate.return_value = {
        "base": "usd",
        "target": "eur",
        "rate": 0.92,
        "source": "frankfurter",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock.check_health.return_value = "reachable"
    return mock


@pytest.fixture
def mock_frankfurter():
    """Return an AsyncMock that patches the Frankfurter client singleton.

    Patches at *both* the API source module and every consumer module so
    that ``from ... import ...`` references are also replaced.
    """
    mock = _make_frankfurter_mock()

    targets = [
        "cryptotracker.api.frankfurter.frankfurter_client",
        "cryptotracker.cli.commands.frankfurter_client",
    ]
    with contextlib.ExitStack() as stack:
        for t in targets:
            stack.enter_context(patch(t, mock))
        yield mock


def _make_coingecko_mock():
    """Create a reusable CoinGecko AsyncMock with sensible defaults."""
    mock = AsyncMock()
    mock.get_coins_list.return_value = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        {"id": "tether", "symbol": "usdt", "name": "Tether"},
        {"id": "binancecoin", "symbol": "bnb", "name": "BNB"},
        {"id": "solana", "symbol": "sol", "name": "Solana"},
    ]
    mock.get_simple_price.return_value = {
        "base": "bitcoin",
        "target": "usd",
        "rate": 67500.0,
        "source": "coingecko",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock.get_crypto_to_crypto_rate.return_value = {
        "base": "bitcoin",
        "target": "ethereum",
        "rate": 18.5,
        "source": "coingecko",
        "fetched_at": datetime.now(timezone.utc),
    }
    mock.check_health.return_value = "reachable"
    return mock


@pytest.fixture
def mock_coingecko():
    """Return an AsyncMock that patches the CoinGecko client singleton.

    Patches at *both* the API source module and every consumer module so
    that ``from ... import ...`` references are also replaced.
    """
    mock = _make_coingecko_mock()

    targets = [
        "cryptotracker.api.coingecko.coingecko_client",
        "cryptotracker.cli.commands.coingecko_client",
    ]
    with contextlib.ExitStack() as stack:
        for t in targets:
            stack.enter_context(patch(t, mock))
        yield mock


@pytest.fixture
def mock_apis(mock_frankfurter, mock_coingecko):
    """Convenience fixture that mocks both external APIs simultaneously."""
    return mock_frankfurter, mock_coingecko


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app():
    """Return the FastAPI app instance (no lifespan — DB is managed
    explicitly by the async_client fixture below).
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from cryptotracker.server.routers import (
        currencies,
        export,
        history,
        rates,
        server_status,
        watchlist,
    )

    app = FastAPI(
        title="CryptoTracker API (test)",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(server_status.router, prefix="/api")
    app.include_router(currencies.router, prefix="/api")
    app.include_router(rates.router, prefix="/api")
    app.include_router(watchlist.router, prefix="/api")
    app.include_router(history.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    return app


@pytest.fixture
async def async_client(test_app):
    """Async HTTP client bound to the test FastAPI app.

    Manually initialises and tears down the database since we removed
    the lifespan handler to avoid async-in-sync-fixture issues.
    """
    from cryptotracker.server.database import init_db, close_db

    await init_db()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client
    await close_db()


# ---------------------------------------------------------------------------
# Helpers for CLI tests
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_runner():
    """Return a Typer CliRunner for invoking CLI commands."""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture(autouse=True)
def _mock_server_unreachable():
    """All CLI tests run in --no-server / direct mode by default.

    Patches ``_server_reachable`` to always return ``False`` so CLI commands
    fall through to direct DB mode without trying to contact a running server.
    """
    with patch(
        "cryptotracker.cli.commands._server_reachable",
        AsyncMock(return_value=False),
    ):
        yield
