"""Tests for CLI commands using Typer CliRunner."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typer.testing import CliRunner

from cryptotracker.cli.main import app
from cryptotracker import __version__

runner = CliRunner()


class TestCLIVersion:
    """Test the --version flag."""

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestCLIRateCommand:
    """Test the 'rate' CLI command."""

    @patch("cryptotracker.cli.commands.rate.APIClient")
    def test_rate_command_success(self, mock_client_class):
        """Test rate command with mocked successful API response."""
        mock_client = AsyncMock()
        mock_client.get_rates.return_value = {
            "base": "USD",
            "rates": [
                {"target": "EUR", "rate": "0.85", "type": "fiat", "change_24h": None},
                {"target": "GBP", "rate": "0.73", "type": "fiat", "change_24h": None},
            ],
            "timestamp": "2024-01-15T12:00:00Z",
            "query_id": 1,
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["rate", "USD", "EUR,GBP"])
        assert result.exit_code == 0

    def test_rate_command_invalid_base(self):
        """Test rate command with invalid base currency code."""
        result = runner.invoke(app, ["rate", "US$", "EUR"])
        assert result.exit_code == 1

    def test_rate_command_invalid_target(self):
        """Test rate command with invalid target currency code."""
        result = runner.invoke(app, ["rate", "USD", "EU$"])
        assert result.exit_code == 1


class TestCLIConvertCommand:
    """Test the 'convert' CLI command."""

    @patch("cryptotracker.cli.commands.convert.APIClient")
    def test_convert_command_success(self, mock_client_class):
        """Test convert command with mocked successful API response."""
        mock_client = AsyncMock()
        mock_client.convert.return_value = {
            "amount": 100.0,
            "from": "USD",
            "to": "EUR",
            "result": 85.0,
            "rate": 0.85,
            "timestamp": "2024-01-15T12:00:00Z",
            "type": "fiat",
            "change_24h": None,
            "query_id": 2,
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["convert", "100", "USD", "EUR"])
        assert result.exit_code == 0

    def test_convert_command_invalid_from_currency(self):
        """Test convert command with invalid source currency."""
        result = runner.invoke(app, ["convert", "100", "US$", "EUR"])
        assert result.exit_code == 1

    def test_convert_command_invalid_to_currency(self):
        """Test convert command with invalid target currency."""
        result = runner.invoke(app, ["convert", "100", "USD", "EU$"])
        assert result.exit_code == 1

    def test_convert_command_negative_amount(self):
        """Test convert command with negative amount."""
        result = runner.invoke(app, ["convert", "-5", "USD", "EUR"])
        # Typer may reject negative numbers or the command logic rejects it
        assert result.exit_code != 0


class TestCLIHistoryCommand:
    """Test the 'history' CLI command."""

    @patch("cryptotracker.cli.commands.history.APIClient")
    def test_history_command_success(self, mock_client_class):
        """Test history command with mocked successful API response."""
        mock_client = AsyncMock()
        mock_client.get_history.return_value = {
            "total": 0,
            "limit": 20,
            "offset": 0,
            "queries": [],
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0

    def test_history_command_invalid_from_date(self):
        """Test history command with invalid from-date format."""
        result = runner.invoke(app, ["history", "--from-date", "not-a-date"])
        assert result.exit_code == 1

    def test_history_command_invalid_to_date(self):
        """Test history command with invalid to-date format."""
        result = runner.invoke(app, ["history", "--to-date", "15-01-2024"])
        assert result.exit_code == 1


class TestCLIExportCommand:
    """Test the 'export' CLI command."""

    def test_export_command_invalid_source(self):
        """Test export command with invalid source."""
        result = runner.invoke(app, ["export", "invalid", "csv"])
        assert result.exit_code == 1

    def test_export_command_invalid_format(self):
        """Test export command with invalid format."""
        result = runner.invoke(app, ["export", "history", "xml"])
        assert result.exit_code == 1

    def test_export_command_watchlist_missing_name(self):
        """Test export command for watchlist without specifying name."""
        result = runner.invoke(app, ["export", "watchlist", "csv"])
        assert result.exit_code == 1


class TestCLIHelpMessages:
    """Test that help messages are displayed correctly."""

    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "CryptoTracker" in result.output

    def test_rate_help(self):
        result = runner.invoke(app, ["rate", "--help"])
        assert result.exit_code == 0

    def test_convert_help(self):
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0

    def test_history_help(self):
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0

    def test_export_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
