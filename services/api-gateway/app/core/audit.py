"""
Audit and security event utilities
"""

from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import ActivityLog, SecurityEvent
from ..core.logging import get_logger

logger = get_logger(__name__)


class AuditAction(str, Enum):
    """Standard audit actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    SEARCH = "search"
    EXECUTE = "execute"
    SHARE = "share"
    DOWNLOAD = "download"


class AuditResource(str, Enum):
    """Standard audit resource types"""
    USER = "user"
    USER_PROFILE = "user_profile"
    USER_PREFERENCES = "user_preferences"
    USER_SETTINGS = "user_settings"
    USER_DATA = "user_data"
    QUERY = "query"
    DASHBOARD = "dashboard"
    ALERT = "alert"
    CONVERSATION = "conversation"
    SESSION = "session"
    API_KEY = "api_key"
    SYSTEM = "system"


async def audit_action(
    db: AsyncSession,
    user_id: Optional[UUID],
    action: AuditAction,
    resource: AuditResource,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log an audit action"""
    
    try:
        activity_log = ActivityLog(
            user_id=user_id,
            action=action.value,
            resource_type=resource.value,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(activity_log)
        await db.commit()
        
        logger.info(
            "Audit action logged",
            user_id=str(user_id) if user_id else None,
            action=action.value,
            resource=resource.value,
            resource_id=resource_id
        )
        
    except Exception as e:
        logger.error(
            "Failed to log audit action",
            user_id=str(user_id) if user_id else None,
            action=action.value,
            resource=resource.value,
            error=str(e)
        )
        # Don't raise exception to avoid breaking the main operation
        pass


async def log_security_event(
    db: AsyncSession,
    user_id: Optional[UUID],
    event_type: str,
    severity: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log a security event"""
    
    try:
        security_event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(security_event)
        await db.commit()
        
        logger.warning(
            "Security event logged",
            user_id=str(user_id) if user_id else None,
            event_type=event_type,
            severity=severity,
            description=description
        )
        
    except Exception as e:
        logger.error(
            "Failed to log security event",
            user_id=str(user_id) if user_id else None,
            event_type=event_type,
            error=str(e)
        )
        # Don't raise exception to avoid breaking the main operation
        pass