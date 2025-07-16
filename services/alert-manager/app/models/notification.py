"""
Notification-related data models.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, EmailStr
import uuid

Base = declarative_base()


class ChannelType(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Base):
    """Notification channel database model."""
    
    __tablename__ = "notification_channels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    channel_type = Column(String(20), nullable=False)
    
    # Owner information
    created_by = Column(String(255), nullable=False, index=True)
    organization_id = Column(String(255), index=True)
    
    # Channel configuration
    config = Column(JSON, nullable=False)  # Channel-specific settings
    credentials = Column(JSON)  # Encrypted credentials
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255))
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Retry configuration
    max_retry_attempts = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=5)
    
    # Metadata
    description = Column(Text)
    tags = Column(JSON, default=lambda: [])
    metadata = Column(JSON, default=lambda: {})
    
    # Statistics
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    notifications = relationship("NotificationHistory", back_populates="channel")


class NotificationTemplate(Base):
    """Notification template database model."""
    
    __tablename__ = "notification_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    channel_type = Column(String(20), nullable=False)
    
    # Owner information
    created_by = Column(String(255), nullable=False, index=True)
    organization_id = Column(String(255), index=True)
    
    # Template content
    subject_template = Column(Text)  # For email, title for others
    body_template = Column(Text, nullable=False)
    
    # Template type and purpose
    template_type = Column(String(50), nullable=False)  # alert_triggered, alert_resolved, etc.
    severity_filter = Column(JSON)  # Which severities this template applies to
    
    # Formatting options
    format_type = Column(String(20), default="text")  # text, html, markdown
    include_charts = Column(Boolean, default=False)
    include_data = Column(Boolean, default=True)
    max_data_rows = Column(Integer, default=10)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Metadata
    description = Column(Text)
    tags = Column(JSON, default=lambda: [])
    metadata = Column(JSON, default=lambda: {})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationHistory(Base):
    """Notification delivery history database model."""
    
    __tablename__ = "notification_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    channel_id = Column(String, ForeignKey("notification_channels.id"), nullable=False, index=True)
    template_id = Column(String, ForeignKey("notification_templates.id"), index=True)
    
    # Notification details
    channel_type = Column(String(20), nullable=False)
    recipient = Column(String(500), nullable=False)
    subject = Column(Text)
    content = Column(Text, nullable=False)
    
    # Delivery information
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(20), default="normal")
    
    # Timing
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    # Retry information
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_retry_at = Column(DateTime)
    
    # Response and tracking
    external_id = Column(String(255))  # ID from external service
    response_data = Column(JSON)  # Response from external service
    error_message = Column(Text)
    error_code = Column(String(50))
    
    # Metadata
    metadata = Column(JSON, default=lambda: {})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channel = relationship("NotificationChannel", back_populates="notifications")
    template = relationship("NotificationTemplate")


# Pydantic models for API

class NotificationChannelCreate(BaseModel):
    """Notification channel creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: ChannelType
    config: Dict[str, Any] = Field(..., min_items=1)
    credentials: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=10000)
    rate_limit_per_day: int = Field(default=10000, ge=1, le=100000)
    max_retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=300)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationChannelUpdate(BaseModel):
    """Notification channel update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=100000)
    max_retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=300)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationChannelResponse(BaseModel):
    """Notification channel response model."""
    id: str
    name: str
    channel_type: str
    created_by: str
    organization_id: Optional[str]
    config: Dict[str, Any]  # Sensitive data excluded
    is_active: bool
    is_verified: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    max_retry_attempts: int
    retry_delay_seconds: int
    description: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    total_sent: int
    total_failed: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationTemplateCreate(BaseModel):
    """Notification template creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: ChannelType
    subject_template: Optional[str] = None
    body_template: str = Field(..., min_length=1)
    template_type: str = Field(..., min_length=1, max_length=50)
    severity_filter: Optional[List[str]] = None
    format_type: str = Field(default="text", pattern="^(text|html|markdown)$")
    include_charts: bool = False
    include_data: bool = True
    max_data_rows: int = Field(default=10, ge=1, le=1000)
    is_default: bool = False
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationTemplateUpdate(BaseModel):
    """Notification template update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject_template: Optional[str] = None
    body_template: Optional[str] = Field(None, min_length=1)
    template_type: Optional[str] = Field(None, min_length=1, max_length=50)
    severity_filter: Optional[List[str]] = None
    format_type: Optional[str] = Field(None, pattern="^(text|html|markdown)$")
    include_charts: Optional[bool] = None
    include_data: Optional[bool] = None
    max_data_rows: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationTemplateResponse(BaseModel):
    """Notification template response model."""
    id: str
    name: str
    channel_type: str
    created_by: str
    organization_id: Optional[str]
    subject_template: Optional[str]
    body_template: str
    template_type: str
    severity_filter: Optional[List[str]]
    format_type: str
    include_charts: bool
    include_data: bool
    max_data_rows: int
    is_active: bool
    is_default: bool
    description: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationSendRequest(BaseModel):
    """Notification send request model."""
    incident_id: str
    channel_ids: List[str] = Field(..., min_items=1)
    template_id: Optional[str] = None
    recipients: Optional[List[str]] = None  # Override default recipients
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationTestRequest(BaseModel):
    """Notification test request model."""
    channel_id: str
    template_id: Optional[str] = None
    test_recipient: str
    test_data: Dict[str, Any] = Field(default_factory=dict)


class NotificationHistoryResponse(BaseModel):
    """Notification history response model."""
    id: str
    incident_id: str
    channel_id: str
    template_id: Optional[str]
    channel_type: str
    recipient: str
    subject: Optional[str]
    status: str
    priority: str
    scheduled_at: datetime
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    attempt_count: int
    max_attempts: int
    next_retry_at: Optional[datetime]
    external_id: Optional[str]
    error_message: Optional[str]
    error_code: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChannelVerificationRequest(BaseModel):
    """Channel verification request model."""
    verification_token: Optional[str] = None
    test_message: bool = True


class ChannelVerificationResponse(BaseModel):
    """Channel verification response model."""
    channel_id: str
    is_verified: bool
    verification_sent: bool
    message: str
    expires_at: Optional[datetime] = None


# Channel-specific configuration models

class EmailChannelConfig(BaseModel):
    """Email channel configuration."""
    smtp_host: str
    smtp_port: int = 587
    smtp_use_tls: bool = True
    from_email: EmailStr
    from_name: Optional[str] = None
    default_recipients: List[EmailStr] = Field(default_factory=list)


class SlackChannelConfig(BaseModel):
    """Slack channel configuration."""
    webhook_url: Optional[str] = None
    bot_token: Optional[str] = None
    channel: str = Field(..., min_length=1)
    username: Optional[str] = "Splunk MCP Alerts"
    icon_emoji: Optional[str] = ":warning:"


class TeamsChannelConfig(BaseModel):
    """Microsoft Teams channel configuration."""
    webhook_url: str = Field(..., min_length=1)
    channel_name: Optional[str] = None


class WebhookChannelConfig(BaseModel):
    """Webhook channel configuration."""
    url: str = Field(..., min_length=1)
    method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH)$")
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=30, ge=1, le=300)
    verify_ssl: bool = True
    auth_type: Optional[str] = Field(None, pattern="^(basic|bearer|api_key)$")
    auth_credentials: Optional[Dict[str, str]] = None


class SMSChannelConfig(BaseModel):
    """SMS channel configuration."""
    provider: str = Field(default="twilio", pattern="^(twilio|aws_sns)$")
    from_number: str = Field(..., min_length=1)
    default_recipients: List[str] = Field(default_factory=list)