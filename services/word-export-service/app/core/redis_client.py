#!/usr/bin/env python3
"""
Redis client and utilities for Word Export Service.

This module provides Redis connection management, caching, rate limiting,
and queue management functionality.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection
redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    try:
        redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            ssl=settings.REDIS_SSL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Get Redis client."""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client


class CacheManager:
    """Redis cache manager for Word Export Service."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "word_export_cache:"
    
    def _make_key(self, key: str) -> str:
        """Create cache key with prefix."""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(self._make_key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            serialized_value = json.dumps(value, default=str)
            return await self.redis.setex(
                self._make_key(key),
                ttl,
                serialized_value
            )
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(await self.redis.delete(self._make_key(key)))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self.redis.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter value."""
        try:
            return await self.redis.incr(self._make_key(key), amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            if not keys:
                return {}
            
            cache_keys = [self._make_key(key) for key in keys]
            values = await self.redis.mget(cache_keys)
            
            result = {}
            for i, value in enumerate(values):
                if value:
                    try:
                        result[keys[i]] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to deserialize cached value for key {keys[i]}")
            
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Set multiple values in cache."""
        try:
            pipe = self.redis.pipeline()
            
            for key, value in data.items():
                serialized_value = json.dumps(value, default=str)
                pipe.setex(self._make_key(key), ttl, serialized_value)
            
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            keys = await self.redis.keys(self._make_key(pattern))
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear_pattern error for pattern {pattern}: {e}")
            return 0


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "word_export_rate_limit:"
    
    def _make_key(self, identifier: str, window: str) -> str:
        """Create rate limit key."""
        return f"{self.prefix}{identifier}:{window}"
    
    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        burst_limit: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            Tuple of (allowed, info) where info contains current count and remaining.
        """
        try:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Use current timestamp as score for sorted set
            score = now.timestamp()
            window_start_score = window_start.timestamp()
            
            key = self._make_key(identifier, f"{window_seconds}s")
            
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start_score)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(score): score})
            
            # Set expiration
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Check burst limit first if provided
            if burst_limit and current_count >= burst_limit:
                allowed = False
            else:
                allowed = current_count < limit
            
            info = {
                "current_count": current_count + 1,  # Include current request
                "limit": limit,
                "remaining": max(0, limit - current_count - 1),
                "reset_time": (now + timedelta(seconds=window_seconds)).isoformat(),
                "window_seconds": window_seconds
            }
            
            return allowed, info
            
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            # On error, allow the request
            return True, {
                "current_count": 0,
                "limit": limit,
                "remaining": limit,
                "reset_time": (datetime.utcnow() + timedelta(seconds=window_seconds)).isoformat(),
                "window_seconds": window_seconds
            }
    
    async def get_status(self, identifier: str, window_seconds: int) -> Dict[str, Any]:
        """Get current rate limit status."""
        try:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            window_start_score = window_start.timestamp()
            
            key = self._make_key(identifier, f"{window_seconds}s")
            
            # Remove old entries and count current
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start_score)
            pipe.zcard(key)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return {
                "current_count": current_count,
                "window_seconds": window_seconds,
                "reset_time": (now + timedelta(seconds=window_seconds)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Rate limit status error for {identifier}: {e}")
            return {
                "current_count": 0,
                "window_seconds": window_seconds,
                "reset_time": (datetime.utcnow() + timedelta(seconds=window_seconds)).isoformat()
            }


class QueueManager:
    """Redis-based queue manager for job processing."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_prefix = "word_export_queue:"
        self.processing_prefix = "word_export_processing:"
    
    def _make_queue_key(self, queue_name: str) -> str:
        """Create queue key."""
        return f"{self.queue_prefix}{queue_name}"
    
    def _make_processing_key(self, queue_name: str) -> str:
        """Create processing set key."""
        return f"{self.processing_prefix}{queue_name}"
    
    async def enqueue(self, queue_name: str, job_data: Dict[str, Any]) -> bool:
        """Add job to queue."""
        try:
            job_json = json.dumps(job_data, default=str)
            await self.redis.lpush(self._make_queue_key(queue_name), job_json)
            
            logger.info(f"Job {job_data.get('job_id')} enqueued to {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Queue enqueue error for {queue_name}: {e}")
            return False
    
    async def dequeue(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get job from queue with blocking pop."""
        try:
            result = await self.redis.brpop(
                self._make_queue_key(queue_name),
                timeout=timeout
            )
            
            if result:
                _, job_json = result
                job_data = json.loads(job_json)
                
                # Move to processing set
                await self.redis.sadd(
                    self._make_processing_key(queue_name),
                    json.dumps(job_data, default=str)
                )
                
                logger.info(f"Job {job_data.get('job_id')} dequeued from {queue_name}")
                return job_data
            
            return None
        except Exception as e:
            logger.error(f"Queue dequeue error for {queue_name}: {e}")
            return None
    
    async def complete_job(self, queue_name: str, job_data: Dict[str, Any]) -> bool:
        """Mark job as completed and remove from processing."""
        try:
            job_json = json.dumps(job_data, default=str)
            removed = await self.redis.srem(
                self._make_processing_key(queue_name),
                job_json
            )
            
            if removed:
                logger.info(f"Job {job_data.get('job_id')} completed and removed from processing")
            
            return bool(removed)
        except Exception as e:
            logger.error(f"Queue complete_job error for {queue_name}: {e}")
            return False
    
    async def get_queue_size(self, queue_name: str = "default") -> Dict[str, int]:
        """Get queue and processing set sizes."""
        try:
            pipe = self.redis.pipeline()
            pipe.llen(self._make_queue_key(queue_name))
            pipe.scard(self._make_processing_key(queue_name))
            
            results = await pipe.execute()
            pending = results[0]
            processing = results[1]
            
            return {
                "pending": pending,
                "processing": processing,
                "total": pending + processing
            }
        except Exception as e:
            logger.error(f"Queue size error for {queue_name}: {e}")
            return {"pending": 0, "processing": 0, "total": 0}
    
    async def clear_queue(self, queue_name: str) -> bool:
        """Clear all jobs from queue and processing set."""
        try:
            pipe = self.redis.pipeline()
            pipe.delete(self._make_queue_key(queue_name))
            pipe.delete(self._make_processing_key(queue_name))
            
            await pipe.execute()
            logger.info(f"Queue {queue_name} cleared")
            return True
        except Exception as e:
            logger.error(f"Queue clear error for {queue_name}: {e}")
            return False


# Global manager instances
cache_manager: Optional[CacheManager] = None
rate_limiter: Optional[RateLimiter] = None
queue_manager: Optional[QueueManager] = None


def get_cache_manager() -> CacheManager:
    """Get cache manager instance."""
    global cache_manager
    
    if not cache_manager:
        cache_manager = CacheManager(get_redis())
    
    return cache_manager


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    global rate_limiter
    
    if not rate_limiter:
        rate_limiter = RateLimiter(get_redis())
    
    return rate_limiter


def get_queue_manager() -> QueueManager:
    """Get queue manager instance."""
    global queue_manager
    
    if not queue_manager:
        queue_manager = QueueManager(get_redis())
    
    return queue_manager


# Export commonly used functions and classes
__all__ = [
    "init_redis",
    "close_redis",
    "get_redis",
    "get_cache_manager",
    "get_rate_limiter",
    "get_queue_manager",
    "CacheManager",
    "RateLimiter",
    "QueueManager"
]