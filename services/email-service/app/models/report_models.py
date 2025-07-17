"""
Report-related models for email service.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ReportFormat(str, Enum):
    """Report output formats."""
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    XML = "xml"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ReportPriority(str, Enum):
    """Report generation priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# SQLAlchemy Models

class EmailReport(Base):
    """Email report database model."""
    __tablename__ = "email_reports"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Report configuration
    query_text = Column(Text, nullable=False)
    spl_query = Column(Text, nullable=True)
    search_indexes = Column(JSON, nullable=True)
    time_range = Column(String(50), nullable=False)
    
    # Output configuration
    output_formats = Column(JSON, nullable=False)  # List of ReportFormat
    include_raw_data = Column(Boolean, default=True)
    include_visualizations = Column(Boolean, default=True)
    include_summary = Column(Boolean, default=True)
    max_results = Column(Integer, default=10000)
    
    # Visualization configuration
    chart_types = Column(JSON, nullable=True)
    chart_config = Column(JSON, nullable=True)
    dashboard_config = Column(JSON, nullable=True)
    
    # Generation metadata
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    priority = Column(SQLEnum(ReportPriority), default=ReportPriority.NORMAL)
    
    # Execution tracking
    requested_by = Column(String(255), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Results metadata
    query_execution_time = Column(Float, nullable=True)
    report_generation_time = Column(Float, nullable=True)
    total_records = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # File storage
    file_paths = Column(JSON, nullable=True)  # {format: file_path}
    download_urls = Column(JSON, nullable=True)  # {format: download_url}
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Email context
    email_message_id = Column(PGUUID(as_uuid=True), nullable=True)
    correlation_id = Column(String(255), nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)


class ReportSchedule(Base):
    """Report schedule database model."""
    __tablename__ = "report_schedules"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Schedule configuration
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True)
    
    # Report template
    report_template = Column(JSON, nullable=False)
    output_formats = Column(JSON, nullable=False)
    
    # Recipients
    recipients = Column(JSON, nullable=False)  # List of email addresses
    cc_recipients = Column(JSON, nullable=True)
    bcc_recipients = Column(JSON, nullable=True)
    
    # Email configuration
    email_subject_template = Column(String(500), nullable=False)
    email_body_template = Column(Text, nullable=True)
    include_attachments = Column(Boolean, default=True)
    
    # Execution tracking
    created_by = Column(String(255), nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    next_execution_at = Column(DateTime, nullable=False)
    execution_count = Column(Integer, default=0)
    
    # Error handling
    consecutive_failures = Column(Integer, default=0)
    max_failures = Column(Integer, default=5)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    # Status tracking
    is_paused = Column(Boolean, default=False)
    paused_at = Column(DateTime, nullable=True)
    paused_by = Column(String(255), nullable=True)
    pause_reason = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ReportTemplate(Base):
    """Report template database model."""
    __tablename__ = "report_templates"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    
    # Template configuration
    template_content = Column(JSON, nullable=False)
    default_parameters = Column(JSON, nullable=True)
    required_parameters = Column(JSON, nullable=True)
    
    # Template metadata
    version = Column(String(20), default="1.0")
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Ownership
    created_by = Column(String(255), nullable=False)
    shared_with = Column(JSON, nullable=True)  # List of user IDs
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ReportExecution(Base):
    """Report execution log database model."""
    __tablename__ = "report_executions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id = Column(PGUUID(as_uuid=True), nullable=True)
    schedule_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Execution details
    execution_type = Column(String(20), nullable=False)  # manual, scheduled, api
    started_by = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Execution configuration
    parameters = Column(JSON, nullable=True)
    output_formats = Column(JSON, nullable=False)
    
    # Results
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    total_records = Column(Integer, nullable=True)
    file_sizes = Column(JSON, nullable=True)  # {format: size_bytes}
    
    # Performance metrics
    query_time_ms = Column(Float, nullable=True)
    generation_time_ms = Column(Float, nullable=True)
    total_time_ms = Column(Float, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_stack_trace = Column(Text, nullable=True)
    
    # Email delivery
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_recipients = Column(JSON, nullable=True)
    
    # Storage
    file_paths = Column(JSON, nullable=True)
    download_urls = Column(JSON, nullable=True)
    retention_until = Column(DateTime, nullable=True)


# Pydantic Models for API

class EmailReportCreate(BaseModel):
    """Create email report request."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    query_text: str = Field(..., max_length=10000)
    search_indexes: Optional[List[str]] = None
    time_range: str = Field(..., max_length=50)
    output_formats: List[ReportFormat] = Field(..., min_items=1)
    include_raw_data: bool = True
    include_visualizations: bool = True
    include_summary: bool = True
    max_results: int = Field(default=10000, ge=1, le=100000)
    chart_types: Optional[List[str]] = None
    chart_config: Optional[Dict[str, Any]] = None
    priority: ReportPriority = ReportPriority.NORMAL
    expires_in_hours: int = Field(default=168, ge=1, le=8760)  # Default 1 week
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    @validator("output_formats")
    def validate_output_formats(cls, v):
        if not v:
            raise ValueError("At least one output format is required")
        return v


class EmailReportResponse(BaseModel):
    """Email report response."""
    id: UUID
    name: str
    description: Optional[str] = None
    status: ReportStatus
    priority: ReportPriority
    requested_by: str
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    query_execution_time: Optional[float] = None
    report_generation_time: Optional[float] = None
    total_records: Optional[int] = None
    file_size_bytes: Optional[int] = None
    download_urls: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ReportScheduleCreate(BaseModel):
    """Create report schedule request."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    cron_expression: str = Field(..., max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    report_template: Dict[str, Any] = Field(...)
    output_formats: List[ReportFormat] = Field(..., min_items=1)
    recipients: List[str] = Field(..., min_items=1)
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    email_subject_template: str = Field(..., max_length=500)
    email_body_template: Optional[str] = None
    include_attachments: bool = True
    
    @validator("cron_expression")
    def validate_cron_expression(cls, v):
        # Basic validation - in real implementation, use croniter
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts")
        return v


class ReportScheduleResponse(BaseModel):
    """Report schedule response."""
    id: UUID
    name: str
    description: Optional[str] = None
    cron_expression: str
    timezone: str
    is_active: bool
    recipients: List[str]
    created_by: str
    last_executed_at: Optional[datetime] = None
    next_execution_at: datetime
    execution_count: int
    consecutive_failures: int
    is_paused: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReportTemplateCreate(BaseModel):
    """Create report template request."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    template_content: Dict[str, Any] = Field(...)
    default_parameters: Optional[Dict[str, Any]] = None
    required_parameters: Optional[List[str]] = None
    is_public: bool = False
    shared_with: Optional[List[str]] = None


class ReportTemplateResponse(BaseModel):
    """Report template response."""
    id: UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str
    is_public: bool
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReportStatsResponse(BaseModel):
    """Report statistics response."""
    total_reports: int
    pending_reports: int
    completed_reports: int
    failed_reports: int
    average_generation_time: float
    total_file_size_mb: float
    reports_by_format: Dict[str, int]
    reports_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


class ReportExecutionResponse(BaseModel):
    """Report execution response."""
    id: UUID
    report_id: Optional[UUID] = None
    schedule_id: Optional[UUID] = None
    execution_type: str
    started_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ReportStatus
    total_records: Optional[int] = None
    query_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    email_sent: bool
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True