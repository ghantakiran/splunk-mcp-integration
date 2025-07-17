"""
Rate limiting utilities for Microsoft Teams bot.
"""

import asyncio
import time
from typing import Dict, Optional
import redis.asyncio as redis
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Redis-based rate limiter for Teams bot."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.requests_per_window = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                socket_timeout=settings.redis_timeout,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Rate limiter initialized with Redis")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for rate limiting: {str(e)}")
            logger.info("Falling back to in-memory rate limiting")
            self.redis_client = None
            self._memory_cache = {}
    
    async def cleanup(self):
        """Cleanup Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user is within rate limits.
        
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        if self.redis_client:
            return await self._check_redis_rate_limit(user_id)
        else:
            return await self._check_memory_rate_limit(user_id)
    
    async def _check_redis_rate_limit(self, user_id: str) -> bool:
        """Check rate limit using Redis sliding window."""
        try:
            key = f"teams_rate_limit:{user_id}"
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window_seconds + 1)
            
            results = await pipe.execute()
            current_count = results[1] if len(results) > 1 else 0
            
            # Check if within limits
            if current_count < self.requests_per_window:
                logger.debug(
                    "Rate limit check passed",
                    user_id=user_id,
                    current_count=current_count,
                    limit=self.requests_per_window
                )
                return True
            else:
                logger.warning(
                    "Rate limit exceeded",
                    user_id=user_id,
                    current_count=current_count,
                    limit=self.requests_per_window
                )
                
                # Remove the request we just added since it's rejected
                await self.redis_client.zrem(key, str(current_time))
                return False
                
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            # Fall back to allowing the request
            return True
    
    async def _check_memory_rate_limit(self, user_id: str) -> bool:
        """Check rate limit using in-memory storage (fallback)."""
        try:
            current_time = time.time()
            
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
            
            # Clean expired entries periodically
            if len(self._memory_cache) > 1000:  # Prevent memory leak
                await self._clean_memory_cache()
            
            # Get user's request history
            user_requests = self._memory_cache.get(user_id, [])
            
            # Remove requests outside current window
            window_start = current_time - self.window_seconds
            user_requests = [req_time for req_time in user_requests if req_time > window_start]
            
            # Check if within limits
            if len(user_requests) < self.requests_per_window:
                user_requests.append(current_time)
                self._memory_cache[user_id] = user_requests
                
                logger.debug(
                    "Memory rate limit check passed",
                    user_id=user_id,
                    current_count=len(user_requests) - 1,
                    limit=self.requests_per_window
                )
                return True
            else:
                logger.warning(
                    "Memory rate limit exceeded",
                    user_id=user_id,
                    current_count=len(user_requests),
                    limit=self.requests_per_window
                )
                return False
                
        except Exception as e:
            logger.error(f"Memory rate limit check failed: {str(e)}")
            # Fall back to allowing the request
            return True
    
    async def _clean_memory_cache(self):
        """Clean expired entries from memory cache."""
        try:
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            for user_id in list(self._memory_cache.keys()):
                user_requests = self._memory_cache[user_id]
                user_requests = [req_time for req_time in user_requests if req_time > window_start]
                
                if user_requests:
                    self._memory_cache[user_id] = user_requests
                else:
                    del self._memory_cache[user_id]
                    
        except Exception as e:
            logger.error(f"Failed to clean memory cache: {str(e)}")
    
    async def get_user_rate_limit_status(self, user_id: str) -> Dict[str, any]:
        """Get current rate limit status for a user."""
        try:
            if self.redis_client:
                key = f"teams_rate_limit:{user_id}"
                current_time = time.time()
                window_start = current_time - self.window_seconds
                
                # Count current requests
                count = await self.redis_client.zcount(key, window_start, current_time)
                
                return {
                    "requests_used": count,
                    "requests_limit": self.requests_per_window,
                    "window_seconds": self.window_seconds,
                    "requests_remaining": max(0, self.requests_per_window - count),
                    "reset_time": current_time + self.window_seconds
                }
            else:
                # Memory fallback
                user_requests = self._memory_cache.get(user_id, [])
                current_time = time.time()
                window_start = current_time - self.window_seconds
                
                valid_requests = [req for req in user_requests if req > window_start]
                count = len(valid_requests)
                
                return {
                    "requests_used": count,
                    "requests_limit": self.requests_per_window,
                    "window_seconds": self.window_seconds,
                    "requests_remaining": max(0, self.requests_per_window - count),
                    "reset_time": current_time + self.window_seconds
                }
                
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {str(e)}")
            return {
                "requests_used": 0,
                "requests_limit": self.requests_per_window,
                "window_seconds": self.window_seconds,
                "requests_remaining": self.requests_per_window,
                "reset_time": time.time() + self.window_seconds
            }
    
    async def reset_user_rate_limit(self, user_id: str):
        """Reset rate limit for a specific user (admin function)."""
        try:
            if self.redis_client:
                key = f"teams_rate_limit:{user_id}"
                await self.redis_client.delete(key)
                logger.info(f"Reset rate limit for Teams user {user_id}")
            else:
                if user_id in self._memory_cache:
                    del self._memory_cache[user_id]
                    logger.info(f"Reset memory rate limit for Teams user {user_id}")
                    
        except Exception as e:
            logger.error(f"Failed to reset rate limit for user {user_id}: {str(e)}")
    
    def get_config(self) -> Dict[str, any]:
        """Get current rate limiter configuration."""
        return {
            "requests_per_window": self.requests_per_window,
            "window_seconds": self.window_seconds,
            "backend": "redis" if self.redis_client else "memory",
            "redis_url": settings.redis_url if self.redis_client else None
        }