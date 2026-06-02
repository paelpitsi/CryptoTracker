"""Watchlists router."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_session
from cryptotracker.server.services.watchlist_service import WatchlistService
from cryptotracker.server.schemas.watchlist import (
    WatchlistListResponse,
    WatchlistDetailResponse,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistDeleteResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistItemDeleteResponse
)
from cryptotracker.common.exceptions import (
    WatchlistNotFoundError,
    WatchlistItemNotFoundError,
    DuplicateWatchlistError,
    DuplicateWatchlistItemError,
    CurrencyNotFoundError
)
from cryptotracker.common.logger import logger

router = APIRouter(prefix="/api/v1", tags=["watchlists"])


@router.get("/watchlists", response_model=WatchlistListResponse)
async def get_watchlists(session: AsyncSession = Depends(get_session)):
    """Get all watchlists."""
    
    try:
        service = WatchlistService(session)
        result = await service.get_watchlists()
        return result
        
    except Exception as e:
        logger.error(f"Error in get_watchlists: {e}")
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


@router.post("/watchlists", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(
    request: WatchlistCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new watchlist."""
    
    try:
        service = WatchlistService(session)
        result = await service.create_watchlist(
            name=request.name,
            description=request.description
        )
        return result
        
    except DuplicateWatchlistError as e:
        logger.warning(f"Duplicate watchlist: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "DUPLICATE_WATCHLIST",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in create_watchlist: {e}")
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


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistDetailResponse)
async def get_watchlist(
    watchlist_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get detailed watchlist with current rates."""
    
    try:
        service = WatchlistService(session)
        result = await service.get_watchlist(watchlist_id)
        return result
        
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
    except Exception as e:
        logger.error(f"Error in get_watchlist: {e}")
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


@router.delete("/watchlists/{watchlist_id}", response_model=WatchlistDeleteResponse)
async def delete_watchlist(
    watchlist_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete a watchlist."""
    
    try:
        service = WatchlistService(session)
        result = await service.delete_watchlist(watchlist_id)
        return result
        
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
    except Exception as e:
        logger.error(f"Error in delete_watchlist: {e}")
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


@router.post("/watchlists/{watchlist_id}/items", response_model=WatchlistItemResponse, status_code=201)
async def add_watchlist_item(
    watchlist_id: int,
    request: WatchlistItemCreate,
    session: AsyncSession = Depends(get_session)
):
    """Add a currency pair to a watchlist."""
    
    try:
        service = WatchlistService(session)
        result = await service.add_item(
            watchlist_id=watchlist_id,
            base_currency=request.base_currency,
            target_currency=request.target_currency,
            currency_type=request.type
        )
        return result
        
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
    except DuplicateWatchlistItemError as e:
        logger.warning(f"Duplicate watchlist item: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "DUPLICATE_WATCHLIST_ITEM",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except CurrencyNotFoundError as e:
        logger.warning(f"Currency not found: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "CURRENCY_NOT_FOUND",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in add_watchlist_item: {e}")
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


@router.delete("/watchlists/{watchlist_id}/items/{item_id}", response_model=WatchlistItemDeleteResponse)
async def remove_watchlist_item(
    watchlist_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Remove a currency pair from a watchlist."""
    
    try:
        service = WatchlistService(session)
        result = await service.remove_item(
            watchlist_id=watchlist_id,
            item_id=item_id
        )
        return result
        
    except WatchlistItemNotFoundError as e:
        logger.warning(f"Watchlist item not found: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WATCHLIST_ITEM_NOT_FOUND",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in remove_watchlist_item: {e}")
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
