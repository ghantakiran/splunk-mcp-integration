#!/usr/bin/env python3
"""
Logging configuration for HTML Report Service.

This module configures structured logging using structlog
with proper formatting and context management.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def configure_logging():
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    )
    
    # Configure structlog
    processors = [
        # Add timestamp
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        
        # Add context processors
        add_correlation_id,
        add_service_context,
        
        # Stack info for errors
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    # Add appropriate formatter
    if settings.LOG_FORMAT.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set log level for specific modules
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # Configure file logging if specified
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        
        if settings.LOG_FORMAT.lower() == "json":
            file_formatter = structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
            )
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries."""
    # Try to get correlation ID from context
    import contextvars
    
    correlation_id = getattr(contextvars, 'correlation_id', None)
    if correlation_id and hasattr(correlation_id, 'get'):
        try:
            event_dict['correlation_id'] = correlation_id.get()
        except LookupError:
            pass
    
    return event_dict


def add_service_context(logger, method_name, event_dict):
    """Add service context to log entries."""
    event_dict['service'] = 'html-report-service'
    event_dict['version'] = '1.0.0'
    return event_dict


class StructuredLogger:
    """Structured logger wrapper with additional context methods."""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Bind additional context to logger."""
        new_logger = StructuredLogger("bound")
        new_logger.logger = self.logger.bind(**kwargs)
        return new_logger
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# Context manager for request logging
class RequestLoggingContext:
    """Context manager for request-scoped logging."""
    
    def __init__(self, correlation_id: str, user_id: int = None, **context):
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.context = context
        self.logger = get_logger("request")
    
    def __enter__(self):
        """Enter context and bind logging data."""
        bind_data = {
            "correlation_id": self.correlation_id,
            **self.context
        }
        
        if self.user_id:
            bind_data["user_id"] = self.user_id
        
        self.logger = self.logger.bind(**bind_data)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            self.logger.error(
                "Request completed with error",
                exception_type=exc_type.__name__,
                exception_message=str(exc_val)
            )
        else:
            self.logger.info("Request completed successfully")


# Performance logging utilities
class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_generation_time(
        self,
        job_id: int,
        generation_time_ms: int,
        chart_count: int,
        table_count: int,
        file_size: int
    ):
        """Log report generation performance."""
        self.logger.info(
            "Report generation completed",
            job_id=job_id,
            generation_time_ms=generation_time_ms,
            chart_count=chart_count,
            table_count=table_count,
            file_size_bytes=file_size,
            file_size_mb=round(file_size / 1024 / 1024, 2)
        )
    
    def log_database_query(
        self,
        query_type: str,
        duration_ms: int,
        affected_rows: int = None
    ):
        """Log database query performance."""
        log_data = {
            "query_type": query_type,
            "duration_ms": duration_ms
        }
        
        if affected_rows is not None:
            log_data["affected_rows"] = affected_rows
        
        self.logger.info("Database query executed", **log_data)
    
    def log_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool = None,
        duration_ms: int = None
    ):
        """Log cache operation performance."""
        log_data = {
            "operation": operation,
            "cache_key": key
        }
        
        if hit is not None:
            log_data["cache_hit"] = hit
        
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
        
        self.logger.info("Cache operation executed", **log_data)


# Security logging utilities
class SecurityLogger:
    """Logger for security events."""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_authentication_attempt(
        self,
        user_id: int,
        success: bool,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Log authentication attempt."""
        log_data = {
            "user_id": user_id,
            "success": success,
            "event_type": "authentication"
        }
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        if user_agent:
            log_data["user_agent"] = user_agent
        
        if success:
            self.logger.info("Authentication successful", **log_data)
        else:
            self.logger.warning("Authentication failed", **log_data)
    
    def log_authorization_failure(
        self,
        user_id: int,
        resource: str,
        action: str,
        ip_address: str = None
    ):
        """Log authorization failure."""
        log_data = {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "event_type": "authorization_failure"
        }
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        self.logger.warning("Authorization failed", **log_data)
    
    def log_rate_limit_exceeded(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        ip_address: str = None
    ):
        """Log rate limit exceeded event."""
        log_data = {
            "identifier": identifier,
            "limit": limit,
            "window_seconds": window_seconds,
            "event_type": "rate_limit_exceeded"
        }
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        self.logger.warning("Rate limit exceeded", **log_data)
    
    def log_suspicious_activity(
        self,
        activity_type: str,
        details: Dict[str, Any],
        user_id: int = None,
        ip_address: str = None
    ):
        """Log suspicious activity."""
        log_data = {
            "activity_type": activity_type,
            "details": details,
            "event_type": "suspicious_activity"
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        self.logger.warning("Suspicious activity detected", **log_data)


# Global logger instances
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()


# Export commonly used components
__all__ = [
    "configure_logging",
    "get_logger",
    "StructuredLogger",
    "RequestLoggingContext",
    "PerformanceLogger",
    "SecurityLogger",
    "performance_logger",
    "security_logger"
]
