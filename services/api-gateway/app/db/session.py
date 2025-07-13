"""
Database session management with async SQLAlchemy
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Global engine instance
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine_config():
    """Get database engine configuration"""
    config = {
        "echo": settings.database_echo,
        "future": True,
    }
    
    # Configure connection pool
    if "sqlite" in settings.database_url:
        # SQLite configuration
        config.update({
            "poolclass": NullPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20
            }
        })
    else:
        # PostgreSQL configuration
        config.update({
            "poolclass": QueuePool,
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # 1 hour
            "connect_args": {
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "splunk_mcp_api_gateway",
                }
            }
        })
    
    return config


async def create_engine() -> AsyncEngine:
    """Create async database engine"""
    global engine
    
    if engine is None:
        config = get_engine_config()
        engine = create_async_engine(settings.database_url, **config)
        
        logger.info(
            "Database engine created",
            database_url=settings.database_url.split("@")[-1],  # Remove credentials
            pool_size=config.get("pool_size"),
            max_overflow=config.get("max_overflow")
        )
    
    return engine


async def create_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create async session maker"""
    global AsyncSessionLocal
    
    if AsyncSessionLocal is None:
        engine = await create_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        logger.info("Database session maker created")
    
    return AsyncSessionLocal


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session
    
    Usage:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_async_session)):
            ...
    """
    session_maker = await create_session_maker()
    
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e), exc_info=True)
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and create tables if needed"""
    from .base import Base
    
    try:
        engine = await create_engine()
        
        # Create all tables
        async with engine.begin() as conn:
            # Check if we need to create tables
            # In production, this should be handled by migrations
            if settings.environment == "development":
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created/verified")
        
        # Test connection
        session_maker = await create_session_maker()
        async with session_maker() as session:
            await session.execute("SELECT 1")
            logger.info("Database connection established successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True)
        raise


async def close_db():
    """Close database connections"""
    global engine, AsyncSessionLocal
    
    if engine:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        logger.info("Database connections closed")


# SQLite-specific configuration for development
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance and consistency"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set synchronous mode for balance of safety and performance
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Set cache size (negative value means KB)
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        # Set temp store to memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


class DatabaseManager:
    """Database connection manager for advanced operations"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def initialize(self):
        """Initialize database manager"""
        self.engine = await create_engine()
        self.session_maker = await create_session_maker()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            if not self.session_maker:
                await self.initialize()
            
            async with self.session_maker() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_connection_info(self) -> dict:
        """Get database connection information"""
        if not self.engine:
            await self.initialize()
        
        pool = self.engine.pool
        return {
            "pool_size": getattr(pool, "size", None),
            "checked_out": getattr(pool, "checkedout", None),
            "overflow": getattr(pool, "overflow", None),
            "checked_in": getattr(pool, "checkedin", None),
        }
    
    async def execute_raw_sql(self, sql: str, params: dict = None):
        """Execute raw SQL (use with caution)"""
        if not self.session_maker:
            await self.initialize()
        
        async with self.session_maker() as session:
            result = await session.execute(sql, params or {})
            await session.commit()
            return result
    
    async def close(self):
        """Close database manager"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_maker = None


# Global database manager instance
db_manager = DatabaseManager()