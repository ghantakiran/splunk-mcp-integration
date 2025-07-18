"""
BI-related data models for the BI Integration Service.
"""

import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator

Base = declarative_base()


class BIProvider(enum.Enum):
    """BI provider enumeration."""
    TABLEAU = "tableau"
    POWERBI = "powerbi"
    LOOKER = "looker"
    QLIK = "qlik"


class IntegrationStatus(enum.Enum):
    """Integration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    DISABLED = "disabled"


class DataSourceType(enum.Enum):
    """Data source type enumeration."""
    SPLUNK = "splunk"
    DATABASE = "database"
    FILE = "file"
    CLOUD = "cloud"
    API = "api"


class RefreshStatus(enum.Enum):
    """Refresh status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublishStatus(enum.Enum):
    """Publish status enumeration."""
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"
    UPDATING = "updating"


# SQLAlchemy Models
class BIIntegration(Base):
    """BI integration database model."""
    __tablename__ = "bi_integrations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    provider = Column(Enum(BIProvider), nullable=False)
    
    # Connection configuration
    server_url = Column(String(2048), nullable=False)
    site_id = Column(String(255))
    credentials = Column(JSON, nullable=False)  # Encrypted credentials
    connection_config = Column(JSON, default=dict)
    
    # Status and health
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    health_status = Column(String(50), default="unknown")
    
    # Publishing settings
    auto_publish = Column(Boolean, default=False)
    publish_schedule = Column(JSON, default=dict)
    default_project = Column(String(255))
    
    # Refresh settings
    auto_refresh = Column(Boolean, default=True)
    refresh_interval_minutes = Column(Integer, default=60)
    refresh_schedule = Column(JSON, default=dict)
    
    # Security settings
    encrypt_extracts = Column(Boolean, default=True)
    allow_public_access = Column(Boolean, default=False)
    permissions_config = Column(JSON, default=dict)
    
    # Metrics
    total_publishes = Column(Integer, default=0)
    successful_publishes = Column(Integer, default=0)
    failed_publishes = Column(Integer, default=0)
    total_refreshes = Column(Integer, default=0)
    successful_refreshes = Column(Integer, default=0)
    failed_refreshes = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_sources = relationship("BIDataSource", back_populates="integration")
    workbooks = relationship("BIWorkbook", back_populates="integration")
    dashboards = relationship("BIDashboard", back_populates="integration")
    reports = relationship("BIReport", back_populates="integration")
    refresh_tasks = relationship("BIRefreshTask", back_populates="integration")
    logs = relationship("BILog", back_populates="integration")


class BIDataSource(Base):
    """BI data source database model."""
    __tablename__ = "bi_data_sources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID in BI system
    
    # Data source information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum(DataSourceType), nullable=False)
    
    # Connection details
    connection_string = Column(Text)
    connection_config = Column(JSON, default=dict)
    splunk_query = Column(Text)  # SPL query for Splunk data sources
    
    # Schema information
    database_name = Column(String(255))
    table_name = Column(String(255))
    fields = Column(JSON, default=list)  # Field definitions
    
    # Security
    requires_authentication = Column(Boolean, default=True)
    security_config = Column(JSON, default=dict)
    
    # Status
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    last_refresh_at = Column(DateTime)
    last_error = Column(Text)
    
    # External data
    external_data = Column(JSON, default=dict)  # Full external record
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="data_sources")
    workbooks = relationship("BIWorkbook", back_populates="data_source")
    extracts = relationship("BIExtract", back_populates="data_source")


class BIWorkbook(Base):
    """BI workbook database model."""
    __tablename__ = "bi_workbooks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    data_source_id = Column(String(36), ForeignKey("bi_data_sources.id"), nullable=True)
    external_id = Column(String(255), nullable=False)  # ID in BI system
    
    # Workbook information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    project_name = Column(String(255))
    project_id = Column(String(255))
    
    # Content
    file_path = Column(String(2048))
    file_size_bytes = Column(Integer)
    thumbnail_url = Column(String(2048))
    
    # Publishing information
    publish_status = Column(Enum(PublishStatus), default=PublishStatus.DRAFT)
    published_at = Column(DateTime)
    published_by = Column(String(255))
    web_page_url = Column(String(2048))
    
    # Version control
    version = Column(String(50))
    version_notes = Column(Text)
    
    # Permissions
    permissions = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    # Usage statistics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    
    # Status
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    
    # External data
    external_data = Column(JSON, default=dict)  # Full external record
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="workbooks")
    data_source = relationship("BIDataSource", back_populates="workbooks")
    dashboards = relationship("BIDashboard", back_populates="workbook")


