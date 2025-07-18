"""
Logging configuration for Webhook Service.
"""

import sys
import structlog
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from .config import settings


def configure_logging() -> None:
    """Configure structured logging for the webhook service."""
    
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


def add_webhook_context(
    webhook_id: str,
    endpoint_url: str,
    event_type: str,
    delivery_id: str = None
) -> Dict[str, Any]:
    """Add webhook context to log context."""
    context = {
        "webhook_id": webhook_id,
        "endpoint_url": endpoint_url,
        "event_type": event_type,
    }
    
    if delivery_id:
        context["delivery_id"] = delivery_id
    
    return context


def add_event_context(
    event_id: str,
    event_type: str,
    event_source: str,
    payload_size: int = None
) -> Dict[str, Any]:
    """Add event context to log context."""
    context = {
        "event_id": event_id,
        "event_type": event_type,
        "event_source": event_source,
    }
    
    if payload_size is not None:
        context["payload_size"] = payload_size
    
    return context


def add_delivery_context(
    delivery_id: str,
    webhook_id: str,
    attempt_number: int,
    status: str,
    response_time: float = None
) -> Dict[str, Any]:
    """Add delivery context to log context."""
    context = {
        "delivery_id": delivery_id,
        "webhook_id": webhook_id,
        "attempt_number": attempt_number,
        "delivery_status": status,
    }
    
    if response_time is not None:
        context["response_time"] = response_time
    
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


def add_security_context(
    action: str,
    resource: str,
    permission: str,
    allowed: bool
) -> Dict[str, Any]:
    """Add security context to log context."""
    return {
        "security_action": action,
        "security_resource": resource,
        "security_permission": permission,
        "security_allowed": allowed,
    }


def add_analytics_context(
    metric_name: str,
    metric_value: float,
    metric_type: str,
    tags: Dict[str, str] = None
) -> Dict[str, Any]:
    """Add analytics context to log context."""
    context = {
        "metric_name": metric_name,
        "metric_value": metric_value,
        "metric_type": metric_type,
    }
    
    if tags:
        context["metric_tags"] = tags
    
    return context


# Initialize logging configuration
configure_logging()