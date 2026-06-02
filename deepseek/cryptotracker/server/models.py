"""
SQLAlchemy ORM models for CryptoTracker.

Defines all database tables: Profiles, RateHistory, ConversionHistory,
WatchList, and RequestLog.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Profile(Base):
    """
    User profile for data isolation.

    All history, watchlist, and logs are scoped to a profile.
    A default profile named 'default' is created automatically.
    """

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    # Relationships
    rate_history = relationship("RateHistory", back_populates="profile", lazy="dynamic")
    conversion_history = relationship(
        "ConversionHistory", back_populates="profile", lazy="dynamic"
    )
    watchlist = relationship("WatchList", back_populates="profile", lazy="dynamic")
    request_logs = relationship("RequestLog", back_populates="profile", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, name='{self.name}')>"


class RateHistory(Base):
    """
    History of fetched exchange rates.

    Each record stores the rate for a specific currency pair at a point in time.
    """

    __tablename__ = "rate_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    base_currency = Column(String(20), nullable=False, index=True)
    target_currency = Column(String(20), nullable=False)
    rate = Column(Float, nullable=False)
    source = Column(String(20), nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=_utcnow)

    # Composite index for fast historical lookups
    __table_args__ = (
        Index(
            "ix_rate_history_pair_time",
            "base_currency",
            "target_currency",
            "fetched_at",
        ),
    )

    profile = relationship("Profile", back_populates="rate_history")

    def __repr__(self) -> str:
        return (
            f"<RateHistory(id={self.id}, {self.base_currency}->{self.target_currency}"
            f" = {self.rate})>"
        )


class ConversionHistory(Base):
    """
    History of currency conversions.

    Stores the input amount, output result, and the rate used.
    """

    __tablename__ = "conversion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    base_currency = Column(String(20), nullable=False)
    target_currency = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    result = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    source = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    profile = relationship("Profile", back_populates="conversion_history")

    def __repr__(self) -> str:
        return (
            f"<ConversionHistory(id={self.id}, {self.amount} {self.base_currency}"
            f" -> {self.result} {self.target_currency})>"
        )


class WatchList(Base):
    """
    Tracked currency pairs for a profile.

    Each entry represents a pair the user wants to monitor.
    The pair (profile_id, base_currency, target_currency) is unique.
    """

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    base_currency = Column(String(20), nullable=False)
    target_currency = Column(String(20), nullable=False)
    pair_type = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "profile_id", "base_currency", "target_currency", name="uq_watchlist_pair"
        ),
    )

    profile = relationship("Profile", back_populates="watchlist")

    def __repr__(self) -> str:
        return (
            f"<WatchList(id={self.id}, {self.base_currency}->{self.target_currency}"
            f" [{self.pair_type}])>"
        )


class RequestLog(Base):
    """
    Audit log of all API requests made by the server.

    Records the command, parameters, status code, and any error messages.
    """

    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    command = Column(String(30), nullable=False)
    params_json = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    profile = relationship("Profile", back_populates="request_logs")

    def __repr__(self) -> str:
        return (
            f"<RequestLog(id={self.id}, command='{self.command}', "
            f"status={self.status_code})>"
        )
