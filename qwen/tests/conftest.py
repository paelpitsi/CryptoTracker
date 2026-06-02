"""Shared test fixtures and configuration."""

import os
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./data/test_cryptotracker.db"
os.environ["LOG_LEVEL"] = "ERROR"

from cryptotracker.server.models.base import Base
from cryptotracker.server.models.currency import Currency
from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.database import get_session


# Use in-memory or file-based SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./data/test_cryptotracker.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Clean up test database file
    test_db_path = "./data/test_cryptotracker.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session with seed data (currencies and a default watchlist)."""
    # Seed fiat currencies
    fiat_currencies = [
        ("USD", "United States Dollar"),
        ("EUR", "Euro"),
        ("GBP", "Pound Sterling"),
        ("RUB", "Russian Ruble"),
    ]
    for code, name in fiat_currencies:
        db_session.add(Currency(code=code, name=name, type="fiat", is_active=True))

    # Seed crypto currencies
    crypto_currencies = [
        ("BTC", "Bitcoin", "bitcoin"),
        ("ETH", "Ethereum", "ethereum"),
    ]
    for code, name, cg_id in crypto_currencies:
        db_session.add(Currency(code=code, name=name, type="crypto", coingecko_id=cg_id, is_active=True))

    # Seed a default watchlist
    watchlist = Watchlist(name="default", description="Default watchlist")
    db_session.add(watchlist)

    await db_session.commit()
    yield db_session


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_session dependency for testing."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def client(seeded_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing FastAPI endpoints."""
    from cryptotracker.server.main import app

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
