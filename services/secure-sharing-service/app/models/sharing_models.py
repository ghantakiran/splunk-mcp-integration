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


class ShareRole(str, Enum):
    """Roles for sharing operations."""
    ADMIN = "admin"
    MANAGER = "manager"
    CREATOR = "creator"
    MEMBER = "member"
    VIEWER = "viewer"


class ShareOperation(str, Enum):
    """Operations that can be performed on shares."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SHARE = "share"
    REVOKE = "revoke"
    MANAGE_PERMISSIONS = "manage_permissions"
    VIEW_ANALYTICS = "view_analytics"


class PermissionScope(str, Enum):
    """Scope of permissions for sharing."""
    GLOBAL = "global"
    RESOURCE_TYPE = "resource_type"
    RESOURCE = "resource"
    SHARE = "share"


class AuditEventType(str, Enum):
    """Types of events that can be audited."""
    SHARE_CREATED = "share_created"
    SHARE_UPDATED = "share_updated"
    SHARE_DELETED = "share_deleted"
    SHARE_ACCESSED = "share_accessed"
    SHARE_REVOKED = "share_revoked"
    SHARE_EXPIRED = "share_expired"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    CONFIGURATION_CHANGED = "configuration_changed"
    SECURITY_VIOLATION = "security_violation"
    PASSWORD_CHANGED = "password_changed"
    BULK_OPERATION = "bulk_operation"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEventCategory(str, Enum):
    """Categories for audit events."""
    SHARE_MANAGEMENT = "share_management"
    ACCESS_CONTROL = "access_control"
    PERMISSION_MANAGEMENT = "permission_management"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


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


# Role-Based Permission Models
class ShareRolePermission(BaseModel):
    """Model for role-based permissions."""
    model_config = ConfigDict(from_attributes=True)
    
    role: ShareRole
    operations: List[ShareOperation]
    scope: PermissionScope
    scope_id: Optional[str] = None  # resource_type, resource_id, or share_id
    conditions: Optional[Dict[str, Any]] = None  # Additional conditions
    
    @validator('operations')
    def validate_operations(cls, v, values):
        role = values.get('role')
        if role == ShareRole.VIEWER and any(op in [ShareOperation.CREATE, ShareOperation.UPDATE, ShareOperation.DELETE] for op in v):
            raise ValueError("Viewer role cannot have create, update, or delete operations")
        return v


class CreateRolePermissionRequest(BaseModel):
    """Request model for creating role permissions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    user_id: str = Field(..., description="User ID to assign role")
    role: ShareRole = Field(..., description="Role to assign")
    scope: PermissionScope = Field(..., description="Scope of the permission")
    scope_id: Optional[str] = Field(None, description="ID for resource/share specific permissions")
    resource_types: Optional[List[ShareType]] = Field(None, description="Specific resource types for resource_type scope")
    expires_at: Optional[datetime] = Field(None, description="When the role assignment expires")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Additional conditions for the role")


class UpdateRolePermissionRequest(BaseModel):
    """Request model for updating role permissions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    role: Optional[ShareRole] = Field(None, description="New role")
    expires_at: Optional[datetime] = Field(None, description="New expiration time")
    conditions: Optional[Dict[str, Any]] = Field(None, description="New conditions")
    active: Optional[bool] = Field(None, description="Whether the permission is active")


class RolePermissionResponse(BaseModel):
    """Response model for role permissions."""
    model_config = ConfigDict(from_attributes=True)
    
    permission_id: UUID
    user_id: str
    role: ShareRole
    scope: PermissionScope
    scope_id: Optional[str]
    resource_types: Optional[List[ShareType]]
    operations: List[ShareOperation]
    conditions: Optional[Dict[str, Any]]
    active: bool
    expires_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime


class UserRolePermissionsResponse(BaseModel):
    """Response model for user's role permissions."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    permissions: List[RolePermissionResponse]
    effective_operations: Dict[str, List[ShareOperation]]  # scope -> operations
    can_create_shares: bool
    can_manage_permissions: bool
    can_view_analytics: bool


