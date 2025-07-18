#!/usr/bin/env python3
"""
Redis client configuration and connection management for PowerPoint Export Service.

This module handles Redis connections for caching, rate limiting, and job queues.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional, Union

import aioredis
from aioredis import Redis
from structlog import get_logger

from app.core.config import settings


logger = get_logger(__name__)


class RedisManager:
    """Redis connection manager."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self._lock = asyncio.Lock()
    
    async def create_connection(self) -> Redis:
        """Create Redis connection."""
        if self.redis is None:
            async with self._lock:
                if self.redis is None:
                    try:
                        self.redis = await aioredis.from_url(
                            settings.REDIS_URL,
                            db=settings.REDIS_DB,
                            password=settings.REDIS_PASSWORD,
                            ssl=settings.REDIS_SSL,
                            decode_responses=True,
                            max_connections=20,
                            retry_on_timeout=True
                        )
                        # Test connection
                        await self.redis.ping()
                        logger.info("Redis connection created successfully")
                    except Exception as e:
                        logger.error("Failed to create Redis connection", error=str(e))
                        raise
        return self.redis
    
    async def close_connection(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Redis connection closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Redis, None]:
        """Get Redis connection context manager."""
        if not self.redis:
            await self.create_connection()
        
        try:
            yield self.redis
        except Exception as e:
            logger.error("Redis connection error", error=str(e))
            raise
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        async with self.get_connection() as redis:
            try:
                result = await redis.set(key, value, ex=ex)
                return bool(result)
            except Exception as e:
                logger.error("Redis SET failed", key=key, error=str(e))
                raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key from Redis."""
        async with self.get_connection() as redis:
            try:
                return await redis.get(key)
            except Exception as e:
                logger.error("Redis GET failed", key=key, error=str(e))
                raise
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        async with self.get_connection() as redis:
            try:
                return await redis.delete(*keys)
            except Exception as e:
                logger.error("Redis DELETE failed", keys=keys, error=str(e))
                raise
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        async with self.get_connection() as redis:
            try:
                result = await redis.exists(key)
                return bool(result)
            except Exception as e:
                logger.error("Redis EXISTS failed", key=key, error=str(e))
                raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key."""
        async with self.get_connection() as redis:
            try:
                result = await redis.expire(key, seconds)
                return bool(result)
            except Exception as e:
                logger.error("Redis EXPIRE failed", key=key, error=str(e))
                raise
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key's value."""
        async with self.get_connection() as redis:
            try:
                return await redis.incr(key, amount)
            except Exception as e:
                logger.error("Redis INCR failed", key=key, error=str(e))
                raise
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a key's value."""
        async with self.get_connection() as redis:
            try:
                return await redis.decr(key, amount)
            except Exception as e:
                logger.error("Redis DECR failed", key=key, error=str(e))
                raise
    
    async def hset(self, name: str, mapping: dict) -> int:
        """Set hash fields."""
        async with self.get_connection() as redis:
            try:
                return await redis.hset(name, mapping=mapping)
            except Exception as e:
                logger.error("Redis HSET failed", name=name, error=str(e))
                raise
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        async with self.get_connection() as redis:
            try:
                return await redis.hget(name, key)
            except Exception as e:
                logger.error("Redis HGET failed", name=name, key=key, error=str(e))
                raise
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields and values."""
        async with self.get_connection() as redis:
            try:
                return await redis.hgetall(name)
            except Exception as e:
                logger.error("Redis HGETALL failed", name=name, error=str(e))
                raise
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        async with self.get_connection() as redis:
            try:
                return await redis.hdel(name, *keys)
            except Exception as e:
                logger.error("Redis HDEL failed", name=name, keys=keys, error=str(e))
                raise
    
    async def lpush(self, name: str, *values: str) -> int:
        """Push values to the left of a list."""
        async with self.get_connection() as redis:
            try:
                return await redis.lpush(name, *values)
            except Exception as e:
                logger.error("Redis LPUSH failed", name=name, error=str(e))
                raise
    
    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from the right of a list."""
        async with self.get_connection() as redis:
            try:
                return await redis.rpop(name)
            except Exception as e:
                logger.error("Redis RPOP failed", name=name, error=str(e))
                raise
    
    async def llen(self, name: str) -> int:
        """Get list length."""
        async with self.get_connection() as redis:
            try:
                return await redis.llen(name)
            except Exception as e:
                logger.error("Redis LLEN failed", name=name, error=str(e))
                raise


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions
async def init_redis() -> None:
    """Initialize Redis connection."""
    await redis_manager.create_connection()
    logger.info("Redis initialized")


async def close_redis() -> None:
    """Close Redis connection."""
    await redis_manager.close_connection()
    logger.info("Redis closed")


@asynccontextmanager
async def get_redis_connection() -> AsyncGenerator[Redis, None]:
    """Get Redis connection context manager."""
    async with redis_manager.get_connection() as redis:
        yield redis


# Cache utilities
class CacheManager:
    """Cache management utilities."""
    
    @staticmethod
    def make_cache_key(prefix: str, *args: Union[str, int]) -> str:
        """Create a cache key from prefix and arguments."""
        key_parts = [str(prefix)] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    @staticmethod
    async def get_cached(key: str) -> Optional[str]:
        """Get cached value."""
        return await redis_manager.get(key)
    
    @staticmethod
    async def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL."""
        return await redis_manager.set(key, str(value), ex=ttl)
    
    @staticmethod
    async def delete_cached(*keys: str) -> int:
        """Delete cached values."""
        return await redis_manager.delete(*keys)
    
    @staticmethod
    async def cache_exists(key: str) -> bool:
        """Check if cache key exists."""
        return await redis_manager.exists(key)


# Rate limiting utilities
class RateLimiter:
    """Rate limiting utilities using sliding window algorithm."""
    
    @staticmethod
    async def check_rate_limit(
        identifier: str,
        limit: int,
        window: int,
        burst: Optional[int] = None
    ) -> tuple[bool, dict]:
        """Check if request is within rate limit."""
        now = int(asyncio.get_event_loop().time())
        key = f"rate_limit:{identifier}"
        
        async with get_redis_connection() as redis:
            # Use sliding window algorithm
            pipe = redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Check burst limit
            if burst and current_count > burst:
                return False, {
                    "allowed": False,
                    "count": current_count,
                    "limit": limit,
                    "burst": burst,
                    "reset_at": now + window
                }
            
            # Check rate limit
            allowed = current_count <= limit
            
            return allowed, {
                "allowed": allowed,
                "count": current_count,
                "limit": limit,
                "burst": burst,
                "reset_at": now + window
            }


# Job queue utilities
class JobQueue:
    """Job queue utilities."""
    
    @staticmethod
    async def enqueue_job(queue_name: str, job_data: str) -> int:
        """Enqueue a job."""
        return await redis_manager.lpush(queue_name, job_data)
    
    @staticmethod
    async def dequeue_job(queue_name: str) -> Optional[str]:
        """Dequeue a job."""
        return await redis_manager.rpop(queue_name)
    
    @staticmethod
    async def queue_length(queue_name: str) -> int:
        """Get queue length."""
        return await redis_manager.llen(queue_name)


# Export commonly used functions and classes
__all__ = [
    "init_redis",
    "close_redis",
    "get_redis_connection",
    "redis_manager",
    "CacheManager",
    "RateLimiter",
    "JobQueue"
]
