"""
FastAPI application factory for the CryptoTracker server.

Creates and configures the FastAPI app with all routers, lifespan handler,
CORS middleware, and global exception handling.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cryptotracker.config import settings
from cryptotracker.server.database import init_db, close_db
from cryptotracker.server.routers import (
    rates,
    watchlist,
    history,
    export,
    currencies,
    server_status,
)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging() -> None:
    """Configure application logging via the standard logging module."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: initialize DB on startup, close on shutdown."""
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready at %s", settings.db_full_path)
    yield
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance ready to be served by uvicorn.
    """
    app = FastAPI(
        title="CryptoTracker API",
        version="1.0.0",
        description=(
            "REST API for CryptoTracker — cryptocurrency and fiat "
            "exchange rate tracking."
        ),
        lifespan=lifespan,
    )

    # CORS — allow local CLI clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(server_status.router, prefix="/api")
    app.include_router(currencies.router, prefix="/api")
    app.include_router(rates.router, prefix="/api")
    app.include_router(watchlist.router, prefix="/api")
    app.include_router(history.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch unhandled exceptions and return a 500 JSON response."""
        logger = logging.getLogger(__name__)
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "internal_error",
            },
        )

    return app


# Module-level app instance for uvicorn
app = create_app()