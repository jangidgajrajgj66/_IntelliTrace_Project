"""
Structured Logger for IntelliTrace.
Author: Gajraj Jangid
Provides unified console and file logging with severity formatting,
traceability, and rotation.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from config import APP_LOG_PATH, LOGGING_CONFIG

_is_configured = False

def setup_logging(level: int = logging.INFO):
    """Initializes root logger with console and rotating file handlers."""
    global _is_configured
    if _is_configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console Handler with human-friendly format
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=LOGGING_CONFIG["format"],
        datefmt=LOGGING_CONFIG["datefmt"]
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # Rotating File Handler
    try:
        APP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            APP_LOG_PATH,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(console_formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging at {APP_LOG_PATH}: {e}")

    _is_configured = True

def get_logger(name: str) -> logging.Logger:
    """Returns a named logger configured with application formatting."""
    if not _is_configured:
        setup_logging()
    return logging.getLogger(name)
