"""
Router for /api/watch endpoints.

CRUD operations for the watchlist: add, list, delete currency pairs.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_db
from cryptotracker.server.models import Profile, WatchList, RateHistory
from cryptotracker.server.schemas import (
    WatchAddRequest,
    WatchAddResponse,
    WatchDeleteResponse,
    WatchListItem,
    WatchListResponse,
)
from cryptotracker.server.routers.rates import (
    _ensure_fiat_cache,
    _ensure_crypto_cache,
    _determine_pair_type,
    _crypto_symbol_to_id,
    _fiat_currencies_cache,
)
from cryptotracker.api.frankfurter import frankfurter_client
from cryptotracker.api.coingecko import coingecko_client


router = APIRouter(tags=["watchlist"])


async def _get_or_create_profile(
    db: AsyncSession, profile_name: str
) -> Profile:
    """Get or create a profile."""
    result = await db.execute(
        select(Profile).where(Profile.name == profile_name)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(name=profile_name)
        db.add(profile)
        await db.flush()
    return profile


@router.post("/watch", response_model=WatchAddResponse, status_code=201)
async def add_to_watchlist(
    body: WatchAddRequest,
    profile: str = Query("default", description="Profile name"),
    db: AsyncSession = Depends(get_db),
):
    """Add a currency pair to the watchlist."""
    base = body.base.lower().strip()
    target = body.target.lower().strip()

    if base == target:
        raise HTTPException(
            status_code=400,
            detail="Base and target currencies must be different.",
        )

    await _ensure_fiat_cache()
    await _ensure_crypto_cache()

    profile_obj = await _get_or_create_profile(db, profile)

    # Check if already tracked
    existing = await db.execute(
        select(WatchList).where(
            WatchList.profile_id == profile_obj.id,
            WatchList.base_currency == base,
            WatchList.target_currency == target,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Pair {base}→{target} is already in the watchlist. "
                    f"Use 'list-watch' to see all tracked pairs.",
        )

    pair_type = _determine_pair_type(base, target)

    entry = WatchList(
        profile_id=profile_obj.id,
        base_currency=base,
        target_currency=target,
        pair_type=pair_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    return WatchAddResponse(
        id=entry.id,
        base=entry.base_currency,
        target=entry.target_currency,
        pair_type=entry.pair_type,
        created_at=entry.created_at,
    )


@router.get("/watch", response_model=WatchListResponse)
async def list_watchlist(
    profile: str = Query("default", description="Profile name"),
    db: AsyncSession = Depends(get_db),
):
    """List all watched pairs with current rates."""
    profile_obj = await _get_or_create_profile(db, profile)

    result = await db.execute(
        select(WatchList).where(WatchList.profile_id == profile_obj.id)
    )
    entries = result.scalars().all()

    pairs: list[WatchListItem] = []

    for entry in entries:
        current_rate: Optional[float] = None
        rate_source = "unavailable"

        try:
            base = entry.base_currency
            target = entry.target_currency
            pair_type = entry.pair_type

            if pair_type == "fiat-fiat":
                rate_data = await frankfurter_client.get_rate(base, target)
                current_rate = rate_data["rate"]
                rate_source = "frankfurter"
            else:
                crypto_map = _crypto_symbol_to_id
                if base in crypto_map:
                    coin_id = crypto_map[base]
                    rate_data = await coingecko_client.get_simple_price(
                        coin_id, target
                    )
                    current_rate = rate_data["rate"]
                    rate_source = "coingecko"
                elif target in crypto_map:
                    coin_id = crypto_map[target]
                    rate_data = await coingecko_client.get_simple_price(
                        coin_id, base
                    )
                    inv_rate = (
                        1.0 / rate_data["rate"]
                        if rate_data["rate"] != 0
                        else 0.0
                    )
                    current_rate = inv_rate
                    rate_source = "coingecko"
                else:
                    # Try crypto-to-crypto
                    base_id = crypto_map.get(base, base)
                    target_id = crypto_map.get(target, target)
                    rate_data = await coingecko_client.get_crypto_to_crypto_rate(
                        base_id, target_id
                    )
                    current_rate = rate_data["rate"]
                    rate_source = "coingecko"
        except Exception:
            current_rate = None
            rate_source = "unavailable"

        pairs.append(WatchListItem(
            id=entry.id,
            base=entry.base_currency,
            target=entry.target_currency,
            pair_type=entry.pair_type,
            current_rate=current_rate,
            rate_source=rate_source,
            added_at=entry.created_at,
        ))

    return WatchListResponse(
        profile=profile,
        pairs=pairs,
        count=len(pairs),
    )


@router.delete("/watch/{watch_id}", response_model=WatchDeleteResponse)
async def remove_from_watchlist(
    watch_id: int,
    profile: str = Query("default", description="Profile name"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a currency pair from the watchlist."""
    profile_obj = await _get_or_create_profile(db, profile)

    result = await db.execute(
        select(WatchList).where(
            WatchList.id == watch_id,
            WatchList.profile_id == profile_obj.id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Watchlist entry with id={watch_id} not found "
                    f"for profile '{profile}'.",
        )

    await db.execute(
        delete(WatchList).where(WatchList.id == watch_id)
    )
    await db.flush()

    return WatchDeleteResponse(deleted=True, id=watch_id)