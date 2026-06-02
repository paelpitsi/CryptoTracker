"""Rate command for CLI."""

import asyncio
from datetime import datetime
from decimal import Decimal
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_rates_table,
    display_success,
    display_error,
    console
)
from cryptotracker.cli.utils.validators import parse_currency_list, is_valid_currency_code
from cryptotracker.common.exceptions import ServerUnavailableError

rate_app = typer.Typer(help="Get exchange rates")


@rate_app.callback(invoke_without_command=True)
def rate(
    base: str = typer.Argument(..., help="Base currency code (e.g., USD)"),
    targets: str = typer.Argument(..., help="Target currencies comma-separated (e.g., EUR,RUB,BTC)"),
    type: str = typer.Option("all", "--type", "-t", help="Currency type (fiat, crypto, all)")
):
    """Get exchange rates for multiple target currencies."""
    asyncio.run(_rate_async(base, targets, type))


async def _rate_async(base: str, targets: str, currency_type: str):
    """Async implementation of rate command."""
    base = base.upper()
    target_list = parse_currency_list(targets)
    
    if not is_valid_currency_code(base):
        display_error(f"Invalid base currency code '{base}'")
        raise typer.Exit(code=1)
    
    for target in target_list:
        if not is_valid_currency_code(target):
            display_error(f"Invalid target currency code '{target}'")
            raise typer.Exit(code=1)
    
    try:
        client = APIClient()
        result = await client.get_rates(base, target_list, currency_type)
        
        display_rates_table(
            base=result["base"],
            rates=result["rates"],
            timestamp=datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
        )
        
        display_success(f"Query saved to history (ID: {result['query_id']})")
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)
