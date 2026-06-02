"""Export router."""

from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_session
from cryptotracker.server.services.export_service import ExportService
from cryptotracker.common.exceptions import WatchlistNotFoundError
from cryptotracker.common.logger import logger

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/export/history")
async def export_history(
    format: str = Query(..., description="Export format (csv or json)"),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    command_type: Optional[str] = Query(None, description="Filter by command type"),
    session: AsyncSession = Depends(get_session)
):
    """Export query history to CSV or JSON."""
    
    try:
        if format not in ["csv", "json"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Format must be 'csv' or 'json'",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        service = ExportService(session)
        content, filename, content_type = await service.export_history(
            format=format,
            date_from=date_from,
            date_to=date_to,
            command_type=command_type
        )
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in export_history: {e}")
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


@router.get("/export/watchlist/{watchlist_id}")
async def export_watchlist(
    watchlist_id: int,
    format: str = Query(..., description="Export format (csv or json)"),
    include_rates: bool = Query(True, description="Include current rates"),
    session: AsyncSession = Depends(get_session)
):
    """Export watchlist to CSV or JSON."""
    
    try:
        if format not in ["csv", "json"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Format must be 'csv' or 'json'",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        service = ExportService(session)
        content, filename, content_type = await service.export_watchlist(
            watchlist_id=watchlist_id,
            format=format,
            include_rates=include_rates
        )
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except WatchlistNotFoundError as e:
        logger.warning(f"Watchlist not found: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WATCHLIST_NOT_FOUND",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in export_watchlist: {e}")
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
