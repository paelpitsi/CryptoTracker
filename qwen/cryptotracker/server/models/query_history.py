"""Query history models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cryptotracker.server.models.base import Base


class QueryHistory(Base):
    """Query history model for storing metadata about each query."""
    
    __tablename__ = "query_history"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    command_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'rate', 'convert', 'watch', 'list-watch'
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'success', 'error', 'partial'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    items: Mapped[List["QueryHistoryItem"]] = relationship(
        back_populates="query_history",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_query_history_created_at", "created_at"),
        Index("idx_query_history_command_type", "command_type"),
    )
    
    def __repr__(self) -> str:
        return f"<QueryHistory(id={self.id}, command_type='{self.command_type}', status='{self.status}')>"


class QueryHistoryItem(Base):
    """Query history item model for storing detailed results of each query."""
    
    __tablename__ = "query_history_items"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_history_id: Mapped[int] = mapped_column(
        ForeignKey("query_history.id", ondelete="CASCADE"),
        nullable=False
    )
    currency_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("currencies.id"),
        nullable=True
    )
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    rate: Mapped[Decimal] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(default=Decimal("1.0"), nullable=False)
    result: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    currency_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'fiat' or 'crypto'
    change_24h: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query_history: Mapped["QueryHistory"] = relationship(back_populates="items")
    
    __table_args__ = (
        Index("idx_query_history_items_query_id", "query_history_id"),
        Index("idx_query_history_items_currencies", "base_currency", "target_currency"),
        Index("idx_query_history_items_timestamp", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<QueryHistoryItem(id={self.id}, base='{self.base_currency}', target='{self.target_currency}')>"
