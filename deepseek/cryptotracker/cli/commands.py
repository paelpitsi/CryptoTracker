"""
CLI command implementations for CryptoTracker.

Each function is a Typer command callback.  The commands support two modes:

1. **Server mode** (default): sends HTTP requests to the local FastAPI server.
2. **Direct mode** (fallback, ``--no-server``): if the server is unreachable or
   explicitly disabled, commands call external APIs directly and write to the
   local SQLite database via SQLAlchemy.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import typer
from sqlalchemy import select

from cryptotracker.api.client import build_client, request_with_retry
from cryptotracker.api.coingecko import coingecko_client
from cryptotracker.api.frankfurter import frankfurter_client
from cryptotracker.cli.errors import (
    EXIT_EXTERNAL_API_ERROR,
    EXIT_SERVER_UNREACHABLE,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    EXIT_EXPORT_ERROR,
    handle_cli_error,
    handle_connection_error,
    handle_http_error,
)
from cryptotracker.cli.formatting import (
    console,
    convert_panel,
    error_panel,
    export_panel,
    history_table,
    rate_panel,
    server_banner,
    watch_add_panel,
    watch_remove_panel,
    watchlist_table,
    create_progress,
)
from cryptotracker.config import settings
from cryptotracker.server.database import (
    get_session_factory,
    init_db,
    close_db,
)
from cryptotracker.server.models import (
    Profile,
    RateHistory,
    ConversionHistory,
    WatchList,
    RequestLog,
)

# ---------------------------------------------------------------------------
# Global Typer "state" — injected via main.py callback
# ---------------------------------------------------------------------------

_profile_name: str = "default"
_server_url: str = "http://localhost:8420"
_use_server: bool = True


def set_global_options(profile: str, server_url: str, use_server: bool) -> None:
    """Called from main.py callback to set global CLI options."""
    global _profile_name, _server_url, _use_server
    _profile_name = profile
    _server_url = server_url.rstrip("/")
    _use_server = use_server


# ---------------------------------------------------------------------------
# Helpers: direct mode DB access
# ---------------------------------------------------------------------------


async def _direct_get_or_create_profile() -> Profile:
    """Get or create a profile via direct DB access."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Profile).where(Profile.name == _profile_name)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = Profile(name=_profile_name)
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
        return profile


async def _direct_log_request(
    command: str,
    params: dict,
    status_code: int,
    error_message: Optional[str] = None,
) -> None:
    """Write a request log via direct DB access."""
    factory = get_session_factory()
    async with factory() as session:
        profile = await _direct_get_or_create_profile()
        log = RequestLog(
            profile_id=profile.id,
            command=command,
            params_json=json.dumps(params),
            status_code=status_code,
            error_message=error_message,
        )
        session.add(log)
        await session.commit()


# ---------------------------------------------------------------------------
# Helpers: server communication
# ---------------------------------------------------------------------------


async def _server_get(
    path: str, params: Optional[dict] = None
) -> dict:
    """Send a GET request to the server API.

    Args:
        path: API path (e.g., '/api/rate').
        params: Query parameters dict.

    Returns:
        Parsed JSON response.
    """
    full_params = {"profile": _profile_name}
    if params:
        full_params.update(params)

    async with build_client() as client:
        response = await request_with_retry(
            client,
            "GET",
            f"{_server_url}{path}",
            params=full_params,
            max_retries=1,
        )
        response.raise_for_status()
        return response.json()


async def _server_post(
    path: str, body: dict, params: Optional[dict] = None
) -> dict:
    """Send a POST request to the server API."""
    full_params = {"profile": _profile_name}
    if params:
        full_params.update(params)

    async with build_client() as client:
        response = await request_with_retry(
            client,
            "POST",
            f"{_server_url}{path}",
            params=full_params,
            json=body,
            max_retries=1,
        )
        response.raise_for_status()
        return response.json()


async def _server_delete(path: str) -> dict:
    """Send a DELETE request to the server API."""
    async with build_client() as client:
        response = await request_with_retry(
            client,
            "DELETE",
            f"{_server_url}{path}",
            params={"profile": _profile_name},
            max_retries=1,
        )
        response.raise_for_status()
        return response.json()


