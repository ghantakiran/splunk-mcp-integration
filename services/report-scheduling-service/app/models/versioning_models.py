"""
Pydantic models for report versioning and history functionality.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class VersionAction(str, Enum):
    """Version action types."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"
    ARCHIVED = "archived"


class ChangeType(str, Enum):
    """Types of changes that can be made."""
    SCHEDULE_CONFIG = "schedule_config"
    QUERY = "query"
    FORMAT = "format"
    DELIVERY = "delivery"
    METADATA = "metadata"
    STATUS = "status"


class HistoryEventType(str, Enum):
    """History event types."""
    EXECUTION = "execution"
    VERSION_CHANGE = "version_change"
    SUBSCRIPTION_CHANGE = "subscription_change"
    DELIVERY_ATTEMPT = "delivery_attempt"
    ERROR = "error"
    SYSTEM = "system"


# Request Models
class CreateVersionRequest(BaseModel):
    """Request model for creating a version."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False
    )
    
    schedule_id: UUID = Field(..., description="Schedule ID to version")
    version_name: Optional[str] = Field(None, max_length=255, description="Optional version name")
    description: Optional[str] = Field(None, max_length=1000, description="Version description")
    changes: List[ChangeType] = Field(..., description="Types of changes made")
    change_notes: Optional[str] = Field(None, max_length=2000, description="Detailed change notes")
    tags: Optional[List[str]] = Field(None, description="Version tags")


class RestoreVersionRequest(BaseModel):
    """Request model for restoring a version."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    version_id: UUID = Field(..., description="Version ID to restore")
    restore_notes: Optional[str] = Field(None, max_length=1000, description="Restore operation notes")


class CompareVersionsRequest(BaseModel):
    """Request model for comparing versions."""
    model_config = ConfigDict(validate_assignment=True)
    
    version_id_1: UUID = Field(..., description="First version ID")
    version_id_2: UUID = Field(..., description="Second version ID")
    include_metadata: bool = Field(True, description="Include metadata in comparison")


class HistoryFilterRequest(BaseModel):
    """Request model for filtering history."""
    model_config = ConfigDict(validate_assignment=True)
    
    schedule_id: Optional[UUID] = Field(None, description="Filter by schedule ID")
    event_types: Optional[List[HistoryEventType]] = Field(None, description="Filter by event types")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    limit: int = Field(50, ge=1, le=1000, description="Results limit")
    offset: int = Field(0, ge=0, description="Results offset")


# Response Models
class VersionResponse(BaseModel):
    """Response model for a version."""
    model_config = ConfigDict(from_attributes=True)
    
    version_id: UUID
    schedule_id: UUID
    version_number: int
    version_name: Optional[str]
    description: Optional[str]
    action: VersionAction
    changes: List[ChangeType]
    change_notes: Optional[str]
    tags: Optional[List[str]]
    
    # Configuration snapshot
    schedule_config: Dict[str, Any]
    
    # User context
    created_by: str
    created_at: datetime
    
    # Version metadata
    is_current: bool
    parent_version_id: Optional[UUID]
    checksum: str
    size_bytes: int


class VersionListResponse(BaseModel):
    """Response model for version list."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[VersionResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class VersionComparisonResponse(BaseModel):
    """Response model for version comparison."""
    model_config = ConfigDict(from_attributes=True)
    
    version_1: VersionResponse
    version_2: VersionResponse
    differences: Dict[str, Any]
    summary: Dict[str, Any]
    is_identical: bool


class HistoryEventResponse(BaseModel):
    """Response model for a history event."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: UUID
    schedule_id: UUID
    event_type: HistoryEventType
    event_title: str
    event_description: Optional[str]
    
    # Event context
    user_id: Optional[str]
    session_id: Optional[str]
    correlation_id: Optional[str]
    
    # Event data
    event_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]
    
    # Relationships
    version_id: Optional[UUID]
    execution_id: Optional[UUID]
    
    # Timing
    occurred_at: datetime
    created_at: datetime


class HistoryResponse(BaseModel):
    """Response model for history list."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[HistoryEventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class VersionStatsResponse(BaseModel):
    """Response model for version statistics."""
    model_config = ConfigDict(from_attributes=True)
    
    schedule_id: UUID
    total_versions: int
    current_version_number: int
    
    # Version breakdown
    versions_by_action: Dict[str, int]
    versions_by_change_type: Dict[str, int]
    
    # Timeline data
    first_version_created: datetime
    last_version_created: datetime
    most_active_user: Optional[str]
    
    # Size statistics
    total_size_bytes: int
    average_size_bytes: float
    largest_version_size: int


class HistoryStatsResponse(BaseModel):
    """Response model for history statistics."""
    model_config = ConfigDict(from_attributes=True)
    
    schedule_id: UUID
    total_events: int
    
    # Event breakdown
    events_by_type: Dict[str, int]
    events_by_user: Dict[str, int]
    
    # Timeline data
    first_event_date: datetime
    last_event_date: datetime
    most_active_day: str
    
    # Activity metrics
    daily_average_events: float
    peak_events_per_day: int
    quiet_periods: List[Dict[str, Any]]


# Utility Models
class VersionDiff(BaseModel):
    """Model for version differences."""
    model_config = ConfigDict(from_attributes=True)
    
    field_path: str
    change_type: str  # added, removed, modified
    old_value: Optional[Any]
    new_value: Optional[Any]
    description: str


class RestoreResult(BaseModel):
    """Result model for version restore operation."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    restored_version_id: UUID
    new_version_id: Optional[UUID]
    message: str
    warnings: List[str]
    changes_applied: List[str]


class ArchiveResult(BaseModel):
    """Result model for version archive operation."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    archived_versions: List[UUID]
    total_archived: int
    space_freed_bytes: int
    message: str