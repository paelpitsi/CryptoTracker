"""Server configuration."""

from cryptotracker.common.config import settings


class ServerConfig:
    """Server configuration class."""
    
    HOST: str = settings.server_host
    PORT: int = settings.server_port
    DATABASE_URL: str = settings.database_url
    LOG_LEVEL: str = settings.log_level
