#!/usr/bin/env python3
"""
Rate limiting utilities for CSV Export Service.

This module provides rate limiting functionality using Redis,
with sliding window algorithm and configurable limits per user and endpoint.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import time

from fastapi import HTTPException, status, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self):
        self.redis = None
        self.default_window = 60  # 1 minute window
        self.default_limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.burst_limit = settings.RATE_LIMIT_BURST
    
    def _get_redis(self):
        """Get Redis client."""
        if not self.redis:
            self.redis = get_redis()
        return self.redis
    
    async def is_allowed(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        cost: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Request limit (default: from settings)
            window: Time window in seconds (default: 60)
            cost: Cost of this request (default: 1)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        try:
            redis_client = self._get_redis()
            limit = limit or self.default_limit
            window = window or self.default_window
            
            current_time = time.time()
            window_start = current_time - window
            
            # Key for this identifier
            key = f"rate_limit:{identifier}"
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window + 1)
            
            # Execute pipeline
            results = await pipe.execute()
            
            current_count = results[1]  # Count before adding new request
            
            # Calculate rate limit info
            remaining = max(0, limit - current_count - cost)
            reset_time = int(current_time + window)
            
            rate_limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "window": window,
                "current_count": current_count + cost
            }
            
            # Check if request is allowed
            is_allowed = (current_count + cost) <= limit
            
            if not is_allowed:
                # Remove the request we just added since it's not allowed
                await redis_client.zrem(key, str(current_time))
                rate_limit_info["remaining"] = 0
                rate_limit_info["current_count"] = current_count
            
            return is_allowed, rate_limit_info
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Allow request on error (fail open)
            return True, {
                "limit": limit or self.default_limit,
                "remaining": limit or self.default_limit,
                "reset": int(time.time() + (window or self.default_window)),
                "window": window or self.default_window,
                "current_count": 0,
                "error": "Rate limiter unavailable"
            }
    
    async def reset_limit(self, identifier: str) -> bool:
        """Reset rate limit for identifier."""
        try:
            redis_client = self._get_redis()
            key = f"rate_limit:{identifier}"
            
            deleted = await redis_client.delete(key)
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")
            return False
    
    async def get_current_usage(self, identifier: str, window: Optional[int] = None) -> Dict[str, Any]:
        """Get current rate limit usage for identifier."""
        try:
            redis_client = self._get_redis()
            window = window or self.default_window
            
            current_time = time.time()
            window_start = current_time - window
            
            key = f"rate_limit:{identifier}"
            
            # Count requests in current window
            count = await redis_client.zcount(key, window_start, current_time)
            
            return {
                "identifier": identifier,
                "current_count": count,
                "window": window,
                "window_start": window_start,
                "window_end": current_time
            }
            
        except Exception as e:
            logger.error(f"Rate limit usage error: {e}")
            return {
                "identifier": identifier,
                "current_count": 0,
                "window": window or self.default_window,
                "error": "Unable to get usage"
            }


class EndpointRateLimiter:
    """Endpoint-specific rate limiting."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        
        # Define endpoint-specific limits
        self.endpoint_limits = {
            # Export endpoints - more restrictive
            "/api/v1/export": {"limit": 20, "window": 60, "cost": 2},
            "/api/v1/export/bulk": {"limit": 5, "window": 60, "cost": 5},
            "/api/v1/export/validate": {"limit": 50, "window": 60, "cost": 1},
            
            # Template endpoints - moderate limits
            "/api/v1/templates": {"limit": 30, "window": 60, "cost": 1},
            "/api/v1/templates/create": {"limit": 10, "window": 60, "cost": 2},
            
            # Analytics endpoints - high limits
            "/api/v1/analytics": {"limit": 100, "window": 60, "cost": 1},
            "/api/v1/jobs": {"limit": 100, "window": 60, "cost": 1},
            
            # Status endpoints - very high limits
            "/health": {"limit": 1000, "window": 60, "cost": 1},
            "/metrics": {"limit": 500, "window": 60, "cost": 1}
        }
    
    def get_endpoint_config(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for endpoint."""
        # Exact match first
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Prefix match for dynamic routes
        for endpoint_path, config in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                return config
        
        # Default limits
        return {"limit": settings.RATE_LIMIT_REQUESTS_PER_MINUTE, "window": 60, "cost": 1}
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        user_role: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for specific endpoint."""
        
        # Get endpoint configuration
        config = self.get_endpoint_config(endpoint)
        
        # Adjust limits based on user role
        limit_multiplier = {
            "admin": 3.0,
            "manager": 2.0,
            "user": 1.0,
            "viewer": 0.5
        }.get(user_role, 1.0)
        
        adjusted_limit = int(config["limit"] * limit_multiplier)
        
        return await self.rate_limiter.is_allowed(
            identifier=f"{identifier}:{endpoint}",
            limit=adjusted_limit,
            window=config["window"],
            cost=config["cost"]
        )


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limit headers to responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = EndpointRateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and internal routes
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Get identifier (user_id if authenticated, otherwise IP)
        identifier = self._get_identifier(request)
        
        # Get user role if available
        user_role = getattr(request.state, "user_role", None)
        
        # Check rate limit
        is_allowed, rate_info = await self.rate_limiter.check_rate_limit(
            identifier, request.url.path, user_role
        )
        
        if not is_allowed:
            # Rate limit exceeded
            response = Response(
                content='{"error": "Rate limit exceeded", "detail": "Too many requests"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        else:
            # Process request
            response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
        response.headers["X-RateLimit-Window"] = str(rate_info["window"])
        
        if "error" in rate_info:
            response.headers["X-RateLimit-Error"] = rate_info["error"]
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get first IP from comma-separated list
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"


async def check_user_rate_limit(user_id: int, endpoint: str, user_role: str = "user") -> Dict[str, Any]:
    """
    Check rate limit for authenticated user.
    
    Args:
        user_id: User identifier
        endpoint: API endpoint
        user_role: User role for adjusted limits
        
    Returns:
        Dictionary with rate limit information
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    limiter = EndpointRateLimiter()
    
    is_allowed, rate_info = await limiter.check_rate_limit(
        identifier=f"user:{user_id}",
        endpoint=endpoint,
        user_role=user_role
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_info["limit"],
                "reset": rate_info["reset"],
                "window": rate_info["window"]
            }
        )
    
    return rate_info


async def check_ip_rate_limit(ip_address: str, endpoint: str) -> Dict[str, Any]:
    """
    Check rate limit for IP address.
    
    Args:
        ip_address: Client IP address
        endpoint: API endpoint
        
    Returns:
        Dictionary with rate limit information
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    limiter = EndpointRateLimiter()
    
    is_allowed, rate_info = await limiter.check_rate_limit(
        identifier=f"ip:{ip_address}",
        endpoint=endpoint,
        user_role="viewer"  # Most restrictive for anonymous users
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_info["limit"],
                "reset": rate_info["reset"],
                "window": rate_info["window"]
            }
        )
    
    return rate_info


# Global rate limiter instances
global_rate_limiter = RateLimiter()
endpoint_rate_limiter = EndpointRateLimiter()


# Export commonly used functions and classes
__all__ = [
    "RateLimiter",
    "EndpointRateLimiter", 
    "RateLimitHeadersMiddleware",
    "check_user_rate_limit",
    "check_ip_rate_limit",
    "global_rate_limiter",
    "endpoint_rate_limiter"
]