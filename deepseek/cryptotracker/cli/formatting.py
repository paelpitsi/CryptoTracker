"""
Rich formatting utilities for CLI output.

Provides coloured panels, tables, progress bars, and number formatting
consistent with the CryptoTracker design system.
"""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

import os
import sys

# Force UTF-8 output on Windows to support emoji and box-drawing characters
os.environ.setdefault("PYTHONUTF8", "1")

console = Console(
    force_terminal=True,
    color_system="standard",
    legacy_windows=False if sys.platform == "win32" else None,
)


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

HEADER_STYLE = "bold cyan"
SUCCESS_STYLE = "bold green"
ERROR_STYLE = "bold red"
CURRENCY_STYLE = "bold yellow"
TIMESTAMP_STYLE = "dim"
SOURCE_STYLE = "italic dim"
AMOUNT_STYLE = "bold green"


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------


def format_currency(amount: float, currency: str) -> str:
    """Format a currency amount with appropriate decimal places.

    Fiat currencies: 2 decimal places with thousands separators.
    Cryptocurrencies: up to 8 decimal places if < 1.

    Args:
        amount: The numeric amount.
        currency: Currency code (lowercase).

    Returns:
        Formatted string like '68,450.12' or '0.00251432'.
    """
    # Known fiat currencies (uppercase, 3-letter codes are typically fiat)
    is_fiat = len(currency) == 3 and currency.isalpha()

    if is_fiat:
        if abs(amount) < 0.01 and amount != 0:
            return f"{amount:.6f}"
        return f"{amount:,.2f}"
    else:
        # Crypto: show up to 8 decimals if fractional
        if abs(amount) >= 1:
            return f"{amount:,.2f}"
        else:
            return f"{amount:.8f}"


def format_pair(base: str, target: str) -> str:
    """Format a currency pair for display.

    Args:
        base: Base currency code.
        target: Target currency code.

    Returns:
        Formatted string: 'BTC → USD'.
    """
    return f"{base.upper()} → {target.upper()}"


