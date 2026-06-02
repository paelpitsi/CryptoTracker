"""FastAPI application main module."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cryptotracker.server.database import init_db
from cryptotracker.server.routers import health, rates, history, watchlists, currencies, export
from cryptotracker.common.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")
    yield
    # Shutdown
    logger.info("Shutting down server...")


app = FastAPI(
    title="CryptoTracker API",
    description="API for tracking cryptocurrency and fiat currency rates",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router)
app.include_router(rates.router)
app.include_router(history.router)
app.include_router(watchlists.router)
app.include_router(currencies.router)
app.include_router(export.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.critical(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


def run_server(host: str = "localhost", port: int = 8000, reload: bool = False, workers: int = 1):
    """Run the FastAPI server using uvicorn."""
    import uvicorn
    uvicorn.run(
        "cryptotracker.server.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers
    )
