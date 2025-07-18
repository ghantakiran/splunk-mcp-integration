"""
Rate limiting utilities for PDF Export Service.
"""

import asyncio
import time
from typing import Dict, Optional, Tuple
import structlog
from app.core.redis_client import get_redis_connection

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    def __init__(self):
        self.redis_client = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis_client is None:
            async with get_redis_connection() as redis_client:
                self.redis_client = redis_client
        return self.redis_client
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit."""
        try:
            async with get_redis_connection() as redis_client:
                return await self._sliding_window_check(redis_client, key, limit, window)
        except Exception as e:
            logger.error("Rate limiter error", key=key, error=str(e))
            # Allow request if rate limiter fails
            return True
    
    async def _sliding_window_check(self, redis_client, key: str, limit: int, window: int) -> bool:
        """Sliding window rate limiting algorithm."""
        current_time = int(time.time())
        pipeline = redis_client.pipeline()
        
        # Remove expired entries
        pipeline.zremrangebyscore(key, 0, current_time - window)
        
        # Count current requests
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipeline.expire(key, window)
        
        results = await pipeline.execute()
        current_requests = results[1]
        
        return current_requests < limit
    
    async def get_remaining_requests(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests for the current window."""
        try:
            async with get_redis_connection() as redis_client:
                current_time = int(time.time())
                
                # Remove expired entries and count current requests
                pipeline = redis_client.pipeline()
                pipeline.zremrangebyscore(key, 0, current_time - window)
                pipeline.zcard(key)
                
                results = await pipeline.execute()
                current_requests = results[1]
                
                return max(0, limit - current_requests)
        except Exception as e:
            logger.error("Failed to get remaining requests", key=key, error=str(e))
            return limit
    
    async def get_reset_time(self, key: str, window: int) -> Optional[int]:
        """Get timestamp when rate limit resets."""
        try:
            async with get_redis_connection() as redis_client:
                # Get the oldest entry in the window
                oldest_entries = await redis_client.zrange(key, 0, 0, withscores=True)
                
                if oldest_entries:
                    oldest_timestamp = int(oldest_entries[0][1])
                    return oldest_timestamp + window
                
                return None
        except Exception as e:
            logger.error("Failed to get reset time", key=key, error=str(e))
            return None
    
    async def clear_rate_limit(self, key: str) -> bool:
        """Clear rate limit for a key."""
        try:
            async with get_redis_connection() as redis_client:
                await redis_client.delete(key)
                return True
        except Exception as e:
            logger.error("Failed to clear rate limit", key=key, error=str(e))
            return False


class BurstRateLimiter:
    """Rate limiter with burst capability."""
    
    def __init__(self, tokens_per_second: float, burst_size: int):
        self.tokens_per_second = tokens_per_second
        self.burst_size = burst_size
        self.buckets: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_update)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """Check if request is allowed using token bucket algorithm."""
        async with self.lock:
            current_time = time.time()
            
            if key not in self.buckets:
                self.buckets[key] = (self.burst_size, current_time)
            
            tokens_available, last_update = self.buckets[key]
            
            # Add tokens based on time elapsed
            time_elapsed = current_time - last_update
            tokens_available = min(
                self.burst_size,
                tokens_available + (time_elapsed * self.tokens_per_second)
            )
            
            # Check if we have enough tokens
            if tokens_available >= tokens:
                tokens_available -= tokens
                self.buckets[key] = (tokens_available, current_time)
                return True
            else:
                self.buckets[key] = (tokens_available, current_time)
                return False
    
    async def get_available_tokens(self, key: str) -> float:
        """Get number of available tokens."""
        async with self.lock:
            current_time = time.time()
            
            if key not in self.buckets:
                return self.burst_size
            
            tokens_available, last_update = self.buckets[key]
            
            # Add tokens based on time elapsed
            time_elapsed = current_time - last_update
            tokens_available = min(
                self.burst_size,
                tokens_available + (time_elapsed * self.tokens_per_second)
            )
            
            return tokens_available


