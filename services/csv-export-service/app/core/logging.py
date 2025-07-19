#!/usr/bin/env python3
"""
Logging configuration for CSV Export Service.

This module provides structured logging configuration with correlation IDs,
JSON formatting, and performance monitoring for the CSV export service.
"""

import logging
import logging.config
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def configure_logging():
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s %(user_id)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "plain": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "json" if settings.LOG_FORMAT == "json" else "plain",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
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
            },
            "redis": {
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
            "level": settings.LOG_LEVEL,
            "formatter": "json" if settings.LOG_FORMAT == "json" else "plain",
            "filename": settings.LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
        
        # Add file handler to all loggers
        for logger_config in logging_config["loggers"].values():
            if "file" not in logger_config["handlers"]:
                logger_config["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)
    
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
            add_correlation_id,
            add_performance_metrics,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries."""
    # Try to get correlation ID from context
    correlation_id = getattr(logger, "_context", {}).get("correlation_id")
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_performance_metrics(logger, method_name, event_dict):
    """Add performance metrics to log entries."""
    # Add performance context if available
    performance_data = getattr(logger, "_context", {}).get("performance")
    if performance_data:
        event_dict.update(performance_data)
    return event_dict


class CorrelationLogger:
    """Logger with correlation ID support."""
    
    def __init__(self, logger_name: str):
        self.logger = structlog.get_logger(logger_name)
        self._context = {}
    
    def bind(self, **kwargs) -> 'CorrelationLogger':
        """Bind context data to logger."""
        new_logger = CorrelationLogger(self.logger.name)
        new_logger._context = {**self._context, **kwargs}
        new_logger.logger = self.logger.bind(**new_logger._context)
        return new_logger
    
    def with_correlation_id(self, correlation_id: str) -> 'CorrelationLogger':
        """Add correlation ID to logger context."""
        return self.bind(correlation_id=correlation_id)
    
    def with_user_id(self, user_id: int) -> 'CorrelationLogger':
        """Add user ID to logger context."""
        return self.bind(user_id=user_id)
    
    def with_job_id(self, job_id: int) -> 'CorrelationLogger':
        """Add job ID to logger context."""
        return self.bind(job_id=job_id)
    
    def with_performance(self, **metrics) -> 'CorrelationLogger':
        """Add performance metrics to logger context."""
        return self.bind(performance=metrics)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, **kwargs)


class PerformanceLogger:
    """Performance monitoring logger."""
    
    def __init__(self, logger: CorrelationLogger):
        self.logger = logger
        self.start_time = None
        self.metrics = {}
    
    def start_operation(self, operation_name: str, **context):
        """Start tracking an operation."""
        self.start_time = datetime.utcnow()
        self.metrics = {
            "operation": operation_name,
            "start_time": self.start_time.isoformat(),
            **context
        }
        
        self.logger.with_performance(**self.metrics).info(
            f"Starting {operation_name}",
            operation=operation_name
        )
    
    def end_operation(self, success: bool = True, **result_data):
        """End tracking an operation."""
        if self.start_time:
            end_time = datetime.utcnow()
            duration = (end_time - self.start_time).total_seconds()
            
            self.metrics.update({
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "success": success,
                **result_data
            })
            
            log_level = "info" if success else "error"
            getattr(self.logger.with_performance(**self.metrics), log_level)(
                f"Completed {self.metrics.get('operation', 'operation')} in {duration:.3f}s",
                duration=duration,
                success=success
            )
    
    def log_checkpoint(self, checkpoint_name: str, **data):
        """Log a checkpoint during operation."""
        if self.start_time:
            checkpoint_time = datetime.utcnow()
            elapsed = (checkpoint_time - self.start_time).total_seconds()
            
            checkpoint_data = {
                "checkpoint": checkpoint_name,
                "elapsed_seconds": elapsed,
                **data
            }
            
            self.logger.with_performance(**{**self.metrics, **checkpoint_data}).info(
                f"Checkpoint: {checkpoint_name}",
                checkpoint=checkpoint_name,
                elapsed=elapsed
            )


class CSVExportLogger:
    """Specialized logger for CSV export operations."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.base_logger = CorrelationLogger("csv_export")
        if correlation_id:
            self.base_logger = self.base_logger.with_correlation_id(correlation_id)
    
    def for_user(self, user_id: int) -> CorrelationLogger:
        """Get logger for specific user."""
        return self.base_logger.with_user_id(user_id)
    
    def for_job(self, job_id: int, user_id: Optional[int] = None) -> CorrelationLogger:
        """Get logger for specific job."""
        logger = self.base_logger.with_job_id(job_id)
        if user_id:
            logger = logger.with_user_id(user_id)
        return logger
    
    def performance_tracker(self, correlation_id: Optional[str] = None) -> PerformanceLogger:
        """Get performance tracker."""
        logger = self.base_logger
        if correlation_id:
            logger = logger.with_correlation_id(correlation_id)
        return PerformanceLogger(logger)
    
    def log_export_start(self, job_id: int, user_id: int, job_name: str, config: Dict[str, Any]):
        """Log export operation start."""
        self.for_job(job_id, user_id).info(
            "CSV export started",
            job_name=job_name,
            export_format=config.get("export_format"),
            compression=config.get("compression", {}).get("compression_type"),
            row_limit=config.get("data_processing", {}).get("max_rows")
        )
    
    def log_export_success(
        self, 
        job_id: int, 
        user_id: int, 
        file_path: str, 
        file_size: int, 
        row_count: int,
        generation_time_ms: int
    ):
        """Log successful export."""
        self.for_job(job_id, user_id).info(
            "CSV export completed successfully",
            file_path=file_path,
            file_size_bytes=file_size,
            file_size_mb=round(file_size / (1024 * 1024), 2),
            row_count=row_count,
            generation_time_ms=generation_time_ms,
            generation_time_seconds=round(generation_time_ms / 1000, 3)
        )
    
    def log_export_failure(self, job_id: int, user_id: int, error: str, generation_time_ms: int):
        """Log failed export."""
        self.for_job(job_id, user_id).error(
            "CSV export failed",
            error=error,
            generation_time_ms=generation_time_ms,
            generation_time_seconds=round(generation_time_ms / 1000, 3)
        )
    
    def log_validation_error(self, user_id: int, validation_issues: list):
        """Log validation errors."""
        self.for_user(user_id).warning(
            "Data validation failed",
            issues=validation_issues,
            issue_count=len(validation_issues)
        )
    
    def log_rate_limit(self, user_id: int, endpoint: str, limit: int):
        """Log rate limit exceeded."""
        self.for_user(user_id).warning(
            "Rate limit exceeded",
            endpoint=endpoint,
            limit=limit
        )


def get_logger(name: str = "csv_export") -> CorrelationLogger:
    """Get a correlation-aware logger."""
    return CorrelationLogger(name)


def get_csv_logger(correlation_id: Optional[str] = None) -> CSVExportLogger:
    """Get CSV export specialized logger."""
    return CSVExportLogger(correlation_id)


# Export commonly used functions and classes
__all__ = [
    "configure_logging",
    "get_logger",
    "get_csv_logger",
    "CorrelationLogger",
    "PerformanceLogger",
    "CSVExportLogger"
]