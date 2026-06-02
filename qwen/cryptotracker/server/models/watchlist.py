"""Watchlist models."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cryptotracker.server.models.base import Base, TimestampMixin


class Watchlist(Base, TimestampMixin):
    """Watchlist model for storing currency pair watchlists."""
    
    __tablename__ = "watchlists"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    items: Mapped[List["WatchlistItem"]] = relationship(
        back_populates="watchlist",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_watchlists_name", "name"),
    )
    
    def __repr__(self) -> str:
        return f"<Watchlist(id={self.id}, name='{self.name}')>"


class WatchlistItem(Base):
    """Watchlist item model for storing currency pairs in watchlists."""
    
    __tablename__ = "watchlist_items"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False
    )
    currency_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("currencies.id"),
        nullable=True
    )
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    currency_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'fiat' or 'crypto'
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    
    __table_args__ = (
        Index("idx_watchlist_items_watchlist_id", "watchlist_id"),
        UniqueConstraint(
            "watchlist_id", "base_currency", "target_currency",
            name="uq_watchlist_items_unique"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<WatchlistItem(id={self.id}, base='{self.base_currency}', target='{self.target_currency}')>"
