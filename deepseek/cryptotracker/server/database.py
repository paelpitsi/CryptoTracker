"""
Database engine, session factory, and dependency injection for FastAPI.

Provides an async SQLAlchemy engine backed by aiosqlite and SQLite.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cryptotracker.config import settings
from cryptotracker.server.models import Base


def _get_db_url() -> str:
    """Build the async SQLite connection URL."""
    db_path = settings.db_full_path
    # Ensure the data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


# Singleton engine
_engine = None


def get_engine():
    """Return the async SQLAlchemy engine (lazy init)."""
    global _engine
    if _engine is None:
        db_url = _get_db_url()
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
        )
    return _engine


# Async session factory
_async_session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session maker (lazy init)."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def init_db() -> None:
    """Create all tables if they do not exist."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine and release resources."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _async_session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
