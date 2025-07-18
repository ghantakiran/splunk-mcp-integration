#!/usr/bin/env python3
"""
Rate limiting utilities for PowerPoint Export Service.

This module provides rate limiting functionality using Redis
with sliding window algorithm.
"""

import asyncio
from typing import Tuple, Dict, Any

from structlog import get_logger

from app.core.config import settings
from app.core.redis_client import RateLimiter as RedisRateLimiter


logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    def __init__(self, message: str, retry_after: int, details: Dict[str, Any]):
        self.message = message
        self.retry_after = retry_after
        self.details = details
        super().__init__(message)


async def check_rate_limit(
    identifier: str,
    limit: int,
    window: int,
    burst: int = None
) -> bool:
    """Check if request is within rate limit.
    
    Args:
        identifier: Unique identifier for rate limiting (e.g., user ID, IP)
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        burst: Maximum burst requests allowed (optional)
    
    Returns:
        True if within limit, False if rate limit exceeded
    """
    try:
        allowed, details = await RedisRateLimiter.check_rate_limit(
            identifier=identifier,
            limit=limit,
            window=window,
            burst=burst
        )
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                current_count=details.get("count"),
                limit=limit,
                window=window
            )
        
        return allowed
    
    except Exception as e:
        logger.error("Rate limit check failed", identifier=identifier, error=str(e))
        # Fail open - allow request if rate limiting fails
        return True


async def check_rate_limit_with_details(
    identifier: str,
    limit: int,
    window: int,
    burst: int = None
) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit and return detailed information.
    
    Args:
        identifier: Unique identifier for rate limiting
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        burst: Maximum burst requests allowed (optional)
    
    Returns:
        Tuple of (allowed, details)
    """
    try:
        allowed, details = await RedisRateLimiter.check_rate_limit(
            identifier=identifier,
            limit=limit,
            window=window,
            burst=burst
        )
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded with details",
                identifier=identifier,
                details=details
            )
        
        return allowed, details
    
    except Exception as e:
        logger.error("Rate limit check with details failed", identifier=identifier, error=str(e))
        # Fail open - allow request if rate limiting fails
        return True, {"error": "Rate limiting unavailable"}


async def enforce_rate_limit(
    identifier: str,
    limit: int,
    window: int,
    burst: int = None
) -> None:
    """Enforce rate limit and raise exception if exceeded.
    
    Args:
        identifier: Unique identifier for rate limiting
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        burst: Maximum burst requests allowed (optional)
    
    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    allowed, details = await check_rate_limit_with_details(
        identifier=identifier,
        limit=limit,
        window=window,
        burst=burst
    )
    
    if not allowed:
        retry_after = details.get("reset_at", 0) - int(asyncio.get_event_loop().time())
        retry_after = max(retry_after, 0)
        
        raise RateLimitExceeded(
            message=f"Rate limit exceeded for {identifier}",
            retry_after=retry_after,
            details=details
        )


# Predefined rate limiters for common use cases
async def check_user_rate_limit(user_id: int) -> bool:
    """Check rate limit for a specific user."""
    return await check_rate_limit(
        identifier=f"user:{user_id}",
        limit=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        window=60,
        burst=settings.RATE_LIMIT_BURST
    )


async def check_ip_rate_limit(ip_address: str) -> bool:
    """Check rate limit for a specific IP address."""
    return await check_rate_limit(
        identifier=f"ip:{ip_address}",
        limit=settings.RATE_LIMIT_REQUESTS_PER_MINUTE * 5,  # More lenient for IP
        window=60,
        burst=settings.RATE_LIMIT_BURST * 2
    )


async def check_global_rate_limit() -> bool:
    """Check global rate limit for the service."""
    return await check_rate_limit(
        identifier="global",
        limit=10000,  # High global limit
        window=60,
        burst=1000
    )


async def check_endpoint_rate_limit(endpoint: str, user_id: int) -> bool:
    """Check rate limit for a specific endpoint and user."""
    # Different limits for different endpoints
    endpoint_limits = {
        "generate": (10, 60),  # 10 requests per minute for generation
        "bulk_generate": (2, 300),  # 2 requests per 5 minutes for bulk
        "download": (100, 60),  # 100 downloads per minute
        "list": (200, 60),  # 200 list requests per minute
    }
    
    limit, window = endpoint_limits.get(endpoint, (50, 60))  # Default limit
    
    return await check_rate_limit(
        identifier=f"endpoint:{endpoint}:user:{user_id}",
        limit=limit,
        window=window,
        burst=min(limit // 5, 10)  # Burst is 1/5 of limit or 10, whichever is smaller
    )


async def check_file_size_rate_limit(user_id: int, file_size_mb: float) -> bool:
    """Check rate limit based on file size (for large file processing)."""
    # Limit based on total MB processed per hour
    max_mb_per_hour = 1000  # 1GB per hour per user
    
    return await check_rate_limit(
        identifier=f"file_size:user:{user_id}",
        limit=int(max_mb_per_hour / max(file_size_mb, 1)),  # Adjust limit based on file size
        window=3600,  # 1 hour window
        burst=5
    )


# Rate limiting decorators and utilities
class RateLimitConfig:
    """Rate limiting configuration."""
    
    def __init__(
        self,
        requests_per_minute: int = None,
        requests_per_hour: int = None,
        burst: int = None,
        per_user: bool = True,
        per_ip: bool = False,
        per_endpoint: bool = False
    ):
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.requests_per_hour = requests_per_hour
        self.burst = burst or settings.RATE_LIMIT_BURST
        self.per_user = per_user
        self.per_ip = per_ip
        self.per_endpoint = per_endpoint


# Default rate limiting configurations
DEFAULT_CONFIG = RateLimitConfig()
STRICT_CONFIG = RateLimitConfig(requests_per_minute=20, burst=5)
LENIENT_CONFIG = RateLimitConfig(requests_per_minute=200, burst=50)
BULK_CONFIG = RateLimitConfig(requests_per_minute=5, requests_per_hour=50, burst=2)


# Export commonly used functions and classes
__all__ = [
    "check_rate_limit",
    "check_rate_limit_with_details",
    "enforce_rate_limit",
    "check_user_rate_limit",
    "check_ip_rate_limit",
    "check_global_rate_limit",
    "check_endpoint_rate_limit",
    "check_file_size_rate_limit",
    "RateLimitExceeded",
    "RateLimitConfig",
    "DEFAULT_CONFIG",
    "STRICT_CONFIG",
    "LENIENT_CONFIG",
    "BULK_CONFIG"
]
