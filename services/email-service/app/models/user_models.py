"""
User-related models for email service.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EmailUser(Base):
    """Email user database model."""
    __tablename__ = "email_users"
    
    id = Column(String(255), primary_key=True)  # External user ID
    email_address = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    
    # User status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Authentication context
    organization = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    roles = Column(JSON, nullable=True)
    permissions = Column(JSON, nullable=True)
    
    # Splunk context
    splunk_user_id = Column(String(255), nullable=True)
    accessible_indexes = Column(JSON, nullable=True)
    default_indexes = Column(JSON, nullable=True)
    
    # Usage statistics
    total_emails_sent = Column(Integer, default=0)
    total_emails_received = Column(Integer, default=0)
    total_queries_sent = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class UserEmailSettings(Base):
    """User email settings database model."""
    __tablename__ = "user_email_settings"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), unique=True, nullable=False)
    
    # Email format preferences
    preferred_format = Column(String(10), default="html")  # html, text
    enable_rich_formatting = Column(Boolean, default=True)
    enable_inline_images = Column(Boolean, default=True)
    
    # Query preferences
    auto_execute_queries = Column(Boolean, default=False)
    require_confirmation = Column(Boolean, default=True)
    max_results_per_query = Column(Integer, default=1000)
    default_time_range = Column(String(50), default="last_hour")
    
    # Report preferences
    default_report_format = Column(String(10), default="pdf")
    include_raw_data = Column(Boolean, default=True)
    include_visualizations = Column(Boolean, default=True)
    compress_attachments = Column(Boolean, default=True)
    
    # Notification preferences
    notify_on_completion = Column(Boolean, default=True)
    notify_on_errors = Column(Boolean, default=True)
    notify_on_large_results = Column(Boolean, default=True)
    large_results_threshold = Column(Integer, default=10000)
    
    # Security preferences
    require_secure_delivery = Column(Boolean, default=False)
    allowed_sender_domains = Column(JSON, nullable=True)
    blocked_sender_domains = Column(JSON, nullable=True)
    
    # Response preferences
    enable_auto_responses = Column(Boolean, default=True)
    auto_response_template = Column(Text, nullable=True)
    response_delay_seconds = Column(Integer, default=5)
    
    # Rate limiting preferences
    max_emails_per_hour = Column(Integer, default=50)
    max_queries_per_hour = Column(Integer, default=20)
    max_reports_per_day = Column(Integer, default=10)
    
    # Language and localization
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    date_format = Column(String(20), default="YYYY-MM-DD")
    time_format = Column(String(10), default="24h")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserSubscription(Base):
    """User subscription database model."""
    __tablename__ = "user_subscriptions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False)
    
    # Subscription details
    subscription_name = Column(String(255), nullable=False)
    subscription_type = Column(String(50), nullable=False)  # alert, report, digest
    description = Column(Text, nullable=True)
    
    # Query configuration
    query_text = Column(Text, nullable=False)
    spl_query = Column(Text, nullable=True)
    search_indexes = Column(JSON, nullable=True)
    time_range = Column(String(50), default="last_hour")
    
    # Schedule configuration
    frequency = Column(String(20), nullable=False)  # realtime, hourly, daily, weekly, monthly
    cron_expression = Column(String(100), nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Delivery configuration
    delivery_format = Column(String(10), default="html")
    include_attachments = Column(Boolean, default=True)
    attachment_formats = Column(JSON, nullable=True)  # ["csv", "pdf"]
    
    # Filtering and conditions
    filters = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    threshold_config = Column(JSON, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_executed_at = Column(DateTime, nullable=True)
    next_execution_at = Column(DateTime, nullable=True)
    execution_count = Column(Integer, default=0)
    
    # Error handling
    consecutive_failures = Column(Integer, default=0)
    max_failures = Column(Integer, default=5)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API

class EmailUserCreate(BaseModel):
    """Create email user request."""
    id: str = Field(..., max_length=255)
    email_address: EmailStr
    name: Optional[str] = Field(None, max_length=255)
    organization: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    roles: Optional[List[str]] = None
    permissions: Optional[Dict[str, Any]] = None
    splunk_user_id: Optional[str] = Field(None, max_length=255)
    accessible_indexes: Optional[List[str]] = None
    default_indexes: Optional[List[str]] = None


class EmailUserResponse(BaseModel):
    """Email user response."""
    id: str
    email_address: str
    name: Optional[str] = None
    is_active: bool
    is_verified: bool
    organization: Optional[str] = None
    department: Optional[str] = None
    roles: Optional[List[str]] = None
    total_emails_sent: int
    total_emails_received: int
    total_queries_sent: int
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserEmailSettingsCreate(BaseModel):
    """Create user email settings request."""
    user_id: str = Field(..., max_length=255)
    preferred_format: str = Field(default="html", regex="^(html|text)$")
    enable_rich_formatting: bool = True
    auto_execute_queries: bool = False
    require_confirmation: bool = True
    max_results_per_query: int = Field(default=1000, ge=1, le=50000)
    default_time_range: str = Field(default="last_hour", max_length=50)
    default_report_format: str = Field(default="pdf", regex="^(pdf|html|csv|xlsx)$")
    notify_on_completion: bool = True
    notify_on_errors: bool = True
    enable_auto_responses: bool = True
    max_emails_per_hour: int = Field(default=50, ge=1, le=1000)
    max_queries_per_hour: int = Field(default=20, ge=1, le=100)
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)


class UserEmailSettingsResponse(BaseModel):
    """User email settings response."""
    id: UUID
    user_id: str
    preferred_format: str
    enable_rich_formatting: bool
    auto_execute_queries: bool
    require_confirmation: bool
    max_results_per_query: int
    default_time_range: str
    default_report_format: str
    notify_on_completion: bool
    notify_on_errors: bool
    enable_auto_responses: bool
    max_emails_per_hour: int
    max_queries_per_hour: int
    language: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserSubscriptionCreate(BaseModel):
    """Create user subscription request."""
    subscription_name: str = Field(..., max_length=255)
    subscription_type: str = Field(..., regex="^(alert|report|digest)$")
    description: Optional[str] = None
    query_text: str = Field(..., max_length=10000)
    search_indexes: Optional[List[str]] = None
    time_range: str = Field(default="last_hour", max_length=50)
    frequency: str = Field(..., regex="^(realtime|hourly|daily|weekly|monthly)$")
    cron_expression: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    delivery_format: str = Field(default="html", regex="^(html|text|pdf)$")
    include_attachments: bool = True
    attachment_formats: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None


class UserSubscriptionResponse(BaseModel):
    """User subscription response."""
    id: UUID
    user_id: str
    subscription_name: str
    subscription_type: str
    description: Optional[str] = None
    query_text: str
    frequency: str
    timezone: str
    delivery_format: str
    is_active: bool
    last_executed_at: Optional[datetime] = None
    next_execution_at: Optional[datetime] = None
    execution_count: int
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    """User statistics response."""
    total_users: int
    active_users: int
    verified_users: int
    total_emails_today: int
    total_queries_today: int
    top_users: List[Dict[str, Any]]
    usage_by_hour: List[Dict[str, Any]]


class UserActivityResponse(BaseModel):
    """User activity response."""
    user_id: str
    email_address: str
    recent_emails: List[Dict[str, Any]]
    recent_queries: List[Dict[str, Any]]
    active_subscriptions: List[Dict[str, Any]]
    last_activity: Optional[datetime] = None