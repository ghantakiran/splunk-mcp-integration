"""
Structured logging configuration for Alert Management service.
"""
import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.types import Processor

from .config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Define log processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.debug:
        # Development formatting
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    else:
        # Production formatting
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


class AlertLogger:
    """Enhanced logger for alert-specific operations."""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def log_alert_created(
        self,
        alert_id: str,
        rule_name: str,
        user_id: str,
        conditions: Dict[str, Any],
        **kwargs
    ) -> None:
        """Log alert rule creation."""
        self.logger.info(
            "Alert rule created",
            alert_id=alert_id,
            rule_name=rule_name,
            user_id=user_id,
            conditions=conditions,
            **kwargs
        )
    
    def log_alert_triggered(
        self,
        alert_id: str,
        incident_id: str,
        rule_name: str,
        trigger_value: Any,
        threshold: Any,
        **kwargs
    ) -> None:
        """Log alert trigger event."""
        self.logger.warning(
            "Alert triggered",
            alert_id=alert_id,
            incident_id=incident_id,
            rule_name=rule_name,
            trigger_value=trigger_value,
            threshold=threshold,
            **kwargs
        )
    
    def log_notification_sent(
        self,
        notification_id: str,
        incident_id: str,
        channel: str,
        recipient: str,
        status: str,
        **kwargs
    ) -> None:
        """Log notification delivery."""
        self.logger.info(
            "Notification sent",
            notification_id=notification_id,
            incident_id=incident_id,
            channel=channel,
            recipient=recipient,
            status=status,
            **kwargs
        )
    
    def log_alert_acknowledged(
        self,
        incident_id: str,
        acknowledged_by: str,
        **kwargs
    ) -> None:
        """Log alert acknowledgment."""
        self.logger.info(
            "Alert acknowledged",
            incident_id=incident_id,
            acknowledged_by=acknowledged_by,
            **kwargs
        )
    
    def log_alert_resolved(
        self,
        incident_id: str,
        resolved_by: str,
        resolution_time: float,
        **kwargs
    ) -> None:
        """Log alert resolution."""
        self.logger.info(
            "Alert resolved",
            incident_id=incident_id,
            resolved_by=resolved_by,
            resolution_time_minutes=resolution_time,
            **kwargs
        )
    
    def log_escalation(
        self,
        incident_id: str,
        escalation_level: int,
        escalated_to: str,
        reason: str,
        **kwargs
    ) -> None:
        """Log alert escalation."""
        self.logger.warning(
            "Alert escalated",
            incident_id=incident_id,
            escalation_level=escalation_level,
            escalated_to=escalated_to,
            reason=reason,
            **kwargs
        )
    
    def log_error(
        self,
        operation: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log error events."""
        self.logger.error(
            f"Alert operation failed: {operation}",
            error=error,
            context=context or {},
            **kwargs
        )


# Initialize logging on module import
configure_logging()