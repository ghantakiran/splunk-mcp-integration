"""
User-related data models for the BI Integration Service.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

Base = declarative_base()


class BIUser(Base):
    """BI user database model."""
    __tablename__ = "bi_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    
    # BI-specific user information
    external_ids = Column(JSON, default=dict)  # Provider-specific user IDs
    roles = Column(JSON, default=list)  # BI roles
    permissions = Column(JSON, default=list)  # BI permissions
    
    # User preferences
    default_provider = Column(String(50))
    preferred_export_format = Column(String(50), default="pdf")
    notification_preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # BI-specific preferences
    default_refresh_schedule = Column(JSON, default=dict)
    auto_publish_enabled = Column(Boolean, default=False)
    email_on_publish = Column(Boolean, default=True)
    email_on_refresh_failure = Column(Boolean, default=True)
    
    # Usage statistics
    total_workbooks_created = Column(Integer, default=0)
    total_dashboards_created = Column(Integer, default=0)
    total_refreshes_triggered = Column(Integer, default=0)
    last_activity_at = Column(DateTime)
    
    # Status
    active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = relationship("UserBISettings", back_populates="user", uselist=False)
    integrations = relationship("UserBIIntegration", back_populates="user")


class UserBISettings(Base):
    """User BI settings database model."""
    __tablename__ = "user_bi_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("bi_users.id"), nullable=False, unique=True)
    
    # Publishing preferences
    default_project = Column(String(255))
    auto_publish_workbooks = Column(Boolean, default=False)
    auto_publish_dashboards = Column(Boolean, default=False)
    publish_with_tabs = Column(Boolean, default=True)
    show_selection_as_tabs = Column(Boolean, default=False)
    
    # Refresh preferences
    default_refresh_interval = Column(Integer, default=60)  # minutes
    auto_refresh_on_publish = Column(Boolean, default=True)
    incremental_refresh_enabled = Column(Boolean, default=True)
    
    # Data source preferences
    default_connection_timeout = Column(Integer, default=300)  # seconds
    max_extract_rows = Column(Integer, default=1000000)
    enable_extract_encryption = Column(Boolean, default=True)
    
    # Notification preferences
    email_on_publish_success = Column(Boolean, default=False)
    email_on_publish_failure = Column(Boolean, default=True)
    email_on_refresh_success = Column(Boolean, default=False)
    email_on_refresh_failure = Column(Boolean, default=True)
    slack_notifications = Column(Boolean, default=False)
    teams_notifications = Column(Boolean, default=False)
    
    # UI preferences
    dashboard_theme = Column(String(50), default="default")
    show_performance_recorder = Column(Boolean, default=False)
    auto_save_enabled = Column(Boolean, default=True)
    show_toolbar = Column(Boolean, default=True)
    
    # Export preferences
    default_export_format = Column(String(50), default="pdf")
    export_quality = Column(String(50), default="high")
    include_data = Column(Boolean, default=False)
    max_export_rows = Column(Integer, default=10000)
    
    # Security preferences
    require_ssl = Column(Boolean, default=True)
    session_timeout_minutes = Column(Integer, default=480)  # 8 hours
    enable_guest_access = Column(Boolean, default=False)
    
    # Performance preferences
    query_timeout_seconds = Column(Integer, default=300)
    max_concurrent_refreshes = Column(Integer, default=5)
    cache_results = Column(Boolean, default=True)
    cache_timeout_minutes = Column(Integer, default=60)
    
    # Advanced settings
    enable_javascript = Column(Boolean, default=False)
    allow_url_access = Column(Boolean, default=False)
    custom_css = Column(Text)
    custom_javascript = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("BIUser", back_populates="settings")


class UserBIIntegration(Base):
    """User-specific BI integration database model."""
    __tablename__ = "user_bi_integrations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("bi_users.id"), nullable=False)
    integration_id = Column(String(36), ForeignKey("bi_integrations.id"), nullable=False)
    
    # User-specific configuration
    alias = Column(String(255))  # User-friendly name for the integration
    is_default = Column(Boolean, default=False)
    access_level = Column(String(50), default="publisher")  # viewer, interactor, publisher, admin
    
    # Personal credentials (encrypted)
    personal_credentials = Column(JSON, default=dict)
    use_global_credentials = Column(Boolean, default=True)
    
    # Publishing preferences
    default_project_override = Column(String(255))
    publish_permissions = Column(JSON, default=dict)
    auto_tag_with_username = Column(Boolean, default=True)
    
    # Refresh preferences
    personal_refresh_schedule = Column(JSON, default=dict)
    max_refresh_frequency = Column(Integer, default=15)  # minimum minutes between refreshes
    
    # Workspace preferences
    favorite_workbooks = Column(JSON, default=list)
    favorite_dashboards = Column(JSON, default=list)
    recent_projects = Column(JSON, default=list)
    bookmarked_views = Column(JSON, default=list)
    
    # Usage statistics
    total_workbooks_published = Column(Integer, default=0)
    total_dashboards_published = Column(Integer, default=0)
    total_extracts_created = Column(Integer, default=0)
    total_refreshes_triggered = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Collaboration
    shared_with_users = Column(JSON, default=list)
    shared_projects = Column(JSON, default=list)
    collaboration_settings = Column(JSON, default=dict)
    
    # Performance tracking
    average_publish_time_seconds = Column(Float)
    average_refresh_time_seconds = Column(Float)
    success_rate_percentage = Column(Float)
    
    # Status
    active = Column(Boolean, default=True)
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("BIUser", back_populates="integrations")


# Pydantic Models for API
class BIUserCreate(BaseModel):
    """Pydantic model for creating BI users."""
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: str = Field(..., min_length=1, max_length=255)
    external_ids: Dict[str, str] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    default_provider: Optional[str] = Field(None, max_length=50)
    preferred_export_format: str = Field(default="pdf", max_length=50)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    timezone: str = Field(default="UTC", max_length=50)
    language: str = Field(default="en", max_length=10)


class BIUserUpdate(BaseModel):
    """Pydantic model for updating BI users."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    external_ids: Optional[Dict[str, str]] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    default_provider: Optional[str] = Field(None, max_length=50)
    preferred_export_format: Optional[str] = Field(None, max_length=50)
    notification_preferences: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    auto_publish_enabled: Optional[bool] = None
    email_on_publish: Optional[bool] = None
    email_on_refresh_failure: Optional[bool] = None
    active: Optional[bool] = None


