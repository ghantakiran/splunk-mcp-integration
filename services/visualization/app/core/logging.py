"""
Structured logging configuration for Visualization Service
"""
import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.typing import EventDict

from .config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log events"""
    event_dict["service"] = "visualization"
    event_dict["version"] = settings.app_version
    return event_dict


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log events if available"""
    # This will be populated by middleware
    correlation_id = getattr(logger, "_correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging() -> None:
    """Configure structured logging"""
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_app_context,
        add_correlation_id,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.debug:
        # Human-readable format for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON format for production
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


# Chart-specific logging functions
def log_chart_generation(
    chart_type: str,
    data_points: int,
    generation_time: float,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Log chart generation events"""
    logger = get_logger("chart_generation")
    
    log_data = {
        "chart_type": chart_type,
        "data_points": data_points,
        "generation_time_seconds": generation_time,
        "success": success,
    }
    
    if error:
        log_data["error"] = error
        logger.error("Chart generation failed", **log_data)
    else:
        logger.info("Chart generated successfully", **log_data)


def log_chart_export(
    chart_id: str,
    export_format: str,
    file_size_bytes: int,
    export_time: float,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Log chart export events"""
    logger = get_logger("chart_export")
    
    log_data = {
        "chart_id": chart_id,
        "export_format": export_format,
        "file_size_bytes": file_size_bytes,
        "export_time_seconds": export_time,
        "success": success,
    }
    
    if error:
        log_data["error"] = error
        logger.error("Chart export failed", **log_data)
    else:
        logger.info("Chart exported successfully", **log_data)


def log_dashboard_operation(
    operation: str,
    dashboard_id: str,
    user_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log dashboard operations"""
    logger = get_logger("dashboard_operations")
    
    log_data = {
        "operation": operation,
        "dashboard_id": dashboard_id,
        "user_id": user_id,
    }
    
    if details:
        log_data.update(details)
    
    logger.info("Dashboard operation performed", **log_data)


def log_performance_metrics(
    operation: str,
    duration: float,
    memory_usage: Optional[int] = None,
    cpu_usage: Optional[float] = None,
) -> None:
    """Log performance metrics"""
    logger = get_logger("performance")
    
    log_data = {
        "operation": operation,
        "duration_seconds": duration,
    }
    
    if memory_usage is not None:
        log_data["memory_usage_bytes"] = memory_usage
    
    if cpu_usage is not None:
        log_data["cpu_usage_percent"] = cpu_usage
    
    logger.info("Performance metrics", **log_data)