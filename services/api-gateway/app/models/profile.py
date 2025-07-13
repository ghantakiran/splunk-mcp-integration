"""
User profile management data models and schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID
from enum import Enum


class NotificationMethod(str, Enum):
    """Notification delivery methods"""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class ThemeMode(str, Enum):
    """UI theme modes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ChartType(str, Enum):
    """Default chart types for visualizations"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"
    AUTO = "auto"


class DashboardLayout(str, Enum):
    """Dashboard layout preferences"""
    GRID = "grid"
    MASONRY = "masonry"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class UserProfileUpdate(BaseModel):
    """User profile update request model"""
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    language: Optional[str] = Field(None, max_length=10, description="User language code")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    job_title: Optional[str] = Field(None, max_length=100, description="Job title")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    
    @validator('timezone')
    def validate_timezone(cls, v):
        if v is not None:
            # Common timezone validation - would use pytz in production
            valid_timezones = [
                'UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
                'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Asia/Tokyo',
                'Asia/Shanghai', 'Australia/Sydney'
            ]
            if v not in valid_timezones:
                raise ValueError(f'Invalid timezone. Must be one of: {", ".join(valid_timezones)}')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v is not None:
            valid_languages = ['en', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'it', 'ru']
            if v not in valid_languages:
                raise ValueError(f'Invalid language. Must be one of: {", ".join(valid_languages)}')
        return v


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    slack_notifications: bool = Field(default=False, description="Enable Slack notifications")
    teams_notifications: bool = Field(default=False, description="Enable Teams notifications")
    push_notifications: bool = Field(default=True, description="Enable push notifications")
    in_app_notifications: bool = Field(default=True, description="Enable in-app notifications")
    
    # Notification categories
    query_completion: bool = Field(default=True, description="Notify when queries complete")
    alert_triggers: bool = Field(default=True, description="Notify when alerts trigger")
    dashboard_shares: bool = Field(default=True, description="Notify when dashboards are shared")
    system_updates: bool = Field(default=False, description="Notify about system updates")
    security_events: bool = Field(default=True, description="Notify about security events")
    weekly_summary: bool = Field(default=False, description="Weekly usage summary")
    
    # Delivery methods by category
    default_method: NotificationMethod = Field(default=NotificationMethod.EMAIL, description="Default notification method")
    alert_method: NotificationMethod = Field(default=NotificationMethod.EMAIL, description="Alert notification method")
    security_method: NotificationMethod = Field(default=NotificationMethod.EMAIL, description="Security notification method")
    
    # Quiet hours
    quiet_hours_enabled: bool = Field(default=False, description="Enable quiet hours")
    quiet_start_time: Optional[str] = Field(None, description="Quiet hours start time (HH:MM)")
    quiet_end_time: Optional[str] = Field(None, description="Quiet hours end time (HH:MM)")
    
    @validator('quiet_start_time', 'quiet_end_time')
    def validate_time_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%H:%M')
            except ValueError:
                raise ValueError('Time must be in HH:MM format')
        return v


class UIPreferences(BaseModel):
    """User interface preferences"""
    theme: ThemeMode = Field(default=ThemeMode.LIGHT, description="UI theme mode")
    density: str = Field(default="comfortable", description="UI density (compact, comfortable, spacious)")
    sidebar_collapsed: bool = Field(default=False, description="Sidebar collapsed state")
    show_tooltips: bool = Field(default=True, description="Show UI tooltips")
    animations_enabled: bool = Field(default=True, description="Enable UI animations")
    
    # Font and accessibility
    font_size: str = Field(default="medium", description="Font size (small, medium, large)")
    high_contrast: bool = Field(default=False, description="High contrast mode")
    screen_reader_mode: bool = Field(default=False, description="Screen reader optimization")
    
    # Dashboard preferences
    default_dashboard_layout: DashboardLayout = Field(default=DashboardLayout.GRID, description="Default dashboard layout")
    panels_per_row: int = Field(default=3, ge=1, le=6, description="Default panels per row")
    auto_refresh_enabled: bool = Field(default=False, description="Auto-refresh dashboards")
    auto_refresh_interval: int = Field(default=30, ge=10, le=300, description="Auto-refresh interval in seconds")
    
    # Chart preferences
    default_chart_type: ChartType = Field(default=ChartType.AUTO, description="Default chart type")
    color_palette: str = Field(default="default", description="Chart color palette")
    show_grid_lines: bool = Field(default=True, description="Show grid lines in charts")
    animate_charts: bool = Field(default=True, description="Animate chart transitions")


class QueryPreferences(BaseModel):
    """Query and SPL preferences"""
    default_time_range: str = Field(default="24h", description="Default query time range")
    max_results: int = Field(default=1000, ge=10, le=10000, description="Maximum query results")
    query_timeout: int = Field(default=300, ge=30, le=3600, description="Query timeout in seconds")
    
    # SPL preferences
    auto_complete_enabled: bool = Field(default=True, description="Enable SPL auto-completion")
    syntax_highlighting: bool = Field(default=True, description="Enable SPL syntax highlighting")
    query_validation: bool = Field(default=True, description="Validate queries before execution")
    save_query_history: bool = Field(default=True, description="Save query history")
    
    # Result preferences
    table_page_size: int = Field(default=50, ge=10, le=1000, description="Results table page size")
    export_format: str = Field(default="csv", description="Default export format")
    include_metadata: bool = Field(default=False, description="Include metadata in exports")
    
    # Performance
    streaming_enabled: bool = Field(default=False, description="Enable streaming results")
    cache_results: bool = Field(default=True, description="Cache query results")
    cache_duration: int = Field(default=3600, ge=300, le=86400, description="Cache duration in seconds")


class SecurityPreferences(BaseModel):
    """Security and privacy preferences"""
    two_factor_enabled: bool = Field(default=False, description="Two-factor authentication enabled")
    session_timeout: int = Field(default=3600, ge=300, le=86400, description="Session timeout in seconds")
    password_expiry_days: int = Field(default=90, ge=30, le=365, description="Password expiry in days")
    
    # Privacy settings
    activity_tracking: bool = Field(default=True, description="Allow activity tracking")
    usage_analytics: bool = Field(default=True, description="Share usage analytics")
    error_reporting: bool = Field(default=True, description="Automatic error reporting")
    
    # Access control
    trusted_devices_enabled: bool = Field(default=False, description="Remember trusted devices")
    ip_whitelist_enabled: bool = Field(default=False, description="Enable IP whitelist")
    ip_whitelist: List[str] = Field(default_factory=list, description="Allowed IP addresses")
    
    # Audit preferences
    log_queries: bool = Field(default=True, description="Log all queries")
    log_exports: bool = Field(default=True, description="Log all exports")
    log_dashboard_views: bool = Field(default=False, description="Log dashboard views")


class IntegrationPreferences(BaseModel):
    """External integration preferences"""
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    teams_webhook_url: Optional[str] = Field(None, description="Teams webhook URL")
    jira_base_url: Optional[str] = Field(None, description="Jira base URL")
    jira_username: Optional[str] = Field(None, description="Jira username")
    
    # Splunk preferences
    default_splunk_app: Optional[str] = Field(None, description="Default Splunk app")
    splunk_search_head: Optional[str] = Field(None, description="Preferred search head")
    accessible_indexes: List[str] = Field(default_factory=list, description="Accessible Splunk indexes")
    
    # API preferences
    api_rate_limit: int = Field(default=1000, ge=100, le=10000, description="Personal API rate limit")
    webhook_timeout: int = Field(default=30, ge=5, le=120, description="Webhook timeout in seconds")


class UserPreferencesUpdate(BaseModel):
    """Complete user preferences update model"""
    notifications: Optional[NotificationPreferences] = Field(None, description="Notification preferences")
    ui: Optional[UIPreferences] = Field(None, description="UI preferences")
    query: Optional[QueryPreferences] = Field(None, description="Query preferences")
    security: Optional[SecurityPreferences] = Field(None, description="Security preferences")
    integrations: Optional[IntegrationPreferences] = Field(None, description="Integration preferences")


class UserPreferencesResponse(BaseModel):
    """User preferences response model"""
    notifications: NotificationPreferences = Field(..., description="Notification preferences")
    ui: UIPreferences = Field(..., description="UI preferences")
    query: QueryPreferences = Field(..., description="Query preferences")
    security: SecurityPreferences = Field(..., description="Security preferences")
    integrations: IntegrationPreferences = Field(..., description="Integration preferences")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class ActivitySummary(BaseModel):
    """User activity summary"""
    total_queries: int = Field(..., description="Total queries executed")
    queries_this_week: int = Field(..., description="Queries this week")
    queries_this_month: int = Field(..., description="Queries this month")
    dashboards_created: int = Field(..., description="Dashboards created")
    dashboards_shared: int = Field(..., description="Dashboards shared")
    alerts_created: int = Field(..., description="Alert rules created")
    last_query_time: Optional[datetime] = Field(None, description="Last query execution time")
    most_used_indexes: List[str] = Field(default_factory=list, description="Most frequently used indexes")
    favorite_chart_types: List[str] = Field(default_factory=list, description="Most used chart types")


class UserProfileExtended(BaseModel):
    """Extended user profile with additional information"""
    id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    full_name: str = Field(..., description="Full name")
    display_name: str = Field(..., description="Display name")
    
    # Profile information
    phone_number: Optional[str] = Field(None, description="Phone number")
    department: Optional[str] = Field(None, description="Department")
    job_title: Optional[str] = Field(None, description="Job title")
    bio: Optional[str] = Field(None, description="User bio")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    
    # Account status
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    is_superuser: bool = Field(..., description="Superuser status")
    
    # Access control
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    
    # Localization
    timezone: str = Field(default="UTC", description="User timezone")
    language: str = Field(default="en", description="User language")
    
    # Session info
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Total login count")
    
    # Activity summary
    activity: ActivitySummary = Field(..., description="User activity summary")
    
    # Timestamps
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User settings and configuration"""
    profile: UserProfileExtended = Field(..., description="User profile information")
    preferences: UserPreferencesResponse = Field(..., description="User preferences")
    
    class Config:
        from_attributes = True


