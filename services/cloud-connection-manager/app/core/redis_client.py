"""
Redis client configuration and setup for Cloud Connection Manager Service.
"""

import logging
import json
from typing import Any, Optional, Dict, List
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[redis.Redis] = None
connection_pool: Optional[ConnectionPool] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client, connection_pool
    
    try:
        # Create connection pool
        connection_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            socket_keepalive=settings.REDIS_SOCKET_KEEPALIVE,
            socket_keepalive_options=settings.REDIS_SOCKET_KEEPALIVE_OPTIONS,
            decode_responses=True
        )
        
        # Create Redis client
        redis_client = redis.Redis(connection_pool=connection_pool)
        
        # Test connection
        await redis_client.ping()
        
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {str(e)}")
        raise


async def close_redis():
    """Close Redis connection."""
    global redis_client, connection_pool
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if connection_pool:
        await connection_pool.disconnect()
        connection_pool = None
    
    logger.info("Redis connections closed")


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    if not redis_client:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    
    return redis_client


class RedisCache:
    """Redis cache utility class."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            serialized_value = json.dumps(value, default=str)
            await self.client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {str(e)}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key."""
        try:
            await self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {str(e)}")
            return False


class RedisRateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (usually user/IP based)
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            import time
            
            now = int(time.time())
            window_start = now - window
            
            # Use Redis pipeline for atomic operations
            pipe = self.client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            current_count = results[1] + 1  # +1 for the current request
            
            return current_count <= limit, current_count
            
        except Exception as e:
            logger.error(f"Rate limiter error for key {key}: {str(e)}")
            # Allow request on error to prevent blocking
            return True, 0


class RedisMetrics:
    """Redis-based metrics collection."""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def increment_counter(self, metric: str, tags: Dict[str, str] = None, 
                              amount: int = 1) -> bool:
        """Increment a counter metric."""
        try:
            key = self._build_metric_key(metric, tags)
            await self.client.incrby(key, amount)
            return True
        except Exception as e:
            logger.error(f"Metrics increment error for {metric}: {str(e)}")
            return False
    
    async def set_gauge(self, metric: str, value: float, 
                       tags: Dict[str, str] = None) -> bool:
        """Set a gauge metric value."""
        try:
            key = self._build_metric_key(metric, tags)
            await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Metrics gauge error for {metric}: {str(e)}")
            return False
    
    async def add_histogram_value(self, metric: str, value: float,
                                 tags: Dict[str, str] = None) -> bool:
        """Add value to histogram metric."""
        try:
            import time
            
            key = self._build_metric_key(metric, tags, "histogram")
            timestamp = int(time.time())
            
            # Store value with timestamp for histogram calculation
            await self.client.zadd(key, {str(value): timestamp})
            
            # Keep only recent values (last hour)
            hour_ago = timestamp - 3600
            await self.client.zremrangebyscore(key, 0, hour_ago)
            
            return True
        except Exception as e:
            logger.error(f"Metrics histogram error for {metric}: {str(e)}")
            return False
    
    async def get_counter(self, metric: str, tags: Dict[str, str] = None) -> int:
        """Get counter value."""
        try:
            key = self._build_metric_key(metric, tags)
            value = await self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Metrics get counter error for {metric}: {str(e)}")
            return 0
    
    async def get_gauge(self, metric: str, tags: Dict[str, str] = None) -> float:
        """Get gauge value."""
        try:
            key = self._build_metric_key(metric, tags)
            value = await self.client.get(key)
            return float(value) if value else 0.0
        except Exception as e:
            logger.error(f"Metrics get gauge error for {metric}: {str(e)}")
            return 0.0
    
    def _build_metric_key(self, metric: str, tags: Dict[str, str] = None,
                         suffix: str = None) -> str:
        """Build Redis key for metric."""
        key_parts = ["metrics", metric]
        
        if tags:
            tag_parts = [f"{k}:{v}" for k, v in sorted(tags.items())]
            key_parts.extend(tag_parts)
        
        if suffix:
            key_parts.append(suffix)
        
        return ":".join(key_parts)


# Health check function
async def check_redis_health() -> bool:
    """Check Redis connectivity."""
    try:
        if not redis_client:
            return False
        
        await redis_client.ping()
        return True
        
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False