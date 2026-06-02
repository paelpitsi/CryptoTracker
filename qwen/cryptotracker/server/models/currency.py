"""Currency model."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from cryptotracker.server.models.base import Base, TimestampMixin


class Currency(Base, TimestampMixin):
    """Currency model for storing fiat and crypto currencies."""
    
    __tablename__ = "currencies"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'fiat' or 'crypto'
    coingecko_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        Index("idx_currencies_code", "code"),
        Index("idx_currencies_type", "type"),
        Index("idx_currencies_coingecko_id", "coingecko_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Currency(id={self.id}, code='{self.code}', type='{self.type}')>"
