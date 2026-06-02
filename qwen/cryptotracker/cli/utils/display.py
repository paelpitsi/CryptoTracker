"""Rich display helpers for CLI output."""

import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn


# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console()


def format_rate(rate: Decimal, precision: int = 8) -> str:
    """Format rate with appropriate precision."""
    if rate < Decimal("0.0001"):
        return f"{rate:.8f}"
    elif rate < Decimal("1"):
        return f"{rate:.6f}"
    elif rate < Decimal("100"):
        return f"{rate:.4f}"
    else:
        return f"{rate:,.2f}"


def format_change(change: Optional[Decimal]) -> str:
    """Format 24h change percentage."""
    if change is None:
        return "-"
    
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"


def get_change_style(change: Optional[Decimal]) -> str:
    """Get Rich style for change value."""
    if change is None:
        return "dim"
    return "green" if change >= 0 else "red"


def display_rates_table(base: str, rates: list[dict], timestamp: datetime) -> None:
    """Display exchange rates in a Rich table."""
    
    table = Table(
        title=f"Exchange Rates - {base} ({timestamp.strftime('%Y-%m-%d %H:%M')})",
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    table.add_column("Target", style="cyan", justify="left")
    table.add_column("Rate", style="white", justify="right")
    table.add_column("Type", style="yellow", justify="center")
    table.add_column("24h Change", style="green", justify="right")
    
    for rate in rates:
        change = rate.get("change_24h")
        change_str = format_change(Decimal(str(change)) if change else None)
        change_style = get_change_style(Decimal(str(change)) if change else None)
        
        table.add_row(
            rate["target"],
            format_rate(Decimal(str(rate["rate"]))),
            rate["type"].capitalize(),
            f"[{change_style}]{change_str}[/{change_style}]"
        )
    
    console.print(table)


def display_conversion_panel(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    result: Decimal,
    rate: Decimal,
    timestamp: datetime,
    currency_type: str,
    change_24h: Optional[Decimal] = None
) -> None:
    """Display currency conversion result in a Rich panel."""
    
    change_str = format_change(change_24h)
    change_style = get_change_style(change_24h)
    
    content = Text()
    content.append(f"\n  Amount:     ", style="bold")
    content.append(f"{amount:.2f} {from_currency}\n")
    content.append(f"  Rate:       ", style="bold")
    content.append(f"{format_rate(rate)} {from_currency}/{to_currency}\n")
    content.append(f"  Result:     ", style="bold")
    content.append(f"{format_rate(result)} {to_currency}\n")
    
    if change_24h is not None:
        content.append(f"\n  24h Change: ", style="bold")
        content.append(f"{change_str}", style=change_style)
        content.append("\n")
    
    content.append(f"  Timestamp:  ", style="bold")
    content.append(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
    content.append(f"  Type:       ", style="bold")
    content.append(f"{currency_type.capitalize()}\n")
    
    panel = Panel(
        content,
        title="Currency Conversion",
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)


def display_history_table(queries: list[dict], total: int, limit: int, offset: int) -> None:
    """Display query history in a Rich table."""
    
    table = Table(
        title=f"Query History (Last {limit} queries)",
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        show_lines=True
    )
    
    table.add_column("ID", style="dim", justify="right", width=4)
    table.add_column("Timestamp", style="cyan", justify="left", width=19)
    table.add_column("Command", style="yellow", justify="left", width=10)
    table.add_column("Details", style="white", justify="left")
    table.add_column("Status", style="green", justify="center", width=8)
    
    for query in queries:
        status = query["status"]
        status_style = "green" if status == "success" else "red"
        
        # Format details
        details = []
        for item in query.get("items", []):
            if query["command_type"] == "convert":
                details.append(f"{item['base_currency']} → {item['target_currency']}")
            else:
                details.append(f"{item['base_currency']}/{item['target_currency']}")
        
        details_str = ", ".join(details[:3])
        if len(details) > 3:
            details_str += f" (+{len(details) - 3} more)"
        
        created_at = datetime.fromisoformat(query["created_at"].replace("Z", "+00:00"))
        
        table.add_row(
            str(query["id"]),
            created_at.strftime("%Y-%m-%d %H:%M:%S"),
            query["command_type"],
            details_str,
            f"[{status_style}]{status.capitalize()}[/{status_style}]"
        )
    
    console.print(table)
    console.print(f"\nTotal queries: {total}")
    console.print(f"Showing: {offset + 1}-{offset + len(queries)}")


def display_watchlists_table(watchlists: list[dict]) -> None:
    """Display watchlists in a Rich table."""
    
    table = Table(
        title="Your Watchlists",
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    table.add_column("ID", style="dim", justify="right", width=4)
    table.add_column("Name", style="cyan", justify="left")
    table.add_column("Description", style="white", justify="left")
    table.add_column("Items", style="yellow", justify="right", width=6)
    
    for watchlist in watchlists:
        table.add_row(
            str(watchlist["id"]),
            watchlist["name"],
            watchlist.get("description") or "-",
            str(watchlist["items_count"])
        )
    
    console.print(table)


def display_watchlist_detail(watchlist: dict, timestamp: datetime) -> None:
    """Display watchlist details with current rates."""
    
    table = Table(
        title=f"Watchlist: {watchlist['name']} ({timestamp.strftime('%Y-%m-%d %H:%M')})",
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    table.add_column("Pair", style="cyan", justify="left")
    table.add_column("Rate", style="white", justify="right")
    table.add_column("Type", style="yellow", justify="center")
    table.add_column("24h Change", style="green", justify="right")
    
    for item in watchlist.get("items", []):
        pair = f"{item['base_currency']}/{item['target_currency']}"
        rate = item.get("current_rate")
        change = item.get("change_24h")
        
        rate_str = format_rate(Decimal(str(rate))) if rate else "N/A"
        change_str = format_change(Decimal(str(change)) if change else None)
        change_style = get_change_style(Decimal(str(change)) if change else None)
        
        table.add_row(
            pair,
            rate_str,
            item["type"].capitalize(),
            f"[{change_style}]{change_str}[/{change_style}]"
        )
    
    console.print(table)


def display_success(message: str) -> None:
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def display_error(message: str) -> None:
    """Display error message."""
    console.print(f"[red]✗[/red] Error: {message}")


def display_warning(message: str) -> None:
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] Warning: {message}")


def display_info(message: str) -> None:
    """Display info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def create_progress() -> Progress:
    """Create a Rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    )


def display_server_banner(host: str, port: int, database_url: str) -> None:
    """Display server startup banner."""
    
    banner = Text()
    banner.append("CryptoTracker Server v1.0.0\n", style="bold cyan")
    banner.append("\n")
    banner.append(f"Starting server on http://{host}:{port}\n", style="white")
    banner.append(f"Database: {database_url}\n", style="dim")
    banner.append(f"API Documentation: http://{host}:{port}/docs\n", style="cyan")
    banner.append("\n")
    banner.append("Press CTRL+C to stop the server", style="yellow")
    
    panel = Panel(
        banner,
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)