class PerUserRateLimiter:
    """Per-user rate limiter with different limits for different operations."""
    
    def __init__(self):
        self.base_limiter = RateLimiter()
        self.limits = {
            "pdf_generation": {"limit": 10, "window": 3600},  # 10 PDFs per hour
            "template_creation": {"limit": 5, "window": 3600},  # 5 templates per hour
            "api_calls": {"limit": 100, "window": 3600},  # 100 API calls per hour
            "bulk_operations": {"limit": 2, "window": 3600},  # 2 bulk operations per hour
        }
    
    async def is_allowed(self, user_id: str, operation: str) -> bool:
        """Check if user is allowed to perform operation."""
        if operation not in self.limits:
            logger.warning("Unknown operation for rate limiting", operation=operation)
            return True
        
        limit_config = self.limits[operation]
        key = f"user:{user_id}:{operation}"
        
        return await self.base_limiter.is_allowed(
            key,
            limit_config["limit"],
            limit_config["window"]
        )
    
    async def get_remaining_requests(self, user_id: str, operation: str) -> int:
        """Get remaining requests for user and operation."""
        if operation not in self.limits:
            return 1000  # Default high limit for unknown operations
        
        limit_config = self.limits[operation]
        key = f"user:{user_id}:{operation}"
        
        return await self.base_limiter.get_remaining_requests(
            key,
            limit_config["limit"],
            limit_config["window"]
        )
    
    async def get_reset_time(self, user_id: str, operation: str) -> Optional[int]:
        """Get reset time for user and operation."""
        if operation not in self.limits:
            return None
        
        limit_config = self.limits[operation]
        key = f"user:{user_id}:{operation}"
        
        return await self.base_limiter.get_reset_time(
            key,
            limit_config["window"]
        )
    
    def update_limits(self, operation: str, limit: int, window: int):
        """Update rate limits for an operation."""
        self.limits[operation] = {"limit": limit, "window": window}
        logger.info("Rate limit updated", operation=operation, limit=limit, window=window)


class IPRateLimiter:
    """IP-based rate limiter for DDoS protection."""
    
    def __init__(self):
        self.base_limiter = RateLimiter()
        self.limits = {
            "requests_per_minute": {"limit": 60, "window": 60},
            "requests_per_hour": {"limit": 1000, "window": 3600},
            "requests_per_day": {"limit": 10000, "window": 86400},
        }
    
    async def is_allowed(self, ip_address: str) -> bool:
        """Check if IP is allowed to make requests."""
        # Check all time windows
        for limit_type, config in self.limits.items():
            key = f"ip:{ip_address}:{limit_type}"
            
            allowed = await self.base_limiter.is_allowed(
                key,
                config["limit"],
                config["window"]
            )
            
            if not allowed:
                logger.warning(
                    "IP rate limit exceeded",
                    ip_address=ip_address,
                    limit_type=limit_type,
                    limit=config["limit"],
                    window=config["window"]
                )
                return False
        
        return True
    
    async def get_ip_status(self, ip_address: str) -> Dict[str, Dict[str, int]]:
        """Get rate limit status for IP address."""
        status = {}
        
        for limit_type, config in self.limits.items():
            key = f"ip:{ip_address}:{limit_type}"
            
            remaining = await self.base_limiter.get_remaining_requests(
                key,
                config["limit"],
                config["window"]
            )
            
            reset_time = await self.base_limiter.get_reset_time(
                key,
                config["window"]
            )
            
            status[limit_type] = {
                "limit": config["limit"],
                "remaining": remaining,
                "reset_time": reset_time,
                "window": config["window"]
            }
        
        return status


# Global rate limiter instances
rate_limiter = RateLimiter()
per_user_limiter = PerUserRateLimiter()
ip_limiter = IPRateLimiter()
burst_limiter = BurstRateLimiter(tokens_per_second=10.0, burst_size=50)


async def check_rate_limit(user_id: str, operation: str = "api_calls") -> bool:
    """Convenience function to check rate limit."""
    return await per_user_limiter.is_allowed(user_id, operation)


async def check_ip_rate_limit(ip_address: str) -> bool:
    """Convenience function to check IP rate limit."""
    return await ip_limiter.is_allowed(ip_address)


async def get_rate_limit_headers(user_id: str, operation: str = "api_calls") -> Dict[str, str]:
    """Get rate limit headers for response."""
    try:
        remaining = await per_user_limiter.get_remaining_requests(user_id, operation)
        reset_time = await per_user_limiter.get_reset_time(user_id, operation)
        
        headers = {
            "X-RateLimit-Limit": str(per_user_limiter.limits[operation]["limit"]),
            "X-RateLimit-Remaining": str(remaining),
        }
        
        if reset_time:
            headers["X-RateLimit-Reset"] = str(reset_time)
        
        return headers
    except Exception as e:
        logger.error("Failed to get rate limit headers", user_id=user_id, operation=operation, error=str(e))
        return {}


async def clear_user_rate_limits(user_id: str):
    """Clear all rate limits for a user."""
    try:
        async with get_redis_connection() as redis_client:
            keys = await redis_client.keys(f"user:{user_id}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info("Rate limits cleared for user", user_id=user_id, keys_cleared=len(keys))
    except Exception as e:
        logger.error("Failed to clear user rate limits", user_id=user_id, error=str(e))