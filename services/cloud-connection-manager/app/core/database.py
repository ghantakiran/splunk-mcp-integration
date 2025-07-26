"""
Database configuration and setup for Cloud Connection Manager Service.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database engine
engine = None
SessionLocal = None


class Base(DeclarativeBase):
    """Base class for database models."""
    pass


async def init_db():
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            poolclass=StaticPool if settings.DATABASE_URL.startswith("sqlite") else None,
        )
        
        # Create session factory
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def close_db():
    """Close database connections."""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    if not SessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Health check function
async def check_database_health() -> bool:
    """Check database connectivity."""
    try:
        if not engine:
            return False
        
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False