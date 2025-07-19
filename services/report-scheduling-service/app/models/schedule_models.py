"""
Pydantic models for report scheduling system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator, root_validator
from croniter import croniter


class ScheduleStatus(str, Enum):
    """Schedule status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class DeliveryMethod(str, Enum):
    """Delivery method enumeration."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    FILE_STORAGE = "file_storage"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    PDF = "pdf"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    WORD = "word"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    HTML = "html"


class Priority(str, Enum):
    """Job priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# Base Models
class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Delivery Configuration Models
class EmailDeliveryConfig(BaseModel):
    """Email delivery configuration."""
    recipients: List[str] = Field(..., min_items=1, description="Email recipients")
    cc: Optional[List[str]] = Field(default=None, description="CC recipients")
    bcc: Optional[List[str]] = Field(default=None, description="BCC recipients")
    subject_template: str = Field(..., description="Email subject template")
    body_template: str = Field(..., description="Email body template")
    attach_report: bool = Field(default=True, description="Attach report file")
    include_summary: bool = Field(default=True, description="Include report summary")


class SlackDeliveryConfig(BaseModel):
    """Slack delivery configuration."""
    webhook_url: str = Field(..., description="Slack webhook URL")
    channel: Optional[str] = Field(default=None, description="Slack channel")
    username: Optional[str] = Field(default="ReportBot", description="Bot username")
    message_template: str = Field(..., description="Message template")
    include_preview: bool = Field(default=True, description="Include report preview")


class TeamsDeliveryConfig(BaseModel):
    """Microsoft Teams delivery configuration."""
    webhook_url: str = Field(..., description="Teams webhook URL")
    message_template: str = Field(..., description="Message template")
    include_preview: bool = Field(default=True, description="Include report preview")
    use_adaptive_card: bool = Field(default=True, description="Use adaptive card format")


class WebhookDeliveryConfig(BaseModel):
    """Webhook delivery configuration."""
    url: str = Field(..., description="Webhook URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    payload_template: str = Field(..., description="Payload template")
    authentication: Optional[Dict[str, Any]] = Field(default=None, description="Authentication config")


class FileStorageDeliveryConfig(BaseModel):
    """File storage delivery configuration."""
    storage_path: str = Field(..., description="Storage path")
    filename_template: str = Field(..., description="Filename template")
    create_directories: bool = Field(default=True, description="Create directories if needed")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing files")


# Main Models
class ReportConfiguration(BaseModel):
    """Report generation configuration."""
    query: str = Field(..., description="Splunk query or natural language query")
    query_type: str = Field(default="natural", description="Query type: 'spl' or 'natural'")
    time_range: Dict[str, Any] = Field(..., description="Time range configuration")
    format: ReportFormat = Field(..., description="Report output format")
    format_options: Optional[Dict[str, Any]] = Field(default=None, description="Format-specific options")
    visualization_config: Optional[Dict[str, Any]] = Field(default=None, description="Visualization configuration")
    data_filters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Additional data filters")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Report parameters")


class DeliveryConfiguration(BaseModel):
    """Delivery configuration."""
    method: DeliveryMethod = Field(..., description="Delivery method")
    config: Union[
        EmailDeliveryConfig,
        SlackDeliveryConfig,
        TeamsDeliveryConfig,
        WebhookDeliveryConfig,
        FileStorageDeliveryConfig
    ] = Field(..., description="Method-specific configuration")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay_minutes: int = Field(default=5, description="Delay between retries in minutes")
    timeout_seconds: int = Field(default=300, description="Delivery timeout in seconds")


class ScheduleConfiguration(BaseModel):
    """Schedule configuration."""
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    timezone: str = Field(default="UTC", description="Timezone for schedule")
    start_date: Optional[datetime] = Field(default=None, description="Schedule start date")
    end_date: Optional[datetime] = Field(default=None, description="Schedule end date")
    max_executions: Optional[int] = Field(default=None, description="Maximum number of executions")
    allow_overlap: bool = Field(default=False, description="Allow overlapping executions")
    priority: Priority = Field(default=Priority.MEDIUM, description="Execution priority")

    @validator("cron_expression")
    def validate_cron_expression(cls, v):
        """Validate cron expression syntax."""
        try:
            croniter(v)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression: {e}")
        return v

    @validator("timezone")
    def validate_timezone(cls, v):
        """Validate timezone string."""
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            # Fallback for older Python versions
            import pytz
            try:
                pytz.timezone(v)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"Unknown timezone: {v}")
        return v


