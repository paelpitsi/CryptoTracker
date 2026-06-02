"""Common Pydantic schemas."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ErrorWrapper(BaseModel):
    """Error wrapper for API responses."""
    
    error: ErrorResponse


class HealthResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Server status")
    version: str = Field(..., description="Server version")
    database: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
