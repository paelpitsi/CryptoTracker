"""Currency Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CurrencyBase(BaseModel):
    """Base currency schema."""
    
    code: str = Field(..., max_length=10, description="Currency code")
    name: str = Field(..., max_length=100, description="Currency name")
    type: str = Field(..., description="Currency type (fiat or crypto)")
    coingecko_id: Optional[str] = Field(None, max_length=50, description="CoinGecko ID for crypto")
    is_active: bool = Field(True, description="Is currency active")


class CurrencyCreate(CurrencyBase):
    """Schema for creating a currency."""
    pass


class CurrencyResponse(CurrencyBase):
    """Schema for currency response."""
    
    id: int = Field(..., description="Currency ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class CurrencyListResponse(BaseModel):
    """Schema for currency list response."""
    
    currencies: list[CurrencyResponse] = Field(..., description="List of currencies")


class CurrencySyncResponse(BaseModel):
    """Schema for currency sync response."""
    
    fiat_added: int = Field(..., description="Number of fiat currencies added")
    fiat_updated: int = Field(..., description="Number of fiat currencies updated")
    crypto_added: int = Field(..., description="Number of crypto currencies added")
    crypto_updated: int = Field(..., description="Number of crypto currencies updated")
    message: str = Field(..., description="Sync result message")
