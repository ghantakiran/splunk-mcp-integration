"""
Authentication utilities for PDF Export Service.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import hmac
import secrets
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from app.core.config import settings
from app.models.user_models import UserRole, UserPermission
from app.core.database import execute_query

logger = structlog.get_logger(__name__)

# Security schemes
security = HTTPBearer()


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class AuthorizationError(Exception):
    """Authorization error."""
    pass


def create_access_token(user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = user_data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise AuthenticationError("Failed to create access token")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Token payload invalid")
        
        return payload
    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID from database."""
    try:
        user = await execute_query(
            "SELECT * FROM pdf_users WHERE id = $1",
            user_id,
            fetchrow=True
        )
        return dict(user) if user else None
    except Exception as e:
        logger.error("Failed to get user by ID", user_id=user_id, error=str(e))
        return None


async def get_user_by_external_id(external_id: str) -> Optional[Dict[str, Any]]:
    """Get user by external ID from database."""
    try:
        user = await execute_query(
            "SELECT * FROM pdf_users WHERE external_id = $1",
            external_id,
            fetchrow=True
        )
        return dict(user) if user else None
    except Exception as e:
        logger.error("Failed to get user by external ID", external_id=external_id, error=str(e))
        return None


async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new user in database."""
    try:
        user_id = await execute_query(
            """
            INSERT INTO pdf_users (external_id, email, name, role, permissions, preferences)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            user_data["external_id"],
            user_data["email"],
            user_data["name"],
            user_data.get("role", UserRole.USER),
            user_data.get("permissions", {}),
            user_data.get("preferences", {}),
            fetchval=True
        )
        
        # Get created user
        user = await get_user_by_id(user_id)
        logger.info("User created successfully", user_id=user_id, external_id=user_data["external_id"])
        return user
    except Exception as e:
        logger.error("Failed to create user", user_data=user_data, error=str(e))
        raise


async def update_user(user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update user in database."""
    try:
        # Build update query dynamically
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in user_data.items():
            if field in ["email", "name", "role", "permissions", "preferences", "status"]:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        
        if not update_fields:
            raise ValueError("No valid fields to update")
        
        params.append(user_id)
        
        await execute_query(
            f"UPDATE pdf_users SET {', '.join(update_fields)} WHERE id = ${param_count}",
            *params
        )
        
        # Get updated user
        user = await get_user_by_id(user_id)
        logger.info("User updated successfully", user_id=user_id)
        return user
    except Exception as e:
        logger.error("Failed to update user", user_id=user_id, error=str(e))
        raise


def hash_password(password: str) -> str:
    """Hash password using PBKDF2."""
    salt = secrets.token_hex(32)
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return salt + pwdhash.hex()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    salt = hashed[:64]
    stored_hash = hashed[64:]
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return pwdhash.hex() == stored_hash


def check_permission(user_permissions: Dict[str, Any], required_permission: str) -> bool:
    """Check if user has required permission."""
    # Admin has all permissions
    if user_permissions.get("role") == UserRole.ADMIN:
        return True
    
    # Check explicit permissions
    permissions = user_permissions.get("permissions", {})
    if required_permission in permissions:
        return permissions[required_permission]
    
    # Check role-based permissions
    role = user_permissions.get("role", UserRole.USER)
    role_permissions = get_role_permissions(role)
    
    return required_permission in role_permissions


def get_role_permissions(role: UserRole) -> list:
    """Get permissions for a role."""
    role_permissions = {
        UserRole.ADMIN: [
            UserPermission.PDF_CREATE,
            UserPermission.PDF_READ,
            UserPermission.PDF_UPDATE,
            UserPermission.PDF_DELETE,
            UserPermission.TEMPLATE_CREATE,
            UserPermission.TEMPLATE_READ,
            UserPermission.TEMPLATE_UPDATE,
            UserPermission.TEMPLATE_DELETE,
            UserPermission.ANALYTICS_READ,
            UserPermission.ADMIN_READ,
            UserPermission.ADMIN_WRITE,
        ],
        UserRole.MANAGER: [
            UserPermission.PDF_CREATE,
            UserPermission.PDF_READ,
            UserPermission.PDF_UPDATE,
            UserPermission.PDF_DELETE,
            UserPermission.TEMPLATE_CREATE,
            UserPermission.TEMPLATE_READ,
            UserPermission.TEMPLATE_UPDATE,
            UserPermission.ANALYTICS_READ,
        ],
        UserRole.ANALYST: [
            UserPermission.PDF_CREATE,
            UserPermission.PDF_READ,
            UserPermission.PDF_UPDATE,
            UserPermission.TEMPLATE_READ,
            UserPermission.ANALYTICS_READ,
        ],
        UserRole.USER: [
            UserPermission.PDF_CREATE,
            UserPermission.PDF_READ,
            UserPermission.TEMPLATE_READ,
        ],
        UserRole.VIEWER: [
            UserPermission.PDF_READ,
            UserPermission.TEMPLATE_READ,
        ],
    }
    
    return role_permissions.get(role, [])


def require_permission(required_permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check permission
            if not check_permission(current_user, required_permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{required_permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: UserRole):
    """Decorator to require specific role."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check role
            user_role = current_user.get("role")
            if user_role != required_role and user_role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{required_role}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def generate_api_key(user_id: int) -> str:
    """Generate API key for user."""
    data = f"{user_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify API key and return user data."""
    # This would typically involve database lookup
    # For now, we'll implement a simple verification
    try:
        # In production, store API keys in database with associated user
        # For now, return None to force JWT authentication
        return None
    except Exception as e:
        logger.error("Failed to verify API key", error=str(e))
        return None


async def log_authentication_event(user_id: int, event_type: str, success: bool, 
                                  ip_address: str = None, user_agent: str = None, 
                                  error_message: str = None):
    """Log authentication event."""
    try:
        await execute_query(
            """
            INSERT INTO pdf_export_logs (user_id, level, message, context)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            "INFO" if success else "WARNING",
            f"Authentication event: {event_type}",
            {
                "event_type": event_type,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_message": error_message
            }
        )
    except Exception as e:
        logger.error("Failed to log authentication event", error=str(e))


async def get_current_user_full(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user with full profile information."""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Token payload invalid")
        
        # Get user from database
        user = await get_user_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found")
        
        # Update last login
        await execute_query(
            "UPDATE pdf_users SET last_login = CURRENT_TIMESTAMP WHERE id = $1",
            user["id"]
        )
        
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )