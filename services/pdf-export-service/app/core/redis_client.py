"""
Redis client management for PDF Export Service.
"""

import asyncio
import json
from typing import Optional, Any, Dict, List
import redis.asyncio as redis
from redis.asyncio import Redis
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global Redis pool
_redis_pool: Optional[Redis] = None


async def create_redis_pool() -> Redis:
    """Create Redis connection pool."""
    global _redis_pool
    
    if _redis_pool is not None:
        return _redis_pool
    
    logger.info("Creating Redis connection pool", redis_url=settings.REDIS_URL)
    
    try:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=settings.REDIS_TIMEOUT,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            max_connections=20
        )
        
        # Test connection
        await _redis_pool.ping()
        
        logger.info("Redis connection pool created successfully")
        return _redis_pool
        
    except Exception as e:
        logger.error("Failed to create Redis pool", error=str(e))
        raise


async def close_redis_pool():
    """Close Redis connection pool."""
    global _redis_pool
    
    if _redis_pool is not None:
        logger.info("Closing Redis connection pool")
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection pool closed")


def get_redis_pool() -> Optional[Redis]:
    """Get the Redis connection pool."""
    return _redis_pool


@asynccontextmanager
async def get_redis_connection():
    """Get Redis connection from pool."""
    if _redis_pool is None:
        await create_redis_pool()
    
    try:
        yield _redis_pool
    except Exception as e:
        logger.error("Redis connection error", error=str(e))
        raise


class RedisCache:
    """Redis cache wrapper with JSON serialization."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error("Redis get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        try:
            serialized_value = json.dumps(value, default=str)
            return await self.redis.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error("Redis set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.error("Redis delete error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error("Redis exists error", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error("Redis expire error", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error("Redis ttl error", key=key, error=str(e))
            return -1
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.error("Redis keys error", pattern=pattern, error=str(e))
            return []
    
    async def flushdb(self) -> bool:
        """Flush current database."""
        try:
            return await self.redis.flushdb()
        except Exception as e:
            logger.error("Redis flushdb error", error=str(e))
            return False


class RedisQueue:
    """Redis queue implementation."""
    
    def __init__(self, redis_client: Redis, queue_name: str):
        self.redis = redis_client
        self.queue_name = queue_name
    
    async def enqueue(self, item: Any) -> bool:
        """Add item to queue."""
        try:
            serialized_item = json.dumps(item, default=str)
            return await self.redis.lpush(self.queue_name, serialized_item) > 0
        except Exception as e:
            logger.error("Redis enqueue error", queue=self.queue_name, error=str(e))
            return False
    
    async def dequeue(self, timeout: int = 0) -> Optional[Any]:
        """Remove and return item from queue."""
        try:
            if timeout > 0:
                result = await self.redis.brpop(self.queue_name, timeout=timeout)
                if result:
                    return json.loads(result[1])
                return None
            else:
                item = await self.redis.rpop(self.queue_name)
                if item:
                    return json.loads(item)
                return None
        except Exception as e:
            logger.error("Redis dequeue error", queue=self.queue_name, error=str(e))
            return None
    
    async def size(self) -> int:
        """Get queue size."""
        try:
            return await self.redis.llen(self.queue_name)
        except Exception as e:
            logger.error("Redis queue size error", queue=self.queue_name, error=str(e))
            return 0
    
    async def clear(self) -> bool:
        """Clear queue."""
        try:
            return await self.redis.delete(self.queue_name) > 0
        except Exception as e:
            logger.error("Redis queue clear error", queue=self.queue_name, error=str(e))
            return False


class RedisLock:
    """Redis distributed lock implementation."""
    
    def __init__(self, redis_client: Redis, lock_name: str, timeout: int = 10):
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.identifier = None
    
    async def acquire(self) -> bool:
        """Acquire lock."""
        try:
            import uuid
            self.identifier = str(uuid.uuid4())
            
            # Use SET with NX and EX options for atomic operation
            result = await self.redis.set(
                self.lock_name,
                self.identifier,
                nx=True,
                ex=self.timeout
            )
            
            if result:
                logger.debug("Lock acquired", lock=self.lock_name, identifier=self.identifier)
                return True
            else:
                logger.debug("Lock acquisition failed", lock=self.lock_name)
                return False
        except Exception as e:
            logger.error("Redis lock acquire error", lock=self.lock_name, error=str(e))
            return False
    
    async def release(self) -> bool:
        """Release lock."""
        try:
            if self.identifier is None:
                return False
            
            # Use Lua script to ensure atomic check-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, self.lock_name, self.identifier)
            
            if result == 1:
                logger.debug("Lock released", lock=self.lock_name, identifier=self.identifier)
                self.identifier = None
                return True
            else:
                logger.debug("Lock release failed", lock=self.lock_name, identifier=self.identifier)
                return False
        except Exception as e:
            logger.error("Redis lock release error", lock=self.lock_name, error=str(e))
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


async def get_cache() -> RedisCache:
    """Get Redis cache instance."""
    async with get_redis_connection() as redis_client:
        return RedisCache(redis_client)


async def get_queue(queue_name: str) -> RedisQueue:
    """Get Redis queue instance."""
    async with get_redis_connection() as redis_client:
        return RedisQueue(redis_client, queue_name)


async def get_lock(lock_name: str, timeout: int = 10) -> RedisLock:
    """Get Redis lock instance."""
    async with get_redis_connection() as redis_client:
        return RedisLock(redis_client, lock_name, timeout)


async def health_check() -> dict:
    """Check Redis health."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        async with get_redis_connection() as redis_client:
            await redis_client.ping()
            
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }