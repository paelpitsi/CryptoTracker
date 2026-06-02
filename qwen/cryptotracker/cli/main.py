"""Main CLI application entry point."""

import typer
from typing import Optional

from cryptotracker import __version__
from cryptotracker.cli.commands.server import server_app
from cryptotracker.cli.commands.rate import rate
from cryptotracker.cli.commands.convert import convert
from cryptotracker.cli.commands.history import history
from cryptotracker.cli.commands.watch import watch_app
from cryptotracker.cli.commands.list_watch import list_watch
from cryptotracker.cli.commands.export import export

app = typer.Typer(
    name="cryptotracker",
    help="CryptoTracker - CLI application for tracking cryptocurrency and fiat currency rates",
    add_completion=False
)

# Add subcommands
app.add_typer(server_app, name="server")
app.command(name="rate")(rate)
app.command(name="convert")(convert)
app.command(name="history")(history)
app.add_typer(watch_app, name="watch")
app.command(name="list-watch")(list_watch)
app.command(name="export")(export)


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"CryptoTracker v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True
    )
):
    """CryptoTracker - Track cryptocurrency and fiat currency rates from the command line."""
    pass


if __name__ == "__main__":
    app()
