#!/usr/bin/env python3
"""
Database configuration and connection management for PowerPoint Export Service.

This module handles database connections, session management, and provides
utilities for database operations.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool
from structlog import get_logger

from app.core.config import settings


logger = get_logger(__name__)


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
    
    async def create_pool(self) -> Pool:
        """Create database connection pool."""
        if self.pool is None:
            async with self._lock:
                if self.pool is None:
                    try:
                        self.pool = await asyncpg.create_pool(
                            settings.DATABASE_URL,
                            min_size=1,
                            max_size=settings.DATABASE_POOL_SIZE,
                            max_queries=50000,
                            max_inactive_connection_lifetime=300,
                            timeout=settings.DATABASE_POOL_TIMEOUT,
                            command_timeout=60
                        )
                        logger.info("Database pool created successfully")
                    except Exception as e:
                        logger.error("Failed to create database pool", error=str(e))
                        raise
        return self.pool
    
    async def close_pool(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get database connection from pool."""
        if not self.pool:
            await self.create_pool()
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error("Database connection error", error=str(e))
                raise
    
    async def execute_query(self, query: str, *args, fetch: str = "all") -> any:
        """Execute a database query."""
        async with self.get_connection() as conn:
            try:
                if fetch == "all":
                    result = await conn.fetch(query, *args)
                    return [dict(row) for row in result]
                elif fetch == "one":
                    result = await conn.fetchrow(query, *args)
                    return dict(result) if result else None
                elif fetch == "val":
                    return await conn.fetchval(query, *args)
                else:
                    await conn.execute(query, *args)
                    return None
            except Exception as e:
                logger.error("Query execution failed", query=query, error=str(e))
                raise
    
    async def execute_transaction(self, queries: list) -> None:
        """Execute multiple queries in a transaction."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    for query_data in queries:
                        if isinstance(query_data, tuple):
                            query, args = query_data
                            await conn.execute(query, *args)
                        else:
                            await conn.execute(query_data)
                except Exception as e:
                    logger.error("Transaction failed", error=str(e))
                    raise


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
async def init_db() -> None:
    """Initialize database connection."""
    await db_manager.create_pool()
    logger.info("Database initialized")


async def close_db() -> None:
    """Close database connection."""
    await db_manager.close_pool()
    logger.info("Database closed")


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection context manager."""
    async with db_manager.get_connection() as conn:
        yield conn


async def execute_query(query: str, *args, fetch: str = "all") -> any:
    """Execute a database query."""
    return await db_manager.execute_query(query, *args, fetch=fetch)


async def execute_transaction(queries: list) -> None:
    """Execute multiple queries in a transaction."""
    await db_manager.execute_transaction(queries)


# Database schema initialization
CREATE_TABLES_SQL = """
-- PowerPoint export jobs table
CREATE TABLE IF NOT EXISTS ppt_export_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    presentation_config JSONB NOT NULL,
    data_source JSONB NOT NULL,
    output_format VARCHAR(20) NOT NULL DEFAULT 'pptx',
    theme VARCHAR(50) NOT NULL DEFAULT 'office',
    file_path VARCHAR(500),
    file_size INTEGER,
    slide_count INTEGER,
    chart_count INTEGER,
    animation_count INTEGER,
    error_message TEXT,
    generation_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- PowerPoint templates table
CREATE TABLE IF NOT EXISTS ppt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    theme VARCHAR(50) NOT NULL,
    template_data JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PowerPoint slides table
CREATE TABLE IF NOT EXISTS ppt_slides (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES ppt_export_jobs(id) ON DELETE CASCADE,
    slide_number INTEGER NOT NULL,
    slide_title VARCHAR(255),
    slide_type VARCHAR(50) NOT NULL,
    slide_content JSONB NOT NULL,
    layout VARCHAR(50) NOT NULL,
    animation VARCHAR(50),
    transition VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PowerPoint charts table
CREATE TABLE IF NOT EXISTS ppt_charts (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES ppt_export_jobs(id) ON DELETE CASCADE,
    slide_id INTEGER NOT NULL REFERENCES ppt_slides(id) ON DELETE CASCADE,
    chart_type VARCHAR(50) NOT NULL,
    chart_data JSONB NOT NULL,
    chart_config JSONB NOT NULL,
    position_x FLOAT NOT NULL,
    position_y FLOAT NOT NULL,
    width FLOAT NOT NULL,
    height FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PowerPoint export analytics table
CREATE TABLE IF NOT EXISTS ppt_export_analytics (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES ppt_export_jobs(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PowerPoint user preferences table
CREATE TABLE IF NOT EXISTS ppt_user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    default_theme VARCHAR(50) NOT NULL DEFAULT 'office',
    default_animation VARCHAR(50) NOT NULL DEFAULT 'fade',
    default_transition VARCHAR(50) NOT NULL DEFAULT 'fade',
    default_font_family VARCHAR(100) NOT NULL DEFAULT 'Calibri',
    default_font_size INTEGER NOT NULL DEFAULT 18,
    default_color_scheme VARCHAR(50) NOT NULL DEFAULT 'blue',
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_user_id ON ppt_export_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_status ON ppt_export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_created_at ON ppt_export_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_expires_at ON ppt_export_jobs(expires_at);
CREATE INDEX IF NOT EXISTS idx_ppt_slides_job_id ON ppt_slides(job_id);
CREATE INDEX IF NOT EXISTS idx_ppt_slides_slide_number ON ppt_slides(slide_number);
CREATE INDEX IF NOT EXISTS idx_ppt_charts_job_id ON ppt_charts(job_id);
CREATE INDEX IF NOT EXISTS idx_ppt_charts_slide_id ON ppt_charts(slide_id);
CREATE INDEX IF NOT EXISTS idx_ppt_export_analytics_user_id ON ppt_export_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_ppt_export_analytics_timestamp ON ppt_export_analytics(timestamp);

-- Create trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ppt_templates_updated_at
    BEFORE UPDATE ON ppt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ppt_user_preferences_updated_at
    BEFORE UPDATE ON ppt_user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


async def create_tables() -> None:
    """Create database tables."""
    try:
        await execute_query(CREATE_TABLES_SQL, fetch="none")
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


# Export commonly used functions
__all__ = [
    "init_db",
    "close_db",
    "get_db_connection",
    "execute_query",
    "execute_transaction",
    "create_tables",
    "db_manager"
]