class RolePermissionCheck(BaseModel):
    """Model for checking role permissions."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    operation: ShareOperation
    scope: PermissionScope
    scope_id: Optional[str] = None
    resource_type: Optional[ShareType] = None
    share_id: Optional[UUID] = None
    
    # Results
    has_permission: bool
    granted_by_role: Optional[ShareRole] = None
    granted_by_permission_id: Optional[UUID] = None
    reason: Optional[str] = None


class PermissionAuditLog(BaseModel):
    """Model for permission audit logging."""
    model_config = ConfigDict(from_attributes=True)
    
    log_id: UUID
    user_id: str
    operation: ShareOperation
    scope: PermissionScope
    scope_id: Optional[str]
    resource_type: Optional[ShareType]
    share_id: Optional[UUID]
    permission_granted: bool
    granted_by_role: Optional[ShareRole]
    granted_by_permission_id: Optional[UUID]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict[str, Any]]


class SharePermissionMatrix(BaseModel):
    """Model for permission matrix display."""
    model_config = ConfigDict(from_attributes=True)
    
    role: ShareRole
    permissions: Dict[ShareOperation, Dict[PermissionScope, bool]]
    description: str
    typical_use_cases: List[str]


class BulkRoleOperation(BaseModel):
    """Model for bulk role operations."""
    model_config = ConfigDict(from_attributes=True)
    
    operation: str  # assign, update, revoke
    user_ids: List[str]
    role: ShareRole
    scope: PermissionScope
    scope_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # Results
    successful_operations: int
    failed_operations: int
    errors: List[Dict[str, Any]]


# Audit Trail Models
class AuditTrailEvent(BaseModel):
    """Model for audit trail events."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: UUID
    event_type: AuditEventType
    category: AuditEventCategory
    severity: AuditEventSeverity
    
    # Event details
    title: str
    description: str
    timestamp: datetime
    
    # User and session context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Resource context
    share_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[ShareType] = None
    
    # Operation context
    operation: Optional[ShareOperation] = None
    scope: Optional[PermissionScope] = None
    scope_id: Optional[str] = None
    
    # Before and after states for changes
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    
    # Additional context and metadata
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Request tracing
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Security context
    authentication_method: Optional[str] = None
    authorization_granted: Optional[bool] = None
    
    # System context
    service_name: str = "secure-sharing-service"
    service_version: Optional[str] = None
    
    # Tags for categorization and filtering
    tags: Optional[List[str]] = None


class CreateAuditEventRequest(BaseModel):
    """Request model for creating audit events."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    event_type: AuditEventType
    category: AuditEventCategory
    severity: AuditEventSeverity = AuditEventSeverity.LOW
    
    title: str = Field(..., max_length=255)
    description: str = Field(..., max_length=2000)
    
    # Optional context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    share_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[ShareType] = None
    
    operation: Optional[ShareOperation] = None
    scope: Optional[PermissionScope] = None
    scope_id: Optional[str] = None
    
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    authentication_method: Optional[str] = None
    authorization_granted: Optional[bool] = None
    
    tags: Optional[List[str]] = None


class AuditTrailQuery(BaseModel):
    """Query parameters for audit trail retrieval."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Event filtering
    event_types: Optional[List[AuditEventType]] = None
    categories: Optional[List[AuditEventCategory]] = None
    severities: Optional[List[AuditEventSeverity]] = None
    
    # User and resource filtering
    user_ids: Optional[List[str]] = None
    share_ids: Optional[List[UUID]] = None
    resource_ids: Optional[List[UUID]] = None
    resource_types: Optional[List[ShareType]] = None
    
    # Operation filtering
    operations: Optional[List[ShareOperation]] = None
    scopes: Optional[List[PermissionScope]] = None
    
    # Security filtering
    authorization_granted: Optional[bool] = None
    ip_addresses: Optional[List[str]] = None
    
    # Text search
    search_query: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # Pagination and sorting
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="timestamp")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class AuditTrailResponse(BaseModel):
    """Response model for audit trail queries."""
    model_config = ConfigDict(from_attributes=True)
    
    events: List[AuditTrailEvent]
    total_count: int
    filtered_count: int
    limit: int
    offset: int
    has_more: bool
    
    # Query summary
    query_metadata: Dict[str, Any]
    execution_time_ms: float


class AuditTrailStatistics(BaseModel):
    """Statistics for audit trail analysis."""
    model_config = ConfigDict(from_attributes=True)
    
    total_events: int
    event_count_by_type: Dict[AuditEventType, int]
    event_count_by_category: Dict[AuditEventCategory, int]
    event_count_by_severity: Dict[AuditEventSeverity, int]
    
    # Time-based statistics
    events_by_hour: List[Dict[str, Any]]
    events_by_day: List[Dict[str, Any]]
    
    # User activity
    top_active_users: List[Dict[str, Any]]
    unique_users_count: int
    
    # Resource activity
    most_accessed_shares: List[Dict[str, Any]]
    resource_type_activity: Dict[ShareType, int]
    
    # Security insights
    security_events_count: int
    failed_authorization_count: int
    suspicious_activity_indicators: List[Dict[str, Any]]
    
    # Operational insights
    peak_activity_hours: List[int]
    average_events_per_day: float
    retention_policy_compliance: Dict[str, Any]


