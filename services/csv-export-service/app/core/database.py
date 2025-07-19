#!/usr/bin/env python3
"""
Database configuration and utilities for CSV Export Service.

This module provides database connection management, session handling,
and database operations for the CSV export service.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, timedelta

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.csv_models import JobStatus

logger = logging.getLogger(__name__)

# Global variables
engine = None
async_session_maker = None
connection_pool = None


async def init_db():
    """Initialize database connection and create tables."""
    global engine, async_session_maker, connection_pool
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            echo=settings.DEBUG,
            poolclass=NullPool if settings.DEBUG else None
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create connection pool for direct PostgreSQL operations
        connection_pool = await asyncpg.create_pool(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+asyncpg://", "postgresql://"),
            min_size=5,
            max_size=settings.DATABASE_POOL_SIZE,
            command_timeout=60
        )
        
        # Create tables if they don't exist
        await create_tables()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connections."""
    global engine, connection_pool
    
    try:
        if connection_pool:
            await connection_pool.close()
            logger.info("Database connection pool closed")
        
        if engine:
            await engine.dispose()
            logger.info("Database engine disposed")
            
    except Exception as e:
        logger.error(f"Error closing database: {e}")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def create_tables():
    """Create database tables for CSV export service."""
    
    create_tables_sql = """
    -- CSV Export Users table
    CREATE TABLE IF NOT EXISTS csv_users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        role VARCHAR(50) DEFAULT 'user',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        settings JSONB DEFAULT '{}'::jsonb
    );

    -- CSV Export Jobs table
    CREATE TABLE IF NOT EXISTS csv_export_jobs (
        job_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES csv_users(user_id) ON DELETE CASCADE,
        job_name VARCHAR(255) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        priority INTEGER DEFAULT 5,
        data_source JSONB NOT NULL,
        export_config JSONB NOT NULL,
        file_path TEXT,
        file_size BIGINT,
        row_count INTEGER,
        column_count INTEGER,
        error_message TEXT,
        generation_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        expires_at TIMESTAMP,
        metadata JSONB DEFAULT '{}'::jsonb
    );

    -- CSV Export Templates table
    CREATE TABLE IF NOT EXISTS csv_export_templates (
        template_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES csv_users(user_id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        export_config JSONB NOT NULL,
        is_default BOOLEAN DEFAULT false,
        is_active BOOLEAN DEFAULT true,
        usage_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name)
    );

    -- CSV Export Analytics table
    CREATE TABLE IF NOT EXISTS csv_export_analytics (
        analytics_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES csv_users(user_id) ON DELETE SET NULL,
        job_id INTEGER REFERENCES csv_export_jobs(job_id) ON DELETE CASCADE,
        event_type VARCHAR(100) NOT NULL,
        event_data JSONB DEFAULT '{}'::jsonb,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        session_id VARCHAR(255),
        ip_address INET,
        user_agent TEXT
    );

    -- CSV Export Metrics table
    CREATE TABLE IF NOT EXISTS csv_export_metrics (
        metric_id SERIAL PRIMARY KEY,
        metric_name VARCHAR(100) NOT NULL,
        metric_value DECIMAL(15,4) NOT NULL,
        metric_type VARCHAR(50) NOT NULL,
        labels JSONB DEFAULT '{}'::jsonb,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        period_start TIMESTAMP,
        period_end TIMESTAMP
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_csv_export_jobs_user_id ON csv_export_jobs(user_id);
    CREATE INDEX IF NOT EXISTS idx_csv_export_jobs_status ON csv_export_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_csv_export_jobs_created_at ON csv_export_jobs(created_at);
    CREATE INDEX IF NOT EXISTS idx_csv_export_jobs_expires_at ON csv_export_jobs(expires_at);
    CREATE INDEX IF NOT EXISTS idx_csv_export_templates_user_id ON csv_export_templates(user_id);
    CREATE INDEX IF NOT EXISTS idx_csv_export_analytics_user_id ON csv_export_analytics(user_id);
    CREATE INDEX IF NOT EXISTS idx_csv_export_analytics_timestamp ON csv_export_analytics(timestamp);
    CREATE INDEX IF NOT EXISTS idx_csv_export_metrics_timestamp ON csv_export_metrics(timestamp);
    CREATE INDEX IF NOT EXISTS idx_csv_export_metrics_name ON csv_export_metrics(metric_name);

    -- Triggers for updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_csv_users_updated_at ON csv_users;
    CREATE TRIGGER update_csv_users_updated_at 
        BEFORE UPDATE ON csv_users 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_csv_export_templates_updated_at ON csv_export_templates;
    CREATE TRIGGER update_csv_export_templates_updated_at 
        BEFORE UPDATE ON csv_export_templates 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    
    try:
        if connection_pool:
            async with connection_pool.acquire() as conn:
                await conn.execute(create_tables_sql)
            logger.info("Database tables created successfully")
        else:
            logger.warning("Connection pool not available, skipping table creation")
            
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


# Database operations
async def create_user(username: str, email: str, role: str = "user") -> int:
    """Create a new user."""
    query = """
    INSERT INTO csv_users (username, email, role)
    VALUES ($1, $2, $3)
    RETURNING user_id
    """
    
    async with connection_pool.acquire() as conn:
        user_id = await conn.fetchval(query, username, email, role)
        logger.info(f"Created user {username} with ID {user_id}")
        return user_id


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    query = """
    SELECT user_id, username, email, role, is_active, created_at, last_login, settings
    FROM csv_users
    WHERE user_id = $1
    """
    
    async with connection_pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id)
        return dict(row) if row else None


async def create_export_job(
    user_id: int,
    job_name: str,
    data_source: Dict[str, Any],
    export_config: Dict[str, Any],
    priority: int = 5,
    expires_in_hours: int = 24
) -> int:
    """Create a new export job."""
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    query = """
    INSERT INTO csv_export_jobs (
        user_id, job_name, data_source, export_config, priority, expires_at
    )
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING job_id
    """
    
    async with connection_pool.acquire() as conn:
        job_id = await conn.fetchval(
            query, user_id, job_name, data_source, export_config, priority, expires_at
        )
        logger.info(f"Created export job {job_id} for user {user_id}")
        return job_id


async def update_job_status(
    job_id: int,
    status: str,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None
) -> None:
    """Update job status."""
    query = """
    UPDATE csv_export_jobs 
    SET status = $2, error_message = $3, started_at = COALESCE($4, started_at), 
        completed_at = COALESCE($5, completed_at)
    WHERE job_id = $1
    """
    
    async with connection_pool.acquire() as conn:
        await conn.execute(query, job_id, status, error_message, started_at, completed_at)


async def update_job_completion(
    job_id: int,
    status: str,
    file_path: str,
    file_size: int,
    row_count: int,
    column_count: int,
    generation_time_ms: int
) -> None:
    """Update job with completion details."""
    query = """
    UPDATE csv_export_jobs 
    SET status = $2, file_path = $3, file_size = $4, row_count = $5, 
        column_count = $6, generation_time_ms = $7, completed_at = CURRENT_TIMESTAMP
    WHERE job_id = $1
    """
    
    async with connection_pool.acquire() as conn:
        await conn.execute(
            query, job_id, status, file_path, file_size, 
            row_count, column_count, generation_time_ms
        )


async def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Get job by ID."""
    query = """
    SELECT job_id, user_id, job_name, status, priority, data_source, export_config,
           file_path, file_size, row_count, column_count, error_message,
           generation_time_ms, created_at, started_at, completed_at, expires_at
    FROM csv_export_jobs
    WHERE job_id = $1
    """
    
    async with connection_pool.acquire() as conn:
        row = await conn.fetchrow(query, job_id)
        return dict(row) if row else None


