"""
Logging configuration for Cloud Connection Manager Service.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.SERVICE_NAME,
            "version": settings.VERSION
        }
        
        # Add extra fields from record
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        if hasattr(record, 'endpoint_id'):
            log_entry["endpoint_id"] = record.endpoint_id
        
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields passed via extra parameter
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info', 'message']:
                if not key.startswith('_') and isinstance(value, (str, int, float, bool, list, dict)):
                    log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Text formatter for human-readable logs."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging():
    """Setup logging configuration."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Set formatter based on configuration
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter())
    
    root_logger.addHandler(console_handler)
    
    # Add file handler if path is specified
    if settings.LOG_FILE_PATH:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(settings.LOG_FILE_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=settings.LOG_FILE_PATH,
                maxBytes=_parse_size(settings.LOG_ROTATION_SIZE),
                backupCount=settings.LOG_RETENTION_COUNT
            )
            file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
            
            # Always use JSON format for file logs
            file_handler.setFormatter(JSONFormatter())
            
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Failed to setup file logging: {e}")
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    # Set our service logger to the configured level
    service_logger = logging.getLogger("app")
    service_logger.setLevel(getattr(logging, settings.LOG_LEVEL))


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """Log a message with additional context."""
    logger.log(level, message, extra=context)


def _parse_size(size_str: str) -> int:
    """Parse size string like '100MB' to bytes."""
    size_str = size_str.upper()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # Assume bytes
        return int(size_str)


class StructuredLogger:
    """Structured logger for consistent logging across the application."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def debug(self, message: str, **context):
        """Log debug message with context."""
        self.logger.debug(message, extra=context)
    
    def info(self, message: str, **context):
        """Log info message with context."""
        self.logger.info(message, extra=context)
    
    def warning(self, message: str, **context):
        """Log warning message with context."""
        self.logger.warning(message, extra=context)
    
    def error(self, message: str, **context):
        """Log error message with context."""
        self.logger.error(message, extra=context)
    
    def critical(self, message: str, **context):
        """Log critical message with context."""
        self.logger.critical(message, extra=context)
    
    def log_request(self, method: str, url: str, status_code: int, 
                   response_time: float, **context):
        """Log HTTP request with standard fields."""
        self.info(
            f"{method} {url} {status_code}",
            method=method,
            url=url,
            status_code=status_code,
            response_time_ms=round(response_time * 1000, 2),
            **context
        )
    
    def log_endpoint_health(self, endpoint_id: int, health_status: str,
                           response_time_ms: float, **context):
        """Log endpoint health check."""
        self.info(
            f"Health check for endpoint {endpoint_id}: {health_status}",
            endpoint_id=endpoint_id,
            health_status=health_status,
            response_time_ms=response_time_ms,
            event_type="health_check",
            **context
        )
    
    def log_connection_event(self, endpoint_id: int, event_type: str,
                           connection_count: int, **context):
        """Log connection pool events."""
        self.info(
            f"Connection event for endpoint {endpoint_id}: {event_type}",
            endpoint_id=endpoint_id,
            event_type=event_type,
            connection_count=connection_count,
            **context
        )
    
    def log_failover_event(self, source_endpoint_id: int, target_endpoint_id: int,
                          reason: str, **context):
        """Log failover events."""
        self.warning(
            f"Failover from endpoint {source_endpoint_id} to {target_endpoint_id}: {reason}",
            source_endpoint_id=source_endpoint_id,
            target_endpoint_id=target_endpoint_id,
            reason=reason,
            event_type="failover",
            **context
        )
    
    def log_security_event(self, event_type: str, user_id: str = None, 
                          ip_address: str = None, **context):
        """Log security-related events."""
        self.warning(
            f"Security event: {event_type}",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            security_event=True,
            **context
        )
    
    def log_performance_issue(self, endpoint_id: int, metric_type: str,
                            value: float, threshold: float, **context):
        """Log performance issues."""
        self.warning(
            f"Performance issue on endpoint {endpoint_id}: {metric_type} = {value} (threshold: {threshold})",
            endpoint_id=endpoint_id,
            metric_type=metric_type,
            value=value,
            threshold=threshold,
            event_type="performance_issue",
            **context
        )