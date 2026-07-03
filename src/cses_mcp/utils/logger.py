"""
Logging utilities for the CSES MCP server.
"""

import logging
import sys
from pathlib import Path

from ..config.settings import settings


def setup_logger(
    name: str = "cses_mcp", level: str | None = None, log_file: str | None = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting and configuration.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper()))

    formatter = logging.Formatter(settings.log_format)

    # Console handler (stderr, since stdout is used for MCP stdio transport)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    file_path = log_file or settings.log_file
    if file_path:
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
