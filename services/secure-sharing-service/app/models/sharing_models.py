"""
Pydantic models for secure sharing functionality.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator


class ShareType(str, Enum):
    """Types of resources that can be shared."""
    REPORT = "report"
    DASHBOARD = "dashboard"
    CHART = "chart"
    QUERY_RESULT = "query_result"
    SCHEDULE = "schedule"
    DATASET = "dataset"


class SharePermission(str, Enum):
    """Permission levels for shared resources."""
    VIEW = "view"
    DOWNLOAD = "download"
    INTERACT = "interact"
    COMMENT = "comment"
    EDIT = "edit"


class ShareStatus(str, Enum):
    """Status of shared resources."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"
    REVOKED = "revoked"


class AccessMethod(str, Enum):
    """Methods for accessing shared resources."""
    LINK = "link"
    TOKEN = "token"
    EMAIL_INVITE = "email_invite"
    EMBEDDED = "embedded"


class ExpirationPolicy(str, Enum):
    """Expiration policies for shared resources."""
    NEVER = "never"
    AFTER_TIME = "after_time"
    AFTER_VIEWS = "after_views"
    AFTER_DOWNLOADS = "after_downloads"
    COMBINED = "combined"


# Request Models
class CreateShareRequest(BaseModel):
    """Request model for creating a share."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=False
    )
    
    resource_type: ShareType = Field(..., description="Type of resource being shared")
    resource_id: UUID = Field(..., description="ID of the resource to share")
    resource_name: str = Field(..., max_length=255, description="Display name for the shared resource")
    
    # Access configuration
    permissions: List[SharePermission] = Field(..., description="Permissions granted to viewers")
    access_method: AccessMethod = Field(AccessMethod.LINK, description="Method for accessing the share")
    requires_authentication: bool = Field(True, description="Whether authentication is required")
    
    # Expiration configuration
    expiration_policy: ExpirationPolicy = Field(ExpirationPolicy.AFTER_TIME, description="Expiration policy")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    max_views: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of views")
    max_downloads: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of downloads")
    
    # Security configuration
    password_protected: bool = Field(False, description="Whether password protection is enabled")
    password: Optional[str] = Field(None, min_length=8, max_length=128, description="Access password")
    allowed_domains: Optional[List[str]] = Field(None, description="Allowed email domains")
    allowed_users: Optional[List[str]] = Field(None, description="Specific allowed user emails")
    
    # Display configuration
    description: Optional[str] = Field(None, max_length=1000, description="Share description")
    custom_message: Optional[str] = Field(None, max_length=2000, description="Custom message for recipients")
    branding_enabled: bool = Field(True, description="Whether to show branding")
    
    # Notification configuration
    notify_on_access: bool = Field(False, description="Notify owner when accessed")
    notify_on_expiration: bool = Field(True, description="Notify owner when expired")
    notification_emails: Optional[List[str]] = Field(None, description="Additional notification emails")
    
    # Advanced settings
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Tags for organization")
    
    @validator('expires_at')
    def validate_expires_at(cls, v, values):
        if values.get('expiration_policy') == ExpirationPolicy.AFTER_TIME and v is None:
            raise ValueError("expires_at is required when expiration_policy is 'after_time'")
        if v and v <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return v
    
    @validator('password')
    def validate_password(cls, v, values):
        if values.get('password_protected') and not v:
            raise ValueError("password is required when password_protected is True")
        return v


class UpdateShareRequest(BaseModel):
    """Request model for updating a share."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    resource_name: Optional[str] = Field(None, max_length=255)
    permissions: Optional[List[SharePermission]] = Field(None)
    expires_at: Optional[datetime] = Field(None)
    max_views: Optional[int] = Field(None, ge=1, le=10000)
    max_downloads: Optional[int] = Field(None, ge=1, le=1000)
    password_protected: Optional[bool] = Field(None)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    custom_message: Optional[str] = Field(None, max_length=2000)
    notify_on_access: Optional[bool] = Field(None)
    notify_on_expiration: Optional[bool] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    tags: Optional[List[str]] = Field(None)


