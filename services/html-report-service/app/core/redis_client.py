#!/usr/bin/env python3
"""
Redis client configuration and utilities for HTML Report Service.

This module provides Redis connectivity, caching, rate limiting,
and queue management for the HTML report service.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import redis.asyncio as redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

# Global Redis connection
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    
    try:
        # Parse Redis URL
        redis_url = urlparse(settings.REDIS_URL)
        
        # Create Redis connection
        redis_client = redis.Redis(
            host=redis_url.hostname or "localhost",
            port=redis_url.port or 6379,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            ssl=settings.REDIS_SSL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


# Cache utilities
class CacheManager:
    """Cache management utilities."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "html_report"
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}:{key}"
    
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
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self.redis.setex(self._make_key(key), ttl, serialized)
            else:
                await self.redis.set(self._make_key(key), serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            result = await self.redis.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            result = await self.redis.exists(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache."""
        try:
            result = await self.redis.incrby(self._make_key(key), amount)
            return result
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key."""
        try:
            result = await self.redis.expire(self._make_key(key), ttl)
            return result
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False


# Rate limiting utilities
class RateLimiter:
    """Rate limiting utilities using sliding window algorithm."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "rate_limit"
    
    def _make_key(self, identifier: str) -> str:
        """Create a rate limit key."""
        return f"{self.prefix}:{identifier}"
    
    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int
    ) -> bool:
        """Check if request is allowed under rate limit."""
        try:
            key = self._make_key(identifier)
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use a pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return current_count < limit
            
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return True
    
    async def get_usage(
        self,
        identifier: str,
        window_seconds: int
    ) -> Dict[str, int]:
        """Get current rate limit usage."""
        try:
            key = self._make_key(identifier)
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Remove old entries and count current
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return {
                "current_count": current_count,
                "window_seconds": window_seconds,
                "window_start": window_start,
                "current_time": current_time
            }
            
        except Exception as e:
            logger.error(f"Rate limit usage error for {identifier}: {e}")
            return {
                "current_count": 0,
                "window_seconds": window_seconds,
                "window_start": 0,
                "current_time": int(time.time())
            }


# Queue utilities
class QueueManager:
    """Queue management utilities for background jobs."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_name = "html_report_queue"
        self.processing_queue = "html_report_processing"
    
    async def enqueue(self, job_data: Dict[str, Any]) -> bool:
        """Add job to queue."""
        try:
            serialized = json.dumps(job_data, default=str)
            await self.redis.lpush(self.queue_name, serialized)
            return True
        except Exception as e:
            logger.error(f"Queue enqueue error: {e}")
            return False
    
    async def dequeue(self, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Get job from queue (blocking)."""
        try:
            if timeout > 0:
                result = await self.redis.brpoplpush(
                    self.queue_name,
                    self.processing_queue,
                    timeout
                )
            else:
                result = await self.redis.rpoplpush(
                    self.queue_name,
                    self.processing_queue
                )
            
            if result:
                return json.loads(result)
            return None
            
        except Exception as e:
            logger.error(f"Queue dequeue error: {e}")
            return None
    
    async def complete_job(self, job_data: Dict[str, Any]) -> bool:
        """Mark job as completed and remove from processing queue."""
        try:
            serialized = json.dumps(job_data, default=str)
            result = await self.redis.lrem(self.processing_queue, 1, serialized)
            return result > 0
        except Exception as e:
            logger.error(f"Queue complete error: {e}")
            return False
    
    async def get_queue_size(self) -> Dict[str, int]:
        """Get queue sizes."""
        try:
            queue_size = await self.redis.llen(self.queue_name)
            processing_size = await self.redis.llen(self.processing_queue)
            
            return {
                "pending": queue_size,
                "processing": processing_size,
                "total": queue_size + processing_size
            }
        except Exception as e:
            logger.error(f"Queue size error: {e}")
            return {"pending": 0, "processing": 0, "total": 0}


# Session utilities
class SessionManager:
    """Session management utilities."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "session"
        self.default_ttl = 3600  # 1 hour
    
    def _make_key(self, session_id: str) -> str:
        """Create a session key."""
        return f"{self.prefix}:{session_id}"
    
    async def create_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Create a new session."""
        try:
            key = self._make_key(session_id)
            serialized = json.dumps(data, default=str)
            ttl = ttl or self.default_ttl
            
            await self.redis.setex(key, ttl, serialized)
            return True
            
        except Exception as e:
            logger.error(f"Session create error for {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        try:
            key = self._make_key(session_id)
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Session get error for {session_id}: {e}")
            return None
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """Update session data."""
        try:
            key = self._make_key(session_id)
            serialized = json.dumps(data, default=str)
            
            if extend_ttl:
                await self.redis.setex(key, self.default_ttl, serialized)
            else:
                await self.redis.set(key, serialized, keepttl=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Session update error for {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            key = self._make_key(session_id)
            result = await self.redis.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Session delete error for {session_id}: {e}")
            return False


# Global utility instances
cache_manager: Optional[CacheManager] = None
rate_limiter: Optional[RateLimiter] = None
queue_manager: Optional[QueueManager] = None
session_manager: Optional[SessionManager] = None


def get_cache_manager() -> CacheManager:
    """Get cache manager instance."""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager(get_redis())
    return cache_manager


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter(get_redis())
    return rate_limiter


def get_queue_manager() -> QueueManager:
    """Get queue manager instance."""
    global queue_manager
    if queue_manager is None:
        queue_manager = QueueManager(get_redis())
    return queue_manager


def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    global session_manager
    if session_manager is None:
        session_manager = SessionManager(get_redis())
    return session_manager


# Export commonly used components
__all__ = [
    "init_redis",
    "close_redis",
    "get_redis",
    "CacheManager",
    "RateLimiter",
    "QueueManager",
    "SessionManager",
    "get_cache_manager",
    "get_rate_limiter",
    "get_queue_manager",
    "get_session_manager"
]
