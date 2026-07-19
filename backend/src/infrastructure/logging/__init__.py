"""Loguru-based logging setup.

Import the logger directly: `from loguru import logger`.
"""

from .loguru_setup import configure_logging, generate_correlation_id, get_correlation_id, set_correlation_id

__all__ = [
    "configure_logging",
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
]
