#!/usr/bin/env python3
"""
Database configuration and management for HTML Report Service.

This module provides database connectivity, session management,
and model definitions for the HTML report service.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, AsyncGenerator

import asyncpg
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

# SQLAlchemy setup
Base = declarative_base()

# Database engine and session
engine = None
SessionLocal = None


class HTMLReportJob(Base):
    """HTML report job model."""
    __tablename__ = "html_report_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    output_format = Column(String(10), nullable=False, default="html")
    template = Column(String(50), nullable=False, default="modern")
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    chart_count = Column(Integer, nullable=True, default=0)
    table_count = Column(Integer, nullable=True, default=0)
    section_count = Column(Integer, nullable=True, default=0)
    error_message = Column(Text, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    report_config = Column(JSON, nullable=False)
    data_source = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HTMLReportTemplate(Base):
    """HTML report template model."""
    __tablename__ = "html_report_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)
    template_data = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HTMLReportUser(Base):
    """HTML report user model."""
    __tablename__ = "html_report_users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    preferences = Column(JSON, nullable=True, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HTMLReportMetrics(Base):
    """HTML report metrics model."""
    __tablename__ = "html_report_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    total_jobs = Column(Integer, default=0)
    successful_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    avg_generation_time = Column(Float, default=0.0)
    avg_file_size = Column(Float, default=0.0)
    format_stats = Column(JSON, default={})
    template_stats = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def init_db():
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            echo=settings.DEBUG
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
        
        # Test connection
        await test_connection()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def test_connection():
    """Test database connection."""
    try:
        async with get_db_session() as session:
            result = await session.execute("SELECT 1")
            await result.fetchone()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with get_db_session() as session:
        yield session


async def close_db():
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


# Database helper functions
async def create_job(
    session: AsyncSession,
    job_name: str,
    user_id: int,
    report_config: dict,
    data_source: dict,
    output_format: str = "html",
    expires_at: Optional[datetime] = None
) -> HTMLReportJob:
    """Create a new HTML report job."""
    job = HTMLReportJob(
        job_name=job_name,
        user_id=user_id,
        report_config=report_config,
        data_source=data_source,
        output_format=output_format,
        template=report_config.get("template", "modern"),
        expires_at=expires_at
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


async def update_job_status(
    session: AsyncSession,
    job_id: int,
    status: str,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None
) -> Optional[HTMLReportJob]:
    """Update job status."""
    job = await session.get(HTMLReportJob, job_id)
    if not job:
        return None
    
    job.status = status
    if error_message is not None:
        job.error_message = error_message
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    
    await session.flush()
    await session.refresh(job)
    return job


async def update_job_completion(
    session: AsyncSession,
    job_id: int,
    status: str,
    file_path: str,
    file_size: int,
    chart_count: int,
    table_count: int,
    section_count: int,
    generation_time_ms: int
) -> Optional[HTMLReportJob]:
    """Update job with completion details."""
    job = await session.get(HTMLReportJob, job_id)
    if not job:
        return None
    
    job.status = status
    job.file_path = file_path
    job.file_size = file_size
    job.chart_count = chart_count
    job.table_count = table_count
    job.section_count = section_count
    job.generation_time_ms = generation_time_ms
    job.completed_at = datetime.utcnow()
    
    await session.flush()
    await session.refresh(job)
    return job


async def get_job_by_id(session: AsyncSession, job_id: int) -> Optional[HTMLReportJob]:
    """Get job by ID."""
    return await session.get(HTMLReportJob, job_id)


async def get_jobs_by_user(
    session: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
    output_format: Optional[str] = None,
    template: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> list[HTMLReportJob]:
    """Get jobs by user with optional filters."""
    from sqlalchemy import select
    
    query = select(HTMLReportJob).where(HTMLReportJob.user_id == user_id)
    
    if status:
        query = query.where(HTMLReportJob.status == status)
    if output_format:
        query = query.where(HTMLReportJob.output_format == output_format)
    if template:
        query = query.where(HTMLReportJob.template == template)
    
    query = query.order_by(HTMLReportJob.created_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(query)
    return result.scalars().all()


# Export commonly used components
__all__ = [
    "Base",
    "HTMLReportJob",
    "HTMLReportTemplate",
    "HTMLReportUser",
    "HTMLReportMetrics",
    "init_db",
    "close_db",
    "get_db_session",
    "get_db_session_dependency",
    "create_job",
    "update_job_status",
    "update_job_completion",
    "get_job_by_id",
    "get_jobs_by_user"
]
