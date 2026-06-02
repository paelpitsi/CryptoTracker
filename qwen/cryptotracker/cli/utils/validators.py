"""Validators for CLI arguments."""

import re
from datetime import datetime
from typing import Optional


def is_valid_currency_code(code: str) -> bool:
    """Validate currency code format (3-10 uppercase letters/numbers)."""
    pattern = r"^[A-Z0-9]{2,10}$"
    return bool(re.match(pattern, code.upper()))


def is_valid_amount(amount: str) -> bool:
    """Validate amount format (positive number)."""
    try:
        value = float(amount)
        return value > 0
    except ValueError:
        return False


def is_valid_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_currency_list(currencies_str: str) -> list[str]:
    """Parse comma-separated currency list."""
    return [c.strip().upper() for c in currencies_str.split(",") if c.strip()]


def validate_currency_code(code: str) -> Optional[str]:
    """Validate and return error message if invalid."""
    if not is_valid_currency_code(code):
        return f"Invalid currency code '{code}'. Must be 2-10 uppercase letters/numbers."
    return None


def validate_amount(amount: str) -> Optional[str]:
    """Validate and return error message if invalid."""
    if not is_valid_amount(amount):
        return f"Invalid amount '{amount}'. Must be a positive number."
    return None


def validate_date(date_str: str) -> Optional[str]:
    """Validate and return error message if invalid."""
    if not is_valid_date(date_str):
        return f"Invalid date format '{date_str}'. Must be YYYY-MM-DD."
    return None
