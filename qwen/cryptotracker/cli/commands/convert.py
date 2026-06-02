"""Convert command for CLI."""

import asyncio
from datetime import datetime
from decimal import Decimal
import typer
from rich.console import Console

from cryptotracker.client.api_client import APIClient
from cryptotracker.cli.utils.display import (
    display_conversion_panel,
    display_success,
    display_error,
    console
)
from cryptotracker.cli.utils.validators import is_valid_currency_code, is_valid_amount
from cryptotracker.common.exceptions import ServerUnavailableError

convert_app = typer.Typer(help="Convert currency")


@convert_app.callback(invoke_without_command=True)
def convert(
    amount: float = typer.Argument(..., help="Amount to convert"),
    from_currency: str = typer.Argument(..., help="Source currency code"),
    to_currency: str = typer.Argument(..., help="Target currency code"),
    type: str = typer.Option("auto", "--type", "-t", help="Currency type (fiat, crypto, auto)")
):
    """Convert amount from one currency to another."""
    asyncio.run(_convert_async(amount, from_currency, to_currency, type))


async def _convert_async(amount: float, from_currency: str, to_currency: str, currency_type: str):
    """Async implementation of convert command."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if not is_valid_currency_code(from_currency):
        display_error(f"Invalid source currency code '{from_currency}'")
        raise typer.Exit(code=1)
    
    if not is_valid_currency_code(to_currency):
        display_error(f"Invalid target currency code '{to_currency}'")
        raise typer.Exit(code=1)
    
    if amount <= 0:
        display_error(f"Amount must be positive, got {amount}")
        raise typer.Exit(code=1)
    
    try:
        client = APIClient()
        result = await client.convert(amount, from_currency, to_currency, currency_type)
        
        change_24h = None
        if result.get("change_24h") is not None:
            change_24h = Decimal(str(result["change_24h"]))
        
        display_conversion_panel(
            amount=Decimal(str(result["amount"])),
            from_currency=result["from"],
            to_currency=result["to"],
            result=Decimal(str(result["result"])),
            rate=Decimal(str(result["rate"])),
            timestamp=datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00")),
            currency_type=result["type"],
            change_24h=change_24h
        )
        
        display_success(f"Conversion saved to history (ID: {result['query_id']})")
        
    except ServerUnavailableError as e:
        display_error(str(e))
        console.print("\nPlease start the server first:")
        console.print("  [cyan]cryptotracker server[/cyan]")
        raise typer.Exit(code=2)
    except Exception as e:
        display_error(str(e))
        raise typer.Exit(code=99)
