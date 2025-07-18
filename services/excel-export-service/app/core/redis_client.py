"""
Redis client and utilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import redis.asyncio as redis

from app.core.config import settings


logger = logging.getLogger(__name__)

# Redis client
redis_client = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    
    # Test connection
    try:
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


@asynccontextmanager
async def get_redis_connection():
    """Get Redis connection."""
    if not redis_client:
        await init_redis()
    
    try:
        yield redis_client
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        raise


async def get_redis_client():
    """Get Redis client."""
    if not redis_client:
        await init_redis()
    return redis_client