class BIDashboard(Base):
    """BI dashboard database model."""
    __tablename__ = "bi_dashboards"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    workbook_id = Column(String(36), ForeignKey("bi_workbooks.id"), nullable=True)
    external_id = Column(String(255), nullable=False)  # ID in BI system
    
    # Dashboard information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Content
    thumbnail_url = Column(String(2048))
    web_page_url = Column(String(2048))
    embed_code = Column(Text)
    
    # Layout and design
    layout_config = Column(JSON, default=dict)
    theme = Column(String(100))
    filters = Column(JSON, default=list)
    
    # Publishing information
    publish_status = Column(Enum(PublishStatus), default=PublishStatus.DRAFT)
    published_at = Column(DateTime)
    published_by = Column(String(255))
    
    # Permissions
    permissions = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    # Usage statistics
    view_count = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    
    # Status
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    
    # External data
    external_data = Column(JSON, default=dict)  # Full external record
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="dashboards")
    workbook = relationship("BIWorkbook", back_populates="dashboards")


class BIReport(Base):
    """BI report database model."""
    __tablename__ = "bi_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID in BI system
    
    # Report information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    report_type = Column(String(100))  # paginated, dashboard, etc.
    
    # Content
    file_path = Column(String(2048))
    web_page_url = Column(String(2048))
    
    # Data configuration
    dataset_id = Column(String(255))
    query = Column(Text)
    parameters = Column(JSON, default=dict)
    
    # Scheduling
    schedule_config = Column(JSON, default=dict)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    
    # Delivery
    delivery_config = Column(JSON, default=dict)
    recipients = Column(JSON, default=list)
    
    # Status
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    
    # External data
    external_data = Column(JSON, default=dict)  # Full external record
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="reports")


class BIExtract(Base):
    """BI extract database model."""
    __tablename__ = "bi_extracts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    data_source_id = Column(String(36), ForeignKey("bi_data_sources.id"), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID in BI system
    
    # Extract information
    name = Column(String(255), nullable=False)
    file_path = Column(String(2048))
    file_size_bytes = Column(Integer)
    
    # Data information
    row_count = Column(Integer)
    column_count = Column(Integer)
    data_freshness = Column(DateTime)
    
    # Refresh configuration
    refresh_type = Column(String(50))  # full, incremental
    refresh_schedule = Column(JSON, default=dict)
    auto_refresh = Column(Boolean, default=True)
    
    # Performance
    last_refresh_duration_seconds = Column(Float)
    encryption_enabled = Column(Boolean, default=True)
    
    # Status
    status = Column(Enum(RefreshStatus), default=RefreshStatus.PENDING)
    last_refresh_at = Column(DateTime)
    last_error = Column(Text)
    
    # External data
    external_data = Column(JSON, default=dict)  # Full external record
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="refresh_tasks")
    data_source = relationship("BIDataSource", back_populates="extracts")
    refresh_tasks = relationship("BIRefreshTask", back_populates="extract")


class BIRefreshTask(Base):
    """BI refresh task database model."""
    __tablename__ = "bi_refresh_tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    extract_id = Column(String(36), ForeignKey("bi_extracts.id"), nullable=True)
    
    # Task information
    task_type = Column(String(50), nullable=False)  # extract, workbook, dashboard
    target_id = Column(String(255), nullable=False)  # ID of target object
    
    # Execution details
    status = Column(Enum(RefreshStatus), nullable=False, default=RefreshStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Configuration
    refresh_type = Column(String(50))  # full, incremental
    parameters = Column(JSON, default=dict)
    
    # Results
    success = Column(Boolean, default=False)
    rows_processed = Column(Integer)
    error_message = Column(Text)
    warnings = Column(JSON, default=list)
    
    # Scheduling
    scheduled_at = Column(DateTime)
    triggered_by = Column(String(255))  # user, schedule, api
    
    # External data
    external_task_id = Column(String(255))  # Task ID in BI system
    external_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="refresh_tasks")
    extract = relationship("BIExtract", back_populates="refresh_tasks")


