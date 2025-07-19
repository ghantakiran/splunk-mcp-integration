"""
Database configuration and models for the Report Scheduling Service.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

import asyncpg
from sqlalchemy import (
    Column, String, DateTime, Integer, Text, Boolean,
    JSON, Enum as SQLEnum, Float, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.models.schedule_models import (
    ScheduleStatus, DeliveryMethod, ReportFormat,
    Priority, ExecutionStatus
)

# Database setup
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_database() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        return session


# Database Models
class ReportSchedule(Base):
    """Report schedule database model."""
    __tablename__ = "report_schedules"

    schedule_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ScheduleStatus), nullable=False, default=ScheduleStatus.ACTIVE, index=True)
    
    # Schedule configuration
    cron_expression = Column(String(255), nullable=False)
    timezone = Column(String(100), nullable=False, default="UTC")
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    max_executions = Column(Integer, nullable=True)
    allow_overlap = Column(Boolean, nullable=False, default=False)
    priority = Column(SQLEnum(Priority), nullable=False, default=Priority.MEDIUM)
    
    # Report configuration
    query = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=False, default="natural")
    time_range = Column(JSON, nullable=False)
    report_format = Column(SQLEnum(ReportFormat), nullable=False)
    format_options = Column(JSON, nullable=True)
    visualization_config = Column(JSON, nullable=True)
    data_filters = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    
    # Delivery configuration
    delivery_configs = Column(JSON, nullable=False)
    
    # Execution tracking
    next_execution = Column(DateTime(timezone=True), nullable=True, index=True)
    last_execution = Column(DateTime(timezone=True), nullable=True)
    execution_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    executions = relationship("ScheduleExecution", back_populates="schedule", cascade="all, delete-orphan")
    subscriptions = relationship("ReportSubscription", back_populates="schedule", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_schedule_user_status", "user_id", "status"),
        Index("idx_schedule_next_execution", "next_execution", "status"),
        Index("idx_schedule_created_at", "created_at"),
    )


class ScheduleExecution(Base):
    """Schedule execution database model."""
    __tablename__ = "schedule_executions"

    execution_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    schedule_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("report_schedules.schedule_id"), nullable=False, index=True)
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING, index=True)
    
    # Execution timing
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Execution results
    report_file_path = Column(String(1000), nullable=True)
    report_size_bytes = Column(Integer, nullable=True)
    records_processed = Column(Integer, nullable=True)
    delivery_results = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    schedule = relationship("ReportSchedule", back_populates="executions")
    
    # Indexes
    __table_args__ = (
        Index("idx_execution_schedule_status", "schedule_id", "status"),
        Index("idx_execution_scheduled_at", "scheduled_at"),
        Index("idx_execution_status_created", "status", "created_at"),
    )


class ReportSubscription(Base):
    """Report subscription database model."""
    __tablename__ = "report_subscriptions"

    subscription_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    schedule_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("report_schedules.schedule_id"), nullable=False, index=True)
    
    # Delivery configuration
    delivery_method = Column(SQLEnum(DeliveryMethod), nullable=False)
    delivery_config = Column(JSON, nullable=False)
    
    # Subscription settings
    active = Column(Boolean, nullable=False, default=True, index=True)
    preferences = Column(JSON, nullable=True)
    
    # Delivery tracking
    total_deliveries = Column(Integer, nullable=False, default=0)
    successful_deliveries = Column(Integer, nullable=False, default=0)
    failed_deliveries = Column(Integer, nullable=False, default=0)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_delivery_status = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    schedule = relationship("ReportSchedule", back_populates="subscriptions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "schedule_id", name="unique_user_schedule_subscription"),
        Index("idx_subscription_user_active", "user_id", "active"),
        Index("idx_subscription_schedule_active", "schedule_id", "active"),
    )


class DeliveryAttempt(Base):
    """Delivery attempt database model."""
    __tablename__ = "delivery_attempts"

    attempt_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("schedule_executions.execution_id"), nullable=False, index=True)
    subscription_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("report_subscriptions.subscription_id"), nullable=False, index=True)
    
    # Delivery details
    delivery_method = Column(SQLEnum(DeliveryMethod), nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, index=True)
    
    # Timing
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results
    success = Column(Boolean, nullable=False, default=False, index=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_delivery_execution_status", "execution_id", "status"),
        Index("idx_delivery_subscription_success", "subscription_id", "success"),
        Index("idx_delivery_attempted_at", "attempted_at"),
    )


class ScheduleAnalytics(Base):
    """Schedule analytics database model."""
    __tablename__ = "schedule_analytics"

    analytics_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    schedule_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("report_schedules.schedule_id"), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Execution metrics
    total_executions = Column(Integer, nullable=False, default=0)
    successful_executions = Column(Integer, nullable=False, default=0)
    failed_executions = Column(Integer, nullable=False, default=0)
    average_duration_seconds = Column(Float, nullable=True)
    total_duration_seconds = Column(Float, nullable=False, default=0)
    
    # Report metrics
    total_records_processed = Column(Integer, nullable=False, default=0)
    total_report_size_bytes = Column(Integer, nullable=False, default=0)
    average_report_size_bytes = Column(Float, nullable=True)
    
    # Delivery metrics
    total_deliveries = Column(Integer, nullable=False, default=0)
    successful_deliveries = Column(Integer, nullable=False, default=0)
    failed_deliveries = Column(Integer, nullable=False, default=0)
    delivery_success_rate = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_analytics_schedule_period", "schedule_id", "period_type", "period_start"),
        UniqueConstraint("schedule_id", "period_start", "period_type", name="unique_schedule_period_analytics"),
    )


class SystemMetrics(Base):
    """System metrics database model."""
    __tablename__ = "system_metrics"

    metric_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Time period
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    period_type = Column(String(20), nullable=False)  # minute, hour, day
    
    # System metrics
    total_schedules = Column(Integer, nullable=False, default=0)
    active_schedules = Column(Integer, nullable=False, default=0)
    pending_jobs = Column(Integer, nullable=False, default=0)
    running_jobs = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    average_execution_time = Column(Float, nullable=True)
    system_cpu_percent = Column(Float, nullable=True)
    system_memory_percent = Column(Float, nullable=True)
    database_connections = Column(Integer, nullable=True)
    redis_memory_usage = Column(Integer, nullable=True)
    
    # Business metrics
    total_reports_generated = Column(Integer, nullable=False, default=0)
    total_deliveries_sent = Column(Integer, nullable=False, default=0)
    delivery_success_rate = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_metrics_timestamp_period", "timestamp", "period_type"),
    )


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)