"""
CLI command tests for CryptoTracker.

Tests the Typer CLI commands in --no-server (direct) mode with mocked
external APIs and a temporary SQLite database.

Minimum 6 tests covering: rate, convert, history, watch, list-watch, export.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text for clean assertions."""
    return ANSI_ESCAPE_RE.sub("", text)


def _invoke(app, cli_runner, *args):
    """Helper: invoke the Typer app with --no-server flag + given args."""
    full_args = ["--no-server"] + list(args)
    return cli_runner.invoke(app, full_args)


# ---------------------------------------------------------------------------
# Test 1 — rate: same base/target → error
# ---------------------------------------------------------------------------


def test_rate_same_currency_error(cli_runner):
    """``cryptotracker rate usd usd`` must fail with a non-zero exit code."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "rate", "usd", "usd")
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test 2 — rate: valid fiat-fiat pair (mocked APIs)
# ---------------------------------------------------------------------------


def test_rate_fiat_to_fiat(mock_frankfurter, mock_coingecko, cli_runner):
    """``cryptotracker rate usd eur`` should succeed with mocked Frankfurter."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "rate", "usd", "eur")
    assert result.exit_code == 0
    clean = _strip_ansi(result.stdout)
    assert "0.92" in clean, f"expected 0.92 in output:\n{clean}"


# ---------------------------------------------------------------------------
# Test 3 — convert: negative amount → error
# ---------------------------------------------------------------------------


def test_convert_negative_amount_error(cli_runner):
    """``cryptotracker convert usd eur -100`` must fail."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "convert", "usd", "eur", "-100")
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test 4 — convert: same base/target → error
# ---------------------------------------------------------------------------


def test_convert_same_currency_error(cli_runner):
    """``cryptotracker convert eur eur 10`` must fail."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "convert", "eur", "eur", "10")
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test 5 — history: empty history for fresh profile
# ---------------------------------------------------------------------------


def test_history_empty(cli_runner):
    """``cryptotracker history`` on a fresh profile shows zero records."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "history")
    assert result.exit_code == 0
    clean = _strip_ansi(result.stdout).lower()
    assert "0 of 0 total" in clean, f"expected empty history in:\n{clean}"


# ---------------------------------------------------------------------------
# Test 6 — watch: add a pair (mocked APIs)
# ---------------------------------------------------------------------------


def test_watch_add_pair(mock_frankfurter, mock_coingecko, cli_runner):
    """``cryptotracker watch btc usd`` should add the pair."""
    from cryptotracker.main import app

    result = _invoke(app, cli_runner, "watch", "btc", "usd")
    assert result.exit_code == 0
    # Should contain a confirmation message
    assert "btc" in result.stdout.lower()
    assert "usd" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Test 7 — watch: duplicate pair → error
# ---------------------------------------------------------------------------


def test_watch_duplicate_pair_error(mock_frankfurter, mock_coingecko, cli_runner):
    """Adding the same pair twice must fail."""
    from cryptotracker.main import app

    _invoke(app, cli_runner, "watch", "btc", "usd")
    result = _invoke(app, cli_runner, "watch", "btc", "usd")
    assert result.exit_code != 0
    assert "already" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Test 8 — list-watch: lists tracked pairs
# ---------------------------------------------------------------------------


def test_list_watch(mock_frankfurter, mock_coingecko, cli_runner):
    """``cryptotracker list-watch`` shows tracked pairs."""
    from cryptotracker.main import app

    _invoke(app, cli_runner, "watch", "btc", "usd")
    _invoke(app, cli_runner, "watch", "eth", "eur")

    result = _invoke(app, cli_runner, "list-watch")
    assert result.exit_code == 0
    assert "btc" in result.stdout.lower()
    assert "eth" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Test 9 — export: JSON export (mocked)
# ---------------------------------------------------------------------------


def test_export_json(mock_frankfurter, mock_coingecko, cli_runner, tmp_path):
    """``cryptotracker export`` writes a JSON file."""
    from cryptotracker.main import app

    _invoke(app, cli_runner, "rate", "usd", "eur")

    output_file = tmp_path / "export_test.json"
    result = _invoke(
        app,
        cli_runner,
        "export",
        "--format",
        "json",
        "--output",
        str(output_file),
    )
    assert result.exit_code == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert "data" in data


# ---------------------------------------------------------------------------
# Test 10 — export: CSV export (mocked)
# ---------------------------------------------------------------------------


def test_export_csv(mock_frankfurter, mock_coingecko, cli_runner, tmp_path):
    """``cryptotracker export --format csv`` writes a CSV file."""
    from cryptotracker.main import app

    _invoke(app, cli_runner, "rate", "usd", "eur")

    output_file = tmp_path / "export_test.csv"
    result = _invoke(
        app,
        cli_runner,
        "export",
        "--format",
        "csv",
        "--output",
        str(output_file),
    )
    assert result.exit_code == 0
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    # CSV should have a header row
    assert "command" in content or "base_currency" in content