class BILog(Base):
    """BI activity log database model."""
    __tablename__ = "bi_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    
    # Log details
    action = Column(String(255), nullable=False)  # published, refreshed, downloaded, etc.
    resource_type = Column(String(100), nullable=False)  # workbook, dashboard, data_source
    resource_id = Column(String(255))
    resource_name = Column(String(255))
    
    # Context information
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    # Results
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    duration_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    integration = relationship("BIIntegration", back_populates="logs")


class BIMetric(Base):
    """BI metrics database model."""
    __tablename__ = "bi_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=True)
    
    # Metric details
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram
    tags = Column(JSON, default=dict)
    
    # Resource information
    resource_type = Column(String(100))  # workbook, dashboard, data_source
    resource_id = Column(String(255))
    
    # Time bucket
    timestamp = Column(DateTime, default=datetime.utcnow)
    time_bucket = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API
class BIIntegrationCreate(BaseModel):
    """Pydantic model for creating BI integrations."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    provider: BIProvider
    server_url: str = Field(..., min_length=1, max_length=2048)
    site_id: Optional[str] = Field(None, max_length=255)
    credentials: Dict[str, Any]
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    auto_publish: bool = False
    auto_refresh: bool = True
    refresh_interval_minutes: int = Field(default=60, ge=1, le=1440)
    default_project: Optional[str] = Field(None, max_length=255)
    
    @validator("credentials")
    def validate_credentials(cls, v):
        """Validate credentials format."""
        if not isinstance(v, dict):
            raise ValueError("Credentials must be a dictionary")
        return v


class BIIntegrationUpdate(BaseModel):
    """Pydantic model for updating BI integrations."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    server_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    site_id: Optional[str] = Field(None, max_length=255)
    credentials: Optional[Dict[str, Any]] = None
    connection_config: Optional[Dict[str, Any]] = None
    auto_publish: Optional[bool] = None
    auto_refresh: Optional[bool] = None
    refresh_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    default_project: Optional[str] = Field(None, max_length=255)
    status: Optional[IntegrationStatus] = None


class BIIntegrationResponse(BaseModel):
    """Pydantic model for BI integration responses."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    provider: BIProvider
    server_url: str
    site_id: Optional[str]
    status: IntegrationStatus
    last_sync_at: Optional[datetime]
    health_status: str
    auto_publish: bool
    auto_refresh: bool
    refresh_interval_minutes: int
    default_project: Optional[str]
    total_publishes: int
    successful_publishes: int
    failed_publishes: int
    total_refreshes: int
    successful_refreshes: int
    failed_refreshes: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BIDataSourceCreate(BaseModel):
    """Pydantic model for creating BI data sources."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    type: DataSourceType
    connection_string: Optional[str] = None
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    splunk_query: Optional[str] = None
    database_name: Optional[str] = Field(None, max_length=255)
    table_name: Optional[str] = Field(None, max_length=255)
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    requires_authentication: bool = True
    security_config: Dict[str, Any] = Field(default_factory=dict)


class BIDataSourceResponse(BaseModel):
    """Pydantic model for BI data source responses."""
    id: str
    integration_id: str
    external_id: str
    name: str
    description: Optional[str]
    type: DataSourceType
    database_name: Optional[str]
    table_name: Optional[str]
    fields: List[Dict[str, Any]]
    requires_authentication: bool
    status: IntegrationStatus
    last_refresh_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BIWorkbookCreate(BaseModel):
    """Pydantic model for creating BI workbooks."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    project_name: Optional[str] = Field(None, max_length=255)
    file_path: Optional[str] = Field(None, max_length=2048)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class BIWorkbookResponse(BaseModel):
    """Pydantic model for BI workbook responses."""
    id: str
    integration_id: str
    data_source_id: Optional[str]
    external_id: str
    name: str
    description: Optional[str]
    project_name: Optional[str]
    project_id: Optional[str]
    file_size_bytes: Optional[int]
    publish_status: PublishStatus
    published_at: Optional[datetime]
    web_page_url: Optional[str]
    version: Optional[str]
    tags: List[str]
    view_count: int
    download_count: int
    last_accessed_at: Optional[datetime]
    status: IntegrationStatus
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BIAnalytics(BaseModel):
    """Pydantic model for BI analytics."""
    total_integrations: int
    active_integrations: int
    total_workbooks: int
    total_dashboards: int
    total_data_sources: int
    total_refreshes: int
    successful_refreshes: int
    failed_refreshes: int
    publish_statistics: Dict[str, Any]
    usage_statistics: Dict[str, Any]
    provider_distribution: Dict[str, int]
    recent_activity: List[Dict[str, Any]]