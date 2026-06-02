"""Export command for CLI."""

import asyncio
from typing import Optional
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_success,
    display_error,
    display_info,
    create_progress,
    console
)
from cryptotracker.cli.utils.validators import is_valid_date
from cryptotracker.common.exceptions import ServerUnavailableError

export_app = typer.Typer(help="Export data to CSV or JSON")


@export_app.callback(invoke_without_command=True)
def export(
    source: str = typer.Argument(..., help="Data source (history or watchlist)"),
    format: str = typer.Argument(..., help="Export format (csv or json)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    watchlist_name: Optional[str] = typer.Option(None, "--watchlist-name", "-w", help="Watchlist name"),
    from_date: Optional[str] = typer.Option(None, "--from-date", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to-date", help="End date (YYYY-MM-DD)"),
    command: Optional[str] = typer.Option(None, "--command", "-c", help="Filter by command type"),
    include_rates: bool = typer.Option(True, "--include-rates/--no-include-rates", help="Include current rates")
):
    """Export data to CSV or JSON format."""
    asyncio.run(_export_async(
        source, format, output, watchlist_name, from_date, to_date, command, include_rates
    ))


async def _export_async(
    source: str,
    format: str,
    output: Optional[str],
    watchlist_name: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    command: Optional[str],
    include_rates: bool
):
    """Async implementation of export command."""
    
    if source not in ["history", "watchlist"]:
        display_error(f"Invalid source '{source}'. Must be 'history' or 'watchlist'.")
        raise typer.Exit(code=1)
    
    if format not in ["csv", "json"]:
        display_error(f"Invalid format '{format}'. Must be 'csv' or 'json'.")
        raise typer.Exit(code=1)
    
    if from_date and not is_valid_date(from_date):
        display_error(f"Invalid from-date format '{from_date}'. Must be YYYY-MM-DD.")
        raise typer.Exit(code=1)
    
    if to_date and not is_valid_date(to_date):
        display_error(f"Invalid to-date format '{to_date}'. Must be YYYY-MM-DD.")
        raise typer.Exit(code=1)
    
    if source == "watchlist" and not watchlist_name:
        display_error("Watchlist name is required for watchlist export")
        raise typer.Exit(code=1)
    
    try:
        client = APIClient()
        
        display_info("Exporting data...")
        
        with create_progress() as progress:
            task = progress.add_task("Exporting...", total=100)
            
            if source == "history":
                content, filename = await client.export_history(
                    format=format,
                    date_from=from_date,
                    date_to=to_date,
                    command_type=command
                )
            else:  # watchlist
                # Find watchlist ID by name
                watchlists = await client.get_watchlists()
                watchlist_id = None
                for w in watchlists["watchlists"]:
                    if w["name"].lower() == watchlist_name.lower():
                        watchlist_id = w["id"]
                        break
                
                if watchlist_id is None:
                    display_error(f"Watchlist '{watchlist_name}' not found")
                    console.print("\nAvailable watchlists:")
                    for w in watchlists["watchlists"]:
                        console.print(f"  - {w['name']} ({w['items_count']} items)")
                    raise typer.Exit(code=4)
                
                content, filename = await client.export_watchlist(
                    watchlist_id=watchlist_id,
                    format=format,
                    include_rates=include_rates
                )
            
            progress.update(task, advance=50)
            
            # Save to file
            output_path = output or filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            progress.update(task, advance=50)
        
        display_success(f"Successfully exported data")
        display_success(f"File saved: {output_path}")
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except typer.Exit:
        raise
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)
