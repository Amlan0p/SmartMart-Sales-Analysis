"""
utils.py

Small, shared helper utilities used across the project:
- logging configuration
- directory creation helpers
- generic formatting helpers
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance for the given module name.

    The root logging configuration is only applied once, so repeated
    calls from different modules simply attach a logger with the same
    handlers/formatting instead of duplicating output. By default this
    configures console logging only; call ``configure_file_logging`` at
    application start-up (see ``main.py``) to also persist logs to
    ``outputs/logs/application.log``.
    """
    logger = logging.getLogger(name)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL, logging.INFO),
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
        )

    return logger


def configure_file_logging(log_path: Path) -> None:
    """Attach a file handler to the root logger so all subsequent log
    records are also written to ``log_path``, in addition to the
    console. Safe to call multiple times - it will not attach a
    duplicate handler for the same file.
    """
    ensure_directories(log_path.parent)
    root_logger = logging.getLogger()

    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path.resolve():
            return

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root_logger.addHandler(file_handler)


def ensure_directories(*directories: Path) -> None:
    """Create every directory in ``directories`` if it does not exist."""
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def format_currency(value: float) -> str:
    """Format a numeric value as an Indian-Rupee-style currency string."""
    return f"₹{value:,.2f}"


def format_percentage(value: float) -> str:
    """Format a fraction (0-100) as a percentage string with one decimal."""
    return f"{value:.1f}%"


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide two numbers, returning 0.0 instead of raising on a zero
    denominator. Used throughout the analysis module to avoid
    ``ZeroDivisionError`` on edge cases (e.g. an empty group)."""
    if denominator in (0, 0.0):
        return 0.0
    return numerator / denominator
