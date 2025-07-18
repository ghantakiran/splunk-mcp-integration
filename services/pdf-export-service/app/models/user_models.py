"""
User management models for PDF Export Service.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator, EmailStr
from enum import Enum


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    USER = "user"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserPermission(str, Enum):
    """User permissions."""
    PDF_CREATE = "pdf:create"
    PDF_READ = "pdf:read"
    PDF_UPDATE = "pdf:update"
    PDF_DELETE = "pdf:delete"
    TEMPLATE_CREATE = "template:create"
    TEMPLATE_READ = "template:read"
    TEMPLATE_UPDATE = "template:update"
    TEMPLATE_DELETE = "template:delete"
    ANALYTICS_READ = "analytics:read"
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"


# Request Models
class UserCreateRequest(BaseModel):
    """Request model for user creation."""
    external_id: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.USER
    permissions: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @validator('external_id')
    def validate_external_id(cls, v):
        """Validate external ID."""
        if not v.strip():
            raise ValueError('External ID cannot be empty')
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name."""
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate permissions."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('Permissions must be a dictionary')
        return v
    
    @validator('preferences')
    def validate_preferences(cls, v):
        """Validate preferences."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('Preferences must be a dictionary')
        return v


class UserUpdateRequest(BaseModel):
    """Request model for user update."""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None
    permissions: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    status: Optional[UserStatus] = None
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name."""
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip() if v else None


class UserPreferencesRequest(BaseModel):
    """Request model for user preferences update."""
    default_template_id: Optional[int] = None
    default_format: Optional[str] = None
    default_page_size: Optional[str] = None
    default_orientation: Optional[str] = None
    default_dpi: Optional[int] = None
    custom_css: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @validator('default_dpi')
    def validate_dpi(cls, v):
        """Validate DPI."""
        if v is not None and (v < 72 or v > 600):
            raise ValueError('DPI must be between 72 and 600')
        return v


class UserBulkCreateRequest(BaseModel):
    """Request model for bulk user creation."""
    users: List[UserCreateRequest]
    
    @validator('users')
    def validate_users(cls, v):
        """Validate users list."""
        if not v:
            raise ValueError('Users list cannot be empty')
        if len(v) > 100:
            raise ValueError('Maximum 100 users allowed per bulk request')
        return v


class UserSearchRequest(BaseModel):
    """Request model for user search."""
    query: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ['id', 'name', 'email', 'role', 'created_at', 'updated_at']
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {allowed_fields}')
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v


# Response Models
class User(BaseModel):
    """User response model."""
    id: int
    external_id: str
    email: str
    name: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    permissions: Dict[str, Any]
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class UserProfile(BaseModel):
    """User profile response model."""
    id: int
    external_id: str
    email: str
    name: str
    role: UserRole
    status: UserStatus
    permissions: Dict[str, Any]
    preferences: Dict[str, Any]
    export_preferences: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class UserList(BaseModel):
    """User list response model."""
    users: List[User]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserPermissions(BaseModel):
    """User permissions response model."""
    user_id: int
    permissions: Dict[str, Any]
    effective_permissions: List[str]
    role_permissions: List[str]
    granted_permissions: List[str]
    denied_permissions: List[str]


class UserActivity(BaseModel):
    """User activity response model."""
    user_id: int
    activity_type: str
    activity_description: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class UserActivityList(BaseModel):
    """User activity list response model."""
    activities: List[UserActivity]
    total: int
    page: int
    page_size: int


class UserStatistics(BaseModel):
    """User statistics response model."""
    user_id: int
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    total_pages_generated: int
    total_files_size_mb: float
    avg_generation_time_ms: float
    last_activity: Optional[datetime] = None
    favorite_templates: List[Dict[str, Any]]
    usage_by_format: Dict[str, int]
    usage_by_month: Dict[str, int]


class UserPreferences(BaseModel):
    """User preferences response model."""
    id: int
    user_id: int
    default_template_id: Optional[int] = None
    default_format: str = "pdf"
    default_page_size: str = "a4"
    default_orientation: str = "portrait"
    default_dpi: int = 300
    custom_css: Optional[str] = None
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class UserSession(BaseModel):
    """User session response model."""
    user_id: int
    session_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool


class UserBulkCreateResponse(BaseModel):
    """Bulk user creation response model."""
    created_count: int
    failed_count: int
    created_users: List[User]
    errors: List[Dict[str, Any]]


class UserRole(BaseModel):
    """User role response model."""
    name: str
    description: str
    permissions: List[str]
    is_default: bool


class UserRoleList(BaseModel):
    """User role list response model."""
    roles: List[UserRole]
    total: int


# Validation Models
class UserValidation(BaseModel):
    """User validation model."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class UserPasswordChange(BaseModel):
    """User password change model."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserPasswordReset(BaseModel):
    """User password reset model."""
    email: EmailStr
    reset_token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v