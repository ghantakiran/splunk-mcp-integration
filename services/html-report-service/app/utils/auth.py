#!/usr/bin/env python3
"""
Authentication utilities for HTML Report Service.

This module provides JWT token validation, user authentication,
and authorization utilities for the HTML report service.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from structlog import get_logger

from app.core.config import settings
from app.core.redis_client import get_session_manager

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class TokenData:
    """Token data model."""
    
    def __init__(self, user_id: int, email: str, roles: list, permissions: list):
        self.user_id = user_id
        self.email = email
        self.roles = roles
        self.permissions = permissions


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Token validation error: {e}")
        return None


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract and validate bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_current_user_token)
) -> TokenData:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = verify_token(token)
        if payload is None:
            raise credentials_exception
        
        user_id: int = payload.get("sub")
        email: str = payload.get("email")
        roles: list = payload.get("roles", [])
        permissions: list = payload.get("permissions", [])
        
        if user_id is None or email is None:
            raise credentials_exception
        
        token_data = TokenData(
            user_id=user_id,
            email=email,
            roles=roles,
            permissions=permissions
        )
        
        logger.info("User authenticated", user_id=user_id, email=email)
        return token_data
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


async def get_current_user_full(
    current_user: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user with full profile information."""
    # In a real implementation, this would fetch from database
    # For now, return token data as dict
    return {
        "id": current_user.user_id,
        "email": current_user.email,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "is_active": True,
        "is_superuser": "admin" in current_user.roles
    }


def require_permission(permission: str):
    """Dependency factory for permission-based authorization."""
    
    async def permission_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if permission not in current_user.permissions and "admin" not in current_user.roles:
            logger.warning(
                "Permission denied",
                user_id=current_user.user_id,
                required_permission=permission,
                user_permissions=current_user.permissions
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


def require_role(role: str):
    """Dependency factory for role-based authorization."""
    
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if role not in current_user.roles and "admin" not in current_user.roles:
            logger.warning(
                "Role access denied",
                user_id=current_user.user_id,
                required_role=role,
                user_roles=current_user.roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return current_user
    
    return role_checker


async def validate_user_access(
    user_id: int,
    resource_owner_id: int,
    current_user: TokenData
) -> bool:
    """Validate if user has access to a resource."""
    # Admin can access everything
    if "admin" in current_user.roles:
        return True
    
    # User can access their own resources
    if current_user.user_id == resource_owner_id:
        return True
    
    # Manager can access resources from their team
    if "manager" in current_user.roles:
        # In a real implementation, check team membership
        return True
    
    return False


async def get_user_context(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive user context for logging and audit."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_path": str(request.url.path),
        "request_method": request.method
    }


class SessionManager:
    """Session management for user sessions."""
    
    def __init__(self):
        self.redis_session_manager = get_session_manager()
    
    async def create_session(
        self,
        user_id: int,
        session_data: Dict[str, Any],
        ttl: int = 3600
    ) -> str:
        """Create a new user session."""
        import uuid
        
        session_id = str(uuid.uuid4())
        session_data.update({
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        })
        
        success = await self.redis_session_manager.create_session(
            session_id,
            session_data,
            ttl
        )
        
        if success:
            logger.info("Session created", user_id=user_id, session_id=session_id)
            return session_id
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return await self.redis_session_manager.get_session(session_id)
    
    async def update_session(
        self,
        session_id: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """Update session data."""
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        return await self.redis_session_manager.update_session(
            session_id,
            session_data
        )
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        success = await self.redis_session_manager.delete_session(session_id)
        
        if success:
            logger.info("Session invalidated", session_id=session_id)
        
        return success
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (would be called by background task)."""
        # Implementation would depend on Redis key pattern scanning
        # For now, return 0 as placeholder
        return 0


# Global session manager instance
session_manager = SessionManager()


# Permission constants
class Permissions:
    """Permission constants for the HTML report service."""
    
    # Report permissions
    CREATE_REPORT = "html_report:create"
    READ_REPORT = "html_report:read"
    UPDATE_REPORT = "html_report:update"
    DELETE_REPORT = "html_report:delete"
    
    # Template permissions
    CREATE_TEMPLATE = "html_template:create"
    READ_TEMPLATE = "html_template:read"
    UPDATE_TEMPLATE = "html_template:update"
    DELETE_TEMPLATE = "html_template:delete"
    
    # Analytics permissions
    VIEW_ANALYTICS = "html_analytics:view"
    EXPORT_ANALYTICS = "html_analytics:export"
    
    # Admin permissions
    ADMIN_ALL = "html_admin:all"
    MANAGE_USERS = "html_admin:users"
    MANAGE_SYSTEM = "html_admin:system"


# Role constants
class Roles:
    """Role constants for the HTML report service."""
    
    USER = "user"
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPERUSER = "superuser"


# Export commonly used components
__all__ = [
    "TokenData",
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_user_full",
    "require_permission",
    "require_role",
    "validate_user_access",
    "get_user_context",
    "SessionManager",
    "session_manager",
    "Permissions",
    "Roles"
]
