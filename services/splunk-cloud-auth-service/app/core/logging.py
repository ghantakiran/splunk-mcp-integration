"""
Logging configuration for Splunk Cloud Authentication Service
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict
import json

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "splunk-cloud-auth-service",
            "version": settings.app_version,
            "environment": settings.environment
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id
        
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        
        # Add any additional context
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    """Set up structured logging configuration"""
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.environment == "production" else "console",
                "stream": sys.stdout
            }
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"]
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


class ContextLogger:
    """Logger wrapper that adds context to log messages"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set context fields for all subsequent log messages"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields"""
        self.context.clear()
    
    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log message with context"""
        extra = {**self.context, **kwargs}
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context("critical", message, **kwargs)