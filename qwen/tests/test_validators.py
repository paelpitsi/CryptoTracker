"""Tests for CLI validators utility functions."""

import pytest
from cryptotracker.cli.utils.validators import (
    is_valid_currency_code,
    is_valid_amount,
    is_valid_date,
    parse_currency_list,
    validate_currency_code,
    validate_amount,
    validate_date,
)


class TestIsValidCurrencyCode:
    """Tests for is_valid_currency_code validator."""

    def test_valid_fiat_code(self):
        assert is_valid_currency_code("USD") is True

    def test_valid_crypto_code(self):
        assert is_valid_currency_code("BTC") is True

    def test_valid_lowercase_converted(self):
        """Lowercase codes should be accepted (converted internally)."""
        assert is_valid_currency_code("eur") is True

    def test_valid_two_char_code(self):
        assert is_valid_currency_code("EU") is True

    def test_invalid_single_char(self):
        assert is_valid_currency_code("U") is False

    def test_invalid_too_long(self):
        assert is_valid_currency_code("ABCDEFGHIJK") is False  # 11 chars

    def test_invalid_with_special_chars(self):
        assert is_valid_currency_code("US$") is False

    def test_invalid_empty_string(self):
        assert is_valid_currency_code("") is False

    def test_valid_with_numbers(self):
        assert is_valid_currency_code("ABC1") is True


class TestIsValidAmount:
    """Tests for is_valid_amount validator."""

    def test_valid_positive_integer(self):
        assert is_valid_amount("100") is True

    def test_valid_positive_float(self):
        assert is_valid_amount("99.99") is True

    def test_invalid_zero(self):
        assert is_valid_amount("0") is False

    def test_invalid_negative(self):
        assert is_valid_amount("-5") is False

    def test_invalid_string(self):
        assert is_valid_amount("abc") is False

    def test_valid_small_amount(self):
        assert is_valid_amount("0.001") is True


class TestIsValidDate:
    """Tests for is_valid_date validator."""

    def test_valid_date(self):
        assert is_valid_date("2024-01-15") is True

    def test_valid_leap_year(self):
        assert is_valid_date("2024-02-29") is True

    def test_invalid_format(self):
        assert is_valid_date("15-01-2024") is False

    def test_invalid_date_value(self):
        assert is_valid_date("2024-02-30") is False

    def test_invalid_string(self):
        assert is_valid_date("not-a-date") is False

    def test_empty_string(self):
        assert is_valid_date("") is False


class TestParseCurrencyList:
    """Tests for parse_currency_list function."""

    def test_single_currency(self):
        result = parse_currency_list("EUR")
        assert result == ["EUR"]

    def test_multiple_currencies(self):
        result = parse_currency_list("EUR,GBP,RUB")
        assert result == ["EUR", "GBP", "RUB"]

    def test_with_spaces(self):
        result = parse_currency_list("EUR, GBP, RUB")
        assert result == ["EUR", "GBP", "RUB"]

    def test_lowercase_converted(self):
        result = parse_currency_list("eur,gbp")
        assert result == ["EUR", "GBP"]

    def test_empty_entries_filtered(self):
        result = parse_currency_list("EUR,,GBP,")
        assert result == ["EUR", "GBP"]


class TestValidateCurrencyCode:
    """Tests for validate_currency_code (returns error message or None)."""

    def test_valid_returns_none(self):
        assert validate_currency_code("USD") is None

    def test_invalid_returns_message(self):
        result = validate_currency_code("US$")
        assert result is not None
        assert "Invalid currency code" in result


class TestValidateAmount:
    """Tests for validate_amount."""

    def test_valid_returns_none(self):
        assert validate_amount("100") is None

    def test_invalid_returns_message(self):
        result = validate_amount("-5")
        assert result is not None
        assert "Invalid amount" in result


class TestValidateDate:
    """Tests for validate_date."""

    def test_valid_returns_none(self):
        assert validate_date("2024-01-15") is None

    def test_invalid_returns_message(self):
        result = validate_date("not-a-date")
        assert result is not None
        assert "Invalid date format" in result
