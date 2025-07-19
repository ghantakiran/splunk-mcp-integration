#!/usr/bin/env python3
"""
Authentication utilities for Word Export Service.

This module provides JWT token validation, user authentication,
and authorization utilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


class TokenManager:
    """JWT token management utilities."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created access token for user {data.get('user_id')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def refresh_token(self, token: str) -> str:
        """Refresh access token if valid."""
        payload = self.verify_token(token)
        
        # Create new token with same payload (excluding exp and iat)
        new_payload = {k: v for k, v in payload.items() if k not in ["exp", "iat"]}
        return self.create_access_token(new_payload)


class UserContext:
    """User context for authorization."""
    
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        roles: list[str] = None,
        permissions: list[str] = None,
        is_active: bool = True,
        is_admin: bool = False
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.is_active = is_active
        self.is_admin = is_admin
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return self.is_admin or permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return self.is_admin or role in self.roles
    
    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return self.is_admin or any(perm in self.permissions for perm in permissions)
    
    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return self.is_admin or any(role in self.roles for role in roles)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user context to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "is_admin": self.is_admin
        }


# Global token manager instance
token_manager = TokenManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserContext:
    """Get current user from JWT token."""
    try:
        # Extract token
        token = credentials.credentials
        
        # Verify token
        payload = token_manager.verify_token(token)
        
        # Extract user information
        user_id = payload.get("user_id")
        username = payload.get("username")
        email = payload.get("email")
        roles = payload.get("roles", [])
        permissions = payload.get("permissions", [])
        is_active = payload.get("is_active", True)
        is_admin = payload.get("is_admin", False)
        
        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if user is active
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        user_context = UserContext(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles,
            permissions=permissions,
            is_active=is_active,
            is_admin=is_admin
        )
        
        logger.info(f"Authenticated user {username} (ID: {user_id})")
        return user_context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_admin_user(current_user: UserContext = Security(get_current_user)) -> UserContext:
    """Get current user and verify admin privileges."""
    if not current_user.is_admin:
        logger.warning(f"User {current_user.username} attempted admin operation")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


def require_permissions(required_permissions: list[str]):
    """Decorator to require specific permissions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserContext):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User context not found"
                )
            
            if not current_user.has_any_permission(required_permissions):
                logger.warning(
                    f"User {current_user.username} lacks required permissions: {required_permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required permissions: {', '.join(required_permissions)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_roles(required_roles: list[str]):
    """Decorator to require specific roles."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserContext):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User context not found"
                )
            
            if not current_user.has_any_role(required_roles):
                logger.warning(
                    f"User {current_user.username} lacks required roles: {required_roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {', '.join(required_roles)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_user_token(
    user_id: int,
    username: str,
    email: str,
    roles: list[str] = None,
    permissions: list[str] = None,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create user access token."""
    token_data = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": roles or [],
        "permissions": permissions or [],
        "is_active": True,
        "is_admin": is_admin
    }
    
    return token_manager.create_access_token(token_data, expires_delta)


async def authenticate_service_request(service_name: str, api_key: str) -> bool:
    """Authenticate service-to-service requests."""
    # In a real implementation, you would validate the service credentials
    # For now, this is a placeholder
    valid_services = {
        "nlp-engine": "nlp-engine-api-key",
        "visualization": "visualization-api-key",
        "api-gateway": "api-gateway-api-key"
    }
    
    return valid_services.get(service_name) == api_key


# Export commonly used functions and classes
__all__ = [
    "TokenManager",
    "UserContext",
    "token_manager",
    "get_current_user",
    "get_admin_user",
    "require_permissions",
    "require_roles",
    "hash_password",
    "verify_password",
    "create_user_token",
    "authenticate_service_request"
]