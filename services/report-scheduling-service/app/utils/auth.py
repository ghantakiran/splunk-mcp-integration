"""
Authentication utilities for the Report Scheduling Service.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Extract and validate user information from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user information
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract additional user info
        user_info = {
            "user_id": user_id,
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "token_type": payload.get("token_type", "access"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat")
        }
        
        return user_info
        
    except InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
    """
    Check if user has required permission.
    
    Args:
        user: User information dictionary
        required_permission: Required permission string
        
    Returns:
        True if user has permission
        
    Raises:
        HTTPException: If user lacks required permission
    """
    try:
        user_permissions = user.get("permissions", [])
        user_roles = user.get("roles", [])
        
        # Check direct permission
        if required_permission in user_permissions:
            return True
        
        # Check role-based permissions
        role_permissions = {
            "admin": [
                "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
                "subscription:create", "subscription:read", "subscription:update", "subscription:delete", "subscription:test",
                "execution:read", "execution:retry", "execution:cancel", "execution:download", "execution:delete", "execution:logs",
                "analytics:read", "analytics:report",
                "system:admin"
            ],
            "manager": [
                "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
                "subscription:create", "subscription:read", "subscription:update", "subscription:delete", "subscription:test",
                "execution:read", "execution:retry", "execution:cancel", "execution:download", "execution:delete", "execution:logs",
                "analytics:read", "analytics:report"
            ],
            "user": [
                "schedule:create", "schedule:read", "schedule:update", "schedule:execute",
                "subscription:create", "subscription:read", "subscription:update", "subscription:test",
                "execution:read", "execution:retry", "execution:download", "execution:logs",
                "analytics:read"
            ],
            "viewer": [
                "schedule:read",
                "subscription:read",
                "execution:read",
                "analytics:read"
            ]
        }
        
        # Check if any of the user's roles grant the required permission
        for role in user_roles:
            if role in role_permissions:
                if required_permission in role_permissions[role]:
                    return True
        
        # If no permission found, raise exception
        logger.warning(f"User {user.get('user_id')} lacks required permission: {required_permission}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: {required_permission} required"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission check failed"
        )


def get_user_context(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user context for service operations.
    
    Args:
        user: User information dictionary
        
    Returns:
        User context dictionary
    """
    return {
        "user_id": user.get("user_id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "roles": user.get("roles", []),
        "permissions": user.get("permissions", []),
        "is_admin": "admin" in user.get("roles", []),
        "is_manager": "manager" in user.get("roles", []) or "admin" in user.get("roles", [])
    }


def has_role(user: Dict[str, Any], role: str) -> bool:
    """
    Check if user has specific role.
    
    Args:
        user: User information dictionary
        role: Role to check
        
    Returns:
        True if user has role
    """
    return role in user.get("roles", [])


def has_permission(user: Dict[str, Any], permission: str) -> bool:
    """
    Check if user has specific permission (without raising exception).
    
    Args:
        user: User information dictionary
        permission: Permission to check
        
    Returns:
        True if user has permission
    """
    try:
        check_permission(user, permission)
        return True
    except HTTPException:
        return False


def get_service_token() -> str:
    """
    Generate service-to-service authentication token.
    
    Returns:
        JWT token for service authentication
    """
    try:
        payload = {
            "sub": "report-scheduling-service",
            "service": True,
            "permissions": ["service:all"],
            "iat": jwt.datetime.datetime.utcnow(),
            "exp": jwt.datetime.datetime.utcnow() + jwt.timedelta(hours=1)
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating service token: {e}")
        raise


def create_correlation_id() -> str:
    """
    Create correlation ID for request tracking.
    
    Returns:
        Unique correlation ID
    """
    import uuid
    return str(uuid.uuid4())


class AuthContext:
    """Context manager for authentication operations."""
    
    def __init__(self, user: Dict[str, Any]):
        self.user = user
        self.correlation_id = create_correlation_id()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def get_user_id(self) -> str:
        return self.user.get("user_id")
    
    def get_username(self) -> str:
        return self.user.get("username")
    
    def get_roles(self) -> list:
        return self.user.get("roles", [])
    
    def get_permissions(self) -> list:
        return self.user.get("permissions", [])
    
    def is_admin(self) -> bool:
        return has_role(self.user, "admin")
    
    def is_manager(self) -> bool:
        return has_role(self.user, "manager") or self.is_admin()
    
    def can(self, permission: str) -> bool:
        return has_permission(self.user, permission)