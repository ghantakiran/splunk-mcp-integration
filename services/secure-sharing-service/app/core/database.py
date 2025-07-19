"""
Database configuration and models for the Secure Sharing Service.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, Integer, Text, Boolean, Float,
    JSON, Enum as SQLEnum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.models.sharing_models import (
    ShareType, SharePermission, ShareStatus, AccessMethod,
    ExpirationPolicy
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
class SharedResource(Base):
    """Shared resource database model."""
    __tablename__ = "shared_resources"

    share_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_type = Column(SQLEnum(ShareType), nullable=False, index=True)
    resource_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False, index=True)
    resource_name = Column(String(255), nullable=False)
    share_token = Column(String(255), nullable=False, unique=True, index=True)
    
    # Access configuration
    permissions = Column(JSON, nullable=False)  # List of SharePermission values
    access_method = Column(SQLEnum(AccessMethod), nullable=False, default=AccessMethod.LINK)
    requires_authentication = Column(Boolean, nullable=False, default=True)
    
    # Expiration configuration
    expiration_policy = Column(SQLEnum(ExpirationPolicy), nullable=False, default=ExpirationPolicy.AFTER_TIME)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    max_views = Column(Integer, nullable=True)
    max_downloads = Column(Integer, nullable=True)
    
    # Security configuration
    password_protected = Column(Boolean, nullable=False, default=False)
    password_hash = Column(String(255), nullable=True)  # Hashed password
    allowed_domains = Column(JSON, nullable=True)  # List of allowed domains
    allowed_users = Column(JSON, nullable=True)  # List of allowed user emails
    
    # Display configuration
    description = Column(Text, nullable=True)
    custom_message = Column(Text, nullable=True)
    branding_enabled = Column(Boolean, nullable=False, default=True)
    
    # Status and metrics
    status = Column(SQLEnum(ShareStatus), nullable=False, default=ShareStatus.ACTIVE, index=True)
    total_views = Column(Integer, nullable=False, default=0)
    total_downloads = Column(Integer, nullable=False, default=0)
    unique_viewers = Column(Integer, nullable=False, default=0)
    
    # Notification configuration
    notify_on_access = Column(Boolean, nullable=False, default=False)
    notify_on_expiration = Column(Boolean, nullable=False, default=True)
    notification_emails = Column(JSON, nullable=True)
    
    # Tracking
    created_by = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Resource data cache (optional, for performance)
    cached_resource_data = Column(JSON, nullable=True)
    cache_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    access_logs = relationship("ShareAccessLog", back_populates="shared_resource", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_shared_resource_type_status", "resource_type", "status"),
        Index("idx_shared_resource_created_by", "created_by"),
        Index("idx_shared_resource_expires_at", "expires_at"),
        Index("idx_shared_resource_created_at", "created_at"),
        Index("idx_shared_resource_token", "share_token"),
        UniqueConstraint("resource_type", "resource_id", "created_by", name="unique_resource_creator_share"),
    )


class ShareAccessLog(Base):
    """Share access log database model."""
    __tablename__ = "share_access_logs"

    log_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    share_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("shared_resources.share_id"), nullable=False, index=True)
    
    # Access details
    accessed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    user_email = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    referrer = Column(String(1000), nullable=True)
    
    # Action details
    action = Column(String(50), nullable=False, index=True)  # view, download, interact, etc.
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)
    
    # Session information
    session_id = Column(String(255), nullable=True, index=True)
    session_duration = Column(Float, nullable=True)  # Duration in seconds
    
    # Geographic and device information
    country = Column(String(2), nullable=True)  # ISO country code
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    shared_resource = relationship("SharedResource", back_populates="access_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_access_log_share_action", "share_id", "action"),
        Index("idx_access_log_user_accessed", "user_email", "accessed_at"),
        Index("idx_access_log_ip_accessed", "ip_address", "accessed_at"),
        Index("idx_access_log_success_accessed", "success", "accessed_at"),
    )


class ShareInvitation(Base):
    """Share invitation database model for email invites."""
    __tablename__ = "share_invitations"

    invitation_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    share_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("shared_resources.share_id"), nullable=False, index=True)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    invitation_token = Column(String(255), nullable=False, unique=True, index=True)
    personal_message = Column(Text, nullable=True)
    
    # Status tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_uses = Column(Integer, nullable=False, default=1)
    uses_count = Column(Integer, nullable=False, default=0)
    
    # Tracking
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_invitation_email_share", "email", "share_id"),
        Index("idx_invitation_token", "invitation_token"),
        Index("idx_invitation_expires_at", "expires_at"),
    )


class ShareMetrics(Base):
    """Share metrics database model for analytics."""
    __tablename__ = "share_metrics"

    metric_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    share_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("shared_resources.share_id"), nullable=True, index=True)
    
    # Time period
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Access metrics
    total_views = Column(Integer, nullable=False, default=0)
    total_downloads = Column(Integer, nullable=False, default=0)
    unique_viewers = Column(Integer, nullable=False, default=0)
    new_viewers = Column(Integer, nullable=False, default=0)
    returning_viewers = Column(Integer, nullable=False, default=0)
    
    # Engagement metrics
    average_session_duration = Column(Float, nullable=True)
    bounce_rate = Column(Float, nullable=True)  # Percentage
    conversion_rate = Column(Float, nullable=True)  # Percentage
    
    # Geographic metrics
    top_countries = Column(JSON, nullable=True)  # Country -> count mapping
    top_cities = Column(JSON, nullable=True)  # City -> count mapping
    
    # Device metrics
    device_breakdown = Column(JSON, nullable=True)  # Device type -> count
    browser_breakdown = Column(JSON, nullable=True)  # Browser -> count
    os_breakdown = Column(JSON, nullable=True)  # OS -> count
    
    # Referrer metrics
    top_referrers = Column(JSON, nullable=True)  # Referrer -> count
    direct_traffic = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    average_load_time = Column(Float, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    error_rate = Column(Float, nullable=True)  # Percentage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("share_id", "date", "period_type", name="unique_share_date_period_metrics"),
        Index("idx_share_metrics_date_period", "date", "period_type"),
    )


class ShareConfiguration(Base):
    """Share configuration database model for system settings."""
    __tablename__ = "share_configurations"

    config_id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Configuration scope
    scope = Column(String(50), nullable=False, index=True)  # global, user, resource_type
    scope_id = Column(String(255), nullable=True, index=True)  # user_id or resource_type
    
    # Settings
    max_shares_per_user = Column(Integer, nullable=True)
    max_share_duration_days = Column(Integer, nullable=True)
    default_expiration_hours = Column(Integer, nullable=True)
    allowed_permissions = Column(JSON, nullable=True)  # List of allowed permissions
    allowed_access_methods = Column(JSON, nullable=True)  # List of allowed access methods
    
    # Security settings
    require_authentication = Column(Boolean, nullable=True)
    require_password_protection = Column(Boolean, nullable=True)
    allowed_domains_only = Column(Boolean, nullable=True)
    max_views_limit = Column(Integer, nullable=True)
    max_downloads_limit = Column(Integer, nullable=True)
    
    # Branding and customization
    custom_branding = Column(JSON, nullable=True)
    custom_css = Column(Text, nullable=True)
    custom_footer = Column(Text, nullable=True)
    
    # Notification settings
    notify_on_share_creation = Column(Boolean, nullable=False, default=False)
    notify_on_share_access = Column(Boolean, nullable=False, default=False)
    notification_email_template = Column(Text, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="unique_scope_configuration"),
        Index("idx_config_scope", "scope", "scope_id"),
    )


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)