"""
Rate limiting utilities for the Secure Sharing Service.
"""

import time
from typing import Dict, Any, Optional, Callable
from fastapi import HTTPException, status, Request, Depends
import redis.asyncio as redis
from functools import wraps
import hashlib
import json

from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.RATE_LIMIT_ENABLED
        
    async def get_redis(self) -> redis.Redis:
        """Get Redis client connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_CONNECTION_TIMEOUT
            )
        return self.redis_client
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        cost: int = 1
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            cost: Cost of this request (default: 1)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if not self.enabled:
            return True, {"requests_remaining": max_requests, "reset_time": 0}
        
        try:
            redis_client = await self.get_redis()
            current_time = time.time()
            window_start = current_time - window_seconds
            
            # Redis key for this rate limit
            redis_key = f"{settings.RATE_LIMIT_REDIS_PREFIX}{key}"
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in the window
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_requests = results[1]
            
            # Calculate remaining requests
            requests_remaining = max(0, max_requests - current_requests)
            reset_time = current_time + window_seconds
            
            rate_limit_info = {
                "requests_remaining": requests_remaining,
                "reset_time": int(reset_time),
                "current_requests": current_requests,
                "max_requests": max_requests,
                "window_seconds": window_seconds
            }
            
            # Check if request would exceed limit
            if current_requests + cost > max_requests:
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    current_requests=current_requests,
                    max_requests=max_requests,
                    cost=cost
                )
                return False, rate_limit_info
            
            # Add current request(s) to the window
            for _ in range(cost):
                await redis_client.zadd(
                    redis_key,
                    {f"{current_time}_{time.time_ns()}": current_time}
                )
            
            # Set expiration for cleanup
            await redis_client.expire(redis_key, window_seconds + 60)
            
            # Update rate limit info
            rate_limit_info["requests_remaining"] = max(0, requests_remaining - cost)
            rate_limit_info["current_requests"] = current_requests + cost
            
            logger.debug(
                "Rate limit check passed",
                key=key,
                current_requests=current_requests + cost,
                max_requests=max_requests
            )
            
            return True, rate_limit_info
            
        except Exception as e:
            logger.error(
                "Rate limiter error, allowing request",
                error=str(e),
                key=key
            )
            # Fail open - allow the request if rate limiter fails
            return True, {"requests_remaining": max_requests, "reset_time": 0}
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a specific key."""
        if not self.enabled:
            return True
            
        try:
            redis_client = await self.get_redis()
            redis_key = f"{settings.RATE_LIMIT_REDIS_PREFIX}{key}"
            
            result = await redis_client.delete(redis_key)
            
            logger.info(
                "Rate limit reset",
                key=key,
                existed=bool(result)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Rate limit reset failed",
                error=str(e),
                key=key
            )
            return False
    
    async def get_limit_status(self, key: str, window_seconds: int) -> Dict[str, Any]:
        """Get current rate limit status for a key."""
        if not self.enabled:
            return {"current_requests": 0, "window_start": time.time()}
            
        try:
            redis_client = await self.get_redis()
            current_time = time.time()
            window_start = current_time - window_seconds
            
            redis_key = f"{settings.RATE_LIMIT_REDIS_PREFIX}{key}"
            
            # Clean up old entries and count current
            await redis_client.zremrangebyscore(redis_key, 0, window_start)
            current_requests = await redis_client.zcard(redis_key)
            
            return {
                "current_requests": current_requests,
                "window_start": window_start,
                "window_end": current_time
            }
            
        except Exception as e:
            logger.error(
                "Failed to get rate limit status",
                error=str(e),
                key=key
            )
            return {"current_requests": 0, "window_start": time.time()}
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_rate_limit_key(
    request: Request,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None
) -> str:
    """Generate rate limit key based on user or IP."""
    if user_id:
        base_key = f"user:{user_id}"
    else:
        # Fall back to IP address
        ip = request.client.host if request.client else "unknown"
        base_key = f"ip:{ip}"
    
    if endpoint:
        base_key = f"{base_key}:{endpoint}"
    
    return base_key