class BulkPreferenceUpdate(BaseModel):
    """Bulk preference update for administrative operations"""
    user_ids: List[UUID] = Field(..., description="List of user IDs to update")
    preferences: UserPreferencesUpdate = Field(..., description="Preference updates to apply")
    force_update: bool = Field(default=False, description="Force update even if conflicts exist")


class PreferenceTemplate(BaseModel):
    """Preference template for role-based defaults"""
    id: UUID = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    for_roles: List[str] = Field(default_factory=list, description="Applicable roles")
    preferences: UserPreferencesUpdate = Field(..., description="Template preferences")
    is_default: bool = Field(default=False, description="Default template")
    created_by: UUID = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class UserOnboardingProgress(BaseModel):
    """Track user onboarding progress"""
    user_id: UUID = Field(..., description="User ID")
    profile_completed: bool = Field(default=False, description="Profile setup completed")
    preferences_set: bool = Field(default=False, description="Preferences configured")
    first_query_executed: bool = Field(default=False, description="First query executed")
    first_dashboard_created: bool = Field(default=False, description="First dashboard created")
    first_alert_created: bool = Field(default=False, description="First alert created")
    tour_completed: bool = Field(default=False, description="Product tour completed")
    training_completed: bool = Field(default=False, description="Training completed")
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Completion percentage")
    last_step_completed: Optional[str] = Field(None, description="Last completed step")
    completed_at: Optional[datetime] = Field(None, description="Onboarding completion timestamp")
    
    class Config:
        from_attributes = True