#!/usr/bin/env python3
"""
Database connection and session management for Word Export Service.

This module handles PostgreSQL database connections, session management,
and provides database utility functions.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Boolean, Text, JSON, BigInteger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()

# Global engine and session maker
engine = None
async_session_maker = None


class WordExportJob(Base):
    """Word export job model."""
    __tablename__ = "word_export_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    output_format = Column(String(20), nullable=False, default="docx")
    template = Column(String(50), nullable=False, default="professional")
    
    # Job configuration
    document_config = Column(JSON, nullable=False)
    data_source = Column(JSON, nullable=False)
    
    # Job results
    file_path = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    page_count = Column(Integer, nullable=True)
    chart_count = Column(Integer, nullable=True, default=0)
    table_count = Column(Integer, nullable=True, default=0)
    section_count = Column(Integer, nullable=True, default=0)
    
    # Job execution details
    error_message = Column(Text, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)


class WordTemplate(Base):
    """Word template model."""
    __tablename__ = "word_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)
    template_data = Column(JSON, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WordExportAnalytics(Base):
    """Word export analytics model."""
    __tablename__ = "word_export_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    job_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


async def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, async_session_maker
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            echo=settings.DEBUG
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """Close database connections."""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_job(
    session: AsyncSession,
    job_name: str,
    user_id: int,
    document_config: dict,
    data_source: dict,
    output_format: str = "docx",
    expires_in_hours: int = 24
) -> int:
    """Create a new word export job."""
    from datetime import datetime, timedelta
    
    job = WordExportJob(
        job_name=job_name,
        user_id=user_id,
        document_config=document_config,
        data_source=data_source,
        output_format=output_format,
        template=document_config.get("template", "professional"),
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
    )
    
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    logger.info(f"Created job {job.id} for user {user_id}")
    return job.id


async def get_job(session: AsyncSession, job_id: int, user_id: Optional[int] = None) -> Optional[WordExportJob]:
    """Get job by ID and optionally filter by user."""
    from sqlalchemy import select
    
    query = select(WordExportJob).where(WordExportJob.id == job_id)
    if user_id:
        query = query.where(WordExportJob.user_id == user_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_user_jobs(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None
) -> tuple[list[WordExportJob], int]:
    """Get jobs for a user with pagination."""
    from sqlalchemy import select, func as sql_func
    
    # Base query
    query = select(WordExportJob).where(WordExportJob.user_id == user_id)
    count_query = select(sql_func.count(WordExportJob.id)).where(WordExportJob.user_id == user_id)
    
    # Apply status filter
    if status_filter:
        query = query.where(WordExportJob.status == status_filter)
        count_query = count_query.where(WordExportJob.status == status_filter)
    
    # Apply pagination
    query = query.order_by(WordExportJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute queries
    jobs_result = await session.execute(query)
    count_result = await session.execute(count_query)
    
    jobs = jobs_result.scalars().all()
    total_count = count_result.scalar()
    
    return jobs, total_count


async def update_job_status(
    session: AsyncSession,
    job_id: int,
    status: str,
    error_message: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None
) -> None:
    """Update job status."""
    from sqlalchemy import select
    
    # Get job
    result = await session.execute(select(WordExportJob).where(WordExportJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Update fields
    job.status = status
    if error_message:
        job.error_message = error_message
    if started_at:
        job.started_at = started_at
    if completed_at:
        job.completed_at = completed_at
    
    await session.commit()
    logger.info(f"Updated job {job_id} status to {status}")


async def update_job_completion(
    session: AsyncSession,
    job_id: int,
    status: str,
    file_path: str,
    file_size: int,
    page_count: int,
    chart_count: int,
    table_count: int,
    section_count: int,
    generation_time_ms: int
) -> None:
    """Update job with completion details."""
    from datetime import datetime
    from sqlalchemy import select
    
    # Get job
    result = await session.execute(select(WordExportJob).where(WordExportJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Update completion details
    job.status = status
    job.file_path = file_path
    job.file_size = file_size
    job.page_count = page_count
    job.chart_count = chart_count
    job.table_count = table_count
    job.section_count = section_count
    job.generation_time_ms = generation_time_ms
    job.completed_at = datetime.utcnow()
    
    await session.commit()
    logger.info(f"Job {job_id} completed successfully")


async def create_template(
    session: AsyncSession,
    name: str,
    description: str,
    template_type: str,
    template_data: dict,
    created_by: int,
    is_default: bool = False
) -> int:
    """Create a new template."""
    template = WordTemplate(
        name=name,
        description=description,
        template_type=template_type,
        template_data=template_data,
        created_by=created_by,
        is_default=is_default
    )
    
    session.add(template)
    await session.commit()
    await session.refresh(template)
    
    logger.info(f"Created template {template.id}: {name}")
    return template.id


async def get_templates(session: AsyncSession, active_only: bool = True) -> list[WordTemplate]:
    """Get all templates."""
    from sqlalchemy import select
    
    query = select(WordTemplate)
    if active_only:
        query = query.where(WordTemplate.is_active == True)
    
    query = query.order_by(WordTemplate.name)
    
    result = await session.execute(query)
    return result.scalars().all()


async def log_analytics_event(
    session: AsyncSession,
    user_id: int,
    job_id: int,
    event_type: str,
    event_data: Optional[dict] = None
) -> None:
    """Log analytics event."""
    event = WordExportAnalytics(
        user_id=user_id,
        job_id=job_id,
        event_type=event_type,
        event_data=event_data
    )
    
    session.add(event)
    await session.commit()


async def get_analytics(
    session: AsyncSession,
    user_id: Optional[int] = None,
    days: int = 30
) -> dict:
    """Get analytics data."""
    from datetime import datetime, timedelta
    from sqlalchemy import select, func as sql_func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query for jobs
    jobs_query = select(WordExportJob).where(WordExportJob.created_at >= start_date)
    if user_id:
        jobs_query = jobs_query.where(WordExportJob.user_id == user_id)
    
    # Get job statistics
    result = await session.execute(jobs_query)
    jobs = result.scalars().all()
    
    total_jobs = len(jobs)
    successful_jobs = len([j for j in jobs if j.status == "completed"])
    failed_jobs = len([j for j in jobs if j.status == "failed"])
    
    # Calculate averages for successful jobs
    successful_job_list = [j for j in jobs if j.status == "completed"]
    
    if successful_job_list:
        avg_generation_time = sum(j.generation_time_ms or 0 for j in successful_job_list) / len(successful_job_list)
        avg_file_size = sum(j.file_size or 0 for j in successful_job_list) / len(successful_job_list)
        avg_page_count = sum(j.page_count or 0 for j in successful_job_list) / len(successful_job_list)
        avg_chart_count = sum(j.chart_count or 0 for j in successful_job_list) / len(successful_job_list)
        avg_table_count = sum(j.table_count or 0 for j in successful_job_list) / len(successful_job_list)
    else:
        avg_generation_time = avg_file_size = avg_page_count = avg_chart_count = avg_table_count = 0
    
    # Template usage statistics
    template_usage = {}
    for job in jobs:
        template = job.template or "unknown"
        template_usage[template] = template_usage.get(template, 0) + 1
    
    # Daily usage statistics
    daily_usage = {}
    for job in jobs:
        date_key = job.created_at.strftime("%Y-%m-%d")
        if date_key not in daily_usage:
            daily_usage[date_key] = {"total": 0, "successful": 0, "failed": 0}
        daily_usage[date_key]["total"] += 1
        if job.status == "completed":
            daily_usage[date_key]["successful"] += 1
        elif job.status == "failed":
            daily_usage[date_key]["failed"] += 1
    
    return {
        "period_days": days,
        "total_jobs": total_jobs,
        "successful_jobs": successful_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0,
        "avg_generation_time": avg_generation_time,
        "avg_file_size": avg_file_size,
        "avg_page_count": avg_page_count,
        "avg_chart_count": avg_chart_count,
        "avg_table_count": avg_table_count,
        "usage_by_template": template_usage,
        "daily_usage": [{"date": k, **v} for k, v in sorted(daily_usage.items())]
    }


# Export commonly used functions
__all__ = [
    "init_db",
    "close_db",
    "get_db_session",
    "create_job",
    "get_job",
    "get_user_jobs",
    "update_job_status",
    "update_job_completion",
    "create_template",
    "get_templates",
    "log_analytics_event",
    "get_analytics",
    "WordExportJob",
    "WordTemplate",
    "WordExportAnalytics"
]