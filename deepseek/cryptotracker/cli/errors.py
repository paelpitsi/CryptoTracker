"""
CLI error handling utilities.

Provides helper functions and exit code constants for consistent error
reporting in the CLI layer.
"""

import sys
from typing import Optional

import httpx

from cryptotracker.cli.formatting import error_panel


# ---------------------------------------------------------------------------
# Exit codes (matching TZ Appendix A)
# ---------------------------------------------------------------------------

EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_SERVER_UNREACHABLE = 2
EXIT_EXTERNAL_API_ERROR = 3
EXIT_DATABASE_ERROR = 4
EXIT_EXPORT_ERROR = 5


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def handle_cli_error(
    title: str,
    message: str,
    hint: Optional[str] = None,
    details: Optional[dict[str, str]] = None,
    exit_code: int = EXIT_VALIDATION_ERROR,
) -> None:
    """Display a user-friendly error panel and exit.

    Args:
        title: Short error title.
        message: Human-readable description.
        hint: Optional hint for resolution.
        details: Optional extra fields.
        exit_code: Process exit code.
    """
    error_panel(title, message, hint=hint, details=details)
    sys.exit(exit_code)


def handle_http_error(exc: httpx.HTTPStatusError) -> None:
    """Handle an HTTP error from the server or external API.

    Args:
        exc: The httpx HTTPStatusError exception.
    """
    status = exc.response.status_code
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)

    if status == 404:
        handle_cli_error(
            "Currency Not Found",
            detail,
            hint="Run: cryptotracker currencies   or   cryptotracker crypto-currencies",
            exit_code=EXIT_VALIDATION_ERROR,
        )
    elif status == 409:
        handle_cli_error(
            "Pair Already Tracked",
            detail,
            hint="Use 'cryptotracker list-watch' to see tracked pairs.",
            exit_code=EXIT_VALIDATION_ERROR,
        )
    elif status == 422:
        handle_cli_error(
            "Invalid Input",
            detail,
            exit_code=EXIT_VALIDATION_ERROR,
        )
    elif status >= 500:
        handle_cli_error(
            "Server Error",
            detail,
            exit_code=EXIT_EXTERNAL_API_ERROR,
        )
    else:
        handle_cli_error(
            f"HTTP Error {status}",
            detail,
            exit_code=EXIT_VALIDATION_ERROR,
        )


def handle_connection_error(exc: Exception) -> None:
    """Handle a connection error (server unreachable).

    Args:
        exc: The connection exception.
    """
    error_panel(
        "Server Unreachable",
        f"Could not connect to the CryptoTracker server: {exc}",
        hint="Start the server with: cryptotracker server\n"
             "Or use --no-server for direct mode.",
    )