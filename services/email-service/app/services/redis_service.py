"""
Redis service for Email Service.
"""

import asyncio
from typing import Optional, Any, Dict, List

import redis.asyncio as redis

from app.core.config import settings, get_redis_config
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisService:
    """Redis service for caching and session management."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._pool = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            config = get_redis_config()
            
            # Create connection pool
            self._pool = redis.ConnectionPool.from_url(
                config["url"],
                retry_on_timeout=config["retry_on_timeout"],
                health_check_interval=config["health_check_interval"],
            )
            
            # Create Redis client
            self.client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self.client.ping()
            
            logger.info("Redis service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis service", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup Redis connections."""
        try:
            if self.client:
                await self.client.close()
            if self._pool:
                await self._pool.disconnect()
            logger.info("Redis service cleanup completed")
        except Exception as e:
            logger.error("Error during Redis cleanup", error=str(e))
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a value in Redis."""
        try:
            result = await self.client.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error("Redis set failed", error=str(e), key=key)
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error("Redis get failed", error=str(e), key=key)
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis delete failed", error=str(e), key=key)
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis exists failed", error=str(e), key=key)
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        try:
            result = await self.client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error("Redis expire failed", error=str(e), key=key)
            return False