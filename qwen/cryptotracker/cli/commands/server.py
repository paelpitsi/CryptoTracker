"""Server command for CLI."""

import typer
from rich.console import Console

from cryptotracker.cli.utils.display import display_server_banner
from cryptotracker.common.config import settings

console = Console()

server_app = typer.Typer(help="Start the CryptoTracker server")


@server_app.callback(invoke_without_command=True)
def server(
    host: str = typer.Option(settings.server_host, "--host", help="Host to bind to"),
    port: int = typer.Option(settings.server_port, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes")
):
    """Start the CryptoTracker FastAPI server."""
    display_server_banner(host, port, settings.database_url)
    
    from cryptotracker.server.main import run_server
    run_server(host=host, port=port, reload=reload, workers=workers)
