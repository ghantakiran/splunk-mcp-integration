"""
User-related data models for the ITSM Service.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

Base = declarative_base()


class ITSMUser(Base):
    """ITSM user database model."""
    __tablename__ = "itsm_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    
    # ITSM-specific user information
    external_ids = Column(JSON, default=dict)  # Provider-specific user IDs
    roles = Column(JSON, default=list)  # ITSM roles
    permissions = Column(JSON, default=list)  # ITSM permissions
    
    # User preferences
    default_provider = Column(String(50))
    notification_preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Status
    active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = relationship("UserITSMSettings", back_populates="user", uselist=False)
    integrations = relationship("UserITSMIntegration", back_populates="user")


class UserITSMSettings(Base):
    """User ITSM settings database model."""
    __tablename__ = "user_itsm_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("itsm_users.id"), nullable=False, unique=True)
    
    # Default settings
    default_priority = Column(String(20), default="medium")
    default_category = Column(String(255))
    default_assigned_group = Column(String(255))
    
    # Notification settings
    email_notifications = Column(Boolean, default=True)
    slack_notifications = Column(Boolean, default=False)
    teams_notifications = Column(Boolean, default=False)
    sms_notifications = Column(Boolean, default=False)
    
    # Sync preferences
    auto_sync_enabled = Column(Boolean, default=True)
    sync_frequency_minutes = Column(Integer, default=15)
    conflict_resolution = Column(String(50), default="manual")  # manual, auto_local, auto_remote
    
    # Workflow preferences
    auto_workflow_execution = Column(Boolean, default=False)
    workflow_approval_required = Column(Boolean, default=True)
    
    # UI preferences
    dashboard_layout = Column(JSON, default=dict)
    favorite_filters = Column(JSON, default=list)
    custom_fields_visibility = Column(JSON, default=dict)
    
    # Performance settings
    batch_size = Column(Integer, default=100)
    timeout_seconds = Column(Integer, default=30)
    retry_attempts = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("ITSMUser", back_populates="settings")


class UserITSMIntegration(Base):
    """User-specific ITSM integration database model."""
    __tablename__ = "user_itsm_integrations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("itsm_users.id"), nullable=False)
    integration_id = Column(String(36), ForeignKey("itsm_integrations.id"), nullable=False)
    
    # User-specific configuration
    alias = Column(String(255))  # User-friendly name for the integration
    is_default = Column(Boolean, default=False)
    access_level = Column(String(50), default="read_write")  # read_only, read_write, admin
    
    # Personal credentials (encrypted)
    personal_credentials = Column(JSON, default=dict)
    use_global_credentials = Column(Boolean, default=True)
    
    # User-specific field mappings
    custom_field_mappings = Column(JSON, default=dict)
    custom_table_mappings = Column(JSON, default=dict)
    
    # Filters and preferences
    default_filters = Column(JSON, default=dict)
    favorite_queries = Column(JSON, default=list)
    quick_actions = Column(JSON, default=list)
    
    # Usage statistics
    total_queries = Column(Integer, default=0)
    total_tickets_created = Column(Integer, default=0)
    total_tickets_updated = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Status
    active = Column(Boolean, default=True)
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("ITSMUser", back_populates="integrations")


# Pydantic Models for API
class ITSMUserCreate(BaseModel):
    """Pydantic model for creating ITSM users."""
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: str = Field(..., min_length=1, max_length=255)
    external_ids: Dict[str, str] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    default_provider: Optional[str] = Field(None, max_length=50)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    timezone: str = Field(default="UTC", max_length=50)
    language: str = Field(default="en", max_length=10)


class ITSMUserUpdate(BaseModel):
    """Pydantic model for updating ITSM users."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    external_ids: Optional[Dict[str, str]] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    default_provider: Optional[str] = Field(None, max_length=50)
    notification_preferences: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    active: Optional[bool] = None


