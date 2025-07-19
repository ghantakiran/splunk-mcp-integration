"""
Rate limiting utilities for JSON/XML Export Service.
"""

import time
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from app.core.config import settings
from app.core.redis_client import get_rate_limiter

logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""
    
    def __init__(self, retry_after: int = None):
        detail = "Rate limit exceeded"
        if retry_after:
            detail += f". Retry after {retry_after} seconds"
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)} if retry_after else None
        )


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limiting headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limiting headers if they exist in the response context
        if hasattr(request.state, "rate_limit_headers"):
            headers = request.state.rate_limit_headers
            for key, value in headers.items():
                response.headers[key] = str(value)
        
        return response


async def check_rate_limit(
    request: Request,
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
    window: Optional[int] = None,
    burst: Optional[int] = None,
    cost: int = 1
) -> None:
    """Check rate limit for request."""
    # Get rate limiter
    rate_limiter = get_rate_limiter()
    
    # Determine rate limit key
    if user_id:
        key = f"rate_limit:user:{user_id}"
    else:
        # Fall back to IP-based limiting
        client_ip = request.client.host
        key = f"rate_limit:ip:{client_ip}"
    
    # Use configured limits if not specified
    limit = limit or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    window = window or 60  # 1 minute window
    burst = burst or settings.RATE_LIMIT_BURST_SIZE
    
    # Apply cost multiplier
    effective_limit = limit // cost if cost > 1 else limit
    
    try:
        # Check if request is allowed
        is_allowed = await rate_limiter.is_allowed(
            key=key,
            limit=effective_limit,
            window=window,
            burst=burst
        )
        
        # Get current stats
        stats = await rate_limiter.get_stats(key)
        
        # Calculate headers
        remaining = max(0, effective_limit - stats["count"])
        reset_time = stats.get("reset_time", time.time() + window)
        retry_after = int(reset_time - time.time()) if reset_time else window
        
        # Store headers in request state for middleware
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": effective_limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": int(reset_time),
            "X-RateLimit-Window": window
        }
        
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                key=key,
                limit=effective_limit,
                window=window,
                current_count=stats["count"],
                retry_after=retry_after
            )
            raise RateLimitExceeded(retry_after=retry_after)
        
        logger.debug(
            "Rate limit check passed",
            key=key,
            limit=effective_limit,
            remaining=remaining,
            window=window
        )
        
    except RateLimitExceeded:
        raise
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # Allow request on error to avoid blocking service
        pass


class RateLimitConfig:
    """Rate limit configuration for different endpoints."""
    
    # Default rate limits (requests per minute)
    DEFAULT = 60
    
    # Export operation limits
    EXPORT_CREATE = 30
    EXPORT_BULK = 10
    EXPORT_DOWNLOAD = 100
    
    # Admin operation limits
    ADMIN_OPERATIONS = 120
    
    # Analytics and reporting
    ANALYTICS = 60
    
    # File operations
    FILE_UPLOAD = 20
    FILE_DELETE = 40
    
    @classmethod
    def get_limit(cls, operation: str) -> int:
        """Get rate limit for operation."""
        return getattr(cls, operation.upper(), cls.DEFAULT)


async def rate_limit_export_create(request: Request, user_id: str) -> None:
    """Rate limit for export creation."""
    await check_rate_limit(
        request=request,
        user_id=user_id,
        limit=RateLimitConfig.EXPORT_CREATE,
        window=60,
        cost=2  # Higher cost for resource-intensive operations
    )


async def rate_limit_bulk_export(request: Request, user_id: str) -> None:
    """Rate limit for bulk export operations."""
    await check_rate_limit(
        request=request,
        user_id=user_id,
        limit=RateLimitConfig.EXPORT_BULK,
        window=60,
        cost=5  # Much higher cost for bulk operations
    )


async def rate_limit_download(request: Request, user_id: str) -> None:
    """Rate limit for file downloads."""
    await check_rate_limit(
        request=request,
        user_id=user_id,
        limit=RateLimitConfig.EXPORT_DOWNLOAD,
        window=60,
        cost=1
    )


async def rate_limit_admin(request: Request, user_id: str) -> None:
    """Rate limit for admin operations."""
    await check_rate_limit(
        request=request,
        user_id=user_id,
        limit=RateLimitConfig.ADMIN_OPERATIONS,
        window=60,
        cost=1
    )


async def rate_limit_analytics(request: Request, user_id: str) -> None:
    """Rate limit for analytics operations."""
    await check_rate_limit(
        request=request,
        user_id=user_id,
        limit=RateLimitConfig.ANALYTICS,
        window=60,
        cost=1
    )