#!/usr/bin/env python3
"""
Database initialization script for ITSM Service.
"""

import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database
from app.core.redis_client import init_redis
from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_all():
    """Initialize all database components."""
    try:
        logger.info("Starting database initialization...")
        
        # Initialize PostgreSQL
        await init_database()
        logger.info("PostgreSQL database initialized successfully")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized successfully")
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_all())