# API Request/Response Models
class CreateScheduleRequest(BaseModel):
    """Request model for creating a schedule."""
    name: str = Field(..., min_length=1, max_length=255, description="Schedule name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Schedule description")
    schedule_config: ScheduleConfiguration = Field(..., description="Schedule configuration")
    report_config: ReportConfiguration = Field(..., description="Report configuration")
    delivery_configs: List[DeliveryConfiguration] = Field(..., min_items=1, description="Delivery configurations")
    tags: Optional[List[str]] = Field(default=None, description="Schedule tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class UpdateScheduleRequest(BaseModel):
    """Request model for updating a schedule."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Schedule name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Schedule description")
    schedule_config: Optional[ScheduleConfiguration] = Field(default=None, description="Schedule configuration")
    report_config: Optional[ReportConfiguration] = Field(default=None, description="Report configuration")
    delivery_configs: Optional[List[DeliveryConfiguration]] = Field(default=None, description="Delivery configurations")
    status: Optional[ScheduleStatus] = Field(default=None, description="Schedule status")
    tags: Optional[List[str]] = Field(default=None, description="Schedule tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ScheduleResponse(TimestampedModel):
    """Response model for schedule."""
    schedule_id: UUID = Field(..., description="Schedule ID")
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Schedule name")
    description: Optional[str] = Field(default=None, description="Schedule description")
    status: ScheduleStatus = Field(..., description="Schedule status")
    schedule_config: ScheduleConfiguration = Field(..., description="Schedule configuration")
    report_config: ReportConfiguration = Field(..., description="Report configuration")
    delivery_configs: List[DeliveryConfiguration] = Field(..., description="Delivery configurations")
    next_execution: Optional[datetime] = Field(default=None, description="Next scheduled execution")
    last_execution: Optional[datetime] = Field(default=None, description="Last execution time")
    execution_count: int = Field(default=0, description="Total execution count")
    success_count: int = Field(default=0, description="Successful execution count")
    failure_count: int = Field(default=0, description="Failed execution count")
    tags: Optional[List[str]] = Field(default=None, description="Schedule tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ExecutionResponse(TimestampedModel):
    """Response model for schedule execution."""
    execution_id: UUID = Field(..., description="Execution ID")
    schedule_id: UUID = Field(..., description="Schedule ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(default=None, description="Execution start time")
    completed_at: Optional[datetime] = Field(default=None, description="Execution completion time")
    duration_seconds: Optional[float] = Field(default=None, description="Execution duration")
    report_file_path: Optional[str] = Field(default=None, description="Generated report file path")
    delivery_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Delivery results")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Execution metadata")


# Subscription Models
class SubscriptionRequest(BaseModel):
    """Request model for creating a subscription."""
    schedule_id: UUID = Field(..., description="Schedule ID to subscribe to")
    delivery_method: DeliveryMethod = Field(..., description="Preferred delivery method")
    delivery_config: Union[
        EmailDeliveryConfig,
        SlackDeliveryConfig,
        TeamsDeliveryConfig,
        WebhookDeliveryConfig,
        FileStorageDeliveryConfig
    ] = Field(..., description="Delivery configuration")
    active: bool = Field(default=True, description="Subscription active status")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences")


class SubscriptionResponse(TimestampedModel):
    """Response model for subscription."""
    subscription_id: UUID = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    schedule_id: UUID = Field(..., description="Schedule ID")
    delivery_method: DeliveryMethod = Field(..., description="Delivery method")
    delivery_config: Dict[str, Any] = Field(..., description="Delivery configuration")
    active: bool = Field(..., description="Subscription active status")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences")


# Analytics Models
class ScheduleAnalytics(BaseModel):
    """Schedule analytics data."""
    schedule_id: UUID = Field(..., description="Schedule ID")
    total_executions: int = Field(..., description="Total number of executions")
    successful_executions: int = Field(..., description="Number of successful executions")
    failed_executions: int = Field(..., description="Number of failed executions")
    success_rate: float = Field(..., description="Success rate percentage")
    average_duration_seconds: Optional[float] = Field(default=None, description="Average execution duration")
    last_execution_status: Optional[ExecutionStatus] = Field(default=None, description="Last execution status")
    next_execution: Optional[datetime] = Field(default=None, description="Next scheduled execution")


class SystemAnalytics(BaseModel):
    """System-wide analytics data."""
    total_schedules: int = Field(..., description="Total number of schedules")
    active_schedules: int = Field(..., description="Number of active schedules")
    total_executions_24h: int = Field(..., description="Total executions in last 24 hours")
    successful_executions_24h: int = Field(..., description="Successful executions in last 24 hours")
    failed_executions_24h: int = Field(..., description="Failed executions in last 24 hours")
    success_rate_24h: float = Field(..., description="Success rate in last 24 hours")
    pending_jobs: int = Field(..., description="Number of pending jobs")
    active_jobs: int = Field(..., description="Number of active jobs")
    average_execution_time: Optional[float] = Field(default=None, description="Average execution time")
    most_used_formats: List[Dict[str, Any]] = Field(..., description="Most used report formats")
    delivery_method_stats: List[Dict[str, Any]] = Field(..., description="Delivery method statistics")