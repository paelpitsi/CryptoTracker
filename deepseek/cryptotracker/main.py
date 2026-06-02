"""
CryptoTracker CLI — main entry point.

Registers all CLI commands and global options on a Typer application.
The 'server' command starts the FastAPI backend via uvicorn.
"""

import os
import sys

# Force UTF-8 encoding for console I/O on Windows.
# Must be set before any Rich/Typer imports that touch the console.
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import logging
from pathlib import Path

import typer
import uvicorn

from cryptotracker.cli.commands import (
    set_global_options,
    rate,
    convert,
    history,
    watch,
    list_watch,
    export,
)
from cryptotracker.cli.formatting import (
    console,
    server_banner,
    error_panel,
)
from cryptotracker.config import settings

# ---------------------------------------------------------------------------
# Typer application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="cryptotracker",
    help="CryptoTracker :: Cryptocurrency & Fiat Exchange Rate Tracker",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Global callback — runs before every command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    profile: str = typer.Option(
        "default",
        "--profile",
        help="Profile name for data isolation.",
        show_default=True,
    ),
    server_url: str = typer.Option(
        settings.server_url,
        "--server-url",
        help="Base URL of the CryptoTracker server.",
        show_default=True,
    ),
    server: bool = typer.Option(
        True,
        "--server/--no-server",
        help="Use server mode; --no-server for direct mode.",
        show_default=True,
    ),
) -> None:
    """Set global CLI options for profile, server URL, and mode."""
    set_global_options(
        profile=profile,
        server_url=server_url,
        use_server=server,
    )

    # If no subcommand is given, typer shows help (no_args_is_help=True)
    if ctx.invoked_subcommand is None:
        pass


# ---------------------------------------------------------------------------
# Register commands
# ---------------------------------------------------------------------------


@app.command()
def server(
    host: str = typer.Option(
        "127.0.0.1", "--host", help="Server host address."
    ),
    port: int = typer.Option(
        8420, "--port", help="Server port."
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development."
    ),
) -> None:
    """Start the CryptoTracker backend server."""
    # Resolve DB path
    db_path = str(settings.db_full_path)

    # Display startup banner
    console.print()
    server_banner(
        host=host,
        port=port,
        db_path=db_path,
        profile="default",
    )
    console.print()

    # Logging setup for uvicorn
    log_level = settings.log_level.lower()
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = (
        "%(asctime)s [%(levelname)s] %(message)s"
    )
    log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

    # Check external APIs
    async def _check_apis():
        from cryptotracker.api.frankfurter import frankfurter_client
        from cryptotracker.api.coingecko import coingecko_client
        console.print("[dim]Checking external APIs...[/]")
        ff = await frankfurter_client.check_health()
        cg = await coingecko_client.check_health()
        ff_icon = "✅" if ff == "reachable" else "❌"
        cg_icon = "✅" if cg == "reachable" else "❌"
        console.print(f"[dim]Frankfurter API: {ff_icon} {ff}[/]")
        console.print(f"[dim]CoinGecko API:  {cg_icon} {cg}[/]")
        console.print("[dim]Server started successfully.[/]")
        console.print()

    asyncio.run(_check_apis())

    # Start uvicorn
    uvicorn.run(
        "cryptotracker.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


app.command(name="rate")(rate)
app.command(name="convert")(convert)
app.command(name="history")(history)
app.command(name="watch")(watch)
app.command(name="list-watch")(list_watch)
app.command(name="export")(export)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the CLI.

    Runs the Typer app.  This function is called when the user invokes
    `cryptotracker` from the command line after package installation.
    """
    app()


if __name__ == "__main__":
    main()