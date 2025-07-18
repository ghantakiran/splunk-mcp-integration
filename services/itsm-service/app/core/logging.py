"""
Logging configuration for ITSM Service.
"""

import sys
import structlog
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from .config import settings


def configure_logging() -> None:
    """Configure structured logging for the ITSM service."""
    
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


def add_itsm_context(
    provider: str,
    ticket_id: str,
    operation: str,
    table: str = None
) -> Dict[str, Any]:
    """Add ITSM context to log context."""
    context = {
        "itsm_provider": provider,
        "ticket_id": ticket_id,
        "operation": operation,
    }
    
    if table:
        context["itsm_table"] = table
    
    return context


def add_sync_context(
    sync_id: str,
    direction: str,
    provider: str,
    status: str,
    record_count: int = None
) -> Dict[str, Any]:
    """Add synchronization context to log context."""
    context = {
        "sync_id": sync_id,
        "sync_direction": direction,
        "sync_provider": provider,
        "sync_status": status,
    }
    
    if record_count is not None:
        context["record_count"] = record_count
    
    return context


def add_workflow_context(
    workflow_id: str,
    step_id: str,
    step_type: str,
    execution_id: str = None
) -> Dict[str, Any]:
    """Add workflow context to log context."""
    context = {
        "workflow_id": workflow_id,
        "workflow_step_id": step_id,
        "workflow_step_type": step_type,
    }
    
    if execution_id:
        context["workflow_execution_id"] = execution_id
    
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


def add_integration_context(
    integration_id: str,
    provider: str,
    connection_status: str,
    last_sync: str = None
) -> Dict[str, Any]:
    """Add integration context to log context."""
    context = {
        "integration_id": integration_id,
        "integration_provider": provider,
        "connection_status": connection_status,
    }
    
    if last_sync:
        context["last_sync"] = last_sync
    
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


# Initialize logging configuration
configure_logging()