class AuditTrailExportRequest(BaseModel):
    """Request model for exporting audit trail data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    query: AuditTrailQuery
    export_format: str = Field(default="json", pattern="^(json|csv|xlsx)$")
    include_metadata: bool = True
    include_sensitive_data: bool = False
    compression: Optional[str] = Field(default=None, pattern="^(gzip|zip)?$")
    
    # Export customization
    columns: Optional[List[str]] = None
    custom_title: Optional[str] = None
    include_summary: bool = True


# Workflow Approval Models

class WorkflowStatus(str, Enum):
    """Status of approval workflows."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalLevel(str, Enum):
    """Levels of approval required."""
    NONE = "none"
    SINGLE = "single"
    MULTI_LEVEL = "multi_level"
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"


class ApprovalAction(str, Enum):
    """Actions that can be taken on approval requests."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    DELEGATE = "delegate"
    WITHDRAW = "withdraw"


class ApprovalTrigger(str, Enum):
    """Triggers that require approval."""
    SENSITIVE_DATA = "sensitive_data"
    EXTERNAL_SHARING = "external_sharing"
    HIGH_RISK_RESOURCE = "high_risk_resource"
    MANAGER_APPROVAL = "manager_approval"
    COMPLIANCE_REVIEW = "compliance_review"
    SECURITY_REVIEW = "security_review"
    CUSTOM_RULE = "custom_rule"


class CreateApprovalWorkflowRequest(BaseModel):
    """Request model for creating approval workflows."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    # Workflow configuration
    name: str = Field(..., max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    is_active: bool = Field(True, description="Whether workflow is active")
    
    # Trigger configuration
    triggers: List[ApprovalTrigger] = Field(..., description="Approval triggers")
    trigger_conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions for triggers")
    
    # Approval configuration
    approval_level: ApprovalLevel = Field(ApprovalLevel.SINGLE, description="Level of approval required")
    required_approvers: List[str] = Field(..., description="Required approver user IDs")
    optional_approvers: Optional[List[str]] = Field(None, description="Optional approver user IDs")
    approval_threshold: Optional[int] = Field(None, ge=1, description="Number of approvals required")
    
    # Timing configuration
    auto_approve_after: Optional[int] = Field(None, ge=1, le=168, description="Auto-approve after hours")
    expires_after: Optional[int] = Field(None, ge=1, le=720, description="Expire after hours")
    reminder_intervals: Optional[List[int]] = Field(None, description="Reminder intervals in hours")
    
    # Escalation configuration
    escalation_enabled: bool = Field(False, description="Enable escalation")
    escalation_after: Optional[int] = Field(None, ge=1, le=72, description="Escalate after hours")
    escalation_approvers: Optional[List[str]] = Field(None, description="Escalation approver user IDs")
    
    # Advanced settings
    allow_self_approval: bool = Field(False, description="Allow creator to approve their own request")
    require_reason: bool = Field(True, description="Require approval/rejection reason")
    parallel_approval: bool = Field(True, description="Allow parallel approvals")
    
    # Notification settings
    notify_requester: bool = Field(True, description="Notify requester of status changes")
    notify_approvers: bool = Field(True, description="Notify approvers of new requests")
    notification_channels: Optional[List[str]] = Field(None, description="Notification channels")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Workflow tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CreateApprovalRequestRequest(BaseModel):
    """Request model for creating approval requests."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Share context
    share_request: CreateShareRequest = Field(..., description="Original share request")
    workflow_id: UUID = Field(..., description="Workflow to use for approval")
    
    # Request details
    justification: str = Field(..., max_length=2000, description="Justification for the share")
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$", description="Request priority")
    
    # Additional context
    business_case: Optional[str] = Field(None, max_length=1000, description="Business case")
    risk_assessment: Optional[str] = Field(None, max_length=1000, description="Risk assessment")
    compliance_notes: Optional[str] = Field(None, max_length=1000, description="Compliance notes")
    
    # Timing
    requested_approval_by: Optional[datetime] = Field(None, description="When approval is needed by")
    
    # Attachments and references
    attachments: Optional[List[str]] = Field(None, description="Attachment file URLs")
    references: Optional[List[str]] = Field(None, description="Reference links or documents")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ApprovalActionRequest(BaseModel):
    """Request model for taking action on approval requests."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    action: ApprovalAction = Field(..., description="Action to take")
    reason: str = Field(..., max_length=1000, description="Reason for the action")
    
    # Optional fields
    delegate_to: Optional[str] = Field(None, description="User ID to delegate to")
    conditions: Optional[List[str]] = Field(None, description="Conditions for approval")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ApprovalWorkflowResponse(BaseModel):
    """Response model for approval workflows."""
    model_config = ConfigDict(from_attributes=True)
    
    workflow_id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    
    # Trigger configuration
    triggers: List[ApprovalTrigger]
    trigger_conditions: Optional[Dict[str, Any]]
    
    # Approval configuration
    approval_level: ApprovalLevel
    required_approvers: List[str]
    optional_approvers: Optional[List[str]]
    approval_threshold: Optional[int]
    
    # Timing configuration
    auto_approve_after: Optional[int]
    expires_after: Optional[int]
    reminder_intervals: Optional[List[int]]
    
    # Escalation configuration
    escalation_enabled: bool
    escalation_after: Optional[int]
    escalation_approvers: Optional[List[str]]
    
    # Advanced settings
    allow_self_approval: bool
    require_reason: bool
    parallel_approval: bool
    
    # Statistics
    total_requests: int = 0
    approved_requests: int = 0
    rejected_requests: int = 0
    pending_requests: int = 0
    average_approval_time: Optional[float] = None
    
    # Tracking
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    # Metadata
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]


