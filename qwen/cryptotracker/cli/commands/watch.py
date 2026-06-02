"""Watch command for CLI."""

import asyncio
from datetime import datetime
from typing import Optional
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_watchlists_table,
    display_watchlist_detail,
    display_success,
    display_error,
    console
)
from cryptotracker.cli.utils.validators import is_valid_currency_code
from cryptotracker.common.exceptions import ServerUnavailableError

watch_app = typer.Typer(help="Manage watchlists")


@watch_app.command("list")
def list_watchlists():
    """List all watchlists."""
    asyncio.run(_list_watchlists_async())


async def _list_watchlists_async():
    """Async implementation of list watchlists."""
    try:
        client = APIClient()
        result = await client.get_watchlists()
        
        if not result["watchlists"]:
            console.print("[yellow]No watchlists found[/yellow]")
            return
        
        display_watchlists_table(result["watchlists"])
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)


@watch_app.command("show")
def show_watchlist(
    name: str = typer.Argument(..., help="Watchlist name or ID")
):
    """Show watchlist contents with current rates."""
    asyncio.run(_show_watchlist_async(name))


async def _show_watchlist_async(name: str):
    """Async implementation of show watchlist."""
    try:
        client = APIClient()
        
        # Try to parse as ID first
        try:
            watchlist_id = int(name)
        except ValueError:
            # Find by name
            watchlists = await client.get_watchlists()
            watchlist_id = None
            for w in watchlists["watchlists"]:
                if w["name"].lower() == name.lower():
                    watchlist_id = w["id"]
                    break
            
            if watchlist_id is None:
                display_error(f"Watchlist '{name}' not found")
                raise typer.Exit(code=4)
        
        result = await client.get_watchlist(watchlist_id)
        display_watchlist_detail(result, datetime.utcnow())
        display_success(f"Query saved to history")
        
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


@watch_app.command("create")
def create_watchlist(
    name: str = typer.Argument(..., help="Watchlist name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Watchlist description")
):
    """Create a new watchlist."""
    asyncio.run(_create_watchlist_async(name, description))


async def _create_watchlist_async(name: str, description: Optional[str]):
    """Async implementation of create watchlist."""
    try:
        client = APIClient()
        result = await client.create_watchlist(name, description)
        display_success(f"Watchlist '{name}' created (ID: {result['id']})")
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)


@watch_app.command("delete")
def delete_watchlist(
    name: str = typer.Argument(..., help="Watchlist name or ID")
):
    """Delete a watchlist."""
    asyncio.run(_delete_watchlist_async(name))


async def _delete_watchlist_async(name: str):
    """Async implementation of delete watchlist."""
    try:
        client = APIClient()
        
        # Try to parse as ID first
        try:
            watchlist_id = int(name)
        except ValueError:
            # Find by name
            watchlists = await client.get_watchlists()
            watchlist_id = None
            for w in watchlists["watchlists"]:
                if w["name"].lower() == name.lower():
                    watchlist_id = w["id"]
                    break
            
            if watchlist_id is None:
                display_error(f"Watchlist '{name}' not found")
                raise typer.Exit(code=4)
        
        confirm = typer.confirm(f"Are you sure you want to delete watchlist '{name}'?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        result = await client.delete_watchlist(watchlist_id)
        display_success(result["message"])
        
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


@watch_app.command("add")
def add_to_watchlist(
    name: str = typer.Argument(..., help="Watchlist name or ID"),
    base: str = typer.Argument(..., help="Base currency code"),
    target: str = typer.Argument(..., help="Target currency code"),
    type: str = typer.Option("fiat", "--type", "-t", help="Currency type (fiat or crypto)")
):
    """Add a currency pair to a watchlist."""
    asyncio.run(_add_to_watchlist_async(name, base, target, type))


async def _add_to_watchlist_async(name: str, base: str, target: str, currency_type: str):
    """Async implementation of add to watchlist."""
    base = base.upper()
    target = target.upper()
    
    if not is_valid_currency_code(base):
        display_error(f"Invalid base currency code '{base}'")
        raise typer.Exit(code=1)
    
    if not is_valid_currency_code(target):
        display_error(f"Invalid target currency code '{target}'")
        raise typer.Exit(code=1)
    
    try:
        client = APIClient()
        
        # Try to parse as ID first
        try:
            watchlist_id = int(name)
        except ValueError:
            # Find by name
            watchlists = await client.get_watchlists()
            watchlist_id = None
            for w in watchlists["watchlists"]:
                if w["name"].lower() == name.lower():
                    watchlist_id = w["id"]
                    break
            
            if watchlist_id is None:
                display_error(f"Watchlist '{name}' not found")
                raise typer.Exit(code=4)
        
        result = await client.add_watchlist_item(watchlist_id, base, target, currency_type)
        display_success(f"Added {base}/{target} to watchlist")
        
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


@watch_app.command("remove")
def remove_from_watchlist(
    name: str = typer.Argument(..., help="Watchlist name or ID"),
    base: str = typer.Argument(..., help="Base currency code"),
    target: str = typer.Argument(..., help="Target currency code")
):
    """Remove a currency pair from a watchlist."""
    asyncio.run(_remove_from_watchlist_async(name, base, target))


async def _remove_from_watchlist_async(name: str, base: str, target: str):
    """Async implementation of remove from watchlist."""
    base = base.upper()
    target = target.upper()
    
    try:
        client = APIClient()
        
        # Try to parse as ID first
        try:
            watchlist_id = int(name)
        except ValueError:
            # Find by name
            watchlists = await client.get_watchlists()
            watchlist_id = None
            for w in watchlists["watchlists"]:
                if w["name"].lower() == name.lower():
                    watchlist_id = w["id"]
                    break
            
            if watchlist_id is None:
                display_error(f"Watchlist '{name}' not found")
                raise typer.Exit(code=4)
        
        # Get watchlist to find item ID
        watchlist = await client.get_watchlist(watchlist_id)
        item_id = None
        for item in watchlist["items"]:
            if item["base_currency"] == base and item["target_currency"] == target:
                item_id = item["id"]
                break
        
        if item_id is None:
            display_error(f"Currency pair {base}/{target} not found in watchlist")
            raise typer.Exit(code=4)
        
        result = await client.remove_watchlist_item(watchlist_id, item_id)
        display_success(f"Removed {base}/{target} from watchlist")
        
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
