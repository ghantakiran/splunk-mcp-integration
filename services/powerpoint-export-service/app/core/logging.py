#!/usr/bin/env python3
"""
Logging configuration for PowerPoint Export Service.

This module sets up structured logging with JSON format and proper
configuration for production and development environments.
"""

import logging
import sys
from typing import Any, Dict
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
    """Set up structured logging with JSON format."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Configure file logging if specified
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # Disable debug logging for third-party libraries in production
    if not settings.DEBUG:
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("aioredis").setLevel(logging.WARNING)
        logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> Dict[str, Any]:
    """Create a logging context dictionary."""
    return kwargs


# Common logging contexts
def request_context(request_id: str, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a request logging context."""
    return log_context(
        request_id=request_id,
        method=method,
        path=path,
        **kwargs
    )


def job_context(job_id: int, user_id: int, **kwargs: Any) -> Dict[str, Any]:
    """Create a job logging context."""
    return log_context(
        job_id=job_id,
        user_id=user_id,
        **kwargs
    )


def error_context(error: Exception, **kwargs: Any) -> Dict[str, Any]:
    """Create an error logging context."""
    return log_context(
        error_type=type(error).__name__,
        error_message=str(error),
        **kwargs
    )


# Export commonly used functions
__all__ = [
    "setup_logging",
    "get_logger",
    "log_context",
    "request_context",
    "job_context",
    "error_context"
]
