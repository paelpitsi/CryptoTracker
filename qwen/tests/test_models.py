"""Tests for database models and common exceptions."""

import pytest
from datetime import datetime
from decimal import Decimal

from cryptotracker.server.models.currency import Currency
from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.common.exceptions import (
    CryptoTrackerError,
    ValidationError,
    CurrencyNotFoundError,
    WatchlistNotFoundError,
    WatchlistItemNotFoundError,
    DuplicateWatchlistError,
    DuplicateWatchlistItemError,
    ExternalAPIError,
    FrankfurterUnavailableError,
    CoinGeckoUnavailableError,
    RateLimitExceededError,
    DatabaseError,
    ServerUnavailableError,
)


class TestCurrencyModel:
    """Tests for the Currency model."""

    def test_currency_repr(self):
        c = Currency(id=1, code="USD", name="US Dollar", type="fiat", is_active=True)
        assert "USD" in repr(c)
        assert "fiat" in repr(c)

    def test_currency_crypto_repr(self):
        c = Currency(id=2, code="BTC", name="Bitcoin", type="crypto", coingecko_id="bitcoin", is_active=True)
        assert "BTC" in repr(c)
        assert "crypto" in repr(c)


class TestWatchlistModel:
    """Tests for the Watchlist model."""

    def test_watchlist_repr(self):
        w = Watchlist(id=1, name="test")
        assert "test" in repr(w)


class TestWatchlistItemModel:
    """Tests for the WatchlistItem model."""

    def test_watchlist_item_repr(self):
        item = WatchlistItem(
            id=1, watchlist_id=1, base_currency="USD",
            target_currency="EUR", currency_type="fiat"
        )
        assert "USD" in repr(item)
        assert "EUR" in repr(item)


class TestQueryHistoryModel:
    """Tests for the QueryHistory model."""

    def test_query_history_repr(self):
        qh = QueryHistory(id=1, command_type="rate", status="success")
        assert "rate" in repr(qh)
        assert "success" in repr(qh)


class TestQueryHistoryItemModel:
    """Tests for the QueryHistoryItem model."""

    def test_query_history_item_repr(self):
        item = QueryHistoryItem(
            id=1, query_history_id=1, base_currency="USD",
            target_currency="EUR", rate=Decimal("0.85"),
            currency_type="fiat"
        )
        assert "USD" in repr(item)
        assert "EUR" in repr(item)


class TestExceptionsHierarchy:
    """Test that exceptions have the correct hierarchy."""

    def test_base_exception(self):
        with pytest.raises(CryptoTrackerError):
            raise CryptoTrackerError("test")

    def test_validation_error_is_cryptotracker_error(self):
        with pytest.raises(CryptoTrackerError):
            raise ValidationError("validation failed")

    def test_currency_not_found(self):
        with pytest.raises(CryptoTrackerError):
            raise CurrencyNotFoundError("USD not found")

    def test_watchlist_not_found(self):
        with pytest.raises(CryptoTrackerError):
            raise WatchlistNotFoundError("watchlist not found")

    def test_watchlist_item_not_found(self):
        with pytest.raises(CryptoTrackerError):
            raise WatchlistItemNotFoundError("item not found")

    def test_duplicate_watchlist(self):
        with pytest.raises(CryptoTrackerError):
            raise DuplicateWatchlistError("already exists")

    def test_duplicate_watchlist_item(self):
        with pytest.raises(CryptoTrackerError):
            raise DuplicateWatchlistItemError("already exists")

    def test_external_api_error(self):
        with pytest.raises(CryptoTrackerError):
            raise ExternalAPIError("api error")

    def test_frankfurter_unavailable_is_external_api_error(self):
        with pytest.raises(ExternalAPIError):
            raise FrankfurterUnavailableError("frankfurter down")

    def test_coingecko_unavailable_is_external_api_error(self):
        with pytest.raises(ExternalAPIError):
            raise CoinGeckoUnavailableError("coingecko down")

    def test_rate_limit_exceeded_is_external_api_error(self):
        with pytest.raises(ExternalAPIError):
            raise RateLimitExceededError("rate limited")

    def test_database_error(self):
        with pytest.raises(CryptoTrackerError):
            raise DatabaseError("db error")

    def test_server_unavailable(self):
        with pytest.raises(CryptoTrackerError):
            raise ServerUnavailableError("server down")
