"""
Core functionality for NLP Engine service
"""

from .config import settings, get_settings
from .logging import configure_logging, get_logger, LogContext, NLPMetrics

__all__ = [
    "settings",
    "get_settings", 
    "configure_logging",
    "get_logger",
    "LogContext",
    "NLPMetrics"
]