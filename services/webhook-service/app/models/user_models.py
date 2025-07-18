"""
User-related data models for the Webhook Service.
"""

import enum
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, validator
import uuid

Base = declarative_base()


class UserQuotaType(enum.Enum):
    """User quota type enumeration."""
    ENDPOINTS = "endpoints"
    EVENTS_PER_HOUR = "events_per_hour"
    EVENTS_PER_DAY = "events_per_day"
    DELIVERIES_PER_HOUR = "deliveries_per_hour"
    DELIVERIES_PER_DAY = "deliveries_per_day"


class UserRole(enum.Enum):
    """User role enumeration."""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


# SQLAlchemy Models
class WebhookUser(Base):
    """Webhook user database model."""
    __tablename__ = "webhook_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_user_id = Column(String(36), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.BASIC)
    
    # Status
    active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    
    # Preferences
    preferences = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)


class UserWebhookSettings(Base):
    """User webhook settings database model."""
    __tablename__ = "user_webhook_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("webhook_users.id"), nullable=False)
    
    # Notification settings
    email_notifications = Column(Boolean, default=True)
    delivery_failure_notifications = Column(Boolean, default=True)
    quota_warning_notifications = Column(Boolean, default=True)
    security_notifications = Column(Boolean, default=True)
    
    # Default webhook settings
    default_timeout = Column(Integer, default=30)
    default_retry_attempts = Column(Integer, default=3)
    default_retry_delay = Column(Integer, default=300)
    
    # Security settings
    require_signature_verification = Column(Boolean, default=True)
    allowed_domains = Column(JSON, default=list)
    blocked_domains = Column(JSON, default=list)
    
    # Rate limiting preferences
    rate_limit_notifications = Column(Boolean, default=True)
    custom_rate_limits = Column(JSON, default=dict)
    
    # Analytics preferences
    enable_analytics = Column(Boolean, default=True)
    analytics_retention_days = Column(Integer, default=30)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserWebhookQuota(Base):
    """User webhook quota database model."""
    __tablename__ = "user_webhook_quotas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("webhook_users.id"), nullable=False)
    quota_type = Column(Enum(UserQuotaType), nullable=False)
    
    # Quota limits
    limit_value = Column(Integer, nullable=False)
    used_value = Column(Integer, default=0)
    
    # Time period for rate-based quotas
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Reset information
    auto_reset = Column(Boolean, default=True)
    reset_interval = Column(String(20))  # hourly, daily, weekly, monthly
    last_reset_at = Column(DateTime)
    
    # Warnings
    warning_threshold = Column(Float, default=0.8)  # 80%
    warning_sent = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models for API
class WebhookUserCreate(BaseModel):
    """Pydantic model for creating webhook users."""
    external_user_id: str = Field(..., min_length=1, max_length=36)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.BASIC
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("preferences")
    def validate_preferences(cls, v):
        """Validate user preferences."""
        if not isinstance(v, dict):
            raise ValueError("Preferences must be a dictionary")
        return v


class WebhookUserUpdate(BaseModel):
    """Pydantic model for updating webhook users."""
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    active: Optional[bool] = None
    verified: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class WebhookUserResponse(BaseModel):
    """Pydantic model for webhook user responses."""
    id: str
    external_user_id: str
    email: str
    full_name: Optional[str]
    role: UserRole
    active: bool
    verified: bool
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserWebhookSettingsCreate(BaseModel):
    """Pydantic model for creating user webhook settings."""
    email_notifications: bool = True
    delivery_failure_notifications: bool = True
    quota_warning_notifications: bool = True
    security_notifications: bool = True
    default_timeout: int = Field(default=30, ge=1, le=300)
    default_retry_attempts: int = Field(default=3, ge=0, le=10)
    default_retry_delay: int = Field(default=300, ge=0, le=3600)
    require_signature_verification: bool = True
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_domains: List[str] = Field(default_factory=list)
    rate_limit_notifications: bool = True
    custom_rate_limits: Dict[str, int] = Field(default_factory=dict)
    enable_analytics: bool = True
    analytics_retention_days: int = Field(default=30, ge=1, le=365)


class UserWebhookSettingsUpdate(BaseModel):
    """Pydantic model for updating user webhook settings."""
    email_notifications: Optional[bool] = None
    delivery_failure_notifications: Optional[bool] = None
    quota_warning_notifications: Optional[bool] = None
    security_notifications: Optional[bool] = None
    default_timeout: Optional[int] = Field(None, ge=1, le=300)
    default_retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    default_retry_delay: Optional[int] = Field(None, ge=0, le=3600)
    require_signature_verification: Optional[bool] = None
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None
    rate_limit_notifications: Optional[bool] = None
    custom_rate_limits: Optional[Dict[str, int]] = None
    enable_analytics: Optional[bool] = None
    analytics_retention_days: Optional[int] = Field(None, ge=1, le=365)


class UserWebhookSettingsResponse(BaseModel):
    """Pydantic model for user webhook settings responses."""
    id: str
    user_id: str
    email_notifications: bool
    delivery_failure_notifications: bool
    quota_warning_notifications: bool
    security_notifications: bool
    default_timeout: int
    default_retry_attempts: int
    default_retry_delay: int
    require_signature_verification: bool
    allowed_domains: List[str]
    blocked_domains: List[str]
    rate_limit_notifications: bool
    custom_rate_limits: Dict[str, int]
    enable_analytics: bool
    analytics_retention_days: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserWebhookQuotaCreate(BaseModel):
    """Pydantic model for creating user webhook quotas."""
    quota_type: UserQuotaType
    limit_value: int = Field(..., ge=0)
    auto_reset: bool = True
    reset_interval: str = Field(default="daily", regex=r'^(hourly|daily|weekly|monthly)$')
    warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class UserWebhookQuotaUpdate(BaseModel):
    """Pydantic model for updating user webhook quotas."""
    limit_value: Optional[int] = Field(None, ge=0)
    auto_reset: Optional[bool] = None
    reset_interval: Optional[str] = Field(None, regex=r'^(hourly|daily|weekly|monthly)$')
    warning_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class UserWebhookQuotaResponse(BaseModel):
    """Pydantic model for user webhook quota responses."""
    id: str
    user_id: str
    quota_type: UserQuotaType
    limit_value: int
    used_value: int
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    auto_reset: bool
    reset_interval: str
    last_reset_at: Optional[datetime]
    warning_threshold: float
    warning_sent: bool
    utilization_percentage: float
    created_at: datetime
    updated_at: datetime
    
    @validator("utilization_percentage", pre=True, always=True)
    def calculate_utilization(cls, v, values):
        """Calculate utilization percentage."""
        limit_value = values.get("limit_value", 1)
        used_value = values.get("used_value", 0)
        if limit_value > 0:
            return (used_value / limit_value) * 100
        return 0.0
    
    class Config:
        from_attributes = True


class UserStatistics(BaseModel):
    """Pydantic model for user statistics."""
    total_endpoints: int
    active_endpoints: int
    total_events_today: int
    total_deliveries_today: int
    successful_deliveries_today: int
    failed_deliveries_today: int
    quota_utilization: Dict[str, float]
    recent_activity: List[Dict[str, Any]]