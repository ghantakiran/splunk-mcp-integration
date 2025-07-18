"""
Redis client configuration and connection management for BI Integration Service.
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


async def get_redis_health() -> dict:
    """Get Redis health status."""
    try:
        client = await get_redis_client()
        await client.ping()
        
        # Get Redis info
        info = await client.info()
        
        return {
            "status": "healthy",
            "connection": "active",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "url": redis_config["url"].split("@")[-1] if "@" in redis_config["url"] else "***"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }


class RedisBICache:
    """Redis-based caching utilities for BI operations."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
        self.key_prefix = "bi:"
    
    async def cache_workbook_metadata(
        self,
        workbook_id: str,
        metadata: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """Cache workbook metadata."""
        try:
            key = f"{self.key_prefix}workbook:{workbook_id}"
            await self.client.setex(key, ttl, str(metadata))
            return True
        except Exception as e:
            logger.error(f"Failed to cache workbook metadata: {e}")
            return False
    
    async def get_workbook_metadata(self, workbook_id: str) -> Optional[Dict[str, Any]]:
        """Get cached workbook metadata."""
        try:
            key = f"{self.key_prefix}workbook:{workbook_id}"
            data = await self.client.get(key)
            if data:
                import json
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get workbook metadata: {e}")
            return None
    
    async def cache_data_source_schema(
        self,
        data_source_id: str,
        schema: Dict[str, Any],
        ttl: int = 7200
    ) -> bool:
        """Cache data source schema."""
        try:
            key = f"{self.key_prefix}schema:{data_source_id}"
            await self.client.setex(key, ttl, str(schema))
            return True
        except Exception as e:
            logger.error(f"Failed to cache data source schema: {e}")
            return False
    
    async def get_data_source_schema(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        """Get cached data source schema."""
        try:
            key = f"{self.key_prefix}schema:{data_source_id}"
            data = await self.client.get(key)
            if data:
                import json
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get data source schema: {e}")
            return None
    
    async def cache_refresh_status(
        self,
        refresh_id: str,
        status: Dict[str, Any],
        ttl: int = 1800
    ) -> bool:
        """Cache refresh task status."""
        try:
            key = f"{self.key_prefix}refresh:{refresh_id}"
            await self.client.setex(key, ttl, str(status))
            return True
        except Exception as e:
            logger.error(f"Failed to cache refresh status: {e}")
            return False
    
    async def get_refresh_status(self, refresh_id: str) -> Optional[Dict[str, Any]]:
        """Get cached refresh task status."""
        try:
            key = f"{self.key_prefix}refresh:{refresh_id}"
            data = await self.client.get(key)
            if data:
                import json
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get refresh status: {e}")
            return None
    
    async def invalidate_workbook_cache(self, workbook_id: str) -> bool:
        """Invalidate workbook-related cache entries."""
        try:
            keys_to_delete = [
                f"{self.key_prefix}workbook:{workbook_id}",
                f"{self.key_prefix}workbook:{workbook_id}:*"
            ]
            
            for key_pattern in keys_to_delete:
                if "*" in key_pattern:
                    keys = await self.client.keys(key_pattern)
                    if keys:
                        await self.client.delete(*keys)
                else:
                    await self.client.delete(key_pattern)
            
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate workbook cache: {e}")
            return False


class RedisBIQueue:
    """Redis-based queue for BI background tasks."""
    
    def __init__(self, client: redis.Redis, queue_name: str = "bi_tasks"):
        self.client = client
        self.queue_name = queue_name
    
    async def enqueue_publish_task(
        self,
        workbook_id: str,
        project_id: str,
        user_id: str,
        options: Dict[str, Any] = None
    ) -> bool:
        """Enqueue a workbook publish task."""
        try:
            task = {
                "type": "publish_workbook",
                "workbook_id": workbook_id,
                "project_id": project_id,
                "user_id": user_id,
                "options": options or {},
                "created_at": asyncio.get_event_loop().time()
            }
            
            import json
            await self.client.lpush(self.queue_name, json.dumps(task))
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue publish task: {e}")
            return False
    
    async def enqueue_refresh_task(
        self,
        data_source_id: str,
        refresh_type: str,
        user_id: str,
        options: Dict[str, Any] = None
    ) -> bool:
        """Enqueue a data source refresh task."""
        try:
            task = {
                "type": "refresh_data_source",
                "data_source_id": data_source_id,
                "refresh_type": refresh_type,
                "user_id": user_id,
                "options": options or {},
                "created_at": asyncio.get_event_loop().time()
            }
            
            import json
            await self.client.lpush(self.queue_name, json.dumps(task))
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue refresh task: {e}")
            return False
    
    async def dequeue_task(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Dequeue a task from the queue."""
        try:
            result = await self.client.brpop(self.queue_name, timeout=timeout)
            if result:
                import json
                return json.loads(result[1])
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None
    
    async def get_queue_size(self) -> int:
        """Get the number of tasks in the queue."""
        try:
            return await self.client.llen(self.queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0


class RedisBILock:
    """Redis-based distributed lock for BI operations."""
    
    def __init__(self, client: redis.Redis, lock_name: str, timeout: int = 300):
        self.client = client
        self.lock_key = f"bi:lock:{lock_name}"
        self.timeout = timeout
        self.identifier = None
    
    async def acquire(self) -> bool:
        """Acquire the lock."""
        import uuid
        self.identifier = str(uuid.uuid4())
        
        try:
            result = await self.client.set(
                self.lock_key,
                self.identifier,
                nx=True,
                ex=self.timeout
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
            return False
    
    async def release(self) -> bool:
        """Release the lock."""
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
            result = await self.client.eval(lua_script, 1, self.lock_key, self.identifier)
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


class RedisBIRateLimiter:
    """Redis-based rate limiter for BI API calls."""
    
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
            key: Rate limit key (e.g., user_id, integration_id)
            limit: Maximum requests per window
            window: Time window in seconds
            burst: Maximum burst requests (optional)
        
        Returns:
            Tuple of (allowed, info_dict)
        """
        now = asyncio.get_event_loop().time()
        pipeline = self.client.pipeline()
        
        # Rate limit key
        rate_key = f"bi:rate_limit:{key}:{int(now // window)}"
        
        # Get current count
        pipeline.get(rate_key)
        
        # Get previous window count (for sliding window)
        prev_rate_key = f"bi:rate_limit:{key}:{int(now // window) - 1}"
        pipeline.get(prev_rate_key)
        
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
        pipeline.incr(rate_key)
        pipeline.expire(rate_key, window * 2)  # Keep for 2 windows
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