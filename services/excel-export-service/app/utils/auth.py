"""
Authentication utilities.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.models.user_models import User


logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


async def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current user from token."""
    token = credentials.credentials
    payload = await verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"id": int(user_id), "email": payload.get("email", "")}


async def get_current_user_full(
    current_user: dict = Depends(get_current_user)
) -> User:
    """Get current user with full information."""
    return User(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        is_active=True,
        permissions=current_user.get("permissions", {})
    )