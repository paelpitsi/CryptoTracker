"""History service for managing query history."""

from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_
from sqlalchemy.orm import selectinload

from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.schemas.history import (
    HistoryListResponse,
    HistoryQueryResponse,
    HistoryItemResponse,
    HistoryDeleteResponse
)
from cryptotracker.common.logger import logger


class HistoryService:
    """Service for managing query history."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        command_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> HistoryListResponse:
        """Get query history with optional filters."""
        
        try:
            # Build query
            query = select(QueryHistory).options(selectinload(QueryHistory.items))
            
            # Apply filters
            if command_type:
                query = query.where(QueryHistory.command_type == command_type)
            
            if date_from:
                query = query.where(QueryHistory.created_at >= datetime.combine(date_from, datetime.min.time()))
            
            if date_to:
                query = query.where(QueryHistory.created_at <= datetime.combine(date_to, datetime.max.time()))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(QueryHistory.created_at.desc()).offset(offset).limit(limit)
            
            result = await self.session.execute(query)
            queries = result.scalars().all()
            
            # Convert to response format
            query_responses = []
            for q in queries:
                items = [
                    HistoryItemResponse(
                        base_currency=item.base_currency,
                        target_currency=item.target_currency,
                        rate=item.rate,
                        type=item.currency_type,
                        change_24h=item.change_24h
                    )
                    for item in q.items
                ]
                
                query_responses.append(HistoryQueryResponse(
                    id=q.id,
                    created_at=q.created_at,
                    command_type=q.command_type,
                    status=q.status,
                    items=items
                ))
            
            return HistoryListResponse(
                total=total,
                limit=limit,
                offset=offset,
                queries=query_responses
            )
            
        except Exception as e:
            logger.error(f"Error in get_history: {e}")
            raise
    
    async def delete_history(
        self,
        older_than_days: Optional[int] = None,
        delete_all: bool = False
    ) -> HistoryDeleteResponse:
        """Delete query history records."""
        
        try:
            if delete_all:
                # Delete all history
                result = await self.session.execute(delete(QueryHistory))
                deleted_count = result.rowcount
            elif older_than_days:
                # Delete records older than specified days
                cutoff_date = datetime.utcnow() - __import__('datetime').timedelta(days=older_than_days)
                result = await self.session.execute(
                    delete(QueryHistory).where(QueryHistory.created_at < cutoff_date)
                )
                deleted_count = result.rowcount
            else:
                deleted_count = 0
            
            await self.session.commit()
            
            return HistoryDeleteResponse(
                deleted_count=deleted_count,
                message=f"Successfully deleted {deleted_count} query records"
            )
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in delete_history: {e}")
            raise