async def get_user_jobs(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get jobs for a user."""
    if status:
        query = """
        SELECT job_id, job_name, status, file_path, file_size, row_count,
               created_at, started_at, completed_at, expires_at
        FROM csv_export_jobs
        WHERE user_id = $1 AND status = $2
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4
        """
        params = [user_id, status, limit, offset]
    else:
        query = """
        SELECT job_id, job_name, status, file_path, file_size, row_count,
               created_at, started_at, completed_at, expires_at
        FROM csv_export_jobs
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """
        params = [user_id, limit, offset]
    
    async with connection_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def create_template(
    user_id: int,
    name: str,
    description: str,
    export_config: Dict[str, Any],
    is_default: bool = False
) -> int:
    """Create a new template."""
    query = """
    INSERT INTO csv_export_templates (user_id, name, description, export_config, is_default)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING template_id
    """
    
    async with connection_pool.acquire() as conn:
        template_id = await conn.fetchval(
            query, user_id, name, description, export_config, is_default
        )
        logger.info(f"Created template {name} with ID {template_id}")
        return template_id


async def get_user_templates(user_id: int) -> List[Dict[str, Any]]:
    """Get templates for a user."""
    query = """
    SELECT template_id, name, description, export_config, is_default, 
           is_active, usage_count, created_at, updated_at
    FROM csv_export_templates
    WHERE user_id = $1 AND is_active = true
    ORDER BY is_default DESC, name ASC
    """
    
    async with connection_pool.acquire() as conn:
        rows = await conn.fetch(query, user_id)
        return [dict(row) for row in rows]


async def log_analytics_event(
    user_id: Optional[int],
    job_id: Optional[int],
    event_type: str,
    event_data: Dict[str, Any],
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log analytics event."""
    query = """
    INSERT INTO csv_export_analytics 
    (user_id, job_id, event_type, event_data, session_id, ip_address, user_agent)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """
    
    async with connection_pool.acquire() as conn:
        await conn.execute(
            query, user_id, job_id, event_type, event_data, 
            session_id, ip_address, user_agent
        )


async def record_metric(
    metric_name: str,
    metric_value: float,
    metric_type: str,
    labels: Optional[Dict[str, Any]] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None
) -> None:
    """Record a metric."""
    query = """
    INSERT INTO csv_export_metrics 
    (metric_name, metric_value, metric_type, labels, period_start, period_end)
    VALUES ($1, $2, $3, $4, $5, $6)
    """
    
    async with connection_pool.acquire() as conn:
        await conn.execute(
            query, metric_name, metric_value, metric_type, 
            labels or {}, period_start, period_end
        )


async def cleanup_expired_jobs() -> int:
    """Clean up expired jobs."""
    query = """
    DELETE FROM csv_export_jobs
    WHERE expires_at < CURRENT_TIMESTAMP AND status IN ('completed', 'failed')
    """
    
    async with connection_pool.acquire() as conn:
        result = await conn.execute(query)
        count = int(result.split()[-1]) if result else 0
        logger.info(f"Cleaned up {count} expired jobs")
        return count


# Export commonly used functions
__all__ = [
    "init_db",
    "close_db", 
    "get_db_session",
    "create_user",
    "get_user_by_id",
    "create_export_job",
    "update_job_status",
    "update_job_completion",
    "get_job_by_id",
    "get_user_jobs",
    "create_template",
    "get_user_templates",
    "log_analytics_event",
    "record_metric",
    "cleanup_expired_jobs"
]