async def _server_reachable() -> bool:
    """Check if the CryptoTracker server is reachable."""
    try:
        async with build_client() as client:
            response = await client.get(
                f"{_server_url}/api/server/status", timeout=3.0
            )
            return response.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 8.1  rate
# ---------------------------------------------------------------------------


async def _rate_command(base: str, target: str) -> None:
    """Core async logic for the 'rate' command."""
    base = base.lower().strip()
    target = target.lower().strip()

    if base == target:
        handle_cli_error(
            "Invalid Input",
            "Base and target currencies must be different.",
        )

    if _use_server and await _server_reachable():
        try:
            data = await _server_get(
                "/api/rate", {"base": base, "target": target}
            )
            rate_panel(
                base=data["base"],
                target=data["target"],
                rate=data["rate"],
                source=data["source"],
                fetched_at=datetime.fromisoformat(
                    data["fetched_at"].replace("Z", "+00:00")
                ),
            )
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            # Fall through to direct mode
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        # Determine pair type
        fiat_set: set[str] = set()
        crypto_ids: dict[str, str] = {}
        try:
            currencies = await frankfurter_client.get_currencies()
            fiat_set = {k.lower() for k in currencies}
        except Exception:
            pass
        try:
            coins = await coingecko_client.get_coins_list()
            # Prefer well-known coin IDs over obscure ones with the same symbol.
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
            for coin in coins:
                sym = coin["symbol"].lower()
                cid = coin["id"]
                if sym not in crypto_ids:
                    crypto_ids[sym] = cid
                elif sym in _known and cid == _known[sym]:
                    crypto_ids[sym] = cid
        except Exception:
            pass

        base_is_fiat = base in fiat_set
        target_is_fiat = target in fiat_set
        base_is_crypto = base in crypto_ids
        target_is_crypto = target in crypto_ids

        # Heuristic: if both are 3-letter alpha codes AND neither is a
        # known crypto symbol, treat as fiat-fiat pair (Frankfurter).
        base_looks_fiat = base_is_fiat or (
            not base_is_crypto and len(base) == 3 and base.isalpha()
        )
        target_looks_fiat = target_is_fiat or (
            not target_is_crypto and len(target) == 3 and target.isalpha()
        )

        try:
            # Priority 1: known fiat-fiat or looks like fiat-fiat
            if base_looks_fiat and target_looks_fiat:
                try:
                    result = await frankfurter_client.get_rate(base, target)
                    if result.get("rate", 0) <= 0:
                        raise ValueError("Zero rate from Frankfurter")
                except Exception:
                    raise RuntimeError(
                        f"Currency pair {base}/{target} is not supported "
                        f"by Frankfurter. Try crypto pairs instead."
                    )
            elif base_is_crypto and target_looks_fiat:
                result = await coingecko_client.get_simple_price(
                    crypto_ids[base], target
                )
                result["base"] = base
            elif base_looks_fiat and target_is_crypto:
                result = await coingecko_client.get_simple_price(
                    crypto_ids[target], base
                )
                inv_rate = (
                    1.0 / result["rate"] if result["rate"] != 0 else 0.0
                )
                result = {
                    "base": base,
                    "target": target,
                    "rate": inv_rate,
                    "source": "coingecko",
                    "fetched_at": result["fetched_at"],
                }
            else:
                # Try as crypto-to-crypto via USD
                result = await coingecko_client.get_crypto_to_crypto_rate(
                    crypto_ids.get(base, base),
                    crypto_ids.get(target, target),
                )
                result["base"] = base
                result["target"] = target

            # Save to RateHistory
            factory = get_session_factory()
            async with factory() as session:
                profile = await _direct_get_or_create_profile()
                entry = RateHistory(
                    profile_id=profile.id,
                    base_currency=base,
                    target_currency=target,
                    rate=result["rate"],
                    source=result["source"],
                    fetched_at=result["fetched_at"],
                )
                session.add(entry)
                await session.commit()

            await _direct_log_request(
                "rate", {"base": base, "target": target}, 200
            )

            rate_panel(
                base=base,
                target=target,
                rate=result["rate"],
                source=result["source"],
                fetched_at=result["fetched_at"],
            )

        except Exception as exc:
            await _direct_log_request(
                "rate", {"base": base, "target": target}, 502, str(exc)
            )
            handle_cli_error(
                "External API Error",
                f"Cannot fetch rate: {exc}",
                exit_code=EXIT_EXTERNAL_API_ERROR,
            )
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# 8.2  convert
# ---------------------------------------------------------------------------


