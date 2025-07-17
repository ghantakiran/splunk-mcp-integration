"""
Email-related data models.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr, validator
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EmailStatus(str, Enum):
    """Email message status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    REJECTED = "rejected"


class EmailPriority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailType(str, Enum):
    """Email message types."""
    QUERY_REQUEST = "query_request"
    QUERY_RESPONSE = "query_response"
    REPORT = "report"
    ALERT = "alert"
    NOTIFICATION = "notification"
    AUTO_RESPONSE = "auto_response"
    SUBSCRIPTION = "subscription"


class AttachmentType(str, Enum):
    """Email attachment types."""
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    HTML = "html"
    PNG = "png"
    JPG = "jpg"
    TXT = "txt"
    ZIP = "zip"


# SQLAlchemy Models

class EmailMessage(Base):
    """Email message database model."""
    __tablename__ = "email_messages"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(String(255), unique=True, nullable=False)
    thread_id = Column(PGUUID(as_uuid=True), nullable=True)
    parent_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Email headers
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    reply_to = Column(String(255), nullable=True)
    cc = Column(JSON, nullable=True)
    bcc = Column(JSON, nullable=True)
    
    # Message content
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    
    # Message metadata
    email_type = Column(SQLEnum(EmailType), nullable=False)
    priority = Column(SQLEnum(EmailPriority), default=EmailPriority.NORMAL)
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.PENDING)
    
    # Processing metadata
    query_id = Column(PGUUID(as_uuid=True), nullable=True)
    user_id = Column(String(255), nullable=True)
    correlation_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Configuration
    template_id = Column(PGUUID(as_uuid=True), nullable=True)
    metadata = Column(JSON, nullable=True)


class EmailRecipient(Base):
    """Email recipient database model."""
    __tablename__ = "email_recipients"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    email_address = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    recipient_type = Column(String(10), nullable=False)  # to, cc, bcc
    
    # Delivery tracking
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.PENDING)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    bounce_reason = Column(String(255), nullable=True)


class EmailAttachment(Base):
    """Email attachment database model."""
    __tablename__ = "email_attachments"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    attachment_type = Column(SQLEnum(AttachmentType), nullable=False)
    
    # Storage information
    file_path = Column(String(500), nullable=True)
    storage_url = Column(String(500), nullable=True)
    checksum = Column(String(64), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_inline = Column(Boolean, default=False)
    content_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailTemplate(Base):
    """Email template database model."""
    __tablename__ = "email_templates"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Template content
    subject_template = Column(String(500), nullable=False)
    body_text_template = Column(Text, nullable=True)
    body_html_template = Column(Text, nullable=True)
    
    # Template metadata
    email_type = Column(SQLEnum(EmailType), nullable=False)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    
    # Template variables
    variables = Column(JSON, nullable=True)
    default_values = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)


class EmailQueue(Base):
    """Email queue database model."""
    __tablename__ = "email_queue"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    priority = Column(SQLEnum(EmailPriority), default=EmailPriority.NORMAL)
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Queue metadata
    queue_name = Column(String(100), default="default")
    worker_id = Column(String(255), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Status tracking
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.QUEUED)
    error_message = Column(Text, nullable=True)


class EmailLog(Base):
    """Email activity log database model."""
    __tablename__ = "email_logs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Log entry details
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Context
    user_id = Column(String(255), nullable=True)
    correlation_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Performance data
    duration_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)


class EmailThread(Base):
    """Email thread database model."""
    __tablename__ = "email_threads"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    subject = Column(String(500), nullable=False)
    
    # Participants
    participants = Column(JSON, nullable=False)
    initiator_email = Column(String(255), nullable=False)
    
    # Thread metadata
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Query context
    query_context = Column(JSON, nullable=True)
    session_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ScheduledEmail(Base):
    """Scheduled email database model."""
    __tablename__ = "scheduled_emails"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Schedule configuration
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), default="UTC")
    next_run_at = Column(DateTime, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    
    # Email configuration
    template_id = Column(PGUUID(as_uuid=True), nullable=False)
    recipients = Column(JSON, nullable=False)
    query_config = Column(JSON, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    run_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailSubscription(Base):
    """Email subscription database model."""
    __tablename__ = "email_subscriptions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False)
    
    # Subscription configuration
    subscription_type = Column(String(50), nullable=False)
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Filters and preferences
    filters = Column(JSON, nullable=True)
    preferences = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    confirmed_at = Column(DateTime, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailPreference(Base):
    """Email preference database model."""
    __tablename__ = "email_preferences"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), unique=True, nullable=False)
    
    # Email preferences
    enable_html = Column(Boolean, default=True)
    enable_attachments = Column(Boolean, default=True)
    enable_auto_responses = Column(Boolean, default=True)
    enable_threading = Column(Boolean, default=True)
    
    # Notification preferences
    alert_notifications = Column(Boolean, default=True)
    report_notifications = Column(Boolean, default=True)
    query_confirmations = Column(Boolean, default=True)
    error_notifications = Column(Boolean, default=True)
    
    # Format preferences
    default_report_format = Column(String(10), default="html")
    max_results_per_email = Column(Integer, default=1000)
    timezone = Column(String(50), default="UTC")
    
    # Security preferences
    require_encryption = Column(Boolean, default=False)
    allowed_domains = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailMetrics(Base):
    """Email metrics database model."""
    __tablename__ = "email_metrics"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Metric identification
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    
    # Dimensions
    user_id = Column(String(255), nullable=True)
    email_type = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    
    # Time dimension
    timestamp = Column(DateTime, default=datetime.utcnow)
    date_key = Column(String(10), nullable=False)  # YYYY-MM-DD
    hour_key = Column(Integer, nullable=False)  # 0-23
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)


# Pydantic Models for API

class EmailMessageCreate(BaseModel):
    """Create email message request."""
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    subject: str = Field(..., max_length=500)
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    email_type: EmailType = EmailType.NOTIFICATION
    priority: EmailPriority = EmailPriority.NORMAL
    reply_to: Optional[EmailStr] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    template_id: Optional[UUID] = None
    template_variables: Optional[Dict[str, Any]] = None
    attachments: Optional[List[str]] = None  # File paths or URLs
    metadata: Optional[Dict[str, Any]] = None


class EmailMessageResponse(BaseModel):
    """Email message response."""
    id: UUID
    message_id: str
    status: EmailStatus
    recipient_email: str
    subject: str
    email_type: EmailType
    priority: EmailPriority
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailTemplateCreate(BaseModel):
    """Create email template request."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    subject_template: str = Field(..., max_length=500)
    body_text_template: Optional[str] = None
    body_html_template: Optional[str] = None
    email_type: EmailType
    variables: Optional[List[str]] = None
    default_values: Optional[Dict[str, Any]] = None


class EmailTemplateResponse(BaseModel):
    """Email template response."""
    id: UUID
    name: str
    description: Optional[str] = None
    email_type: EmailType
    is_active: bool
    version: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class EmailStatsResponse(BaseModel):
    """Email statistics response."""
    total_sent: int
    total_delivered: int
    total_failed: int
    total_bounced: int
    delivery_rate: float
    bounce_rate: float
    recent_activity: List[Dict[str, Any]]


class EmailQueueStatus(BaseModel):
    """Email queue status response."""
    queue_name: str
    pending_count: int
    processing_count: int
    failed_count: int
    average_processing_time: float
    oldest_pending: Optional[datetime] = None