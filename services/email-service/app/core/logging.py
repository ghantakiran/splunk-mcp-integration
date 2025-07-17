"""
Logging configuration for Email Service.
"""

import sys
import structlog
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from .config import settings


def configure_logging() -> None:
    """Configure structured logging for the email service."""
    
    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="ISO")
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def add_correlation_id(correlation_id: str) -> Dict[str, Any]:
    """Add correlation ID to log context."""
    return {"correlation_id": correlation_id}


def add_user_context(user_id: str, email: str) -> Dict[str, Any]:
    """Add user context to log context."""
    return {
        "user_id": user_id,
        "user_email": email,
    }


def add_request_context(
    method: str,
    path: str,
    user_agent: str = None,
    ip_address: str = None
) -> Dict[str, Any]:
    """Add request context to log context."""
    context = {
        "http_method": method,
        "http_path": path,
    }
    
    if user_agent:
        context["user_agent"] = user_agent
    
    if ip_address:
        context["ip_address"] = ip_address
    
    return context


def add_email_context(
    message_id: str,
    sender: str,
    recipient: str,
    subject: str
) -> Dict[str, Any]:
    """Add email context to log context."""
    return {
        "email_message_id": message_id,
        "email_sender": sender,
        "email_recipient": recipient,
        "email_subject": subject,
    }


def add_query_context(
    query_id: str,
    query_text: str,
    spl_query: str = None,
    execution_time: float = None
) -> Dict[str, Any]:
    """Add query context to log context."""
    context = {
        "query_id": query_id,
        "query_text": query_text[:500] + "..." if len(query_text) > 500 else query_text,
    }
    
    if spl_query:
        context["spl_query"] = spl_query[:500] + "..." if len(spl_query) > 500 else spl_query
    
    if execution_time is not None:
        context["execution_time"] = execution_time
    
    return context


def add_performance_context(
    operation: str,
    duration_ms: float,
    success: bool = True,
    error_type: str = None
) -> Dict[str, Any]:
    """Add performance context to log context."""
    context = {
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
    }
    
    if error_type:
        context["error_type"] = error_type
    
    return context


# Initialize logging configuration
configure_logging()