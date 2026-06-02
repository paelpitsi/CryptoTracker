"""
CryptoTracker configuration management.

Loads settings from environment variables and .env file using pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CRYPTOTRACKER_",
        extra="ignore",
    )

    # --- Server ---
    server_host: str = "127.0.0.1"
    server_port: int = 8420

    # --- Database ---
    db_path: str = "data/cryptotracker.db"

    # --- External APIs ---
    frankfurter_url: str = "https://api.frankfurter.app"
    coingecko_url: str = "https://api.coingecko.com/api/v3"

    # --- HTTP Client ---
    request_timeout: float = 15.0
    max_retries: int = 3

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def server_url(self) -> str:
        """Full server base URL."""
        return f"http://{self.server_host}:{self.server_port}"

    @property
    def api_url(self) -> str:
        """Base API URL."""
        return f"{self.server_url}/api"

    @property
    def db_full_path(self) -> Path:
        """Resolved absolute path to the database file."""
        p = Path(self.db_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve()


# Global singleton
settings = Settings()
