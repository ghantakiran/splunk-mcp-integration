"""
Redis client configuration and connection management for ITSM Service.
"""

import asyncio
from typing import Optional, Any, Dict
import redis.asyncio as redis
from contextlib import asynccontextmanager

from .config import get_redis_config
from .logging import get_logger

logger = get_logger(__name__)

# Redis configuration
redis_config = get_redis_config()

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global _redis_client
    
    try:
        _redis_client = redis.from_url(
            redis_config["url"],
            socket_timeout=redis_config["timeout"],
            retry_on_timeout=redis_config["retry_on_timeout"],
            health_check_interval=redis_config["health_check_interval"],
            decode_responses=True,
        )
        
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client
    
    if _redis_client is None:
        await init_redis()
    
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


@asynccontextmanager
async def get_redis_session():
    """Get Redis session context manager."""
    client = await get_redis_client()
    try:
        yield client
    except Exception as e:
        logger.error(f"Redis operation failed: {e}")
        raise


async def check_redis_connection() -> bool:
    """Check Redis connection health."""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception:
        return False


class RedisRateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        burst: int = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window: Time window in seconds
            burst: Maximum burst requests (optional)
        
        Returns:
            Tuple of (allowed, info_dict)
        """
        now = asyncio.get_event_loop().time()
        pipeline = self.client.pipeline()
        
        # Sliding window key
        window_key = f"rate_limit:{key}:{int(now // window)}"
        
        # Get current count
        pipeline.get(window_key)
        
        # Get previous window count (for sliding window)
        prev_window_key = f"rate_limit:{key}:{int(now // window) - 1}"
        pipeline.get(prev_window_key)
        
        results = await pipeline.execute()
        current_count = int(results[0] or 0)
        prev_count = int(results[1] or 0)
        
        # Calculate sliding window count
        window_start = int(now // window) * window
        elapsed = now - window_start
        prev_weight = (window - elapsed) / window
        sliding_count = current_count + (prev_count * prev_weight)
        
        # Check burst limit if specified
        if burst and current_count >= burst:
            return False, {
                "allowed": False,
                "current_count": current_count,
                "sliding_count": sliding_count,
                "limit": limit,
                "window": window,
                "burst": burst,
                "reason": "burst_limit_exceeded"
            }
        
        # Check rate limit
        if sliding_count >= limit:
            return False, {
                "allowed": False,
                "current_count": current_count,
                "sliding_count": sliding_count,
                "limit": limit,
                "window": window,
                "burst": burst,
                "reason": "rate_limit_exceeded"
            }
        
        # Increment counter
        pipeline = self.client.pipeline()
        pipeline.incr(window_key)
        pipeline.expire(window_key, window * 2)  # Keep for 2 windows
        await pipeline.execute()
        
        return True, {
            "allowed": True,
            "current_count": current_count + 1,
            "sliding_count": sliding_count + 1,
            "limit": limit,
            "window": window,
            "burst": burst,
            "remaining": max(0, limit - sliding_count - 1)
        }


class RedisCache:
    """Redis-based caching utilities."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: int = None
    ) -> bool:
        """Set value in cache."""
        try:
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache."""
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key."""
        try:
            await self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            return False


class RedisQueue:
    """Redis-based queue for ITSM operations."""
    
    def __init__(self, client: redis.Redis, queue_name: str):
        self.client = client
        self.queue_name = queue_name
    
    async def push(self, item: str) -> bool:
        """Push item to queue."""
        try:
            await self.client.lpush(self.queue_name, item)
            return True
        except Exception as e:
            logger.error(f"Queue push failed: {e}")
            return False
    
    async def pop(self, timeout: int = 0) -> Optional[str]:
        """Pop item from queue (blocking)."""
        try:
            result = await self.client.brpop(self.queue_name, timeout=timeout)
            if result:
                return result[1]
            return None
        except Exception as e:
            logger.error(f"Queue pop failed: {e}")
            return None
    
    async def size(self) -> int:
        """Get queue size."""
        try:
            return await self.client.llen(self.queue_name)
        except Exception as e:
            logger.error(f"Queue size check failed: {e}")
            return 0
    
    async def clear(self) -> bool:
        """Clear queue."""
        try:
            await self.client.delete(self.queue_name)
            return True
        except Exception as e:
            logger.error(f"Queue clear failed: {e}")
            return False


class RedisLock:
    """Redis-based distributed lock."""
    
    def __init__(self, client: redis.Redis, key: str, timeout: int = 30):
        self.client = client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.identifier = None
    
    async def acquire(self) -> bool:
        """Acquire lock."""
        import uuid
        self.identifier = str(uuid.uuid4())
        
        try:
            result = await self.client.set(
                self.key,
                self.identifier,
                nx=True,
                ex=self.timeout
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
            return False
    
    async def release(self) -> bool:
        """Release lock."""
        if not self.identifier:
            return False
        
        try:
            # Use Lua script to ensure atomic compare-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await self.client.eval(lua_script, 1, self.key, self.identifier)
            return bool(result)
        except Exception as e:
            logger.error(f"Lock release failed: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        if await self.acquire():
            return self
        raise Exception("Failed to acquire lock")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()