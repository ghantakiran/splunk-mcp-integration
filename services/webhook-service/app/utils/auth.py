"""
Authentication utilities for Webhook Service.
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


class User:
    """User model for authentication."""
    
    def __init__(self, user_id: str, email: str, roles: List[str] = None):
        self.id = user_id
        self.email = email
        self.roles = roles or []
        self.permissions = self._calculate_permissions()
    
    def _calculate_permissions(self) -> List[str]:
        """Calculate permissions based on roles."""
        permissions = []
        
        for role in self.roles:
            if role == "admin":
                permissions.extend([
                    "webhook:create",
                    "webhook:read",
                    "webhook:update",
                    "webhook:delete",
                    "webhook:trigger",
                    "webhook:retry",
                    "webhook:analytics",
                    "webhook:admin",
                ])
            elif role == "premium":
                permissions.extend([
                    "webhook:create",
                    "webhook:read",
                    "webhook:update",
                    "webhook:delete",
                    "webhook:trigger",
                    "webhook:retry",
                    "webhook:analytics",
                ])
            elif role == "basic":
                permissions.extend([
                    "webhook:create",
                    "webhook:read",
                    "webhook:update",
                    "webhook:delete",
                    "webhook:trigger",
                ])
        
        return list(set(permissions))
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current user from JWT token."""
    try:
        token = credentials.credentials
        
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID"
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        
        return User(user_id, email, roles)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions."""
    def permission_checker(current_user: User = Depends(get_current_user)):
        for permission in required_permissions:
            if not current_user.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission} required"
                )
        return current_user
    
    return permission_checker


def create_access_token(
    user_id: str,
    email: str,
    roles: List[str] = None,
    expires_delta: timedelta = None
) -> str:
    """Create JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expiration_hours)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles or [],
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "splunk-mcp-webhook-service",
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


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
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_user_from_request(request: Request) -> Optional[User]:
    """Get user from request without raising exceptions."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        payload = verify_token(token)
        
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        
        if user_id:
            return User(user_id, email, roles)
        
        return None
        
    except Exception:
        return None