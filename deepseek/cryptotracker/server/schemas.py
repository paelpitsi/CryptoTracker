"""
Pydantic schemas for request/response validation in FastAPI.

Defines all data transfer objects used by the API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Server Status
# ---------------------------------------------------------------------------


class ExternalAPIStatus(BaseModel):
    """Status of external APIs."""

    frankfurter: str = "unknown"
    coingecko: str = "unknown"


class ServerStatusResponse(BaseModel):
    """Response for GET /api/server/status."""

    status: str = "ok"
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    external_apis: ExternalAPIStatus = Field(default_factory=ExternalAPIStatus)


# ---------------------------------------------------------------------------
# Currencies
# ---------------------------------------------------------------------------


class CurrenciesResponse(BaseModel):
    """Response for GET /api/currencies (fiat)."""

    source: str = "frankfurter"
    currencies: dict[str, str] = Field(default_factory=dict)
    count: int = 0


class CryptoCurrency(BaseModel):
    """A single cryptocurrency entry."""

    id: str
    symbol: str
    name: str


class CryptoCurrenciesResponse(BaseModel):
    """Response for GET /api/crypto."""

    source: str = "coingecko"
    cryptocurrencies: list[CryptoCurrency] = Field(default_factory=list)
    count: int = 0


# ---------------------------------------------------------------------------
# Rate
# ---------------------------------------------------------------------------


class RateResponse(BaseModel):
    """Response for GET /api/rate."""

    base: str
    target: str
    rate: float
    source: str
    fetched_at: datetime


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------


class ConvertRequest(BaseModel):
    """Request body for POST /api/convert."""

    base: str
    target: str
    amount: float = Field(gt=0, description="Amount must be positive")


class ConvertResponse(BaseModel):
    """Response for POST /api/convert."""

    base: str
    target: str
    amount: float
    result: float
    rate: float
    source: str
    converted_at: datetime


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class HistoryItem(BaseModel):
    """A single request log entry."""

    id: int
    command: str
    params_json: str
    status_code: int
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Response for GET /api/history."""

    profile: str
    total: int
    limit: int
    offset: int
    items: list[HistoryItem]


# ---------------------------------------------------------------------------
# WatchList
# ---------------------------------------------------------------------------


class WatchAddRequest(BaseModel):
    """Request body for POST /api/watch."""

    base: str
    target: str


class WatchAddResponse(BaseModel):
    """Response for POST /api/watch."""

    id: int
    base: str
    target: str
    pair_type: str
    created_at: datetime


class WatchDeleteResponse(BaseModel):
    """Response for DELETE /api/watch/{id}."""

    deleted: bool = True
    id: int


class WatchListItem(BaseModel):
    """A single watchlist entry with current rate."""

    id: int
    base: str
    target: str
    pair_type: str
    current_rate: Optional[float] = None
    rate_source: str = "unavailable"
    added_at: datetime


class WatchListResponse(BaseModel):
    """Response for GET /api/watch."""

    profile: str
    pairs: list[WatchListItem]
    count: int


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportData(BaseModel):
    """Container for exported data in JSON format."""

    watchlist: list[dict] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)
    conversions: list[dict] = Field(default_factory=list)


class ExportResponse(BaseModel):
    """Response for GET /api/export (JSON format)."""

    profile: str
    dataset: str
    exported_at: datetime
    data: ExportData


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str = "unknown_error"