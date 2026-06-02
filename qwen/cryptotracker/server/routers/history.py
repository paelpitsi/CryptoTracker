"""History router."""

from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_session
from cryptotracker.server.services.history_service import HistoryService
from cryptotracker.server.schemas.history import HistoryListResponse, HistoryDeleteResponse
from cryptotracker.common.logger import logger

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    command_type: Optional[str] = Query(None, description="Filter by command type"),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    session: AsyncSession = Depends(get_session)
):
    """Get query history with optional filters."""
    
    try:
        service = HistoryService(session)
        result = await service.get_history(
            limit=limit,
            offset=offset,
            command_type=command_type,
            date_from=date_from,
            date_to=date_to
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@router.delete("/history", response_model=HistoryDeleteResponse)
async def delete_history(
    older_than_days: Optional[int] = Query(None, description="Delete records older than N days"),
    all: bool = Query(False, description="Delete all history"),
    session: AsyncSession = Depends(get_session)
):
    """Delete query history records."""
    
    try:
        if not older_than_days and not all:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Either 'older_than_days' or 'all' parameter must be provided",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        service = HistoryService(session)
        result = await service.delete_history(
            older_than_days=older_than_days,
            delete_all=all
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_history: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
