"""
Logging configuration for BI Integration Service.
"""

import sys
import structlog
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logging() -> None:
    """Setup and configure logging for the BI service."""
    configure_logging()


def configure_logging() -> None:
    """Configure structured logging for the BI service."""
    
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


def add_bi_context(
    provider: str,
    resource_type: str,
    resource_id: str,
    operation: str,
    integration_id: str = None
) -> Dict[str, Any]:
    """Add BI context to log context."""
    context = {
        "bi_provider": provider,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "operation": operation,
    }
    
    if integration_id:
        context["integration_id"] = integration_id
    
    return context


def add_publish_context(
    workbook_id: str,
    project_name: str,
    publish_type: str,
    status: str
) -> Dict[str, Any]:
    """Add publish context to log context."""
    return {
        "workbook_id": workbook_id,
        "project_name": project_name,
        "publish_type": publish_type,
        "publish_status": status,
    }


def add_refresh_context(
    extract_id: str,
    refresh_type: str,
    status: str,
    duration_seconds: float = None
) -> Dict[str, Any]:
    """Add refresh context to log context."""
    context = {
        "extract_id": extract_id,
        "refresh_type": refresh_type,
        "refresh_status": status,
    }
    
    if duration_seconds is not None:
        context["duration_seconds"] = duration_seconds
    
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
        "bi_provider": provider,
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


def add_tableau_context(
    site_id: str,
    workbook_id: str = None,
    project_id: str = None,
    datasource_id: str = None
) -> Dict[str, Any]:
    """Add Tableau-specific context to log context."""
    context = {
        "tableau_site_id": site_id,
    }
    
    if workbook_id:
        context["tableau_workbook_id"] = workbook_id
    
    if project_id:
        context["tableau_project_id"] = project_id
    
    if datasource_id:
        context["tableau_datasource_id"] = datasource_id
    
    return context


def add_powerbi_context(
    workspace_id: str,
    report_id: str = None,
    dataset_id: str = None,
    dashboard_id: str = None
) -> Dict[str, Any]:
    """Add Power BI-specific context to log context."""
    context = {
        "powerbi_workspace_id": workspace_id,
    }
    
    if report_id:
        context["powerbi_report_id"] = report_id
    
    if dataset_id:
        context["powerbi_dataset_id"] = dataset_id
    
    if dashboard_id:
        context["powerbi_dashboard_id"] = dashboard_id
    
    return context


def add_data_context(
    rows_processed: int,
    columns_count: int,
    data_size_bytes: int = None,
    processing_time_ms: float = None
) -> Dict[str, Any]:
    """Add data processing context to log context."""
    context = {
        "rows_processed": rows_processed,
        "columns_count": columns_count,
    }
    
    if data_size_bytes is not None:
        context["data_size_bytes"] = data_size_bytes
    
    if processing_time_ms is not None:
        context["processing_time_ms"] = processing_time_ms
    
    return context


# Initialize logging configuration
configure_logging()