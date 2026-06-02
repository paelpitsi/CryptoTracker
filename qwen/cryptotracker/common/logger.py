"""Logging configuration for CryptoTracker."""

import logging
import os
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from cryptotracker.common.config import settings


def setup_logger(name: str = "cryptotracker") -> logging.Logger:
    """Set up and configure logger with console and file handlers."""
    
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Console handler with Rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
        markup=True
    )
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=settings.log_max_size_mb * 1024 * 1024,
        backupCount=settings.log_backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# Create default logger
logger = setup_logger()
