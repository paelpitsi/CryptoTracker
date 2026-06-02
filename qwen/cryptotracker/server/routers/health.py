"""Health check router."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from cryptotracker.server.database import get_session
from cryptotracker.server.schemas.common import HealthResponse
from cryptotracker.common.logger import logger

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """Check server health and database connection."""
    
    try:
        # Test database connection
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = "disconnected"
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Database connection failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    return HealthResponse(
        status="ok",
        version="1.0.0",
        database=db_status,
        timestamp=datetime.utcnow()
    )
