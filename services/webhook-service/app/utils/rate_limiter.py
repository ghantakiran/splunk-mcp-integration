"""
Rate limiting utilities for Webhook Service.
"""

import asyncio
from typing import Dict, Any
from fastapi import HTTPException, Request

from ..core.config import settings
from ..core.redis_client import get_redis_client, RedisRateLimiter
from ..core.logging import get_logger
from .auth import get_user_from_request

logger = get_logger(__name__)


async def check_rate_limit(request: Request) -> None:
    """Check rate limits for incoming requests."""
    try:
        # Get Redis client
        redis_client = await get_redis_client()
        rate_limiter = RedisRateLimiter(redis_client)
        
        # Get user info
        user = await get_user_from_request(request)
        
        # Determine rate limit key and limits
        if user:
            # User-based rate limiting
            key = f"user:{user.id}"
            limit = settings.rate_limit_per_user
            window = settings.rate_limit_window
            burst = settings.rate_limit_burst
        else:
            # IP-based rate limiting for unauthenticated requests
            client_ip = get_client_ip(request)
            key = f"ip:{client_ip}"
            limit = settings.rate_limit_per_user // 2  # Lower limit for unauthenticated
            window = settings.rate_limit_window
            burst = settings.rate_limit_burst // 2
        
        # Check rate limit
        allowed, info = await rate_limiter.is_allowed(key, limit, window, burst)
        
        if not allowed:
            # Add rate limit headers
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Window": str(window),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(asyncio.get_event_loop().time()) + window),
            }
            
            logger.warning(
                f"Rate limit exceeded for {key}",
                **info
            )
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers=headers
            )
        
        # Add rate limit headers for successful requests
        request.state.rate_limit_info = {
            "limit": limit,
            "remaining": info.get("remaining", 0),
            "window": window,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting check failed: {e}")
        # Allow request to proceed if rate limiting fails
        pass


async def check_webhook_rate_limit(
    user_id: str,
    endpoint_id: str = None
) -> Dict[str, Any]:
    """Check webhook-specific rate limits."""
    try:
        redis_client = await get_redis_client()
        rate_limiter = RedisRateLimiter(redis_client)
        
        # User webhook rate limit
        user_key = f"webhook_user:{user_id}"
        user_allowed, user_info = await rate_limiter.is_allowed(
            user_key,
            settings.rate_limit_per_user,
            settings.rate_limit_window
        )
        
        if not user_allowed:
            return {
                "allowed": False,
                "reason": "user_rate_limit_exceeded",
                "info": user_info
            }
        
        # Endpoint-specific rate limit if provided
        if endpoint_id:
            endpoint_key = f"webhook_endpoint:{endpoint_id}"
            endpoint_allowed, endpoint_info = await rate_limiter.is_allowed(
                endpoint_key,
                settings.rate_limit_per_endpoint,
                settings.rate_limit_window
            )
            
            if not endpoint_allowed:
                return {
                    "allowed": False,
                    "reason": "endpoint_rate_limit_exceeded",
                    "info": endpoint_info
                }
        
        return {
            "allowed": True,
            "user_info": user_info,
            "endpoint_info": endpoint_info if endpoint_id else None
        }
        
    except Exception as e:
        logger.error(f"Webhook rate limiting failed: {e}")
        # Allow if rate limiting fails
        return {"allowed": True, "error": str(e)}


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers (reverse proxy)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # Take the first IP in the chain
        return x_forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip
    
    # Fall back to direct connection IP
    if hasattr(request.client, "host"):
        return request.client.host
    
    return "unknown"


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    
    def __init__(self, message: str, info: Dict[str, Any]):
        self.message = message
        self.info = info
        super().__init__(message)


async def rate_limit_decorator(
    key_prefix: str,
    limit: int,
    window: int,
    burst: int = None
):
    """Decorator for rate limiting functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                redis_client = await get_redis_client()
                rate_limiter = RedisRateLimiter(redis_client)
                
                # Create key from function name and arguments
                key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                allowed, info = await rate_limiter.is_allowed(key, limit, window, burst)
                
                if not allowed:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {func.__name__}",
                        info
                    )
                
                return await func(*args, **kwargs)
                
            except RateLimitExceeded:
                raise
            except Exception as e:
                logger.error(f"Rate limit decorator failed: {e}")
                # Execute function anyway if rate limiting fails
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator