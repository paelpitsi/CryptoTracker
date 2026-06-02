"""Rates router."""

from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_session
from cryptotracker.server.services.rate_service import RateService
from cryptotracker.server.schemas.rates import RatesResponse, ConvertRequest, ConvertResponse
from cryptotracker.common.exceptions import CurrencyNotFoundError, ExternalAPIError
from cryptotracker.common.logger import logger

router = APIRouter(prefix="/api/v1", tags=["rates"])


@router.get("/rates", response_model=RatesResponse)
async def get_rates(
    base: str = Query(..., description="Base currency code"),
    targets: str = Query(..., description="Target currencies (comma-separated)"),
    type: str = Query("all", description="Currency type (fiat, crypto, all)"),
    session: AsyncSession = Depends(get_session)
):
    """Get exchange rates for multiple target currencies."""
    
    try:
        target_list = [t.strip().upper() for t in targets.split(",")]
        
        service = RateService(session)
        result = await service.get_rates(
            base=base.upper(),
            targets=target_list,
            currency_type=type
        )
        
        return result
        
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
    except ExternalAPIError as e:
        logger.error(f"External API error: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "EXTERNAL_API_ERROR",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_rates: {e}")
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


@router.post("/convert", response_model=ConvertResponse)
async def convert_currency(
    request: ConvertRequest,
    session: AsyncSession = Depends(get_session)
):
    """Convert amount from one currency to another."""
    
    try:
        service = RateService(session)
        result = await service.convert(
            amount=request.amount,
            from_currency=request.from_currency.upper(),
            to_currency=request.to_currency.upper(),
            currency_type=request.type
        )
        
        return result
        
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
    except ExternalAPIError as e:
        logger.error(f"External API error: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "EXTERNAL_API_ERROR",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in convert: {e}")
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
