# Shared logging utilities
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
            
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logging(
    service_name: str,
    level: str = "INFO",
    correlation_id: Optional[str] = None
) -> logging.Logger:
    """Set up structured logging for a service."""
    
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Add correlation ID if provided
    if correlation_id:
        logger = logging.LoggerAdapter(logger, {"correlation_id": correlation_id})
    
    return logger


def add_correlation_id(logger: logging.Logger, correlation_id: str) -> logging.LoggerAdapter:
    """Add correlation ID to logger."""
    return logging.LoggerAdapter(logger, {"correlation_id": correlation_id})