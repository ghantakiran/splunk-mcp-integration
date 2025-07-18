"""
Rate limiting utilities.
"""

import asyncio
import logging
import time
from typing import Optional

from app.core.redis_client import get_redis_connection
from app.core.config import settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self):
        self.window_size = 60  # 1 minute window
        self.max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.burst_size = settings.RATE_LIMIT_BURST
    
    async def is_allowed(
        self, 
        key: str, 
        limit: Optional[int] = None, 
        window: Optional[int] = None
    ) -> bool:
        """Check if request is allowed."""
        try:
            limit = limit or self.max_requests
            window = window or self.window_size
            
            async with get_redis_connection() as redis:
                # Use sliding window algorithm
                now = time.time()
                pipeline = redis.pipeline()
                
                # Remove old entries
                pipeline.zremrangebyscore(key, 0, now - window)
                
                # Count current requests
                pipeline.zcard(key)
                
                # Execute pipeline
                results = await pipeline.execute()
                current_requests = results[1]
                
                if current_requests >= limit:
                    return False
                
                # Add current request
                await redis.zadd(key, {str(now): now})
                await redis.expire(key, window)
                
                return True
                
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Allow request if rate limiter fails
            return True
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for key."""
        try:
            async with get_redis_connection() as redis:
                await redis.delete(key)
        except Exception as e:
            logger.error(f"Rate limiter reset error: {e}")
    
    async def get_remaining(self, key: str, limit: Optional[int] = None) -> int:
        """Get remaining requests for key."""
        try:
            limit = limit or self.max_requests
            
            async with get_redis_connection() as redis:
                # Remove old entries
                now = time.time()
                await redis.zremrangebyscore(key, 0, now - self.window_size)
                
                # Count current requests
                current_requests = await redis.zcard(key)
                
                return max(0, limit - current_requests)
                
        except Exception as e:
            logger.error(f"Rate limiter get remaining error: {e}")
            return limit or self.max_requests


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    key: str, 
    limit: Optional[int] = None, 
    window: Optional[int] = None
) -> bool:
    """Check if request is within rate limit."""
    return await rate_limiter.is_allowed(key, limit, window)