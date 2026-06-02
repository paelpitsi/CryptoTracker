"""Rates Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class RateItem(BaseModel):
    """Individual rate item."""
    
    target: str = Field(..., description="Target currency code")
    rate: Decimal = Field(..., description="Exchange rate")
    type: str = Field(..., description="Currency type (fiat or crypto)")
    change_24h: Optional[Decimal] = Field(None, description="24h change percentage")


class RatesResponse(BaseModel):
    """Rates response schema."""
    
    base: str = Field(..., description="Base currency code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    rates: list[RateItem] = Field(..., description="List of rates")
    query_id: int = Field(..., description="Query history ID")


class ConvertRequest(BaseModel):
    """Convert request schema."""
    
    amount: Decimal = Field(..., gt=0, description="Amount to convert")
    from_currency: str = Field(..., alias="from", max_length=10, description="Source currency code")
    to_currency: str = Field(..., alias="to", max_length=10, description="Target currency code")
    type: str = Field("auto", description="Currency type (fiat, crypto, or auto)")
    
    class Config:
        populate_by_name = True


class ConvertResponse(BaseModel):
    """Convert response schema."""
    
    from_currency: str = Field(..., alias="from", description="Source currency code")
    to_currency: str = Field(..., alias="to", description="Target currency code")
    amount: Decimal = Field(..., description="Original amount")
    result: Decimal = Field(..., description="Converted amount")
    rate: Decimal = Field(..., description="Exchange rate used")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Conversion timestamp")
    type: str = Field(..., description="Currency type")
    change_24h: Optional[Decimal] = Field(None, description="24h change percentage for crypto")
    query_id: int = Field(..., description="Query history ID")
    
    class Config:
        populate_by_name = True
