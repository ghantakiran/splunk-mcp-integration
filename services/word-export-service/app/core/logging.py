#!/usr/bin/env python3
"""
Logging configuration for Word Export Service.

This module configures structured logging with correlation IDs
and appropriate log levels for different environments.
"""

import logging
import logging.config
import sys
from typing import Dict, Any

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL.upper(),
                "formatter": "json" if settings.LOG_FORMAT == "json" else "standard",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": settings.LOG_LEVEL.upper(),
                "propagate": False
            },
            "app": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL.upper(),
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False
            }
        }
    }
    
    # Add file handler if specified
    if settings.LOG_FILE:
        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL.upper(),
            "formatter": "json" if settings.LOG_FORMAT == "json" else "standard",
            "filename": settings.LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
        
        # Add file handler to all loggers
        for logger_config in logging_config["loggers"].values():
            if "file" not in logger_config["handlers"]:
                logger_config["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)
    
    # Set levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger instance."""
    return structlog.get_logger(name)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record."""
        # Try to get correlation ID from context
        correlation_id = getattr(record, 'correlation_id', None)
        if not correlation_id:
            # Generate a correlation ID if not present
            import uuid
            correlation_id = str(uuid.uuid4())[:8]
        
        record.correlation_id = correlation_id
        return True


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger(__name__)
    
    async def __call__(self, scope, receive, send):
        """Log request and response details."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        import uuid
        
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        
        # Extract request details
        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()
        
        # Start timer
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "HTTP request started",
            correlation_id=correlation_id,
            method=method,
            path=path,
            query_string=query_string
        )
        
        # Capture response
        response_status = None
        
        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # ms
            
            # Log response
            self.logger.info(
                "HTTP request completed",
                correlation_id=correlation_id,
                method=method,
                path=path,
                status_code=response_status,
                duration_ms=round(duration, 2)
            )
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # ms
            
            # Log error
            self.logger.error(
                "HTTP request failed",
                correlation_id=correlation_id,
                method=method,
                path=path,
                duration_ms=round(duration, 2),
                error=str(e),
                exc_info=True
            )
            raise


def log_function_call(func_name: str, args: Dict[str, Any] = None, correlation_id: str = None):
    """Decorator for logging function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            
            start_time = time.time()
            
            logger.info(
                f"Function {func_name} started",
                correlation_id=correlation_id,
                args=args if args else {},
                kwargs=kwargs
            )
            
            try:
                result = func(*args, **kwargs)
                
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Function {func_name} completed",
                    correlation_id=correlation_id,
                    duration_ms=round(duration, 2)
                )
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Function {func_name} failed",
                    correlation_id=correlation_id,
                    duration_ms=round(duration, 2),
                    error=str(e),
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_async_function_call(func_name: str, args: Dict[str, Any] = None, correlation_id: str = None):
    """Decorator for logging async function calls."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            
            logger = get_logger(func.__module__)
            
            start_time = time.time()
            
            logger.info(
                f"Async function {func_name} started",
                correlation_id=correlation_id,
                args=args if args else {},
                kwargs=kwargs
            )
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Async function {func_name} completed",
                    correlation_id=correlation_id,
                    duration_ms=round(duration, 2)
                )
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Async function {func_name} failed",
                    correlation_id=correlation_id,
                    duration_ms=round(duration, 2),
                    error=str(e),
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# Export commonly used functions
__all__ = [
    "configure_logging",
    "get_logger",
    "CorrelationIdFilter",
    "RequestLoggingMiddleware",
    "log_function_call",
    "log_async_function_call"
]