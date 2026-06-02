"""List-watch command for CLI."""

import asyncio
from datetime import datetime
from typing import Optional
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_watchlist_detail,
    display_success,
    display_error,
    console
)
from cryptotracker.common.exceptions import ServerUnavailableError

list_watch_app = typer.Typer(help="View all watchlists with current rates")


@list_watch_app.callback(invoke_without_command=True)
def list_watch(
    name: Optional[list[str]] = typer.Option(None, "--name", "-n", help="Watchlist names to show"),
    sort: str = typer.Option("name", "--sort", "-s", help="Sort by (name, rate, change)"),
    type: str = typer.Option("all", "--type", "-t", help="Filter by type (fiat, crypto, all)")
):
    """View all watchlists with current rates."""
    asyncio.run(_list_watch_async(name, sort, type))


async def _list_watch_async(names: Optional[list[str]], sort: str, currency_type: str):
    """Async implementation of list-watch command."""
    try:
        client = APIClient()
        
        # Get all watchlists
        watchlists_result = await client.get_watchlists()
        watchlists = watchlists_result["watchlists"]
        
        # Filter by name if specified
        if names:
            watchlists = [w for w in watchlists if w["name"].lower() in [n.lower() for n in names]]
        
        if not watchlists:
            console.print("[yellow]No watchlists found[/yellow]")
            return
        
        # Display each watchlist
        total_pairs = 0
        for watchlist in watchlists:
            console.print(f"\n[bold]Watchlist: {watchlist['name']}[/bold]")
            
            detail = await client.get_watchlist(watchlist["id"])
            
            # Filter by type if specified
            if currency_type != "all":
                detail["items"] = [i for i in detail["items"] if i["type"] == currency_type]
            
            # Sort items
            if sort == "rate":
                detail["items"].sort(key=lambda x: float(x.get("current_rate") or 0), reverse=True)
            elif sort == "change":
                detail["items"].sort(
                    key=lambda x: float(x.get("change_24h") or 0),
                    reverse=True
                )
            else:  # name
                detail["items"].sort(key=lambda x: f"{x['base_currency']}/{x['target_currency']}")
            
            display_watchlist_detail(detail, datetime.utcnow())
            total_pairs += len(detail["items"])
        
        console.print(f"\nTotal pairs: {total_pairs}")
        display_success("Query saved to history")
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)
