"""Logging configuration for operational monitoring.

This module sets up structured logging for the PhilFlood pipeline.
Logs are written to both console (for interactive use) and files (for
auditing and troubleshooting). In production, logs can be forwarded
to centralized logging systems.

Usage:
    from philflood.ops.logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing basin", extra={"basin_id": "agusan", "date": "2025-12-29"})
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = False,
) -> None:
    """Configure logging for the application.
    
    Parameters
    ----------
    log_level : str, optional
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        Defaults to INFO.
    log_file : Path, optional
        Path to log file. If None, only console logging is enabled.
    json_format : bool, optional
        If True, output structured JSON logs. Requires python-json-logger.
        Defaults to False.
    """
    root_logger = logging.getLogger("philflood")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with color-coded output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    if json_format and HAS_JSON_LOGGER:
        console_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            timestamp=True,
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logs
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Capture all details in file
        
        if json_format and HAS_JSON_LOGGER:
            file_formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
                timestamp=True,
            )
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("rasterio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Parameters
    ----------
    name : str
        Logger name, typically __name__ of the calling module.
    
    Returns
    -------
    logging.Logger
        Configured logger instance.
    
    Examples
    --------
    >>> logger = get_logger(__name__)
    >>> logger.info("Starting monitoring run")
    >>> logger.warning("Forecast data missing", extra={"basin": "agusan"})
    """
    # Ensure parent logger is configured
    if not logging.getLogger("philflood").handlers:
        setup_logging()
    
    return logging.getLogger(f"philflood.{name}" if not name.startswith("philflood") else name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages.
    
    This is useful for adding basin_id, run_date, or other contextual
    information to all logs from a particular run.
    
    Examples
    --------
    >>> base_logger = get_logger(__name__)
    >>> logger = LoggerAdapter(base_logger, {"basin_id": "agusan", "date": "2025-12-29"})
    >>> logger.info("Processing forecast")
    # Output includes basin_id and date in all messages
    """
    
    def process(self, msg, kwargs):
        """Add extra context to log messages."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


# Default setup on import (can be reconfigured later)
setup_logging()
