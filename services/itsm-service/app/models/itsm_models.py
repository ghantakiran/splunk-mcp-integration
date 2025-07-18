"""
ITSM-related data models for the ITSM Service.
"""

import enum
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator
import uuid

Base = declarative_base()


class ITSMProvider(enum.Enum):
    """ITSM provider enumeration."""
    SERVICENOW = "servicenow"
    JIRA = "jira"
    REMEDY = "remedy"
    CHERWELL = "cherwell"


class TicketStatus(enum.Enum):
    """Ticket status enumeration."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPriority(enum.Enum):
    """Ticket priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SyncStatus(enum.Enum):
    """Synchronization status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(enum.Enum):
    """Workflow status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


# SQLAlchemy Models
class ITSMIntegration(Base):
    """ITSM integration database model."""
    __tablename__ = "itsm_integrations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    provider = Column(Enum(ITSMProvider), nullable=False)
    
    # Connection configuration
    endpoint_url = Column(String(2048), nullable=False)
    credentials = Column(JSON, nullable=False)  # Encrypted credentials
    connection_config = Column(JSON, default=dict)
    
    # Status and health
    active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    health_status = Column(String(50), default="unknown")
    
    # Synchronization settings
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=15)
    bidirectional_sync = Column(Boolean, default=True)
    
    # Mapping configuration
    field_mappings = Column(JSON, default=dict)
    table_mappings = Column(JSON, default=dict)
    
    # Metrics
    total_syncs = Column(Integer, default=0)
    successful_syncs = Column(Integer, default=0)
    failed_syncs = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tickets = relationship("ITSMTicket", back_populates="integration")
    sync_records = relationship("ITSMSyncRecord", back_populates="integration")
    logs = relationship("ITSMLog", back_populates="integration")


class ITSMTicket(Base):
    """ITSM ticket database model."""
    __tablename__ = "itsm_tickets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID in external system
    external_table = Column(String(100), nullable=False)  # Table/type in external system
    
    # Ticket information
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.NEW)
    priority = Column(Enum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    category = Column(String(255))
    subcategory = Column(String(255))
    
    # Assignment
    assigned_to = Column(String(255))
    assigned_group = Column(String(255))
    reporter = Column(String(255))
    
    # Timing
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    due_date = Column(DateTime)
    resolved_date = Column(DateTime)
    closed_date = Column(DateTime)
    
    # Additional fields
    external_data = Column(JSON, default=dict)  # Full external record
    custom_fields = Column(JSON, default=dict)
    attachments = Column(JSON, default=list)
    
    # Synchronization
    last_synced_at = Column(DateTime)
    sync_version = Column(String(50))
    sync_conflicts = Column(JSON, default=list)
    
    # Local tracking
    created_by = Column(String(36))  # User who created locally
    local_changes = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("ITSMIntegration", back_populates="tickets")
    sync_records = relationship("ITSMSyncRecord", back_populates="ticket")


class ITSMWorkflow(Base):
    """ITSM workflow database model."""
    __tablename__ = "itsm_workflows"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=False)
    
    # Workflow definition
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT)
    
    # Trigger configuration
    trigger_type = Column(String(100), nullable=False)  # event, schedule, manual
    trigger_config = Column(JSON, default=dict)
    
    # Workflow steps
    steps = Column(JSON, nullable=False)  # Array of workflow steps
    variables = Column(JSON, default=dict)  # Workflow variables
    
    # Execution settings
    timeout_minutes = Column(Integer, default=30)
    retry_attempts = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    
    # Metrics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    last_execution_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ITSMSyncRecord(Base):
    """ITSM synchronization record database model."""
    __tablename__ = "itsm_sync_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=False)
    ticket_id = Column(String(36), ForeignKey("itsm_tickets.id"), nullable=True)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # full, incremental, single
    direction = Column(String(20), nullable=False)  # inbound, outbound, bidirectional
    status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    
    # Record information
    external_id = Column(String(255))
    external_table = Column(String(100))
    operation = Column(String(20))  # create, update, delete
    
    # Sync data
    source_data = Column(JSON, default=dict)
    target_data = Column(JSON, default=dict)
    field_mappings = Column(JSON, default=dict)
    
    # Results
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    conflicts = Column(JSON, default=list)
    resolution = Column(String(50))  # auto, manual, skip
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    processing_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("ITSMIntegration", back_populates="sync_records")
    ticket = relationship("ITSMTicket", back_populates="sync_records")


class ITSMLog(Base):
    """ITSM activity log database model."""
    __tablename__ = "itsm_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    
    # Log details
    action = Column(String(255), nullable=False)  # created, updated, synced, etc.
    resource_type = Column(String(100), nullable=False)  # ticket, workflow, integration
    resource_id = Column(String(255))
    
    # Context information
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    # Results
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    integration = relationship("ITSMIntegration", back_populates="logs")


