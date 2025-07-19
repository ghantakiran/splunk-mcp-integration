"""
Redis client configuration and management.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as aioredis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

# Global Redis client
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    logger.info("Initializing Redis connection")
    
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
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
        logger.info("Closing Redis connection")
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    """Get Redis client."""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client


class CacheManager:
    """Cache management utilities."""
    
    def __init__(self):
        self.redis = get_redis()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        try:
            return await self.redis.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key: {key}")
        return None
    
    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expire)
        except Exception as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False


class RateLimiter:
    """Rate limiting using Redis."""
    
    def __init__(self):
        self.redis = get_redis()
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        burst: Optional[int] = None
    ) -> bool:
        """Check if request is allowed using sliding window."""
        try:
            now = time.time()
            pipeline = self.redis.pipeline()
            
            # Remove old entries
            pipeline.zremrangebyscore(key, 0, now - window)
            
            # Count current entries
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiration
            pipeline.expire(key, window)
            
            results = await pipeline.execute()
            current_count = results[1]
            
            # Check burst limit first
            if burst and current_count > burst:
                return False
            
            # Check rate limit
            return current_count <= limit
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # Allow on error
    
    async def get_stats(self, key: str) -> Dict[str, Any]:
        """Get rate limiting stats."""
        try:
            count = await self.redis.zcard(key)
            ttl = await self.redis.ttl(key)
            
            return {
                "count": count,
                "ttl": ttl,
                "reset_time": time.time() + ttl if ttl > 0 else None
            }
        except Exception as e:
            logger.error(f"Rate limiter stats error: {e}")
            return {"count": 0, "ttl": -1, "reset_time": None}


class QueueManager:
    """Queue management for background jobs."""
    
    def __init__(self):
        self.redis = get_redis()
        self.queue_prefix = "jsonxml_export_queue"
    
    async def enqueue(self, job_data: Dict[str, Any]) -> str:
        """Add job to queue."""
        job_id = f"job_{int(time.time() * 1000)}"
        key = f"{self.queue_prefix}:pending"
        
        try:
            await self.redis.lpush(key, json.dumps({
                "job_id": job_id,
                "data": job_data,
                "timestamp": time.time()
            }))
            return job_id
        except Exception as e:
            logger.error(f"Queue enqueue error: {e}")
            raise
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Get job from queue."""
        pending_key = f"{self.queue_prefix}:pending"
        processing_key = f"{self.queue_prefix}:processing"
        
        try:
            # Move from pending to processing
            job_data = await self.redis.brpoplpush(
                pending_key,
                processing_key,
                timeout=1
            )
            
            if job_data:
                return json.loads(job_data)
            return None
            
        except Exception as e:
            logger.error(f"Queue dequeue error: {e}")
            return None
    
    async def complete_job(self, job_id: str) -> bool:
        """Mark job as completed."""
        processing_key = f"{self.queue_prefix}:processing"
        completed_key = f"{self.queue_prefix}:completed"
        
        try:
            # Move from processing to completed
            jobs = await self.redis.lrange(processing_key, 0, -1)
            for job_str in jobs:
                job_data = json.loads(job_str)
                if job_data.get("job_id") == job_id:
                    await self.redis.lrem(processing_key, 1, job_str)
                    await self.redis.lpush(completed_key, job_str)
                    
                    # Set expiration for completed jobs
                    await self.redis.expire(completed_key, 3600)  # 1 hour
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Queue complete job error: {e}")
            return False
    
    async def get_queue_size(self) -> Dict[str, int]:
        """Get queue sizes."""
        try:
            pending = await self.redis.llen(f"{self.queue_prefix}:pending")
            processing = await self.redis.llen(f"{self.queue_prefix}:processing")
            completed = await self.redis.llen(f"{self.queue_prefix}:completed")
            
            return {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "total": pending + processing + completed
            }
        except Exception as e:
            logger.error(f"Queue size error: {e}")
            return {"pending": 0, "processing": 0, "completed": 0, "total": 0}


# Global instances
def get_cache_manager() -> CacheManager:
    """Get cache manager instance."""
    return CacheManager()


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    return RateLimiter()


def get_queue_manager() -> QueueManager:
    """Get queue manager instance."""
    return QueueManager()