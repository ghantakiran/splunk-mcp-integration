#!/usr/bin/env python3
"""
Authentication utilities for CSV Export Service.

This module provides JWT token validation, user authentication,
and authorization utilities for the CSV export service.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_user_by_id
from app.core.redis_client import get_cache_manager

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security scheme
security = HTTPBearer()

# Cache manager for token blacklist
cache_manager = None


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_user_token(user_id: int, username: str, role: str = "user") -> str:
    """Create access token for user."""
    token_data = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "token_type": "access"
    }
    
    return create_access_token(token_data)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check token type
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
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
            detail="Could not validate credentials"
        )


async def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    try:
        global cache_manager
        if not cache_manager:
            from app.core.redis_client import get_cache_manager
            cache_manager = get_cache_manager()
        
        return await cache_manager.exists(f"blacklist:{token}")
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        return False


async def blacklist_token(token: str, expires_in: int = 3600):
    """Add token to blacklist."""
    try:
        global cache_manager
        if not cache_manager:
            from app.core.redis_client import get_cache_manager
            cache_manager = get_cache_manager()
        
        await cache_manager.set(f"blacklist:{token}", "1", ttl=expires_in)
        logger.info("Token blacklisted successfully")
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")


class CurrentUser:
    """Current user information."""
    
    def __init__(self, user_id: int, username: str, role: str, token: str):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.token = token
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        # Define role permissions
        role_permissions = {
            "admin": [
                "csv:read", "csv:create", "csv:update", "csv:delete",
                "template:read", "template:create", "template:update", "template:delete",
                "analytics:read", "user:manage", "system:admin"
            ],
            "manager": [
                "csv:read", "csv:create", "csv:update", "csv:delete",
                "template:read", "template:create", "template:update",
                "analytics:read"
            ],
            "user": [
                "csv:read", "csv:create", "csv:update",
                "template:read", "template:create"
            ],
            "viewer": [
                "csv:read", "template:read"
            ]
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return permission in user_permissions
    
    def can_access_job(self, job_user_id: int) -> bool:
        """Check if user can access specific job."""
        # Admin can access all jobs
        if self.role == "admin":
            return True
        
        # Users can only access their own jobs
        return self.user_id == job_user_id
    
    def can_manage_templates(self) -> bool:
        """Check if user can manage templates."""
        return self.has_permission("template:create")
    
    def can_view_analytics(self) -> bool:
        """Check if user can view analytics."""
        return self.has_permission("analytics:read")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Get current authenticated user."""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Decode token
    payload = decode_token(token)
    
    # Extract user information
    user_id = int(payload.get("sub"))
    username = payload.get("username")
    role = payload.get("role", "user")
    
    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify user exists in database
    user_data = await get_user_by_id(user_id)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return CurrentUser(user_id, username, role, token)


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_checker


def require_role(required_role: str):
    """Decorator to require specific role."""
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        role_hierarchy = {"viewer": 1, "user": 2, "manager": 3, "admin": 4}
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {required_role} or higher"
            )
        
        return current_user
    
    return role_checker


# Common permission dependencies
require_csv_read = require_permission("csv:read")
require_csv_create = require_permission("csv:create")
require_csv_update = require_permission("csv:update")
require_csv_delete = require_permission("csv:delete")

require_template_read = require_permission("template:read")
require_template_create = require_permission("template:create")
require_template_update = require_permission("template:update")
require_template_delete = require_permission("template:delete")

require_analytics_read = require_permission("analytics:read")
require_user_manage = require_permission("user:manage")
require_system_admin = require_permission("system:admin")

# Common role dependencies
require_user_role = require_role("user")
require_manager_role = require_role("manager")
require_admin_role = require_role("admin")


# Optional authentication (for public endpoints with optional user context)
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[CurrentUser]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Export commonly used functions and classes
__all__ = [
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_user_token",
    "decode_token",
    "blacklist_token",
    "CurrentUser",
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "require_role",
    "require_csv_read",
    "require_csv_create",
    "require_csv_update",
    "require_csv_delete",
    "require_template_read",
    "require_template_create",
    "require_template_update",
    "require_template_delete",
    "require_analytics_read",
    "require_user_manage",
    "require_system_admin",
    "require_user_role",
    "require_manager_role",
    "require_admin_role"
]