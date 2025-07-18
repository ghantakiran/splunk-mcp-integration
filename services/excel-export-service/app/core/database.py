"""
Database connection and utilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings


logger = logging.getLogger(__name__)

# Database engine
engine = None
async_session_factory = None


async def init_db():
    """Initialize database connection."""
    global engine, async_session_factory
    
    # Create async engine
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    logger.info("Database initialized")


@asynccontextmanager
async def get_db_connection():
    """Get database connection."""
    conn = None
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            await conn.close()


async def get_db_session():
    """Get database session."""
    if not async_session_factory:
        await init_db()
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def execute_query(
    query: str, 
    *args,
    fetch_one: bool = False,
    fetch_all: bool = False
) -> Union[Any, List[Dict[str, Any]], None]:
    """Execute database query."""
    async with get_db_connection() as conn:
        try:
            if fetch_one:
                result = await conn.fetchrow(query, *args)
                return dict(result) if result else None
            elif fetch_all:
                result = await conn.fetch(query, *args)
                return [dict(row) for row in result]
            else:
                # For INSERT with RETURNING
                if "RETURNING" in query.upper():
                    result = await conn.fetchval(query, *args)
                    return result
                else:
                    await conn.execute(query, *args)
                    return None
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise