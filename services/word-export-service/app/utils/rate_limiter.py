#!/usr/bin/env python3
"""
Rate limiting utilities for Word Export Service.

This module provides middleware and utilities for implementing
rate limiting using Redis-based sliding window algorithm.
"""

import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis_client import get_rate_limiter
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limiting headers to responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Add rate limiting headers to response."""
        try:
            # Initialize rate limiter if needed
            if not self.rate_limiter:
                self.rate_limiter = get_rate_limiter()
            
            response = await call_next(request)
            
            # Add rate limiting headers if they exist in response
            if hasattr(response, "headers"):
                # These headers would be set by the rate limiting logic
                rate_limit_info = getattr(request.state, "rate_limit_info", None)
                if rate_limit_info:
                    response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", ""))
                    response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", ""))
                    response.headers["X-RateLimit-Reset"] = rate_limit_info.get("reset_time", "")
                    response.headers["X-RateLimit-Window"] = str(rate_limit_info.get("window_seconds", ""))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await call_next(request)


async def check_rate_limit(
    request: Request,
    identifier: str,
    limit: int,
    window_seconds: int,
    burst_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check rate limit for a request.
    
    Args:
        request: FastAPI request object
        identifier: Unique identifier for rate limiting (e.g., user ID, IP)
        limit: Maximum number of requests in window
        window_seconds: Time window in seconds
        burst_limit: Optional burst limit for immediate blocking
    
    Returns:
        Dictionary with rate limit information
    
    Raises:
        HTTPException: If rate limit is exceeded
    """
    try:
        rate_limiter = get_rate_limiter()
        
        # Check rate limit
        allowed, info = await rate_limiter.is_allowed(
            identifier=identifier,
            limit=limit,
            window_seconds=window_seconds,
            burst_limit=burst_limit
        )
        
        # Store rate limit info in request state for middleware
        request.state.rate_limit_info = info
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                current_count=info["current_count"],
                limit=info["limit"],
                window_seconds=info["window_seconds"]
            )
            
            # Create rate limit exceeded response
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit} per {window_seconds} seconds",
                    "current_count": info["current_count"],
                    "limit": info["limit"],
                    "remaining": info["remaining"],
                    "reset_time": info["reset_time"],
                    "retry_after": window_seconds
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": info["reset_time"],
                    "Retry-After": str(window_seconds)
                }
            )
        
        logger.info(
            f"Rate limit check passed for {identifier}",
            current_count=info["current_count"],
            limit=info["limit"],
            remaining=info["remaining"]
        )
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limit check error for {identifier}: {e}")
        # On error, allow the request to proceed
        return {
            "current_count": 0,
            "limit": limit,
            "remaining": limit,
            "reset_time": datetime.utcnow().isoformat(),
            "window_seconds": window_seconds
        }


async def apply_user_rate_limit(request: Request, user_id: int) -> Dict[str, Any]:
    """Apply per-user rate limiting."""
    return await check_rate_limit(
        request=request,
        identifier=f"user:{user_id}",
        limit=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        window_seconds=60,
        burst_limit=settings.RATE_LIMIT_BURST
    )


async def apply_ip_rate_limit(request: Request) -> Dict[str, Any]:
    """Apply per-IP rate limiting."""
    # Get client IP
    client_ip = get_client_ip(request)
    
    return await check_rate_limit(
        request=request,
        identifier=f"ip:{client_ip}",
        limit=settings.RATE_LIMIT_REQUESTS_PER_MINUTE * 2,  # More lenient for IP-based limiting
        window_seconds=60,
        burst_limit=settings.RATE_LIMIT_BURST * 2
    )


async def apply_endpoint_rate_limit(request: Request, endpoint: str, custom_limit: int = None) -> Dict[str, Any]:
    """Apply per-endpoint rate limiting."""
    limit = custom_limit or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    
    return await check_rate_limit(
        request=request,
        identifier=f"endpoint:{endpoint}",
        limit=limit,
        window_seconds=60,
        burst_limit=settings.RATE_LIMIT_BURST
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded headers first (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in case of multiple
        return forwarded_for.split(",")[0].strip()
    
    # Check other common headers
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


def rate_limit_decorator(
    limit: int,
    window_seconds: int = 60,
    burst_limit: Optional[int] = None,
    per_user: bool = True,
    per_ip: bool = False,
    identifier_func: Optional[Callable] = None
):
    """
    Decorator for applying rate limiting to endpoint functions.
    
    Args:
        limit: Maximum requests in window
        window_seconds: Time window in seconds
        burst_limit: Optional burst limit
        per_user: Apply per-user rate limiting
        per_ip: Apply per-IP rate limiting
        identifier_func: Custom function to generate identifier
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, proceed without rate limiting
                return await func(*args, **kwargs)
            
            try:
                # Determine identifier
                if identifier_func:
                    identifier = identifier_func(request)
                elif per_user:
                    # Extract user ID from request (assumes authentication)
                    user_id = getattr(request.state, "user_id", None)
                    if user_id:
                        identifier = f"user:{user_id}"
                    else:
                        identifier = f"ip:{get_client_ip(request)}"
                elif per_ip:
                    identifier = f"ip:{get_client_ip(request)}"
                else:
                    identifier = f"endpoint:{func.__name__}"
                
                # Apply rate limiting
                await check_rate_limit(
                    request=request,
                    identifier=identifier,
                    limit=limit,
                    window_seconds=window_seconds,
                    burst_limit=burst_limit
                )
                
                # Proceed with function execution
                return await func(*args, **kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Rate limit decorator error: {e}")
                # On error, proceed with function execution
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def get_rate_limit_status(identifier: str, window_seconds: int = 60) -> Dict[str, Any]:
    """Get current rate limit status for an identifier."""
    try:
        rate_limiter = get_rate_limiter()
        return await rate_limiter.get_status(identifier, window_seconds)
    except Exception as e:
        logger.error(f"Failed to get rate limit status for {identifier}: {e}")
        return {
            "current_count": 0,
            "window_seconds": window_seconds,
            "reset_time": datetime.utcnow().isoformat()
        }


class RateLimitExceeded(Exception):
    """Custom exception for rate limit exceeded."""
    
    def __init__(self, message: str, info: Dict[str, Any]):
        self.message = message
        self.info = info
        super().__init__(message)


# Export commonly used functions and classes
__all__ = [
    "RateLimitHeadersMiddleware",
    "check_rate_limit",
    "apply_user_rate_limit",
    "apply_ip_rate_limit",
    "apply_endpoint_rate_limit",
    "get_client_ip",
    "rate_limit_decorator",
    "get_rate_limit_status",
    "RateLimitExceeded"
]