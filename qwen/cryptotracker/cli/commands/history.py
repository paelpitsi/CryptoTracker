"""History command for CLI."""

import asyncio
from typing import Optional
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_history_table,
    display_success,
    display_error,
    display_warning,
    console
)
from cryptotracker.cli.utils.validators import is_valid_date
from cryptotracker.common.exceptions import ServerUnavailableError

history_app = typer.Typer(help="View query history")


@history_app.callback(invoke_without_command=True)
def history(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of records"),
    command: Optional[str] = typer.Option(None, "--command", "-c", help="Filter by command type"),
    from_date: Optional[str] = typer.Option(None, "--from-date", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to-date", help="End date (YYYY-MM-DD)"),
    clear: bool = typer.Option(False, "--clear", help="Clear all history"),
    clear_older_than: Optional[int] = typer.Option(None, "--clear-older-than", help="Delete records older than N days")
):
    """View or manage query history."""
    asyncio.run(_history_async(limit, command, from_date, to_date, clear, clear_older_than))


async def _history_async(
    limit: int,
    command: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    clear: bool,
    clear_older_than: Optional[int]
):
    """Async implementation of history command."""
    
    if from_date and not is_valid_date(from_date):
        display_error(f"Invalid from-date format '{from_date}'. Must be YYYY-MM-DD.")
        raise typer.Exit(code=1)
    
    if to_date and not is_valid_date(to_date):
        display_error(f"Invalid to-date format '{to_date}'. Must be YYYY-MM-DD.")
        raise typer.Exit(code=1)
    
    try:
        client = APIClient()
        
        if clear or clear_older_than:
            # Delete operation
            if clear:
                confirm = typer.confirm("Are you sure you want to delete ALL history?")
                if not confirm:
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return
                
                result = await client.delete_history(delete_all=True)
            else:
                confirm = typer.confirm(
                    f"Are you sure you want to delete history older than {clear_older_than} days?"
                )
                if not confirm:
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return
                
                result = await client.delete_history(older_than_days=clear_older_than)
            
            display_success(result["message"])
        else:
            # Get operation
            result = await client.get_history(
                limit=limit,
                offset=0,
                command_type=command,
                date_from=from_date,
                date_to=to_date
            )
            
            if not result["queries"]:
                console.print("[yellow]No history records found[/yellow]")
                return
            
            display_history_table(
                queries=result["queries"],
                total=result["total"],
                limit=result["limit"],
                offset=result["offset"]
            )
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)
