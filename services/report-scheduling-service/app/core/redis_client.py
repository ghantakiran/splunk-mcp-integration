"""
Redis client configuration and utilities for the Report Scheduling Service.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with specialized methods for report scheduling."""
    
    def __init__(self):
        self.pool = None
        self.client = None
    
    async def connect(self):
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=True,
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set key-value pair with optional expiration."""
        try:
            return await self.client.set(key, value, ex=ex, nx=nx)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            return None
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value."""
        try:
            return await self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}, key {key}: {e}")
            return 0
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields and values."""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}
    
    async def lpush(self, name: str, *values: str) -> int:
        """Push values to left of list."""
        try:
            return await self.client.lpush(name, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for list {name}: {e}")
            return 0
    
    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from right of list."""
        try:
            return await self.client.rpop(name)
        except Exception as e:
            logger.error(f"Redis RPOP error for list {name}: {e}")
            return None
    
    async def llen(self, name: str) -> int:
        """Get list length."""
        try:
            return await self.client.llen(name)
        except Exception as e:
            logger.error(f"Redis LLEN error for list {name}: {e}")
            return 0
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add values to set."""
        try:
            return await self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD error for set {name}: {e}")
            return 0
    
    async def srem(self, name: str, *values: str) -> int:
        """Remove values from set."""
        try:
            return await self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Redis SREM error for set {name}: {e}")
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get all set members."""
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for set {name}: {e}")
            return set()
    
    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is set member."""
        try:
            return await self.client.sismember(name, value)
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for set {name}, value {value}: {e}")
            return False
    
    async def incr(self, name: str, amount: int = 1) -> int:
        """Increment key value."""
        try:
            return await self.client.incr(name, amount)
        except Exception as e:
            logger.error(f"Redis INCR error for key {name}: {e}")
            return 0
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            response = await self.client.ping()
            return response is True
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False
    
    # Specialized methods for report scheduling
    
    async def cache_schedule_result(
        self,
        schedule_id: str,
        result: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache schedule execution result."""
        try:
            key = f"schedule_result:{schedule_id}"
            value = json.dumps(result, default=str)
            return await self.set(key, value, ex=ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to cache schedule result: {e}")
            return False
    
    async def get_cached_schedule_result(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get cached schedule execution result."""
        try:
            key = f"schedule_result:{schedule_id}"
            cached = await self.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached schedule result: {e}")
            return None
    
    async def add_to_execution_queue(self, execution_id: str, priority: str = "medium") -> bool:
        """Add execution to processing queue."""
        try:
            queue_name = f"execution_queue:{priority}"
            execution_data = {
                "execution_id": execution_id,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "priority": priority
            }
            return await self.lpush(queue_name, json.dumps(execution_data))
        except Exception as e:
            logger.error(f"Failed to add execution to queue: {e}")
            return False
    
    async def get_next_execution(self, priority: str = "medium") -> Optional[Dict[str, Any]]:
        """Get next execution from queue."""
        try:
            queue_name = f"execution_queue:{priority}"
            execution_json = await self.rpop(queue_name)
            if execution_json:
                return json.loads(execution_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get next execution: {e}")
            return None
    
    async def get_queue_length(self, priority: str = "medium") -> int:
        """Get execution queue length."""
        try:
            queue_name = f"execution_queue:{priority}"
            return await self.llen(queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def track_active_schedule(self, schedule_id: str) -> bool:
        """Track active schedule."""
        try:
            return await self.sadd("active_schedules", schedule_id)
        except Exception as e:
            logger.error(f"Failed to track active schedule: {e}")
            return False
    
    async def remove_active_schedule(self, schedule_id: str) -> bool:
        """Remove schedule from active tracking."""
        try:
            return await self.srem("active_schedules", schedule_id)
        except Exception as e:
            logger.error(f"Failed to remove active schedule: {e}")
            return False
    
    async def get_active_schedules(self) -> set:
        """Get all active schedules."""
        try:
            return await self.smembers("active_schedules")
        except Exception as e:
            logger.error(f"Failed to get active schedules: {e}")
            return set()
    
    async def update_schedule_metrics(self, schedule_id: str, metrics: Dict[str, Any]) -> bool:
        """Update schedule performance metrics."""
        try:
            key = f"schedule_metrics:{schedule_id}"
            for field, value in metrics.items():
                await self.hset(key, field, str(value))
            # Set expiration for metrics (7 days)
            await self.expire(key, 7 * 24 * 3600)
            return True
        except Exception as e:
            logger.error(f"Failed to update schedule metrics: {e}")
            return False
    
    async def get_schedule_metrics(self, schedule_id: str) -> Dict[str, str]:
        """Get schedule performance metrics."""
        try:
            key = f"schedule_metrics:{schedule_id}"
            return await self.hgetall(key)
        except Exception as e:
            logger.error(f"Failed to get schedule metrics: {e}")
            return {}
    
    async def increment_execution_counter(self, counter_type: str) -> int:
        """Increment execution counter."""
        try:
            key = f"execution_counter:{counter_type}:{datetime.now().strftime('%Y-%m-%d')}"
            count = await self.incr(key)
            # Set expiration for daily counters (30 days)
            await self.expire(key, 30 * 24 * 3600)
            return count
        except Exception as e:
            logger.error(f"Failed to increment execution counter: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Get Redis client instance."""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client


async def close_redis_client():
    """Close Redis client connection."""
    await redis_client.close()