class AccessShareRequest(BaseModel):
    """Request model for accessing a shared resource."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    share_token: str = Field(..., description="Share access token")
    password: Optional[str] = Field(None, description="Access password if required")
    user_email: Optional[str] = Field(None, description="User email for tracking")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="User IP address")
    referrer: Optional[str] = Field(None, description="Referrer URL")


class ShareListRequest(BaseModel):
    """Request model for listing shares."""
    model_config = ConfigDict(validate_assignment=True)
    
    resource_type: Optional[ShareType] = Field(None, description="Filter by resource type")
    status: Optional[ShareStatus] = Field(None, description="Filter by status")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    expires_after: Optional[datetime] = Field(None, description="Filter by expiration date")
    expires_before: Optional[datetime] = Field(None, description="Filter by expiration date")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    search: Optional[str] = Field(None, max_length=255, description="Search in names and descriptions")
    limit: int = Field(50, ge=1, le=1000, description="Results limit")
    offset: int = Field(0, ge=0, description="Results offset")


# Response Models
class ShareResponse(BaseModel):
    """Response model for a shared resource."""
    model_config = ConfigDict(from_attributes=True)
    
    share_id: UUID
    resource_type: ShareType
    resource_id: UUID
    resource_name: str
    share_token: str
    share_url: str
    
    # Access configuration
    permissions: List[SharePermission]
    access_method: AccessMethod
    requires_authentication: bool
    
    # Expiration configuration
    expiration_policy: ExpirationPolicy
    expires_at: Optional[datetime]
    max_views: Optional[int]
    max_downloads: Optional[int]
    
    # Security configuration
    password_protected: bool
    allowed_domains: Optional[List[str]]
    allowed_users: Optional[List[str]]
    
    # Display configuration
    description: Optional[str]
    custom_message: Optional[str]
    branding_enabled: bool
    
    # Status and metrics
    status: ShareStatus
    total_views: int
    total_downloads: int
    unique_viewers: int
    
    # Tracking
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime]
    
    # Metadata
    metadata: Optional[Dict[str, Any]]
    tags: Optional[List[str]]


class ShareListResponse(BaseModel):
    """Response model for share list."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[ShareResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ShareAccessResponse(BaseModel):
    """Response model for share access."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    share_id: UUID
    resource_type: ShareType
    resource_id: UUID
    resource_name: str
    permissions: List[SharePermission]
    resource_data: Optional[Dict[str, Any]]
    custom_message: Optional[str]
    branding_enabled: bool
    access_count: int
    remaining_views: Optional[int]
    remaining_downloads: Optional[int]
    expires_at: Optional[datetime]


class ShareStatsResponse(BaseModel):
    """Response model for share statistics."""
    model_config = ConfigDict(from_attributes=True)
    
    share_id: UUID
    total_views: int
    total_downloads: int
    unique_viewers: int
    daily_views: List[Dict[str, Any]]
    top_referrers: List[Dict[str, Any]]
    geographic_distribution: List[Dict[str, Any]]
    device_types: Dict[str, int]
    access_timeline: List[Dict[str, Any]]
    
    # Performance metrics
    average_session_duration: Optional[float]
    bounce_rate: Optional[float]
    conversion_rate: Optional[float]


class ShareAnalyticsResponse(BaseModel):
    """Response model for share analytics."""
    model_config = ConfigDict(from_attributes=True)
    
    total_shares: int
    active_shares: int
    expired_shares: int
    
    # Breakdown by type
    shares_by_type: Dict[str, int]
    shares_by_permission: Dict[str, int]
    shares_by_access_method: Dict[str, int]
    
    # Activity metrics
    total_views_all_shares: int
    total_downloads_all_shares: int
    average_views_per_share: float
    most_viewed_shares: List[Dict[str, Any]]
    
    # Time-based analytics
    shares_created_this_week: int
    shares_created_this_month: int
    views_this_week: int
    views_this_month: int


class AccessLogEntry(BaseModel):
    """Model for access log entries."""
    model_config = ConfigDict(from_attributes=True)
    
    log_id: UUID
    share_id: UUID
    accessed_at: datetime
    user_email: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    referrer: Optional[str]
    action: str  # view, download, interact
    success: bool
    error_message: Optional[str]
    session_duration: Optional[float]
    metadata: Optional[Dict[str, Any]]


class ShareAccessLogsResponse(BaseModel):
    """Response model for share access logs."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[AccessLogEntry]
    total: int
    limit: int
    offset: int
    has_more: bool


# Utility Models
class ExpirationCheckResult(BaseModel):
    """Result model for expiration checks."""
    model_config = ConfigDict(from_attributes=True)
    
    is_expired: bool
    expiration_reason: Optional[str]
    expires_at: Optional[datetime]
    remaining_views: Optional[int]
    remaining_downloads: Optional[int]
    time_until_expiration: Optional[float]  # seconds


class ShareSecurityValidation(BaseModel):
    """Model for security validation results."""
    model_config = ConfigDict(from_attributes=True)
    
    is_valid: bool
    has_access: bool
    requires_password: bool
    domain_allowed: bool
    user_allowed: bool
    error_message: Optional[str]
    warnings: List[str]


class BulkShareOperation(BaseModel):
    """Model for bulk share operations."""
    model_config = ConfigDict(from_attributes=True)
    
    operation: str  # create, update, delete, revoke
    share_ids: List[UUID]
    parameters: Optional[Dict[str, Any]]
    
    # Results
    successful_operations: int
    failed_operations: int
    errors: List[Dict[str, Any]]