class BIUserResponse(BaseModel):
    """Pydantic model for BI user responses."""
    id: str
    email: str
    full_name: str
    external_ids: Dict[str, str]
    roles: List[str]
    permissions: List[str]
    default_provider: Optional[str]
    preferred_export_format: str
    notification_preferences: Dict[str, Any]
    timezone: str
    language: str
    auto_publish_enabled: bool
    email_on_publish: bool
    email_on_refresh_failure: bool
    total_workbooks_created: int
    total_dashboards_created: int
    total_refreshes_triggered: int
    last_activity_at: Optional[datetime]
    active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBISettingsUpdate(BaseModel):
    """Pydantic model for updating user BI settings."""
    default_project: Optional[str] = Field(None, max_length=255)
    auto_publish_workbooks: Optional[bool] = None
    auto_publish_dashboards: Optional[bool] = None
    publish_with_tabs: Optional[bool] = None
    show_selection_as_tabs: Optional[bool] = None
    default_refresh_interval: Optional[int] = Field(None, ge=1, le=1440)
    auto_refresh_on_publish: Optional[bool] = None
    incremental_refresh_enabled: Optional[bool] = None
    default_connection_timeout: Optional[int] = Field(None, ge=30, le=3600)
    max_extract_rows: Optional[int] = Field(None, ge=1000, le=10000000)
    enable_extract_encryption: Optional[bool] = None
    email_on_publish_success: Optional[bool] = None
    email_on_publish_failure: Optional[bool] = None
    email_on_refresh_success: Optional[bool] = None
    email_on_refresh_failure: Optional[bool] = None
    slack_notifications: Optional[bool] = None
    teams_notifications: Optional[bool] = None
    dashboard_theme: Optional[str] = Field(None, max_length=50)
    show_performance_recorder: Optional[bool] = None
    auto_save_enabled: Optional[bool] = None
    show_toolbar: Optional[bool] = None
    default_export_format: Optional[str] = Field(None, max_length=50)
    export_quality: Optional[str] = Field(None, max_length=50)
    include_data: Optional[bool] = None
    max_export_rows: Optional[int] = Field(None, ge=100, le=1000000)
    require_ssl: Optional[bool] = None
    session_timeout_minutes: Optional[int] = Field(None, ge=30, le=1440)
    enable_guest_access: Optional[bool] = None
    query_timeout_seconds: Optional[int] = Field(None, ge=30, le=3600)
    max_concurrent_refreshes: Optional[int] = Field(None, ge=1, le=20)
    cache_results: Optional[bool] = None
    cache_timeout_minutes: Optional[int] = Field(None, ge=1, le=1440)
    enable_javascript: Optional[bool] = None
    allow_url_access: Optional[bool] = None
    custom_css: Optional[str] = None
    custom_javascript: Optional[str] = None


