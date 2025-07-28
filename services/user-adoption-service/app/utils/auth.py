#!/usr/bin/env python3
"""
Authentication Utilities
========================
Authentication and authorization utilities for user adoption service
"""

import jwt
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings

# JWT and Redis setup
security = HTTPBearer()
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

class User(BaseModel):
    """User model for authentication"""
    user_id: str
    email: str
    full_name: str
    is_admin: bool = False
    permissions: list = []
    department: Optional[str] = None
    role: Optional[str] = None

class TokenData(BaseModel):
    """Token data model"""
    user_id: Optional[str] = None
    email: Optional[str] = None

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_from_token(token_data: Dict[str, Any]) -> User:
    """Get user information from token data"""
    # In a real implementation, this would fetch user data from a database
    # For this service, we'll create a user object from token claims
    
    user_id = token_data.get("sub")
    email = token_data.get("email", "")
    full_name = token_data.get("name", "")
    is_admin = token_data.get("is_admin", False)
    permissions = token_data.get("permissions", [])
    department = token_data.get("department")
    role = token_data.get("role")
    
    return User(
        user_id=user_id,
        email=email,
        full_name=full_name,
        is_admin=is_admin,
        permissions=permissions,
        department=department,
        role=role
    )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    token_data = verify_token(token)
    
    # Get user from token
    user = get_user_from_token(token_data)
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    # Add any additional user status checks here if needed
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    try:
        return redis_client.exists(f"blacklisted_token:{token}")
    except Exception:
        # If Redis is unavailable, assume token is not blacklisted
        return False

def blacklist_token(token: str, expires_in: int = 86400) -> bool:
    """Add token to blacklist"""
    try:
        redis_client.setex(f"blacklisted_token:{token}", expires_in, "1")
        return True
    except Exception:
        return False

def check_permission(user: User, required_permission: str) -> bool:
    """Check if user has required permission"""
    if user.is_admin:
        return True
    
    return required_permission in user.permissions

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker

def hash_password(password: str) -> str:
    """Hash password for storage"""
    # This is a simplified implementation
    # In production, use proper password hashing like bcrypt
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    # This is a simplified implementation
    # In production, use proper password verification
    return hash_password(plain_password) == hashed_password

class AuthenticationError(Exception):
    """Custom authentication error"""
    pass

class AuthorizationError(Exception):
    """Custom authorization error"""
    pass

def get_user_context(user: User) -> Dict[str, Any]:
    """Get user context for logging and analytics"""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "department": user.department,
        "role": user.role,
        "is_admin": user.is_admin,
        "permissions_count": len(user.permissions)
    }

def validate_user_access(user: User, resource_owner_id: str) -> bool:
    """Validate if user can access resource"""
    # Admin can access everything
    if user.is_admin:
        return True
    
    # User can access their own resources
    if user.user_id == resource_owner_id:
        return True
    
    return False