async def _convert_command(base: str, target: str, amount: float) -> None:
    """Core async logic for the 'convert' command."""
    base = base.lower().strip()
    target = target.lower().strip()

    if amount <= 0:
        handle_cli_error(
            "Invalid Input",
            "Amount must be positive.",
        )
    if base == target:
        handle_cli_error(
            "Invalid Input",
            "Base and target currencies must be different.",
        )

    if _use_server and await _server_reachable():
        try:
            data = await _server_post(
                "/api/convert",
                {"base": base, "target": target, "amount": amount},
            )
            convert_panel(
                base=data["base"],
                target=data["target"],
                amount=data["amount"],
                result=data["result"],
                rate=data["rate"],
                source=data["source"],
                converted_at=datetime.fromisoformat(
                    data["converted_at"].replace("Z", "+00:00")
                ),
            )
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        # Fetch rate first (reuse rate logic in simplified form)
        fiat_set: set[str] = set()
        crypto_ids: dict[str, str] = {}
        try:
            currencies = await frankfurter_client.get_currencies()
            fiat_set = {k.lower() for k in currencies}
        except Exception:
            pass
        try:
            coins = await coingecko_client.get_coins_list()
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
            for coin in coins:
                sym = coin["symbol"].lower()
                cid = coin["id"]
                if sym not in crypto_ids:
                    crypto_ids[sym] = cid
                elif sym in _known and cid == _known[sym]:
                    crypto_ids[sym] = cid
        except Exception:
            pass

        try:
            base_is_fiat = base in fiat_set
            target_is_fiat = target in fiat_set
            base_is_crypto = base in crypto_ids
            target_is_crypto = target in crypto_ids

            base_looks_fiat = base_is_fiat or (
                not base_is_crypto and len(base) == 3 and base.isalpha()
            )
            target_looks_fiat = target_is_fiat or (
                not target_is_crypto and len(target) == 3 and target.isalpha()
            )

            if base_looks_fiat and target_looks_fiat:
                try:
                    result = await frankfurter_client.get_rate(base, target)
                    if result.get("rate", 0) <= 0:
                        raise ValueError("Zero rate from Frankfurter")
                except Exception:
                    raise RuntimeError(
                        f"Currency pair {base}/{target} is not supported "
                        f"by Frankfurter. Try crypto pairs instead."
                    )
            elif base_is_crypto and target_looks_fiat:
                result = await coingecko_client.get_simple_price(
                    crypto_ids[base], target
                )
                result["base"] = base
            elif base_is_fiat and target_is_crypto:
                result = await coingecko_client.get_simple_price(
                    crypto_ids[target], base
                )
                inv_rate = (
                    1.0 / result["rate"] if result["rate"] != 0 else 0.0
                )
                result = {
                    "base": base,
                    "target": target,
                    "rate": inv_rate,
                    "source": "coingecko",
                    "fetched_at": result["fetched_at"],
                }
            else:
                result = await coingecko_client.get_crypto_to_crypto_rate(
                    crypto_ids.get(base, base),
                    crypto_ids.get(target, target),
                )
                result["base"] = base
                result["target"] = target

            rate = result["rate"]
            result_amount = round(amount * rate, 8)
            converted_at = datetime.now(timezone.utc)

            # Save to ConversionHistory
            factory = get_session_factory()
            async with factory() as session:
                profile = await _direct_get_or_create_profile()
                entry = ConversionHistory(
                    profile_id=profile.id,
                    base_currency=base,
                    target_currency=target,
                    amount=amount,
                    result=result_amount,
                    rate=rate,
                    source=result["source"],
                    created_at=converted_at,
                )
                session.add(entry)
                await session.commit()

            await _direct_log_request(
                "convert",
                {"base": base, "target": target, "amount": amount},
                200,
            )

            convert_panel(
                base=base,
                target=target,
                amount=amount,
                result=result_amount,
                rate=rate,
                source=result["source"],
                converted_at=converted_at,
            )

        except Exception as exc:
            await _direct_log_request(
                "convert",
                {"base": base, "target": target, "amount": amount},
                502,
                str(exc),
            )
            handle_cli_error(
                "External API Error",
                f"Cannot convert: {exc}",
                exit_code=EXIT_EXTERNAL_API_ERROR,
            )
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# 8.3  history
# ---------------------------------------------------------------------------


