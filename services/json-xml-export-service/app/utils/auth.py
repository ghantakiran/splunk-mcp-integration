"""
Authentication utilities for JSON/XML Export Service.
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

# JWT token security scheme
security = HTTPBearer()


class AuthManager:
    """Authentication manager."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )
    
    def verify_token(self, token: str) -> dict:
        """Verify access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_user_from_token(self, token: str) -> dict:
        """Extract user information from token."""
        payload = self.verify_token(token)
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }


# Global auth manager instance
auth_manager = AuthManager()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current authenticated user."""
    try:
        user = auth_manager.get_user_from_token(credentials.credentials)
        logger.info(
            "User authenticated",
            user_id=user["user_id"],
            username=user.get("username")
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        return auth_manager.get_user_from_token(credentials.credentials)
    except HTTPException:
        return None
    except Exception:
        return None


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        user_permissions = user.get("permissions", [])
        user_roles = user.get("roles", [])
        
        # Check if user has the required permission
        if permission not in user_permissions:
            # Check if user has admin role (bypass permission check)
            if "admin" not in user_roles:
                logger.warning(
                    "Permission denied",
                    user_id=user["user_id"],
                    required_permission=permission,
                    user_permissions=user_permissions
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
        
        return user
    
    return dependency


def require_role(role: str):
    """Decorator to require specific role."""
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("roles", [])
        
        if role not in user_roles:
            logger.warning(
                "Role access denied",
                user_id=user["user_id"],
                required_role=role,
                user_roles=user_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        
        return user
    
    return dependency


# Permission constants
class Permissions:
    """Permission constants."""
    JSON_XML_EXPORT_CREATE = "json_xml_export:create"
    JSON_XML_EXPORT_READ = "json_xml_export:read"
    JSON_XML_EXPORT_DELETE = "json_xml_export:delete"
    JSON_XML_EXPORT_ADMIN = "json_xml_export:admin"


# Role constants
class Roles:
    """Role constants."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"