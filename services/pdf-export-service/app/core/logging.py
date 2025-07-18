"""
Logging configuration for PDF Export Service.
"""

import sys
import logging
from typing import Dict, Any
import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    """Configure structured logging."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
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
            _add_correlation_id,
            structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up loggers for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)


def _add_correlation_id(logger, name, event_dict):
    """Add correlation ID to log entries."""
    # Try to get correlation ID from context
    correlation_id = getattr(logger, "_correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record):
        """Add correlation ID to log record."""
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = None
        return True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger."""
    return structlog.get_logger(name)


def with_correlation_id(logger: structlog.stdlib.BoundLogger, correlation_id: str) -> structlog.stdlib.BoundLogger:
    """Add correlation ID to logger."""
    return logger.bind(correlation_id=correlation_id)


def log_request(logger: structlog.stdlib.BoundLogger, method: str, path: str, **kwargs):
    """Log HTTP request."""
    logger.info(
        "HTTP request",
        method=method,
        path=path,
        **kwargs
    )


def log_response(logger: structlog.stdlib.BoundLogger, method: str, path: str, status_code: int, duration: float, **kwargs):
    """Log HTTP response."""
    logger.info(
        "HTTP response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )


def log_error(logger: structlog.stdlib.BoundLogger, error: Exception, context: Dict[str, Any] = None):
    """Log error with context."""
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        context=context or {},
        exc_info=True
    )


def log_pdf_generation(logger: structlog.stdlib.BoundLogger, job_id: str, status: str, **kwargs):
    """Log PDF generation events."""
    logger.info(
        "PDF generation",
        job_id=job_id,
        status=status,
        **kwargs
    )


def log_template_processing(logger: structlog.stdlib.BoundLogger, template_id: str, template_type: str, **kwargs):
    """Log template processing events."""
    logger.info(
        "Template processing",
        template_id=template_id,
        template_type=template_type,
        **kwargs
    )


def log_security_event(logger: structlog.stdlib.BoundLogger, event_type: str, user_id: str = None, **kwargs):
    """Log security-related events."""
    logger.warning(
        "Security event",
        event_type=event_type,
        user_id=user_id,
        **kwargs
    )


def log_performance_metric(logger: structlog.stdlib.BoundLogger, metric_name: str, value: float, unit: str = "ms", **kwargs):
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        metric_name=metric_name,
        value=value,
        unit=unit,
        **kwargs
    )


def log_database_operation(logger: structlog.stdlib.BoundLogger, operation: str, table: str, duration: float = None, **kwargs):
    """Log database operations."""
    log_data = {
        "operation": operation,
        "table": table,
        **kwargs
    }
    
    if duration is not None:
        log_data["duration_ms"] = round(duration * 1000, 2)
    
    logger.info("Database operation", **log_data)


def log_cache_operation(logger: structlog.stdlib.BoundLogger, operation: str, key: str, hit: bool = None, **kwargs):
    """Log cache operations."""
    log_data = {
        "operation": operation,
        "key": key,
        **kwargs
    }
    
    if hit is not None:
        log_data["cache_hit"] = hit
    
    logger.info("Cache operation", **log_data)


def log_external_service_call(logger: structlog.stdlib.BoundLogger, service: str, endpoint: str, 
                             duration: float = None, status_code: int = None, **kwargs):
    """Log external service calls."""
    log_data = {
        "service": service,
        "endpoint": endpoint,
        **kwargs
    }
    
    if duration is not None:
        log_data["duration_ms"] = round(duration * 1000, 2)
    
    if status_code is not None:
        log_data["status_code"] = status_code
    
    logger.info("External service call", **log_data)