class ITSMMetric(Base):
    """ITSM metrics database model."""
    __tablename__ = "itsm_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=True)
    
    # Metric details
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram
    tags = Column(JSON, default=dict)
    
    # Time bucket
    timestamp = Column(DateTime, default=datetime.utcnow)
    time_bucket = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API
class ITSMIntegrationCreate(BaseModel):
    """Pydantic model for creating ITSM integrations."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    provider: ITSMProvider
    endpoint_url: str = Field(..., min_length=1, max_length=2048)
    credentials: Dict[str, Any]
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    sync_enabled: bool = True
    sync_interval_minutes: int = Field(default=15, ge=1, le=1440)
    bidirectional_sync: bool = True
    field_mappings: Dict[str, Any] = Field(default_factory=dict)
    table_mappings: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("credentials")
    def validate_credentials(cls, v):
        """Validate credentials format."""
        if not isinstance(v, dict):
            raise ValueError("Credentials must be a dictionary")
        return v


class ITSMIntegrationUpdate(BaseModel):
    """Pydantic model for updating ITSM integrations."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    endpoint_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    credentials: Optional[Dict[str, Any]] = None
    connection_config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    bidirectional_sync: Optional[bool] = None
    field_mappings: Optional[Dict[str, Any]] = None
    table_mappings: Optional[Dict[str, Any]] = None


class ITSMIntegrationResponse(BaseModel):
    """Pydantic model for ITSM integration responses."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    provider: ITSMProvider
    endpoint_url: str
    active: bool
    last_sync_at: Optional[datetime]
    health_status: str
    sync_enabled: bool
    sync_interval_minutes: int
    bidirectional_sync: bool
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITSMTicketCreate(BaseModel):
    """Pydantic model for creating ITSM tickets."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TicketPriority = TicketPriority.MEDIUM
    category: Optional[str] = Field(None, max_length=255)
    subcategory: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional[str] = Field(None, max_length=255)
    assigned_group: Optional[str] = Field(None, max_length=255)
    due_date: Optional[datetime] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("custom_fields")
    def validate_custom_fields(cls, v):
        """Validate custom fields format."""
        if not isinstance(v, dict):
            raise ValueError("Custom fields must be a dictionary")
        return v


class ITSMTicketUpdate(BaseModel):
    """Pydantic model for updating ITSM tickets."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[str] = Field(None, max_length=255)
    subcategory: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional[str] = Field(None, max_length=255)
    assigned_group: Optional[str] = Field(None, max_length=255)
    due_date: Optional[datetime] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ITSMTicketResponse(BaseModel):
    """Pydantic model for ITSM ticket responses."""
    id: str
    integration_id: str
    external_id: str
    external_table: str
    title: str
    description: Optional[str]
    status: TicketStatus
    priority: TicketPriority
    category: Optional[str]
    subcategory: Optional[str]
    assigned_to: Optional[str]
    assigned_group: Optional[str]
    reporter: Optional[str]
    created_date: Optional[datetime]
    updated_date: Optional[datetime]
    due_date: Optional[datetime]
    resolved_date: Optional[datetime]
    closed_date: Optional[datetime]
    custom_fields: Dict[str, Any]
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITSMWorkflowCreate(BaseModel):
    """Pydantic model for creating ITSM workflows."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    trigger_type: str = Field(..., regex=r'^(event|schedule|manual)$')
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    steps: List[Dict[str, Any]] = Field(..., min_items=1)
    variables: Dict[str, Any] = Field(default_factory=dict)
    timeout_minutes: int = Field(default=30, ge=1, le=1440)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=0, le=3600)
    
    @validator("steps")
    def validate_steps(cls, v):
        """Validate workflow steps."""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("Steps must be a non-empty list")
        for step in v:
            if not isinstance(step, dict) or "type" not in step:
                raise ValueError("Each step must be a dictionary with a 'type' field")
        return v


class ITSMWorkflowResponse(BaseModel):
    """Pydantic model for ITSM workflow responses."""
    id: str
    user_id: str
    integration_id: str
    name: str
    description: Optional[str]
    status: WorkflowStatus
    trigger_type: str
    trigger_config: Dict[str, Any]
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any]
    timeout_minutes: int
    retry_attempts: int
    retry_delay_seconds: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    last_execution_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITSMAnalytics(BaseModel):
    """Pydantic model for ITSM analytics."""
    total_integrations: int
    active_integrations: int
    total_tickets: int
    tickets_by_status: Dict[str, int]
    tickets_by_priority: Dict[str, int]
    sync_statistics: Dict[str, Any]
    workflow_statistics: Dict[str, Any]
    provider_distribution: Dict[str, int]
    recent_activity: List[Dict[str, Any]]