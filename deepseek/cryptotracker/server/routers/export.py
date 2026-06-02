"""
Router for /api/export endpoint.

Exports profile data (history, watchlist, conversions) in JSON or CSV format.
"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_db
from cryptotracker.server.models import (
    Profile,
    RequestLog,
    WatchList,
    ConversionHistory,
)
from cryptotracker.server.schemas import ExportData, ExportResponse

router = APIRouter(tags=["export"])


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


def _model_to_dict(obj) -> dict:
    """Convert a SQLAlchemy model instance to a plain dict."""
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[column.name] = value
    return result


@router.get("/export")
async def export_data(
    profile: str = Query("default", description="Profile name"),
    format: str = Query("json", description="Export format: json or csv"),
    dataset: str = Query(
        "all",
        description="Dataset to export: history, watchlist, conversions, all",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Export profile data in JSON or CSV format."""
    if format not in ("json", "csv"):
        raise HTTPException(
            status_code=400,
            detail="Format must be 'json' or 'csv'.",
        )
    if dataset not in ("history", "watchlist", "conversions", "all"):
        raise HTTPException(
            status_code=400,
            detail="Dataset must be 'history', 'watchlist', 'conversions', or 'all'.",
        )

    profile_obj = await _get_or_create_profile(db, profile)
    exported_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # JSON EXPORT
    # ------------------------------------------------------------------ #
    if format == "json":
        data = ExportData()

        if dataset in ("watchlist", "all"):
            result = await db.execute(
                select(WatchList).where(
                    WatchList.profile_id == profile_obj.id
                )
            )
            data.watchlist = [
                _model_to_dict(row) for row in result.scalars().all()
            ]

        if dataset in ("history", "all"):
            result = await db.execute(
                select(RequestLog)
                .where(RequestLog.profile_id == profile_obj.id)
                .order_by(RequestLog.created_at.desc())
                .limit(1000)
            )
            data.history = [
                _model_to_dict(row) for row in result.scalars().all()
            ]

        if dataset in ("conversions", "all"):
            result = await db.execute(
                select(ConversionHistory)
                .where(ConversionHistory.profile_id == profile_obj.id)
                .order_by(ConversionHistory.created_at.desc())
                .limit(1000)
            )
            data.conversions = [
                _model_to_dict(row) for row in result.scalars().all()
            ]

        return JSONResponse(
            content={
                "profile": profile,
                "dataset": dataset,
                "exported_at": exported_at.isoformat(),
                "data": data.model_dump(),
            }
        )

    # ------------------------------------------------------------------ #
    # CSV EXPORT
    # ------------------------------------------------------------------ #
    output = io.StringIO()
    writer = csv.writer(output)

    if dataset in ("history", "all"):
        result = await db.execute(
            select(RequestLog)
            .where(RequestLog.profile_id == profile_obj.id)
            .order_by(RequestLog.created_at.desc())
            .limit(1000)
        )
        rows = result.scalars().all()

        writer.writerow(
            ["command", "params_json", "status_code", "error_message", "created_at"]
        )
        for row in rows:
            writer.writerow([
                row.command,
                row.params_json,
                row.status_code,
                row.error_message or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        if dataset == "all":
            writer.writerow([])  # separator

    if dataset in ("conversions", "all"):
        result = await db.execute(
            select(ConversionHistory)
            .where(ConversionHistory.profile_id == profile_obj.id)
            .order_by(ConversionHistory.created_at.desc())
            .limit(1000)
        )
        rows = result.scalars().all()

        if dataset == "conversions" or not output.getvalue():
            # Write header only if first dataset or standalone
            pass
        writer.writerow(
            ["base_currency", "target_currency", "amount", "result", "rate",
             "source", "created_at"]
        )
        for row in rows:
            writer.writerow([
                row.base_currency,
                row.target_currency,
                row.amount,
                row.result,
                row.rate,
                row.source,
                row.created_at.isoformat() if row.created_at else "",
            ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="cryptotracker_export_{profile}.csv"'
            )
        },
    )
