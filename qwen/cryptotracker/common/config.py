"""Global configuration for CryptoTracker."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    server_host: str = Field(default="localhost", alias="SERVER_HOST")
    server_port: int = Field(default=8000, alias="SERVER_PORT")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/cryptotracker.db",
        alias="DATABASE_URL"
    )
    
    # External APIs
    frankfurter_base_url: str = "https://api.frankfurter.dev/v1"
    frankfurter_timeout: int = Field(default=10, alias="FRANKFURTER_TIMEOUT")
    
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_timeout: int = Field(default=15, alias="COINGECKO_TIMEOUT")
    
    # Retry
    max_retry_attempts: int = Field(default=3, alias="MAX_RETRY_ATTEMPTS")
    retry_base_delay: float = Field(default=1.0, alias="RETRY_BASE_DELAY")
    
    # Cache
    cache_ttl_seconds: int = Field(default=60, alias="CACHE_TTL_SECONDS")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/server.log", alias="LOG_FILE")
    log_max_size_mb: int = Field(default=10, alias="LOG_MAX_SIZE_MB")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()
