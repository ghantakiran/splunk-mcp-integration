"""
Database configuration and connection management for ITSM Service.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager

from .config import get_database_config
from ..models.itsm_models import Base as ITSMBase
from ..models.user_models import Base as UserBase

# Database configuration
db_config = get_database_config()

# Create async engine
engine = create_async_engine(
    db_config["url"],
    pool_size=db_config["pool_size"],
    max_overflow=db_config["max_overflow"],
    pool_timeout=db_config["pool_timeout"],
    pool_recycle=db_config["pool_recycle"],
    echo=db_config["echo"],
    poolclass=StaticPool if "sqlite" in db_config["url"] else None,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_database() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(ITSMBase.metadata.create_all)
        await conn.run_sync(UserBase.metadata.create_all)


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Check database connection health."""
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False