class ApprovalRequestResponse(BaseModel):
    """Response model for approval requests."""
    model_config = ConfigDict(from_attributes=True)
    
    request_id: UUID
    workflow_id: UUID
    share_id: Optional[UUID]  # Set after share is created
    
    # Request details
    share_request: Dict[str, Any]  # Serialized CreateShareRequest
    justification: str
    priority: str
    status: WorkflowStatus
    
    # Context
    business_case: Optional[str]
    risk_assessment: Optional[str]
    compliance_notes: Optional[str]
    
    # Timing
    requested_approval_by: Optional[datetime]
    auto_approve_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    # Progress tracking
    current_approvers: List[str]
    completed_approvals: List[Dict[str, Any]]
    pending_approvals: List[str]
    escalated: bool = False
    escalated_at: Optional[datetime]
    
    # Final resolution
    final_action: Optional[ApprovalAction]
    final_reason: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejected_by: Optional[str]
    rejected_at: Optional[datetime]
    
    # Tracking
    requested_by: str
    created_at: datetime
    updated_at: datetime
    
    # Attachments and references
    attachments: Optional[List[str]]
    references: Optional[List[str]]
    
    # Metadata
    metadata: Optional[Dict[str, Any]]


class ApprovalActionResponse(BaseModel):
    """Response model for approval actions."""
    model_config = ConfigDict(from_attributes=True)
    
    action_id: UUID
    request_id: UUID
    approver_id: str
    
    action: ApprovalAction
    reason: str
    status: str  # completed, pending, cancelled
    
    # Action details
    delegate_to: Optional[str]
    conditions: Optional[List[str]]
    notes: Optional[str]
    
    # Timing
    taken_at: datetime
    
    # Metadata
    metadata: Optional[Dict[str, Any]]


class ApprovalWorkflowListRequest(BaseModel):
    """Request model for listing approval workflows."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Filtering
    is_active: Optional[bool] = None
    triggers: Optional[List[ApprovalTrigger]] = None
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # Search
    search: Optional[str] = None
    
    # Pagination
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    
    # Sorting
    sort_by: str = Field("created_at", pattern="^(name|created_at|updated_at)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class ApprovalRequestListRequest(BaseModel):
    """Request model for listing approval requests."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Filtering
    workflow_id: Optional[UUID] = None
    status: Optional[WorkflowStatus] = None
    priority: Optional[str] = None
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None  # Current approver
    
    # Time filtering
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    due_before: Optional[datetime] = None
    
    # Search
    search: Optional[str] = None
    
    # Pagination
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    
    # Sorting
    sort_by: str = Field("created_at", pattern="^(created_at|updated_at|priority|status)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class ApprovalStatistics(BaseModel):
    """Statistics for approval workflows."""
    model_config = ConfigDict(from_attributes=True)
    
    # Overall statistics
    total_workflows: int
    active_workflows: int
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    expired_requests: int
    
    # Performance metrics
    average_approval_time_hours: Optional[float]
    median_approval_time_hours: Optional[float]
    approval_rate_percentage: float
    
    # Workflow effectiveness
    workflows_by_trigger: Dict[ApprovalTrigger, int]
    requests_by_priority: Dict[str, int]
    requests_by_status: Dict[WorkflowStatus, int]
    
    # User activity
    top_requesters: List[Dict[str, Any]]
    top_approvers: List[Dict[str, Any]]
    most_active_workflows: List[Dict[str, Any]]
    
    # Time-based analysis
    requests_by_day: List[Dict[str, Any]]
    approval_time_trends: List[Dict[str, Any]]
    
    # Risk and compliance
    high_risk_requests: int
    compliance_review_requests: int
    escalated_requests: int