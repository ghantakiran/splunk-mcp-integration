"""
Multi-tenant models for Splunk Cloud Authentication Service
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
from sqlalchemy import String, Text, JSON, DateTime, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base


class TenantStatus(str, Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DEACTIVATED = "deactivated"


class TenantPlan(str, Enum):
    """Tenant subscription plan"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


# SQLAlchemy Models
class Tenant(Base):
    """Multi-tenant model for cloud authentication"""
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Tenant identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Tenant configuration
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus), 
        default=TenantStatus.PENDING
    )
    plan: Mapped[TenantPlan] = mapped_column(
        SQLEnum(TenantPlan), 
        default=TenantPlan.FREE
    )
    
    # Contact information
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Address information
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Tenant settings
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    custom_branding: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Subscription information
    subscription_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    subscription_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    billing_cycle: Mapped[Optional[BillingCycle]] = mapped_column(SQLEnum(BillingCycle))
    
    # Resource quotas
    quota_users: Mapped[int] = mapped_column(Integer, default=100)
    quota_api_requests_per_hour: Mapped[int] = mapped_column(Integer, default=10000)
    quota_storage_gb: Mapped[int] = mapped_column(Integer, default=10)
    quota_cloud_instances: Mapped[int] = mapped_column(Integer, default=5)
    
    # Usage tracking
    current_users: Mapped[int] = mapped_column(Integer, default=0)
    current_api_requests_hour: Mapped[int] = mapped_column(Integer, default=0)
    current_storage_gb: Mapped[float] = mapped_column(Integer, default=0)
    current_cloud_instances: Mapped[int] = mapped_column(Integer, default=0)
    
    # Tenant lifecycle
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text)


class TenantCloudInstance(Base):
    """Splunk Cloud instances associated with tenants"""
    __tablename__ = "tenant_cloud_instances"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Tenant association
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # Cloud instance details
    instance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    instance_url: Mapped[str] = mapped_column(String(500), nullable=False)
    instance_region: Mapped[str] = mapped_column(String(100), nullable=False)
    instance_stack: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Authentication configuration
    auth_method: Mapped[str] = mapped_column(String(50), default="oauth2")
    client_id: Mapped[Optional[str]] = mapped_column(String(255))
    client_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    
    # Instance metadata
    splunk_version: Mapped[Optional[str]] = mapped_column(String(50))
    deployment_type: Mapped[str] = mapped_column(String(50), default="cloud")
    
    # Health and monitoring
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    health_check_interval: Mapped[int] = mapped_column(Integer, default=300)  # 5 minutes
    
    # Instance configuration
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Usage statistics
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    query_count: Mapped[int] = mapped_column(Integer, default=0)
    data_volume_gb: Mapped[float] = mapped_column(Integer, default=0)


class TenantUsageLog(Base):
    """Tenant resource usage logging"""
    __tablename__ = "tenant_usage_logs"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Tenant association
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # Usage metrics
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Integer, nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Time period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Additional context
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


# Pydantic Models for API
class TenantCreate(BaseModel):
    """Tenant creation model"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    admin_email: EmailStr
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    plan: TenantPlan = TenantPlan.FREE
    
    # Address information
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Custom quotas (optional, will use plan defaults if not specified)
    quota_users: Optional[int] = None
    quota_api_requests_per_hour: Optional[int] = None
    quota_storage_gb: Optional[int] = None
    quota_cloud_instances: Optional[int] = None
    
    @validator("slug")
    def validate_slug(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug can only contain alphanumeric characters, hyphens, and underscores")
        return v.lower()


class TenantUpdate(BaseModel):
    """Tenant update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    status: Optional[TenantStatus] = None
    plan: Optional[TenantPlan] = None
    
    # Address information
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Settings and branding
    settings: Optional[Dict[str, Any]] = None
    custom_branding: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Tenant response model"""
    id: str
    name: str
    slug: str
    domain: Optional[str]
    status: TenantStatus
    plan: TenantPlan
    admin_email: str
    contact_name: Optional[str]
    contact_phone: Optional[str]
    
    # Resource quotas and usage
    quota_users: int
    quota_api_requests_per_hour: int
    quota_storage_gb: int
    quota_cloud_instances: int
    current_users: int
    current_api_requests_hour: int
    current_storage_gb: float
    current_cloud_instances: int
    
    # Dates
    created_at: datetime
    activated_at: Optional[datetime]
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    
    class Config:
        from_attributes = True


class TenantCloudInstanceCreate(BaseModel):
    """Cloud instance creation model"""
    instance_name: str = Field(..., min_length=1, max_length=255)
    instance_url: str = Field(..., min_length=1, max_length=500)
    instance_region: str = Field(..., min_length=1, max_length=100)
    instance_stack: Optional[str] = Field(None, max_length=100)
    auth_method: str = Field(default="oauth2", max_length=50)
    client_id: Optional[str] = Field(None, max_length=255)
    client_secret: Optional[str] = Field(None, max_length=255)
    configuration: Optional[Dict[str, Any]] = None


class TenantCloudInstanceResponse(BaseModel):
    """Cloud instance response model"""
    id: str
    tenant_id: str
    instance_name: str
    instance_url: str
    instance_region: str
    instance_stack: Optional[str]
    auth_method: str
    client_id: Optional[str]
    splunk_version: Optional[str]
    deployment_type: str
    is_healthy: bool
    last_health_check: Optional[datetime]
    last_used: Optional[datetime]
    query_count: int
    data_volume_gb: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantUsageResponse(BaseModel):
    """Tenant usage statistics response"""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    
    # Usage statistics
    total_users: int
    total_api_requests: int
    total_storage_gb: float
    total_cloud_instances: int
    
    # Quota utilization percentages
    users_utilization: float
    api_requests_utilization: float
    storage_utilization: float
    cloud_instances_utilization: float
    
    # Additional metrics
    avg_response_time_ms: Optional[float]
    error_rate: Optional[float]
    uptime_percentage: Optional[float]


class TenantSettings(BaseModel):
    """Tenant settings model"""
    # Authentication settings
    enable_sso: bool = False
    require_mfa: bool = False
    password_policy: Optional[Dict[str, Any]] = None
    
    # Session settings
    session_timeout_minutes: int = 480  # 8 hours
    concurrent_sessions_limit: int = 10
    
    # API settings
    api_rate_limit_override: Optional[int] = None
    enable_api_analytics: bool = True
    
    # Notification settings
    enable_email_notifications: bool = True
    notification_email: Optional[str] = None
    
    # Cloud instance settings
    auto_discover_instances: bool = True
    health_check_interval: int = 300
    
    # Custom settings
    custom_fields: Optional[Dict[str, Any]] = None