"""
Router for /api/history endpoint.

Provides access to request history logs for a profile.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotracker.server.database import get_db
from cryptotracker.server.models import Profile, RequestLog
from cryptotracker.server.schemas import HistoryItem, HistoryResponse

router = APIRouter(tags=["history"])


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


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    profile: str = Query("default", description="Profile name"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    command: str | None = Query(
        None, description="Filter by command name (rate, convert, watch)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve request history for a profile with pagination."""
    profile_obj = await _get_or_create_profile(db, profile)

    # Count total matching records
    count_query = select(func.count()).where(
        RequestLog.profile_id == profile_obj.id
    )
    if command:
        count_query = count_query.where(RequestLog.command == command)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch paginated records
    query = (
        select(RequestLog)
        .where(RequestLog.profile_id == profile_obj.id)
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if command:
        query = query.where(RequestLog.command == command)

    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        HistoryItem(
            id=log.id,
            command=log.command,
            params_json=log.params_json,
            status_code=log.status_code,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return HistoryResponse(
        profile=profile,
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
