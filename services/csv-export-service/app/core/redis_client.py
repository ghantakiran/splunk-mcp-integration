#!/usr/bin/env python3
"""
Redis client configuration and utilities for CSV Export Service.

This module provides Redis connection management, caching utilities,
queue management, and session handling for the CSV export service.
"""

import json
import logging
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connections
redis_client: Optional[Redis] = None
cache_manager: Optional['CacheManager'] = None
queue_manager: Optional['QueueManager'] = None
session_manager: Optional['SessionManager'] = None


async def init_redis():
    """Initialize Redis connections and managers."""
    global redis_client, cache_manager, queue_manager, session_manager
    
    try:
        # Create Redis client
        redis_client = redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            ssl=settings.REDIS_SSL,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        
        # Initialize managers
        cache_manager = CacheManager(redis_client)
        queue_manager = QueueManager(redis_client)
        session_manager = SessionManager(redis_client)
        
        logger.info("Redis client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis():
    """Close Redis connections."""
    global redis_client
    
    try:
        if redis_client:
            await redis_client.close()
            logger.info("Redis client closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")


def get_redis() -> Redis:
    """Get Redis client."""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client


def get_cache_manager() -> 'CacheManager':
    """Get cache manager."""
    if not cache_manager:
        raise RuntimeError("Cache manager not initialized")
    return cache_manager


def get_queue_manager() -> 'QueueManager':
    """Get queue manager."""
    if not queue_manager:
        raise RuntimeError("Queue manager not initialized")
    return queue_manager


def get_session_manager() -> 'SessionManager':
    """Get session manager."""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")
    return session_manager


class CacheManager:
    """Redis cache management."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            value = await self.redis.get(f"csv_cache:{key}")
            if value is None:
                return default
            
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except RedisError as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache."""
        try:
            cache_key = f"csv_cache:{key}"
            ttl = ttl or self.default_ttl
            
            if serialize:
                # Try to serialize as JSON
                try:
                    serialized_value = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    # Fallback to pickle for complex objects
                    serialized_value = pickle.dumps(value).hex()
                    cache_key = f"csv_pickle:{key}"
            else:
                serialized_value = str(value)
            
            await self.redis.setex(cache_key, ttl, serialized_value)
            return True
            
        except RedisError as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            deleted = await self.redis.delete(f"csv_cache:{key}", f"csv_pickle:{key}")
            return deleted > 0
        except RedisError as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(f"csv_cache:{key}") > 0
        except RedisError as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment counter in cache."""
        try:
            cache_key = f"csv_counter:{key}"
            value = await self.redis.incr(cache_key, amount)
            
            if ttl:
                await self.redis.expire(cache_key, ttl)
            
            return value
        except RedisError as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def get_pattern(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        try:
            keys = await self.redis.keys(f"csv_cache:{pattern}")
            return [key.replace("csv_cache:", "") for key in keys]
        except RedisError as e:
            logger.error(f"Cache pattern error for pattern {pattern}: {e}")
            return []


class QueueManager:
    """Redis queue management for job processing."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.queue_prefix = "csv_queue"
        self.processing_prefix = "csv_processing"
    
    async def enqueue(self, queue_name: str, job_data: Dict[str, Any], priority: int = 5) -> bool:
        """Add job to queue with priority."""
        try:
            job_payload = {
                "id": f"job_{datetime.utcnow().timestamp()}",
                "data": job_data,
                "priority": priority,
                "created_at": datetime.utcnow().isoformat(),
                "attempts": 0
            }
            
            # Use sorted set for priority queue
            score = priority + (datetime.utcnow().timestamp() / 1000000)  # Priority + timestamp for FIFO within priority
            
            await self.redis.zadd(
                f"{self.queue_prefix}:{queue_name}",
                {json.dumps(job_payload, default=str): score}
            )
            
            logger.info(f"Job enqueued to {queue_name} with priority {priority}")
            return True
            
        except RedisError as e:
            logger.error(f"Queue enqueue error: {e}")
            return False
    
    async def dequeue(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get next job from queue."""
        try:
            # Get highest priority job (lowest score)
            result = await self.redis.bzpopmin(f"{self.queue_prefix}:{queue_name}", timeout=timeout)
            
            if not result:
                return None
            
            queue_key, job_json, score = result
            job_data = json.loads(job_json)
            
            # Move to processing set
            processing_key = f"{self.processing_prefix}:{queue_name}"
            await self.redis.setex(
                f"{processing_key}:{job_data['id']}", 
                3600,  # 1 hour timeout
                job_json
            )
            
            return job_data
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Queue dequeue error: {e}")
            return None
    
    async def mark_completed(self, queue_name: str, job_id: str) -> bool:
        """Mark job as completed."""
        try:
            processing_key = f"{self.processing_prefix}:{queue_name}:{job_id}"
            deleted = await self.redis.delete(processing_key)
            return deleted > 0
        except RedisError as e:
            logger.error(f"Queue mark completed error: {e}")
            return False
    
    async def mark_failed(self, queue_name: str, job_id: str, error: str) -> bool:
        """Mark job as failed and optionally retry."""
        try:
            processing_key = f"{self.processing_prefix}:{queue_name}:{job_id}"
            job_data = await self.redis.get(processing_key)
            
            if job_data:
                job_info = json.loads(job_data)
                job_info["attempts"] += 1
                job_info["last_error"] = error
                job_info["failed_at"] = datetime.utcnow().isoformat()
                
                # Move to failed set or retry
                if job_info["attempts"] < 3:  # Max 3 attempts
                    # Re-queue with lower priority
                    await self.enqueue(queue_name, job_info["data"], job_info["priority"] + 1)
                    logger.info(f"Job {job_id} requeued for retry {job_info['attempts']}")
                else:
                    # Move to failed set
                    failed_key = f"csv_failed:{queue_name}"
                    await self.redis.setex(failed_key + f":{job_id}", 86400, job_data)  # Keep for 24 hours
                    logger.error(f"Job {job_id} marked as permanently failed")
                
                await self.redis.delete(processing_key)
                return True
            
            return False
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Queue mark failed error: {e}")
            return False
    
    async def get_queue_size(self, queue_name: Optional[str] = None) -> Dict[str, int]:
        """Get queue sizes."""
        try:
            if queue_name:
                pending = await self.redis.zcard(f"{self.queue_prefix}:{queue_name}")
                processing = len(await self.redis.keys(f"{self.processing_prefix}:{queue_name}:*"))
                
                return {
                    "pending": pending,
                    "processing": processing,
                    "total": pending + processing
                }
            else:
                # Get all queues
                queue_keys = await self.redis.keys(f"{self.queue_prefix}:*")
                total_pending = 0
                total_processing = 0
                
                for key in queue_keys:
                    queue_name = key.replace(f"{self.queue_prefix}:", "")
                    pending = await self.redis.zcard(key)
                    processing = len(await self.redis.keys(f"{self.processing_prefix}:{queue_name}:*"))
                    
                    total_pending += pending
                    total_processing += processing
                
                return {
                    "pending": total_pending,
                    "processing": total_processing,
                    "total": total_pending + total_processing
                }
                
        except RedisError as e:
            logger.error(f"Queue size error: {e}")
            return {"pending": 0, "processing": 0, "total": 0}


class SessionManager:
    """Redis session management."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.session_prefix = "csv_session"
        self.default_ttl = 3600  # 1 hour
    
    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> str:
        """Create new session."""
        try:
            session_id = f"session_{user_id}_{datetime.utcnow().timestamp()}"
            session_key = f"{self.session_prefix}:{session_id}"
            
            session_info = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "data": session_data
            }
            
            await self.redis.setex(
                session_key,
                self.default_ttl,
                json.dumps(session_info, default=str)
            )
            
            return session_id
            
        except RedisError as e:
            logger.error(f"Session create error: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        try:
            session_key = f"{self.session_prefix}:{session_id}"
            session_data = await self.redis.get(session_key)
            
            if session_data:
                session_info = json.loads(session_data)
                # Update last accessed
                session_info["last_accessed"] = datetime.utcnow().isoformat()
                await self.redis.setex(session_key, self.default_ttl, json.dumps(session_info, default=str))
                
                return session_info
            
            return None
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Session get error: {e}")
            return None
    
    async def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data."""
        try:
            session_info = await self.get_session(session_id)
            if session_info:
                session_info["data"].update(session_data)
                session_info["last_accessed"] = datetime.utcnow().isoformat()
                
                session_key = f"{self.session_prefix}:{session_id}"
                await self.redis.setex(
                    session_key,
                    self.default_ttl,
                    json.dumps(session_info, default=str)
                )
                return True
            
            return False
            
        except RedisError as e:
            logger.error(f"Session update error: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            session_key = f"{self.session_prefix}:{session_id}"
            deleted = await self.redis.delete(session_key)
            return deleted > 0
        except RedisError as e:
            logger.error(f"Session delete error: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            pattern = f"{self.session_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            cleaned = 0
            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # No expiration set
                    await self.redis.expire(key, self.default_ttl)
                elif ttl == -2:  # Key doesn't exist
                    cleaned += 1
            
            return cleaned
            
        except RedisError as e:
            logger.error(f"Session cleanup error: {e}")
            return 0


# Export commonly used functions and classes
__all__ = [
    "init_redis",
    "close_redis",
    "get_redis",
    "get_cache_manager",
    "get_queue_manager", 
    "get_session_manager",
    "CacheManager",
    "QueueManager",
    "SessionManager"
]