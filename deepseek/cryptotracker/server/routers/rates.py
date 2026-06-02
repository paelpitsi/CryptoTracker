"""
Router for /api/rate and /api/convert endpoints.

Handles fetching exchange rates and performing currency conversions.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.api.frankfurter import frankfurter_client
from cryptotracker.api.coingecko import coingecko_client
from cryptotracker.server.database import get_db
from cryptotracker.server.models import (
    Profile,
    RateHistory,
    ConversionHistory,
    RequestLog,
)
from cryptotracker.server.schemas import (
    ConvertRequest,
    ConvertResponse,
    RateResponse,
)

router = APIRouter(tags=["rates"])

# Cache for known fiat currencies (populated lazily)
_fiat_currencies_cache: set[str] | None = None
# Cache for known crypto IDs mapped from symbol to coin ID
_crypto_symbol_to_id: dict[str, str] = {}
_crypto_id_to_symbol: dict[str, str] = {}


async def _ensure_fiat_cache() -> set[str]:
    """Ensure the fiat currencies cache is populated."""
    global _fiat_currencies_cache
    if _fiat_currencies_cache is None:
        try:
            currencies = await frankfurter_client.get_currencies()
            _fiat_currencies_cache = {k.lower() for k in currencies}
        except Exception:
            _fiat_currencies_cache = set()
    return _fiat_currencies_cache


async def _ensure_crypto_cache() -> dict[str, str]:
    """Ensure the crypto symbol->id cache is populated."""
    global _crypto_symbol_to_id, _crypto_id_to_symbol
    if not _crypto_symbol_to_id:
        _known = {
            "btc": "bitcoin", "eth": "ethereum", "usdt": "tether",
            "bnb": "binancecoin", "sol": "solana", "xrp": "ripple",
            "usdc": "usd-coin", "ada": "cardano", "doge": "dogecoin",
            "dot": "polkadot", "matic": "matic-network",
            "shib": "shiba-inu", "ltc": "litecoin", "link": "chainlink",
            "avax": "avalanche-2", "uni": "uniswap", "near": "near",
            "aave": "aave", "dash": "dash", "zec": "zcash",
            "xmr": "monero", "xlm": "stellar", "trx": "tron",
            "atom": "cosmos", "etc": "ethereum-classic",
        }
        try:
            coins = await coingecko_client.get_coins_list()
            for coin in coins:
                symbol = coin["symbol"].lower()
                cid = coin["id"]
                if symbol not in _crypto_symbol_to_id:
                    _crypto_symbol_to_id[symbol] = cid
                    _crypto_id_to_symbol[cid] = symbol
                elif symbol in _known and cid == _known[symbol]:
                    _crypto_symbol_to_id[symbol] = cid
                    _crypto_id_to_symbol[cid] = symbol
        except Exception:
            pass
    return _crypto_symbol_to_id


def _determine_pair_type(base: str, target: str) -> str:
    """Determine the type of currency pair.

    Args:
        base: Base currency code (lowercase).
        target: Target currency code (lowercase).

    Returns:
        'fiat-fiat', 'crypto-fiat', or 'crypto-crypto'.
    """
    fiat_set = _fiat_currencies_cache or set()
    crypto_map = _crypto_symbol_to_id

    base_is_fiat = base.lower() in fiat_set
    target_is_fiat = target.lower() in fiat_set
    base_is_crypto = base.lower() in crypto_map
    target_is_crypto = target.lower() in crypto_map

    if base_is_fiat and target_is_fiat:
        return "fiat-fiat"
    if base_is_crypto and target_is_fiat:
        return "crypto-fiat"
    if base_is_fiat and target_is_crypto:
        return "crypto-fiat"  # treat symmetrically for API purposes
    if base_is_crypto and target_is_crypto:
        return "crypto-crypto"
    # If unknown, try to infer
    if base_is_fiat:
        return "crypto-fiat"  # assume target is crypto
    if base_is_crypto:
        return "crypto-fiat"
    return "crypto-fiat"  # default assumption


async def _get_or_create_profile(
    db: AsyncSession, profile_name: str
) -> Profile:
    """Get an existing profile or create a new one.

    Args:
        db: Database session.
        profile_name: Name of the profile.

    Returns:
        The Profile instance.
    """
    result = await db.execute(
        select(Profile).where(Profile.name == profile_name)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(name=profile_name)
        db.add(profile)
        await db.flush()
    return profile


async def _log_request(
    db: AsyncSession,
    profile: Profile,
    command: str,
    params: dict,
    status_code: int,
    error_message: str | None = None,
) -> None:
    """Log a request to the RequestLog table.

    Args:
        db: Database session.
        profile: The profile making the request.
        command: Command name ('rate', 'convert', etc.).
        params: Command parameters dict.
        status_code: HTTP status code (0 for local errors).
        error_message: Optional error description.
    """
    log_entry = RequestLog(
        profile_id=profile.id,
        command=command,
        params_json=json.dumps(params),
        status_code=status_code,
        error_message=error_message,
    )
    db.add(log_entry)


# ---------------------------------------------------------------------------
# GET /api/rate
# ---------------------------------------------------------------------------


@router.get("/rate", response_model=RateResponse)
async def get_rate(
    base: str = Query(..., description="Base currency code"),
    target: str = Query(..., description="Target currency code"),
    profile: str = Query("default", description="Profile name"),
    db: AsyncSession = Depends(get_db),
):
    """Get the current exchange rate between two currencies."""
    base = base.lower().strip()
    target = target.lower().strip()

    if base == target:
        raise HTTPException(
            status_code=400, detail="Base and target currencies must be different."
        )

    # Ensure caches
    await _ensure_fiat_cache()
    await _ensure_crypto_cache()

    # Get or create profile
    profile_obj = await _get_or_create_profile(db, profile)

    pair_type = _determine_pair_type(base, target)

    try:
        if pair_type == "fiat-fiat":
            result = await frankfurter_client.get_rate(base, target)
            rate_data = result
        elif pair_type == "crypto-crypto":
            # Both are crypto — compute via USD
            base_id = _crypto_symbol_to_id.get(
                base, base
            )
            target_id = _crypto_symbol_to_id.get(
                target, target
            )
            if base_id == base or target_id == target:
                # Try as CoinGecko ID directly
                pass
            result = await coingecko_client.get_crypto_to_crypto_rate(
                base_id, target_id
            )
            # Map IDs back to symbols
            result["base"] = base
            result["target"] = target
            rate_data = result
        else:
            # crypto-fiat or fiat-crypto
            if base in _crypto_symbol_to_id:
                coin_id = _crypto_symbol_to_id[base]
                vs_currency = target
                result = await coingecko_client.get_simple_price(
                    coin_id, vs_currency
                )
                result["base"] = base
                rate_data = result
            elif target in _crypto_symbol_to_id:
                coin_id = _crypto_symbol_to_id[target]
                vs_currency = base
                result = await coingecko_client.get_simple_price(
                    coin_id, vs_currency
                )
                # Invert: we want base->target
                inv_rate = 1.0 / result["rate"] if result["rate"] != 0 else 0.0
                rate_data = {
                    "base": base,
                    "target": target,
                    "rate": inv_rate,
                    "source": "coingecko",
                    "fetched_at": result["fetched_at"],
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Currency '{base}' or '{target}' not found.",
                )

        # Save to RateHistory
        rate_entry = RateHistory(
            profile_id=profile_obj.id,
            base_currency=base,
            target_currency=target,
            rate=rate_data["rate"],
            source=rate_data["source"],
            fetched_at=rate_data["fetched_at"],
        )
        db.add(rate_entry)

        # Log request
        await _log_request(
            db, profile_obj, "rate",
            {"base": base, "target": target},
            200,
        )

        return RateResponse(**rate_data)

    except HTTPException:
        raise
    except Exception as exc:
        await _log_request(
            db, profile_obj, "rate",
            {"base": base, "target": target},
            502,
            str(exc),
        )
        raise HTTPException(
            status_code=502,
            detail=f"External API error: {exc}",
        )


# ---------------------------------------------------------------------------
# POST /api/convert
# ---------------------------------------------------------------------------


@router.post("/convert", response_model=ConvertResponse)
async def convert_currency(
    body: ConvertRequest,
    profile: str = Query("default", description="Profile name"),
    db: AsyncSession = Depends(get_db),
):
    """Convert an amount from one currency to another."""
    base = body.base.lower().strip()
    target = body.target.lower().strip()
    amount = body.amount

    if amount <= 0:
        raise HTTPException(
            status_code=422,
            detail="Amount must be positive.",
        )

    if base == target:
        raise HTTPException(
            status_code=400,
            detail="Base and target currencies must be different.",
        )

    # Ensure caches
    await _ensure_fiat_cache()
    await _ensure_crypto_cache()

    profile_obj = await _get_or_create_profile(db, profile)
    pair_type = _determine_pair_type(base, target)

    try:
        # Fetch rate using the same logic as /api/rate
        if pair_type == "fiat-fiat":
            result = await frankfurter_client.get_rate(base, target)
            rate_data = result
        elif pair_type == "crypto-crypto":
            base_id = _crypto_symbol_to_id.get(base, base)
            target_id = _crypto_symbol_to_id.get(target, target)
            result = await coingecko_client.get_crypto_to_crypto_rate(
                base_id, target_id
            )
            result["base"] = base
            result["target"] = target
            rate_data = result
        else:
            if base in _crypto_symbol_to_id:
                coin_id = _crypto_symbol_to_id[base]
                result = await coingecko_client.get_simple_price(
                    coin_id, target
                )
                result["base"] = base
                rate_data = result
            elif target in _crypto_symbol_to_id:
                coin_id = _crypto_symbol_to_id[target]
                result = await coingecko_client.get_simple_price(
                    coin_id, base
                )
                inv_rate = (
                    1.0 / result["rate"] if result["rate"] != 0 else 0.0
                )
                rate_data = {
                    "base": base,
                    "target": target,
                    "rate": inv_rate,
                    "source": "coingecko",
                    "fetched_at": result["fetched_at"],
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Currency '{base}' or '{target}' not found.",
                )

        rate = rate_data["rate"]
        result_amount = round(amount * rate, 8)
        converted_at = datetime.now(timezone.utc)

        # Save to ConversionHistory
        conv_entry = ConversionHistory(
            profile_id=profile_obj.id,
            base_currency=base,
            target_currency=target,
            amount=amount,
            result=result_amount,
            rate=rate,
            source=rate_data["source"],
            created_at=converted_at,
        )
        db.add(conv_entry)

        # Log request
        await _log_request(
            db, profile_obj, "convert",
            {"base": base, "target": target, "amount": amount},
            200,
        )

        return ConvertResponse(
            base=base,
            target=target,
            amount=amount,
            result=result_amount,
            rate=rate,
            source=rate_data["source"],
            converted_at=converted_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        await _log_request(
            db, profile_obj, "convert",
            {"base": base, "target": target, "amount": amount},
            502,
            str(exc),
        )
        raise HTTPException(
            status_code=502,
            detail=f"External API error: {exc}",
        )