"""Database configuration and session management."""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from cryptotracker.server.models.base import Base
from cryptotracker.server.models.currency import Currency
from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.common.config import settings
from cryptotracker.common.logger import logger


# Convert sqlite:// to sqlite+aiosqlite:// for async support
def get_async_database_url(url: str) -> str:
    """Convert sync database URL to async."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


DATABASE_URL = get_async_database_url(settings.database_url)

# Ensure data directory exists
db_path = settings.database_url.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables and seed data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed currencies if empty
    async with async_session_factory() as session:
        result = await session.execute(select(Currency).limit(1))
        if result.scalar_one_or_none() is None:
            await seed_currencies(session)
        
        # Create default watchlist if none exists
        result = await session.execute(select(Watchlist).limit(1))
        if result.scalar_one_or_none() is None:
            default_watchlist = Watchlist(
                name="default",
                description="Default watchlist"
            )
            session.add(default_watchlist)
            await session.commit()
            logger.info("Created default watchlist")


async def seed_currencies(session: AsyncSession) -> None:
    """Seed the currencies table with popular fiat and crypto currencies."""
    
    # Popular fiat currencies
    fiat_currencies = [
        ("USD", "United States Dollar"),
        ("EUR", "Euro"),
        ("GBP", "Pound Sterling"),
        ("JPY", "Japanese Yen"),
        ("RUB", "Russian Ruble"),
        ("CNY", "Chinese Renminbi Yuan"),
        ("CHF", "Swiss Franc"),
        ("CAD", "Canadian Dollar"),
        ("AUD", "Australian Dollar"),
        ("INR", "Indian Rupee"),
        ("BRL", "Brazilian Real"),
        ("KRW", "South Korean Won"),
        ("MXN", "Mexican Peso"),
        ("SGD", "Singapore Dollar"),
        ("HKD", "Hong Kong Dollar"),
        ("NOK", "Norwegian Krone"),
        ("NZD", "New Zealand Dollar"),
        ("SEK", "Swedish Krona"),
        ("DKK", "Danish Krone"),
        ("PLN", "Polish Złoty"),
        ("TRY", "Turkish Lira"),
        ("ZAR", "South African Rand"),
        ("CZK", "Czech Koruna"),
        ("HUF", "Hungarian Forint"),
        ("ILS", "Israeli New Sheqel"),
        ("THB", "Thai Baht"),
        ("MYR", "Malaysian Ringgit"),
        ("PHP", "Philippine Peso"),
        ("IDR", "Indonesian Rupiah"),
        ("ISK", "Icelandic Króna"),
        ("BGN", "Bulgarian Lev"),
        ("RON", "Romanian Leu"),
    ]
    
    for code, name in fiat_currencies:
        currency = Currency(
            code=code,
            name=name,
            type="fiat",
            is_active=True
        )
        session.add(currency)
    
    # Popular cryptocurrencies
    crypto_currencies = [
        ("BTC", "Bitcoin", "bitcoin"),
        ("ETH", "Ethereum", "ethereum"),
        ("BNB", "BNB", "binancecoin"),
        ("SOL", "Solana", "solana"),
        ("XRP", "Ripple", "ripple"),
        ("ADA", "Cardano", "cardano"),
        ("DOGE", "Dogecoin", "dogecoin"),
        ("DOT", "Polkadot", "polkadot"),
        ("MATIC", "Polygon", "matic-network"),
        ("LTC", "Litecoin", "litecoin"),
    ]
    
    for code, name, coingecko_id in crypto_currencies:
        currency = Currency(
            code=code,
            name=name,
            type="crypto",
            coingecko_id=coingecko_id,
            is_active=True
        )
        session.add(currency)
    
    await session.commit()
    logger.info(f"Seeded {len(fiat_currencies)} fiat and {len(crypto_currencies)} crypto currencies")
