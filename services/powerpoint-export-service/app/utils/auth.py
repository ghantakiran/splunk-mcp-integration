#!/usr/bin/env python3
"""
Authentication utilities for PowerPoint Export Service.

This module provides JWT token validation and user authentication functions.
"""

import jwt
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from structlog import get_logger

from app.core.config import settings


logger = get_logger(__name__)
security = HTTPBearer()


class AuthenticationError(Exception):
    """Authentication error exception."""
    pass


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
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


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    try:
        payload = verify_token(credentials.credentials)
        
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        return {
            "id": int(user_id),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "exp": payload.get("exp")
        }
    
    except AuthenticationError as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_full(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current user with full details."""
    # This is a simplified implementation
    # In a real application, you might fetch additional user details from the database
    return current_user


async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user."""
    # In a real application, you might check if the user is active/enabled
    return current_user


def require_roles(required_roles: list):
    """Dependency to require specific roles."""
    async def check_roles(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("roles", [])
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return check_roles


def require_permissions(required_permissions: list):
    """Dependency to require specific permissions."""
    async def check_permissions(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        
        if not all(permission in user_permissions for permission in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return check_permissions


# Admin role requirement
require_admin = require_roles(["admin"])

# Common permission requirements
require_powerpoint_create = require_permissions(["powerpoint:create"])
require_powerpoint_read = require_permissions(["powerpoint:read"])
require_powerpoint_update = require_permissions(["powerpoint:update"])
require_powerpoint_delete = require_permissions(["powerpoint:delete"])
require_template_create = require_permissions(["template:create"])
require_template_manage = require_permissions(["template:manage"])


# Export commonly used functions
__all__ = [
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_user_full",
    "get_current_active_user",
    "require_roles",
    "require_permissions",
    "require_admin",
    "require_powerpoint_create",
    "require_powerpoint_read",
    "require_powerpoint_update",
    "require_powerpoint_delete",
    "require_template_create",
    "require_template_manage",
    "AuthenticationError"
]