def rate_limit(
    endpoint: str,
    max_requests: int = None,
    window_seconds: int = None,
    cost: int = 1,
    per_user: bool = True,
    per_ip: bool = True
):
    """
    Rate limiting decorator.
    
    Args:
        endpoint: Endpoint identifier
        max_requests: Maximum requests in window (default from settings)
        window_seconds: Window size in seconds (default from settings)
        cost: Cost of this request type
        per_user: Apply limit per user
        per_ip: Apply limit per IP when no user
    """
    if max_requests is None:
        max_requests = settings.DEFAULT_RATE_LIMIT
    if window_seconds is None:
        window_seconds = settings.DEFAULT_RATE_LIMIT_WINDOW
    
    async def rate_limit_dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        
        # Extract user ID from request if available
        user_id = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from app.utils.auth import verify_token
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                user_id = payload.get("sub") or payload.get("user_id")
        except Exception:
            pass  # No user authentication, will use IP
        
        # Generate rate limit key
        if per_user and user_id:
            rate_key = f"user:{user_id}:{endpoint}"
        elif per_ip:
            ip = request.client.host if request.client else "unknown"
            rate_key = f"ip:{ip}:{endpoint}"
        else:
            rate_key = f"global:{endpoint}"
        
        # Check rate limit
        is_allowed, limit_info = await rate_limiter.is_allowed(
            rate_key, max_requests, window_seconds, cost
        )
        
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded for endpoint",
                endpoint=endpoint,
                rate_key=rate_key,
                max_requests=max_requests,
                current_requests=limit_info.get("current_requests", 0)
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(limit_info.get("requests_remaining", 0)),
                    "X-RateLimit-Reset": str(limit_info.get("reset_time", 0)),
                    "Retry-After": str(window_seconds)
                }
            )
    
    return Depends(rate_limit_dependency)


def get_user_rate_limit_key(user_id: str, endpoint: str) -> str:
    """Get rate limit key for a specific user and endpoint."""
    return f"user:{user_id}:{endpoint}"


def get_ip_rate_limit_key(ip_address: str, endpoint: str) -> str:
    """Get rate limit key for a specific IP and endpoint."""
    return f"ip:{ip_address}:{endpoint}"


async def reset_user_rate_limits(user_id: str) -> bool:
    """Reset all rate limits for a specific user."""
    try:
        redis_client = await rate_limiter.get_redis()
        pattern = f"{settings.RATE_LIMIT_REDIS_PREFIX}user:{user_id}:*"
        
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            
        logger.info(
            "User rate limits reset",
            user_id=user_id,
            keys_deleted=len(keys)
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to reset user rate limits",
            user_id=user_id,
            error=str(e)
        )
        return False


async def get_rate_limit_stats(
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Get rate limit statistics for debugging."""
    try:
        redis_client = await rate_limiter.get_redis()
        
        if user_id:
            pattern = f"{settings.RATE_LIMIT_REDIS_PREFIX}user:{user_id}:*"
        elif ip_address:
            pattern = f"{settings.RATE_LIMIT_REDIS_PREFIX}ip:{ip_address}:*"
        else:
            pattern = f"{settings.RATE_LIMIT_REDIS_PREFIX}*"
        
        keys = await redis_client.keys(pattern)
        stats = {}
        
        for key in keys:
            endpoint = key.split(":")[-1]
            count = await redis_client.zcard(key)
            ttl = await redis_client.ttl(key)
            
            stats[endpoint] = {
                "current_requests": count,
                "ttl_seconds": ttl
            }
        
        return stats
        
    except Exception as e:
        logger.error(
            "Failed to get rate limit stats",
            error=str(e)
        )
        return {}


# Cleanup function for expired rate limit entries
async def cleanup_expired_rate_limits():
    """Clean up expired rate limit entries (background task)."""
    try:
        redis_client = await rate_limiter.get_redis()
        current_time = time.time()
        
        # Get all rate limit keys
        pattern = f"{settings.RATE_LIMIT_REDIS_PREFIX}*"
        keys = await redis_client.keys(pattern)
        
        cleaned_count = 0
        for key in keys:
            # Remove entries older than the longest possible window
            max_window = 3600  # 1 hour
            cutoff_time = current_time - max_window
            
            removed = await redis_client.zremrangebyscore(key, 0, cutoff_time)
            if removed > 0:
                cleaned_count += removed
        
        if cleaned_count > 0:
            logger.debug(
                "Cleaned up expired rate limit entries",
                entries_removed=cleaned_count,
                keys_processed=len(keys)
            )
        
    except Exception as e:
        logger.error(
            "Rate limit cleanup failed",
            error=str(e)
        )