async def _history_command(
    limit: int = 20, command_filter: Optional[str] = None
) -> None:
    """Core async logic for the 'history' command."""
    if _use_server and await _server_reachable():
        try:
            params: dict = {"limit": limit, "offset": 0}
            if command_filter:
                params["command"] = command_filter
            data = await _server_get("/api/history", params)

            items = []
            for item in data["items"]:
                ts = item.get("created_at", "")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                items.append({
                    "id": item["id"],
                    "command": item["command"],
                    "params_json": item["params_json"],
                    "status_code": item["status_code"],
                    "created_at": ts,
                })

            history_table(
                items=items,
                profile=_profile_name,
                total=data["total"],
                limit=data["limit"],
                offset=data["offset"],
            )
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        factory = get_session_factory()
        async with factory() as session:
            profile = await _direct_get_or_create_profile()
            query = (
                select(RequestLog)
                .where(RequestLog.profile_id == profile.id)
                .order_by(RequestLog.created_at.desc())
                .limit(limit)
            )
            if command_filter:
                query = query.where(RequestLog.command == command_filter)
            result = await session.execute(query)
            logs = result.scalars().all()

            items = [
                {
                    "id": log.id,
                    "command": log.command,
                    "params_json": log.params_json,
                    "status_code": log.status_code,
                    "created_at": log.created_at,
                }
                for log in logs
            ]

            # Count total
            from sqlalchemy import func
            count_q = select(func.count()).where(
                RequestLog.profile_id == profile.id
            )
            if command_filter:
                count_q = count_q.where(RequestLog.command == command_filter)
            total_result = await session.execute(count_q)
            total = total_result.scalar() or 0

            history_table(
                items=items,
                profile=_profile_name,
                total=total,
                limit=limit,
                offset=0,
            )
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# 8.4  server — handled in main.py (runs uvicorn directly)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 8.5  watch
# ---------------------------------------------------------------------------