def format_timestamp(dt: datetime) -> str:
    """Format a datetime for display in the user's local time.

    Args:
        dt: A timezone-aware datetime.

    Returns:
        Formatted string like '2026-05-26 13:30:00'.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------


def rate_panel(
    base: str,
    target: str,
    rate: float,
    source: str,
    fetched_at: datetime,
) -> None:
    """Display a rate query result in a styled panel."""
    content = "\n".join([
        f"  [bold yellow]Pair[/]      │ {format_pair(base, target)}",
        f"  [bold yellow]Rate[/]      │ [bold green]1 {base.upper()} = "
        f"{format_currency(rate, target)} {target.upper()}[/]",
        f"  [bold yellow]Source[/]    │ [{SOURCE_STYLE}]{source}[/]",
        f"  [bold yellow]Fetched[/]   │ [{TIMESTAMP_STYLE}]{format_timestamp(fetched_at)}[/]",
    ])
    panel = Panel(
        content,
        title="[bold cyan]💱 Current Exchange Rate[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def convert_panel(
    base: str,
    target: str,
    amount: float,
    result: float,
    rate: float,
    source: str,
    converted_at: datetime,
) -> None:
    """Display a conversion result in a styled panel."""
    content = "\n".join([
        f"  [bold yellow]From[/]        │ {format_currency(amount, base)} "
        f"{base.upper()}",
        f"  [bold yellow]To[/]          │ [bold green]{format_currency(result, target)} "
        f"{target.upper()}[/]",
        f"  [bold yellow]Rate[/]        │ 1 {base.upper()} = "
        f"{format_currency(rate, target)} {target.upper()}",
        f"  [bold yellow]Source[/]      │ [{SOURCE_STYLE}]{source}[/]",
        f"  [bold yellow]Converted[/]   │ [{TIMESTAMP_STYLE}]{format_timestamp(converted_at)}[/]",
    ])
    panel = Panel(
        content,
        title="[bold cyan]🔄 Currency Conversion[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def watch_add_panel(
    base: str,
    target: str,
    pair_type: str,
    added_at: datetime,
) -> None:
    """Display a watchlist add confirmation."""
    content = "\n".join([
        f"  [bold yellow]Pair[/]       │ {format_pair(base, target)}",
        f"  [bold yellow]Type[/]       │ {pair_type}",
        f"  [bold yellow]Added[/]      │ [{TIMESTAMP_STYLE}]{format_timestamp(added_at)}[/]",
    ])
    panel = Panel(
        content,
        title="[bold cyan]👁️  Added to Watchlist[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def watch_remove_panel(base: str, target: str) -> None:
    """Display a watchlist remove confirmation."""
    content = f"  [bold yellow]Pair[/]       │ {format_pair(base, target)}"
    panel = Panel(
        content,
        title="[bold cyan]🗑️  Removed from Watchlist[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def export_panel(
    format_name: str,
    dataset: str,
    records: int,
    output_path: str,
    size_bytes: int,
) -> None:
    """Display export completion info."""
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

    content = "\n".join([
        f"  [bold yellow]Format[/]     │ {format_name.upper()}",
        f"  [bold yellow]Dataset[/]    │ {dataset}",
        f"  [bold yellow]Records[/]    │ [bold green]{records}[/]",
        f"  [bold yellow]Output[/]     │ {output_path}",
        f"  [bold yellow]Size[/]       │ {size_str}",
    ])
    panel = Panel(
        content,
        title="[bold cyan]📦 Export Complete[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def server_banner(
    host: str,
    port: int,
    db_path: str,
    profile: str,
) -> None:
    """Display the server startup banner."""
    content = "\n".join([
        f"  [bold yellow]Server[/]    │ http://{host}:{port}",
        f"  [bold yellow]API Docs[/]  │ http://{host}:{port}/docs",
        f"  [bold yellow]Database[/]  │ {db_path}",
        f"  [bold yellow]Profile[/]   │ {profile}",
    ])
    panel = Panel(
        content,
        title="[bold cyan]🚀 CryptoTracker Server[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Error panel
# ---------------------------------------------------------------------------


def error_panel(
    title: str,
    message: str,
    hint: Optional[str] = None,
    details: Optional[dict[str, str]] = None,
) -> None:
    """Display an error in a styled panel.

    Args:
        title: Error title (e.g., 'Currency Not Found').
        message: Human-readable error description.
        hint: Optional hint for the user.
        details: Optional dict of extra fields (currency, etc.).
    """
    lines = [f"  [bold yellow]Message[/]   │ {message}"]
    if details:
        for key, value in details.items():
            lines.append(f"  [bold yellow]{key.capitalize()}[/]  │ {value}")
    if hint:
        lines.append(f"  [bold yellow]Hint[/]      │ [{SOURCE_STYLE}]{hint}[/]")

    panel = Panel(
        "\n".join(lines),
        title=f"[bold red]❌ Error: {title}[/]",
        border_style="red",
        box=box.ROUNDED,
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def history_table(
    items: list[dict],
    profile: str,
    total: int,
    limit: int,
    offset: int,
) -> None:
    """Render a Rich table of request history.

    Args:
        items: List of dicts with keys: id, command, params_json,
               status_code, created_at.
        profile: Profile name.
        total: Total count of records.
        limit: Page size.
        offset: Current offset.
    """
    table = Table(
        title=f"[bold cyan]📋 Request History (profile: {profile})[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_header=True,
    )
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Command", style="bold yellow")
    table.add_column("Parameters")
    table.add_column("Status")
    table.add_column("Timestamp", style=TIMESTAMP_STYLE)

    for item in items:
        command = item.get("command", "")
        params = item.get("params_json", "")
        status = item.get("status_code", 0)
        ts = item.get("created_at", "")

        # Format params nicely
        try:
            import json
            p = json.loads(params)
            if "base" in p and "target" in p:
                params_str = f"{p['base']} → {p['target']}"
                if "amount" in p:
                    params_str = f"{p['amount']} {params_str}"
            else:
                params_str = params
        except (json.JSONDecodeError, KeyError):
            params_str = params

        # Status with emoji
        if 200 <= status < 300:
            status_str = f"[green]✅ {status}[/]"
        else:
            status_str = f"[red]❌ {status}[/]"

        # Timestamp
        if isinstance(ts, datetime):
            ts_str = format_timestamp(ts)
        elif isinstance(ts, str):
            ts_str = ts[:19].replace("T", " ")
        else:
            ts_str = str(ts)

        table.add_row(
            str(item.get("id", "")),
            command,
            params_str,
            status_str,
            ts_str,
        )

    console.print(table)
    console.print(
        f"[dim]Showing {len(items)} of {total} total records "
        f"(limit={limit}, offset={offset})[/]"
    )


def watchlist_table(items: list[dict], profile: str) -> None:
    """Render a Rich table of watchlist entries with current rates.

    Args:
        items: List of dicts with keys: id, base, target, pair_type,
               current_rate, rate_source, added_at.
        profile: Profile name.
    """
    table = Table(
        title=f"[bold cyan]👁️  Watchlist (profile: {profile})[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_header=True,
    )
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Base", style="bold yellow")
    table.add_column("Target", style="bold yellow")
    table.add_column("Rate", justify="right")
    table.add_column("Source", style=SOURCE_STYLE)
    table.add_column("Added", style=TIMESTAMP_STYLE)

    for item in items:
        rate = item.get("current_rate")
        if rate is not None:
            rate_str = (
                f"[bold green]{format_currency(rate, item.get('target', ''))}[/]"
            )
        else:
            rate_str = "[red]N/A[/]"

        source = item.get("rate_source", "unavailable")
        added = item.get("added_at", "")
        if isinstance(added, datetime):
            added_str = added.strftime("%b %d, %Y")
        elif isinstance(added, str):
            added_str = added[:10]
        else:
            added_str = str(added)

        table.add_row(
            str(item.get("id", "")),
            item.get("base", "").upper(),
            item.get("target", "").upper(),
            rate_str,
            source,
            added_str,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


def create_progress() -> Progress:
    """Create a Rich progress bar for async operations.

    Returns:
        A configured Progress instance (caller must use it as context manager).
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )