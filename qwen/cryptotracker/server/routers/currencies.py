"""Currencies router."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from cryptotracker.server.database import get_session
from cryptotracker.server.models.currency import Currency
from cryptotracker.server.schemas.currency import CurrencyListResponse, CurrencyResponse, CurrencySyncResponse
from cryptotracker.server.external.frankfurter import FrankfurterClient
from cryptotracker.server.external.coingecko import CoinGeckoClient
from cryptotracker.common.logger import logger

router = APIRouter(prefix="/api/v1", tags=["currencies"])


@router.get("/currencies", response_model=CurrencyListResponse)
async def get_currencies(
    type: Optional[str] = Query("all", description="Filter by type (fiat, crypto, all)"),
    search: Optional[str] = Query(None, description="Search by code or name"),
    session: AsyncSession = Depends(get_session)
):
    """Get list of all available currencies."""
    
    try:
        query = select(Currency)
        
        if type and type != "all":
            query = query.where(Currency.type == type)
        
        if search:
            search_term = f"%{search.upper()}%"
            query = query.where(
                or_(
                    Currency.code.ilike(search_term),
                    Currency.name.ilike(search_term)
                )
            )
        
        query = query.order_by(Currency.type, Currency.code)
        
        result = await session.execute(query)
        currencies = result.scalars().all()
        
        currency_responses = [
            CurrencyResponse(
                id=c.id,
                code=c.code,
                name=c.name,
                type=c.type,
                coingecko_id=c.coingecko_id,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in currencies
        ]
        
        return CurrencyListResponse(currencies=currency_responses)
        
    except Exception as e:
        logger.error(f"Error in get_currencies: {e}")
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


@router.post("/currencies/sync", response_model=CurrencySyncResponse)
async def sync_currencies(session: AsyncSession = Depends(get_session)):
    """Synchronize currencies from external APIs."""
    
    try:
        frankfurter = FrankfurterClient()
        coingecko = CoinGeckoClient()
        
        fiat_added = 0
        fiat_updated = 0
        crypto_added = 0
        crypto_updated = 0
        
        # Sync fiat currencies from Frankfurter
        try:
            fiat_currencies = await frankfurter.get_available_currencies()
            
            for code, name in fiat_currencies.items():
                result = await session.execute(
                    select(Currency).where(Currency.code == code)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    if existing.name != name or existing.type != "fiat":
                        existing.name = name
                        existing.type = "fiat"
                        fiat_updated += 1
                else:
                    currency = Currency(
                        code=code,
                        name=name,
                        type="fiat",
                        is_active=True
                    )
                    session.add(currency)
                    fiat_added += 1
        except Exception as e:
            logger.warning(f"Failed to sync fiat currencies: {e}")
        
        # Sync crypto currencies from CoinGecko
        try:
            crypto_list = await coingecko.get_coins_list()
            
            # Only sync top cryptocurrencies (limit to avoid too many)
            popular_cryptos = {
                "bitcoin": "BTC",
                "ethereum": "ETH",
                "binancecoin": "BNB",
                "solana": "SOL",
                "ripple": "XRP",
                "cardano": "ADA",
                "dogecoin": "DOGE",
                "polkadot": "DOT",
                "matic-network": "MATIC",
                "litecoin": "LTC"
            }
            
            for crypto in crypto_list:
                if crypto["id"] in popular_cryptos:
                    code = popular_cryptos[crypto["id"]]
                    name = crypto["name"]
                    
                    result = await session.execute(
                        select(Currency).where(Currency.code == code)
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        if existing.name != name or existing.coingecko_id != crypto["id"]:
                            existing.name = name
                            existing.coingecko_id = crypto["id"]
                            crypto_updated += 1
                    else:
                        currency = Currency(
                            code=code,
                            name=name,
                            type="crypto",
                            coingecko_id=crypto["id"],
                            is_active=True
                        )
                        session.add(currency)
                        crypto_added += 1
        except Exception as e:
            logger.warning(f"Failed to sync crypto currencies: {e}")
        
        await session.commit()
        
        return CurrencySyncResponse(
            fiat_added=fiat_added,
            fiat_updated=fiat_updated,
            crypto_added=crypto_added,
            crypto_updated=crypto_updated,
            message="Currency synchronization completed"
        )
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error in sync_currencies: {e}")
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