class UserBISettingsResponse(BaseModel):
    """Pydantic model for user BI settings responses."""
    id: str
    user_id: str
    default_project: Optional[str]
    auto_publish_workbooks: bool
    auto_publish_dashboards: bool
    publish_with_tabs: bool
    show_selection_as_tabs: bool
    default_refresh_interval: int
    auto_refresh_on_publish: bool
    incremental_refresh_enabled: bool
    default_connection_timeout: int
    max_extract_rows: int
    enable_extract_encryption: bool
    email_on_publish_success: bool
    email_on_publish_failure: bool
    email_on_refresh_success: bool
    email_on_refresh_failure: bool
    slack_notifications: bool
    teams_notifications: bool
    dashboard_theme: str
    show_performance_recorder: bool
    auto_save_enabled: bool
    show_toolbar: bool
    default_export_format: str
    export_quality: str
    include_data: bool
    max_export_rows: int
    require_ssl: bool
    session_timeout_minutes: int
    enable_guest_access: bool
    query_timeout_seconds: int
    max_concurrent_refreshes: int
    cache_results: bool
    cache_timeout_minutes: int
    enable_javascript: bool
    allow_url_access: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBIIntegrationCreate(BaseModel):
    """Pydantic model for creating user BI integrations."""
    integration_id: str
    alias: Optional[str] = Field(None, max_length=255)
    is_default: bool = False
    access_level: str = Field(default="publisher", regex=r'^(viewer|interactor|publisher|admin)$')
    personal_credentials: Dict[str, Any] = Field(default_factory=dict)
    use_global_credentials: bool = True
    default_project_override: Optional[str] = Field(None, max_length=255)
    publish_permissions: Dict[str, Any] = Field(default_factory=dict)
    auto_tag_with_username: bool = True
    personal_refresh_schedule: Dict[str, Any] = Field(default_factory=dict)
    max_refresh_frequency: int = Field(default=15, ge=1, le=1440)


class UserBIIntegrationUpdate(BaseModel):
    """Pydantic model for updating user BI integrations."""
    alias: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = None
    access_level: Optional[str] = Field(None, regex=r'^(viewer|interactor|publisher|admin)$')
    personal_credentials: Optional[Dict[str, Any]] = None
    use_global_credentials: Optional[bool] = None
    default_project_override: Optional[str] = Field(None, max_length=255)
    publish_permissions: Optional[Dict[str, Any]] = None
    auto_tag_with_username: Optional[bool] = None
    personal_refresh_schedule: Optional[Dict[str, Any]] = None
    max_refresh_frequency: Optional[int] = Field(None, ge=1, le=1440)
    active: Optional[bool] = None


class UserBIIntegrationResponse(BaseModel):
    """Pydantic model for user BI integration responses."""
    id: str
    user_id: str
    integration_id: str
    alias: Optional[str]
    is_default: bool
    access_level: str
    use_global_credentials: bool
    default_project_override: Optional[str]
    auto_tag_with_username: bool
    max_refresh_frequency: int
    total_workbooks_published: int
    total_dashboards_published: int
    total_extracts_created: int
    total_refreshes_triggered: int
    last_used_at: Optional[datetime]
    average_publish_time_seconds: Optional[float]
    average_refresh_time_seconds: Optional[float]
    success_rate_percentage: Optional[float]
    active: bool
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True