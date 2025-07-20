"""
Authentication utilities for the Secure Sharing Service.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token data model."""
    sub: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    iss: Optional[str] = None


class AuthError(Exception):
    """Authentication error."""
    pass


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "secure-sharing-service"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Validate required fields
        if not payload.get("sub") and not payload.get("user_id"):
            raise AuthError("Token missing user identifier")
        
        # Check expiration
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            if datetime.now(timezone.utc) > exp_datetime:
                raise AuthError("Token expired")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthError(f"Token verification failed: {str(e)}")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(credentials.credentials)
        
        # Log successful authentication
        logger.debug(
            "User authenticated successfully",
            user_id=payload.get("sub") or payload.get("user_id"),
            roles=payload.get("roles", [])
        )
        
        return payload
        
    except AuthError as e:
        logger.warning(
            "Authentication failed",
            error=str(e),
            token_prefix=credentials.credentials[:10] + "..." if len(credentials.credentials) > 10 else credentials.credentials
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token (optional)."""
    if not credentials:
        return None
    
    try:
        return verify_token(credentials.credentials)
    except AuthError:
        return None


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions."""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        user_roles = current_user.get("roles", [])
        
        # Admin role has all permissions
        if "admin" in user_roles:
            return current_user
        
        # Check if user has required permissions
        missing_permissions = [perm for perm in required_permissions if perm not in user_permissions]
        
        if missing_permissions:
            logger.warning(
                "Permission denied",
                user_id=current_user.get("sub") or current_user.get("user_id"),
                required_permissions=required_permissions,
                missing_permissions=missing_permissions,
                user_permissions=user_permissions
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_roles(required_roles: List[str]):
    """Decorator to require specific roles."""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("roles", [])
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            logger.warning(
                "Role access denied",
                user_id=current_user.get("sub") or current_user.get("user_id"),
                required_roles=required_roles,
                user_roles=user_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of the following roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker


def verify_service_token(token: str) -> bool:
    """Verify service-to-service authentication token."""
    return token == settings.SERVICE_AUTH_TOKEN


def get_service_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Service authentication dependency."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_service_token(credentials.credentials):
        logger.warning(
            "Service authentication failed",
            token_prefix=credentials.credentials[:10] + "..." if len(credentials.credentials) > 10 else credentials.credentials
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


# Permission constants
class Permissions:
    """Permission constants for the sharing service."""
    
    # Share permissions
    SHARE_CREATE = "share:create"
    SHARE_READ = "share:read"
    SHARE_UPDATE = "share:update"
    SHARE_DELETE = "share:delete"
    SHARE_ACCESS = "share:access"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADMIN = "analytics:admin"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"


# Role constants
class Roles:
    """Role constants for the sharing service."""
    
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"
    SERVICE = "service"


# Common permission combinations
SHARE_ADMIN_PERMISSIONS = [
    Permissions.SHARE_CREATE,
    Permissions.SHARE_READ,
    Permissions.SHARE_UPDATE,
    Permissions.SHARE_DELETE,
    Permissions.ANALYTICS_READ
]

SHARE_USER_PERMISSIONS = [
    Permissions.SHARE_CREATE,
    Permissions.SHARE_READ,
    Permissions.SHARE_UPDATE,
    Permissions.SHARE_DELETE
]

SHARE_VIEWER_PERMISSIONS = [
    Permissions.SHARE_READ,
    Permissions.SHARE_ACCESS
]


def get_role_permissions(role: str) -> List[str]:
    """Get permissions for a given role."""
    role_permissions = {
        Roles.ADMIN: SHARE_ADMIN_PERMISSIONS + [
            Permissions.ANALYTICS_ADMIN,
            Permissions.SYSTEM_ADMIN,
            Permissions.SYSTEM_MONITOR
        ],
        Roles.MANAGER: SHARE_ADMIN_PERMISSIONS + [Permissions.SYSTEM_MONITOR],
        Roles.USER: SHARE_USER_PERMISSIONS,
        Roles.VIEWER: SHARE_VIEWER_PERMISSIONS,
        Roles.SERVICE: [Permissions.SYSTEM_MONITOR]
    }
    
    return role_permissions.get(role, [])