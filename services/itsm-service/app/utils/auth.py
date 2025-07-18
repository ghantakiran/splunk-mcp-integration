"""
Authentication and authorization utilities for ITSM Service.
"""

import jwt
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..core.database import get_database
from ..models.user_models import ITSMUser
from ..core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


class User:
    """User class for dependency injection."""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get("id")
        self.email = user_data.get("email")
        self.full_name = user_data.get("full_name")
        self.roles = user_data.get("roles", [])
        self.permissions = user_data.get("permissions", [])
        self.active = user_data.get("active", True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database)
) -> User:
    """Get current authenticated user."""
    
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        stmt = select(ITSMUser).where(ITSMUser.email == user_email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        user.last_login_at = payload.get("iat")
        await db.commit()
        
        return User({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
            "permissions": user.permissions,
            "active": user.active
        })
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permissions(required_permissions: List[str]):
    """Dependency factory for permission checking."""
    
    def permission_checker(current_user: User = Depends(get_current_user)) -> None:
        """Check if user has required permissions."""
        
        if not current_user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Check if user has all required permissions
        user_permissions = set(current_user.permissions)
        required_permissions_set = set(required_permissions)
        
        if not required_permissions_set.issubset(user_permissions):
            missing_permissions = required_permissions_set - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        logger.info(
            "Permission check passed",
            user_id=current_user.id,
            required_permissions=required_permissions,
            user_permissions=current_user.permissions
        )
    
    return permission_checker


def require_roles(required_roles: List[str]):
    """Dependency factory for role checking."""
    
    def role_checker(current_user: User = Depends(get_current_user)) -> None:
        """Check if user has required roles."""
        
        if not current_user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Check if user has any of the required roles
        user_roles = set(current_user.roles)
        required_roles_set = set(required_roles)
        
        if not required_roles_set.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of the following roles: {', '.join(required_roles)}"
            )
        
        logger.info(
            "Role check passed",
            user_id=current_user.id,
            required_roles=required_roles,
            user_roles=current_user.roles
        )
    
    return role_checker


async def get_user_permissions(
    user: User = Depends(get_current_user)
) -> List[str]:
    """Get current user permissions."""
    return user.permissions


async def has_permission(
    user: User,
    permission: str
) -> bool:
    """Check if user has specific permission."""
    return permission in user.permissions


async def has_role(
    user: User,
    role: str
) -> bool:
    """Check if user has specific role."""
    return role in user.roles