class ITSMUserResponse(BaseModel):
    """Pydantic model for ITSM user responses."""
    id: str
    email: str
    full_name: str
    external_ids: Dict[str, str]
    roles: List[str]
    permissions: List[str]
    default_provider: Optional[str]
    notification_preferences: Dict[str, Any]
    timezone: str
    language: str
    active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserITSMSettingsUpdate(BaseModel):
    """Pydantic model for updating user ITSM settings."""
    default_priority: Optional[str] = Field(None, regex=r'^(low|medium|high|critical|emergency)$')
    default_category: Optional[str] = Field(None, max_length=255)
    default_assigned_group: Optional[str] = Field(None, max_length=255)
    email_notifications: Optional[bool] = None
    slack_notifications: Optional[bool] = None
    teams_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    auto_sync_enabled: Optional[bool] = None
    sync_frequency_minutes: Optional[int] = Field(None, ge=1, le=1440)
    conflict_resolution: Optional[str] = Field(None, regex=r'^(manual|auto_local|auto_remote)$')
    auto_workflow_execution: Optional[bool] = None
    workflow_approval_required: Optional[bool] = None
    dashboard_layout: Optional[Dict[str, Any]] = None
    favorite_filters: Optional[List[Dict[str, Any]]] = None
    custom_fields_visibility: Optional[Dict[str, bool]] = None
    batch_size: Optional[int] = Field(None, ge=1, le=1000)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)


class UserITSMSettingsResponse(BaseModel):
    """Pydantic model for user ITSM settings responses."""
    id: str
    user_id: str
    default_priority: str
    default_category: Optional[str]
    default_assigned_group: Optional[str]
    email_notifications: bool
    slack_notifications: bool
    teams_notifications: bool
    sms_notifications: bool
    auto_sync_enabled: bool
    sync_frequency_minutes: int
    conflict_resolution: str
    auto_workflow_execution: bool
    workflow_approval_required: bool
    dashboard_layout: Dict[str, Any]
    favorite_filters: List[Dict[str, Any]]
    custom_fields_visibility: Dict[str, bool]
    batch_size: int
    timeout_seconds: int
    retry_attempts: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserITSMIntegrationCreate(BaseModel):
    """Pydantic model for creating user ITSM integrations."""
    integration_id: str
    alias: Optional[str] = Field(None, max_length=255)
    is_default: bool = False
    access_level: str = Field(default="read_write", regex=r'^(read_only|read_write|admin)$')
    personal_credentials: Dict[str, Any] = Field(default_factory=dict)
    use_global_credentials: bool = True
    custom_field_mappings: Dict[str, Any] = Field(default_factory=dict)
    custom_table_mappings: Dict[str, Any] = Field(default_factory=dict)
    default_filters: Dict[str, Any] = Field(default_factory=dict)
    favorite_queries: List[Dict[str, Any]] = Field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = Field(default_factory=list)


class UserITSMIntegrationUpdate(BaseModel):
    """Pydantic model for updating user ITSM integrations."""
    alias: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = None
    access_level: Optional[str] = Field(None, regex=r'^(read_only|read_write|admin)$')
    personal_credentials: Optional[Dict[str, Any]] = None
    use_global_credentials: Optional[bool] = None
    custom_field_mappings: Optional[Dict[str, Any]] = None
    custom_table_mappings: Optional[Dict[str, Any]] = None
    default_filters: Optional[Dict[str, Any]] = None
    favorite_queries: Optional[List[Dict[str, Any]]] = None
    quick_actions: Optional[List[Dict[str, Any]]] = None
    active: Optional[bool] = None


class UserITSMIntegrationResponse(BaseModel):
    """Pydantic model for user ITSM integration responses."""
    id: str
    user_id: str
    integration_id: str
    alias: Optional[str]
    is_default: bool
    access_level: str
    use_global_credentials: bool
    custom_field_mappings: Dict[str, Any]
    custom_table_mappings: Dict[str, Any]
    default_filters: Dict[str, Any]
    favorite_queries: List[Dict[str, Any]]
    quick_actions: List[Dict[str, Any]]
    total_queries: int
    total_tickets_created: int
    total_tickets_updated: int
    last_used_at: Optional[datetime]
    active: bool
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True