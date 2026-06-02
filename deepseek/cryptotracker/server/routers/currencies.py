"""
Router for /api/currencies and /api/crypto endpoints.

Provides lists of available fiat and cryptocurrencies with in-memory caching.
"""

import asyncio
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.api.frankfurter import frankfurter_client
from cryptotracker.api.coingecko import coingecko_client
from cryptotracker.server.database import get_db
from cryptotracker.server.schemas import (
    CryptoCurrenciesResponse,
    CryptoCurrency,
    CurrenciesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["currencies"])

# In-memory caches with TTL
_fiat_cache: dict | None = None
_fiat_cache_time: float = 0.0
_FIAT_CACHE_TTL: int = 3600  # 1 hour

_crypto_cache: list[dict] | None = None
_crypto_cache_time: float = 0.0
_CRYPTO_CACHE_TTL: int = 86400  # 24 hours


@router.get("/currencies", response_model=CurrenciesResponse)
async def get_currencies(
    profile: str = Query("default", description="Profile name"),
):
    """Get the list of available fiat currencies (cached 1 hour)."""
    global _fiat_cache, _fiat_cache_time

    now = time.time()
    if _fiat_cache is not None and (now - _fiat_cache_time) < _FIAT_CACHE_TTL:
        return CurrenciesResponse(
            source="frankfurter",
            currencies=_fiat_cache,
            count=len(_fiat_cache),
        )

    try:
        currencies = await frankfurter_client.get_currencies()
        _fiat_cache = currencies
        _fiat_cache_time = now
        logger.info("Fiat currencies cache refreshed (%d currencies)", len(currencies))
        return CurrenciesResponse(
            source="frankfurter",
            currencies=currencies,
            count=len(currencies),
        )
    except Exception as exc:
        if _fiat_cache is not None:
            logger.warning(
                "Failed to refresh fiat cache, using stale cache: %s", exc
            )
            return CurrenciesResponse(
                source="frankfurter (cached)",
                currencies=_fiat_cache,
                count=len(_fiat_cache),
            )
        raise HTTPException(
            status_code=502,
            detail=f"Cannot fetch currencies from Frankfurter: {exc}",
        )


@router.get("/crypto", response_model=CryptoCurrenciesResponse)
async def get_crypto_currencies(
    profile: str = Query("default", description="Profile name"),
):
    """Get the list of available cryptocurrencies (cached 24 hours)."""
    global _crypto_cache, _crypto_cache_time

    now = time.time()
    if (
        _crypto_cache is not None
        and (now - _crypto_cache_time) < _CRYPTO_CACHE_TTL
    ):
        items = [
            CryptoCurrency(id=c["id"], symbol=c["symbol"], name=c["name"])
            for c in _crypto_cache
        ]
        return CryptoCurrenciesResponse(
            source="coingecko",
            cryptocurrencies=items,
            count=len(items),
        )

    try:
        coins = await coingecko_client.get_coins_list()
        # Take top 250 by market cap (API returns sorted roughly by popularity)
        top250 = coins[:250]
        _crypto_cache = top250
        _crypto_cache_time = now
        logger.info(
            "Crypto currencies cache refreshed (%d currencies)", len(top250)
        )
        items = [
            CryptoCurrency(id=c["id"], symbol=c["symbol"], name=c["name"])
            for c in top250
        ]
        return CryptoCurrenciesResponse(
            source="coingecko",
            cryptocurrencies=items,
            count=len(items),
        )
    except Exception as exc:
        if _crypto_cache is not None:
            logger.warning(
                "Failed to refresh crypto cache, using stale cache: %s", exc
            )
            items = [
                CryptoCurrency(id=c["id"], symbol=c["symbol"], name=c["name"])
                for c in _crypto_cache
            ]
            return CryptoCurrenciesResponse(
                source="coingecko (cached)",
                cryptocurrencies=items,
                count=len(items),
            )
        raise HTTPException(
            status_code=502,
            detail=f"Cannot fetch cryptocurrencies from CoinGecko: {exc}",
        )