def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    """Create JWT access token."""
    
    import datetime
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_delta)
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.jwt_expiration_seconds)
    
    to_encode.update({"exp": expire, "iat": datetime.datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ITSM-specific permissions
class ITSMPermissions:
    """ITSM service permissions."""
    
    # Integration permissions
    INTEGRATION_CREATE = "itsm:integration:create"
    INTEGRATION_READ = "itsm:integration:read"
    INTEGRATION_UPDATE = "itsm:integration:update"
    INTEGRATION_DELETE = "itsm:integration:delete"
    
    # Ticket permissions
    TICKET_CREATE = "itsm:ticket:create"
    TICKET_READ = "itsm:ticket:read"
    TICKET_UPDATE = "itsm:ticket:update"
    TICKET_DELETE = "itsm:ticket:delete"
    
    # Workflow permissions
    WORKFLOW_CREATE = "itsm:workflow:create"
    WORKFLOW_READ = "itsm:workflow:read"
    WORKFLOW_UPDATE = "itsm:workflow:update"
    WORKFLOW_DELETE = "itsm:workflow:delete"
    WORKFLOW_EXECUTE = "itsm:workflow:execute"
    
    # Synchronization permissions
    SYNC_MANAGE = "itsm:sync:manage"
    SYNC_VIEW = "itsm:sync:view"
    SYNC_RESOLVE_CONFLICTS = "itsm:sync:resolve_conflicts"
    
    # Analytics permissions
    ANALYTICS_VIEW = "itsm:analytics:view"
    ANALYTICS_EXPORT = "itsm:analytics:export"
    
    # Admin permissions
    ADMIN_MANAGE_USERS = "itsm:admin:manage_users"
    ADMIN_MANAGE_SETTINGS = "itsm:admin:manage_settings"
    ADMIN_VIEW_LOGS = "itsm:admin:view_logs"


# ITSM-specific roles
class ITSMRoles:
    """ITSM service roles."""
    
    ADMIN = "itsm_admin"
    MANAGER = "itsm_manager"
    ANALYST = "itsm_analyst"
    USER = "itsm_user"
    VIEWER = "itsm_viewer"


# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    ITSMRoles.ADMIN: [
        ITSMPermissions.INTEGRATION_CREATE,
        ITSMPermissions.INTEGRATION_READ,
        ITSMPermissions.INTEGRATION_UPDATE,
        ITSMPermissions.INTEGRATION_DELETE,
        ITSMPermissions.TICKET_CREATE,
        ITSMPermissions.TICKET_READ,
        ITSMPermissions.TICKET_UPDATE,
        ITSMPermissions.TICKET_DELETE,
        ITSMPermissions.WORKFLOW_CREATE,
        ITSMPermissions.WORKFLOW_READ,
        ITSMPermissions.WORKFLOW_UPDATE,
        ITSMPermissions.WORKFLOW_DELETE,
        ITSMPermissions.WORKFLOW_EXECUTE,
        ITSMPermissions.SYNC_MANAGE,
        ITSMPermissions.SYNC_VIEW,
        ITSMPermissions.SYNC_RESOLVE_CONFLICTS,
        ITSMPermissions.ANALYTICS_VIEW,
        ITSMPermissions.ANALYTICS_EXPORT,
        ITSMPermissions.ADMIN_MANAGE_USERS,
        ITSMPermissions.ADMIN_MANAGE_SETTINGS,
        ITSMPermissions.ADMIN_VIEW_LOGS,
    ],
    ITSMRoles.MANAGER: [
        ITSMPermissions.INTEGRATION_READ,
        ITSMPermissions.INTEGRATION_UPDATE,
        ITSMPermissions.TICKET_CREATE,
        ITSMPermissions.TICKET_READ,
        ITSMPermissions.TICKET_UPDATE,
        ITSMPermissions.WORKFLOW_CREATE,
        ITSMPermissions.WORKFLOW_READ,
        ITSMPermissions.WORKFLOW_UPDATE,
        ITSMPermissions.WORKFLOW_EXECUTE,
        ITSMPermissions.SYNC_MANAGE,
        ITSMPermissions.SYNC_VIEW,
        ITSMPermissions.SYNC_RESOLVE_CONFLICTS,
        ITSMPermissions.ANALYTICS_VIEW,
        ITSMPermissions.ANALYTICS_EXPORT,
    ],
    ITSMRoles.ANALYST: [
        ITSMPermissions.INTEGRATION_READ,
        ITSMPermissions.TICKET_CREATE,
        ITSMPermissions.TICKET_READ,
        ITSMPermissions.TICKET_UPDATE,
        ITSMPermissions.WORKFLOW_READ,
        ITSMPermissions.WORKFLOW_EXECUTE,
        ITSMPermissions.SYNC_VIEW,
        ITSMPermissions.ANALYTICS_VIEW,
    ],
    ITSMRoles.USER: [
        ITSMPermissions.INTEGRATION_READ,
        ITSMPermissions.TICKET_CREATE,
        ITSMPermissions.TICKET_READ,
        ITSMPermissions.TICKET_UPDATE,
        ITSMPermissions.WORKFLOW_READ,
        ITSMPermissions.SYNC_VIEW,
    ],
    ITSMRoles.VIEWER: [
        ITSMPermissions.INTEGRATION_READ,
        ITSMPermissions.TICKET_READ,
        ITSMPermissions.WORKFLOW_READ,
        ITSMPermissions.SYNC_VIEW,
        ITSMPermissions.ANALYTICS_VIEW,
    ],
}