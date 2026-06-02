"""History Pydantic schemas."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class HistoryItemResponse(BaseModel):
    """History item response schema."""
    
    base_currency: str = Field(..., description="Base currency code")
    target_currency: str = Field(..., description="Target currency code")
    rate: Decimal = Field(..., description="Exchange rate")
    type: str = Field(..., description="Currency type")
    change_24h: Optional[Decimal] = Field(None, description="24h change percentage")


class HistoryQueryResponse(BaseModel):
    """History query response schema."""
    
    id: int = Field(..., description="Query ID")
    created_at: datetime = Field(..., description="Query timestamp")
    command_type: str = Field(..., description="Command type")
    status: str = Field(..., description="Query status")
    items: list[HistoryItemResponse] = Field(..., description="Query items")


class HistoryListResponse(BaseModel):
    """History list response schema."""
    
    total: int = Field(..., description="Total number of queries")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")
    queries: list[HistoryQueryResponse] = Field(..., description="List of queries")


class HistoryDeleteResponse(BaseModel):
    """History delete response schema."""
    
    deleted_count: int = Field(..., description="Number of deleted records")
    message: str = Field(..., description="Deletion result message")


class HistoryQueryParams(BaseModel):
    """History query parameters schema."""
    
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of records")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    command_type: Optional[str] = Field(None, description="Filter by command type")
    date_from: Optional[date] = Field(None, description="Start date filter")
    date_to: Optional[date] = Field(None, description="End date filter")
