"""Watchlist Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):
    """Schema for creating a watchlist."""
    
    name: str = Field(..., max_length=50, description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")


class WatchlistItemCreate(BaseModel):
    """Schema for creating a watchlist item."""
    
    base_currency: str = Field(..., max_length=10, description="Base currency code")
    target_currency: str = Field(..., max_length=10, description="Target currency code")
    type: str = Field(..., description="Currency type (fiat or crypto)")


class WatchlistItemResponse(BaseModel):
    """Schema for watchlist item response."""
    
    id: int = Field(..., description="Item ID")
    watchlist_id: int = Field(..., description="Watchlist ID")
    base_currency: str = Field(..., description="Base currency code")
    target_currency: str = Field(..., description="Target currency code")
    type: str = Field(..., description="Currency type")
    added_at: datetime = Field(..., description="Addition timestamp")


class WatchlistItemWithRate(BaseModel):
    """Schema for watchlist item with current rate."""
    
    id: int = Field(..., description="Item ID")
    base_currency: str = Field(..., description="Base currency code")
    target_currency: str = Field(..., description="Target currency code")
    type: str = Field(..., description="Currency type")
    current_rate: Optional[Decimal] = Field(None, description="Current exchange rate")
    change_24h: Optional[Decimal] = Field(None, description="24h change percentage")
    added_at: datetime = Field(..., description="Addition timestamp")


class WatchlistResponse(BaseModel):
    """Schema for watchlist response."""
    
    id: int = Field(..., description="Watchlist ID")
    name: str = Field(..., description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")
    created_at: datetime = Field(..., description="Creation timestamp")
    items_count: int = Field(..., description="Number of items in watchlist")


class WatchlistDetailResponse(BaseModel):
    """Schema for detailed watchlist response with items."""
    
    id: int = Field(..., description="Watchlist ID")
    name: str = Field(..., description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")
    created_at: datetime = Field(..., description="Creation timestamp")
    items: list[WatchlistItemWithRate] = Field(..., description="Watchlist items with rates")


class WatchlistListResponse(BaseModel):
    """Schema for watchlist list response."""
    
    watchlists: list[WatchlistResponse] = Field(..., description="List of watchlists")


class WatchlistDeleteResponse(BaseModel):
    """Schema for watchlist delete response."""
    
    message: str = Field(..., description="Deletion result message")
    deleted_items_count: int = Field(..., description="Number of deleted items")


class WatchlistItemDeleteResponse(BaseModel):
    """Schema for watchlist item delete response."""
    
    message: str = Field(..., description="Deletion result message")