async def _watch_command(base: str, target: str, remove: bool = False) -> None:
    """Core async logic for the 'watch' command."""
    base = base.lower().strip()
    target = target.lower().strip()

    if base == target:
        handle_cli_error(
            "Invalid Input",
            "Base and target currencies must be different.",
        )

    if _use_server and await _server_reachable():
        try:
            if remove:
                # Need to find the watchlist entry ID first
                list_data = await _server_get("/api/watch")
                entry_id = None
                for pair in list_data.get("pairs", []):
                    if (
                        pair["base"] == base and pair["target"] == target
                    ):
                        entry_id = pair["id"]
                        break

                if entry_id is None:
                    handle_cli_error(
                        "Pair Not Tracked",
                        f"The pair {base}→{target} is not in your watchlist.",
                    )

                await _server_delete(f"/api/watch/{entry_id}")
                watch_remove_panel(base, target)
            else:
                data = await _server_post(
                    "/api/watch", {"base": base, "target": target}
                )
                watch_add_panel(
                    base=data["base"],
                    target=data["target"],
                    pair_type=data["pair_type"],
                    added_at=datetime.fromisoformat(
                        data["created_at"].replace("Z", "+00:00")
                    ),
                )
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        factory = get_session_factory()
        async with factory() as session:
            profile = await _direct_get_or_create_profile()

            if remove:
                result = await session.execute(
                    select(WatchList).where(
                        WatchList.profile_id == profile.id,
                        WatchList.base_currency == base,
                        WatchList.target_currency == target,
                    )
                )
                entry = result.scalar_one_or_none()
                if entry is None:
                    handle_cli_error(
                        "Pair Not Tracked",
                        f"The pair {base}→{target} is not in your watchlist.",
                    )
                await session.delete(entry)
                await session.commit()
                watch_remove_panel(base, target)
            else:
                # Check duplicate
                existing = await session.execute(
                    select(WatchList).where(
                        WatchList.profile_id == profile.id,
                        WatchList.base_currency == base,
                        WatchList.target_currency == target,
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    handle_cli_error(
                        "Pair Already Tracked",
                        f"The pair {base}→{target} is already in your watchlist.",
                        hint="Use 'cryptotracker list-watch' to see all pairs.",
                    )

                # Determine pair_type
                pair_type = "crypto-fiat"  # default
                fiat_set: set[str] = set()
                try:
                    currencies = await frankfurter_client.get_currencies()
                    fiat_set = {k.lower() for k in currencies}
                except Exception:
                    pass
                base_is_fiat = base in fiat_set
                target_is_fiat = target in fiat_set
                if base_is_fiat and target_is_fiat:
                    pair_type = "fiat-fiat"
                elif not base_is_fiat and not target_is_fiat:
                    pair_type = "crypto-crypto"

                entry = WatchList(
                    profile_id=profile.id,
                    base_currency=base,
                    target_currency=target,
                    pair_type=pair_type,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(entry)
                await session.commit()
                await session.refresh(entry)

                watch_add_panel(
                    base=base,
                    target=target,
                    pair_type=pair_type,
                    added_at=entry.created_at,
                )
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# 8.6  list-watch
# ---------------------------------------------------------------------------


async def _list_watch_command() -> None:
    """Core async logic for the 'list-watch' command."""
    if _use_server and await _server_reachable():
        try:
            with create_progress() as progress:
                task = progress.add_task(
                    "[cyan]Fetching watchlist...", total=None
                )
                data = await _server_get("/api/watch")
                progress.update(task, completed=True, visible=False)

            items = []
            for pair in data.get("pairs", []):
                added = pair.get("added_at", "")
                if isinstance(added, str):
                    added = datetime.fromisoformat(added.replace("Z", "+00:00"))
                items.append({
                    "id": pair["id"],
                    "base": pair["base"],
                    "target": pair["target"],
                    "pair_type": pair["pair_type"],
                    "current_rate": pair.get("current_rate"),
                    "rate_source": pair.get("rate_source", "unavailable"),
                    "added_at": added,
                })

            watchlist_table(items=items, profile=_profile_name)
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        factory = get_session_factory()
        async with factory() as session:
            profile = await _direct_get_or_create_profile()
            result = await session.execute(
                select(WatchList).where(
                    WatchList.profile_id == profile.id
                )
            )
            entries = result.scalars().all()

            with create_progress() as progress:
                task = progress.add_task(
                    "[cyan]Fetching current rates...", total=len(entries)
                )

                items = []
                for entry in entries:
                    current_rate = None
                    rate_source = "unavailable"
                    try:
                        pair_type = entry.pair_type
                        b = entry.base_currency
                        t = entry.target_currency
                        if pair_type == "fiat-fiat":
                            rd = await frankfurter_client.get_rate(b, t)
                            current_rate = rd["rate"]
                            rate_source = "frankfurter"
                        else:
                            # Try via CoinGecko
                            coins = await coingecko_client.get_coins_list()
                            crypto_ids = {}
                            for coin in coins:
                                sym = coin["symbol"].lower()
                                if sym not in crypto_ids:
                                    crypto_ids[sym] = coin["id"]

                            if b in crypto_ids:
                                rd = await coingecko_client.get_simple_price(
                                    crypto_ids[b], t
                                )
                                current_rate = rd["rate"]
                                rate_source = "coingecko"
                            elif t in crypto_ids:
                                rd = await coingecko_client.get_simple_price(
                                    crypto_ids[t], b
                                )
                                current_rate = (
                                    1.0 / rd["rate"]
                                    if rd["rate"] != 0
                                    else 0.0
                                )
                                rate_source = "coingecko"
                    except Exception:
                        pass

                    items.append({
                        "id": entry.id,
                        "base": entry.base_currency,
                        "target": entry.target_currency,
                        "pair_type": entry.pair_type,
                        "current_rate": current_rate,
                        "rate_source": rate_source,
                        "added_at": entry.created_at,
                    })
                    progress.advance(task)

            watchlist_table(items=items, profile=_profile_name)
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# 8.7  export
# ---------------------------------------------------------------------------


async def _export_command(
    format: str = "json",
    dataset: str = "all",
    output: Optional[Path] = None,
) -> None:
    """Core async logic for the 'export' command."""
    if output is None:
        ext = "csv" if format == "csv" else "json"
        output = Path(f"cryptotracker_export.{ext}")

    if _use_server and await _server_reachable():
        try:
            data = await _server_get(
                "/api/export",
                {"format": format, "dataset": dataset},
            )
            if format == "csv":
                # _server_get returns JSON-parsed data, but CSV should
                # be fetched as raw text
                async with build_client() as client:
                    resp = await request_with_retry(
                        client,
                        "GET",
                        f"{_server_url}/api/export",
                        params={
                            "profile": _profile_name,
                            "format": "csv",
                            "dataset": dataset,
                        },
                        max_retries=1,
                    )
                    resp.raise_for_status()
                    csv_content = resp.text
                output.write_text(csv_content, encoding="utf-8")
                size = len(csv_content.encode("utf-8"))
                # Count records (lines minus header)
                records = max(0, csv_content.strip().count("\n"))
                export_panel(
                    format_name="CSV",
                    dataset=dataset,
                    records=records,
                    output_path=str(output.resolve()),
                    size_bytes=size,
                )
            else:
                output.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                size = output.stat().st_size

                # Count records
                total_records = 0
                exp_data = data.get("data", {})
                if isinstance(exp_data, dict):
                    for key in ("watchlist", "history", "conversions"):
                        records_list = exp_data.get(key, [])
                        if isinstance(records_list, list):
                            total_records += len(records_list)

                export_panel(
                    format_name="JSON",
                    dataset=dataset,
                    records=total_records,
                    output_path=str(output.resolve()),
                    size_bytes=size,
                )
            return
        except httpx.HTTPStatusError as exc:
            handle_http_error(exc)
            return
        except httpx.ConnectError as exc:
            handle_connection_error(exc)
            console.print(
                "[yellow]⚠ Server unreachable, switching to direct mode...[/]"
            )

    # --- Direct mode ---
    await init_db()
    try:
        factory = get_session_factory()
        async with factory() as session:
            profile = await _direct_get_or_create_profile()

            if format == "csv":
                import csv
                import io
                out_buf = io.StringIO()
                writer = csv.writer(out_buf)

                if dataset in ("history", "all"):
                    result = await session.execute(
                        select(RequestLog)
                        .where(RequestLog.profile_id == profile.id)
                        .order_by(RequestLog.created_at.desc())
                        .limit(1000)
                    )
                    rows = result.scalars().all()
                    writer.writerow(
                        ["command", "params_json", "status_code",
                         "error_message", "created_at"]
                    )
                    for row in rows:
                        writer.writerow([
                            row.command,
                            row.params_json,
                            row.status_code,
                            row.error_message or "",
                            row.created_at.isoformat()
                            if row.created_at else "",
                        ])
                    if dataset == "all":
                        writer.writerow([])

                if dataset in ("conversions", "all"):
                    result = await session.execute(
                        select(ConversionHistory)
                        .where(ConversionHistory.profile_id == profile.id)
                        .order_by(ConversionHistory.created_at.desc())
                        .limit(1000)
                    )
                    rows = result.scalars().all()
                    if dataset == "conversions":
                        writer.writerow(
                            ["base_currency", "target_currency", "amount",
                             "result", "rate", "source", "created_at"]
                        )
                    for row in rows:
                        writer.writerow([
                            row.base_currency,
                            row.target_currency,
                            row.amount,
                            row.result,
                            row.rate,
                            row.source,
                            row.created_at.isoformat()
                            if row.created_at else "",
                        ])

                csv_content = out_buf.getvalue()
                out_buf.close()
                output.write_text(csv_content, encoding="utf-8")
                records = max(0, csv_content.strip().count("\n"))
                export_panel(
                    format_name="CSV",
                    dataset=dataset,
                    records=records,
                    output_path=str(output.resolve()),
                    size_bytes=len(csv_content.encode("utf-8")),
                )
            else:
                export_data: dict = {
                    "profile": _profile_name,
                    "dataset": dataset,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "data": {},
                }

                total_records = 0
                if dataset in ("watchlist", "all"):
                    result = await session.execute(
                        select(WatchList).where(
                            WatchList.profile_id == profile.id
                        )
                    )
                    watchlist = []
                    for row in result.scalars().all():
                        watchlist.append({
                            "id": row.id,
                            "base": row.base_currency,
                            "target": row.target_currency,
                            "pair_type": row.pair_type,
                            "created_at": row.created_at.isoformat()
                            if row.created_at else "",
                        })
                    export_data["data"]["watchlist"] = watchlist
                    total_records += len(watchlist)

                if dataset in ("history", "all"):
                    result = await session.execute(
                        select(RequestLog)
                        .where(RequestLog.profile_id == profile.id)
                        .order_by(RequestLog.created_at.desc())
                        .limit(1000)
                    )
                    history = []
                    for row in result.scalars().all():
                        history.append({
                            "id": row.id,
                            "command": row.command,
                            "params_json": row.params_json,
                            "status_code": row.status_code,
                            "error_message": row.error_message,
                            "created_at": row.created_at.isoformat()
                            if row.created_at else "",
                        })
                    export_data["data"]["history"] = history
                    total_records += len(history)

                if dataset in ("conversions", "all"):
                    result = await session.execute(
                        select(ConversionHistory)
                        .where(ConversionHistory.profile_id == profile.id)
                        .order_by(ConversionHistory.created_at.desc())
                        .limit(1000)
                    )
                    conversions = []
                    for row in result.scalars().all():
                        conversions.append({
                            "id": row.id,
                            "base_currency": row.base_currency,
                            "target_currency": row.target_currency,
                            "amount": row.amount,
                            "result": row.result,
                            "rate": row.rate,
                            "source": row.source,
                            "created_at": row.created_at.isoformat()
                            if row.created_at else "",
                        })
                    export_data["data"]["conversions"] = conversions
                    total_records += len(conversions)

                output.write_text(
                    json.dumps(export_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                size = output.stat().st_size
                export_panel(
                    format_name="JSON",
                    dataset=dataset,
                    records=total_records,
                    output_path=str(output.resolve()),
                    size_bytes=size,
                )
    except Exception as exc:
        handle_cli_error(
            "Export Error",
            f"Cannot write export file: {exc}",
            details={"Path": str(output.resolve())},
            exit_code=EXIT_EXPORT_ERROR,
        )
    finally:
        await close_db()


# ---------------------------------------------------------------------------
# Typer command callbacks (thin wrappers)
# ---------------------------------------------------------------------------


def rate(
    base: str = typer.Argument(..., help="Base currency code (e.g., btc, usd)"),
    target: str = typer.Argument(..., help="Target currency code (e.g., eur, rub)"),
) -> None:
    """Get current exchange rate for a currency pair."""
    asyncio.run(_rate_command(base, target))


def convert(
    base: str = typer.Argument(..., help="Base currency code"),
    target: str = typer.Argument(..., help="Target currency code"),
    amount: float = typer.Argument(..., help="Amount in base currency"),
) -> None:
    """Convert an amount between currencies."""
    asyncio.run(_convert_command(base, target, amount))


def history(
    limit: int = typer.Option(20, help="Number of records to show"),
    command: Optional[str] = typer.Option(
        None, help="Filter by command (rate, convert, watch)"
    ),
) -> None:
    """Show request history."""
    asyncio.run(_history_command(limit=limit, command_filter=command))


def watch(
    base: str = typer.Argument(..., help="Base currency code"),
    target: str = typer.Argument(..., help="Target currency code"),
    remove: bool = typer.Option(
        False, "--remove", help="Remove the pair instead of adding"
    ),
) -> None:
    """Add or remove currency pairs to/from watchlist."""
    asyncio.run(_watch_command(base, target, remove=remove))


def list_watch() -> None:
    """Show watchlist with current rates."""
    asyncio.run(_list_watch_command())


def export(
    format: str = typer.Option("json", help="Export format: json or csv"),
    dataset: str = typer.Option(
        "all", help="Dataset: history, watchlist, conversions, all"
    ),
    output: Optional[Path] = typer.Option(
        None, help="Output file path"
    ),
) -> None:
    """Export profile data to JSON or CSV."""
    asyncio.run(_export_command(format=format, dataset=dataset, output=output))