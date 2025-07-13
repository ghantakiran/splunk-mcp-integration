"""
Dependency injection for API endpoints
"""

from typing import Generator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from ..core.config import settings
from ..core.security import security, security_manager
from ..core.exceptions import (
    AuthenticationError,
    SessionExpiredError,
    map_exception_to_http
)
from ..db.session import get_async_session


async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    return redis.from_url(
        settings.redis_url,
        password=settings.redis_password,
        db=settings.redis_db,
        encoding="utf-8",
        decode_responses=True
    )


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    try:
        token = security_manager.extract_token_from_credentials(credentials)
        payload = security_manager.verify_token(token)
        
        if payload is None:
            raise AuthenticationError("Invalid or expired token")
        
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        
        return payload
        
    except AuthenticationError as e:
        raise map_exception_to_http(e)


async def get_current_user(
    db: AsyncSession = Depends(get_async_session),
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    """Get current authenticated user"""
    try:
        user_id = token_data.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token: missing user ID")
        
        # Query user from database
        from sqlalchemy import select
        from ..models.user import User
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        return user
        
    except AuthenticationError as e:
        raise map_exception_to_http(e)


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """Get current active user (alias for get_current_user)"""
    return current_user


async def get_current_admin_user(
    current_user = Depends(get_current_user)
):
    """Get current user with admin privileges"""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_session)
):
    """Get current user if authenticated, None otherwise"""
    if credentials is None:
        return None
    
    try:
        token = security_manager.extract_token_from_credentials(credentials)
        payload = security_manager.verify_token(token)
        
        if payload is None or payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        from sqlalchemy import select
        from ..models.user import User
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        return user if user and user.is_active else None
        
    except Exception:
        return None


async def validate_session(
    request: Request,
    current_user = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Validate user session"""
    try:
        # Get session token from Redis
        session_key = f"session:{current_user.id}"
        stored_session = await redis_client.get(session_key)
        
        if not stored_session:
            raise SessionExpiredError("Session not found")
        
        # Check if session is still valid
        # Additional session validation logic can be added here
        
        # Update last activity
        await redis_client.expire(session_key, settings.session_timeout_minutes * 60)
        
        return current_user
        
    except (SessionExpiredError, Exception) as e:
        if isinstance(e, SessionExpiredError):
            raise map_exception_to_http(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session validation failed"
        )


async def check_rate_limit(
    request: Request,
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user_optional)
) -> None:
    """Check rate limiting for API requests"""
    # Get client identifier
    client_id = current_user.id if current_user else request.client.host
    
    # Rate limiting key
    rate_limit_key = f"rate_limit:{client_id}"
    
    # Check current request count
    current_requests = await redis_client.get(rate_limit_key)
    
    if current_requests is None:
        # First request in this window
        await redis_client.setex(rate_limit_key, 60, 1)
    else:
        current_count = int(current_requests)
        
        if current_count >= settings.rate_limit_requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )
        
        await redis_client.incr(rate_limit_key)


def get_pagination_params(
    page: int = 1,
    page_size: int = 50,
    max_page_size: int = 100
) -> Dict[str, int]:
    """Get pagination parameters with validation"""
    if page < 1:
        page = 1
    
    if page_size < 1:
        page_size = 50
    elif page_size > max_page_size:
        page_size = max_page_size
    
    offset = (page - 1) * page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": offset,
        "limit": page_size
    }


def get_query_filters(
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None
) -> Dict[str, Any]:
    """Get common query filters"""
    filters = {}
    
    if search:
        filters["search"] = search.strip()
    
    if start_date:
        filters["start_date"] = start_date
    
    if end_date:
        filters["end_date"] = end_date
    
    if status:
        filters["status"] = status
    
    if tags:
        filters["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    return filters