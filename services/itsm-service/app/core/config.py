"""
Configuration management for ITSM Service.
"""

import os
from typing import List, Optional, Any, Dict
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ITSM service configuration settings."""
    
    # Application settings
    app_name: str = "Splunk MCP ITSM Service"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8008, env="PORT")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis configuration
    redis_url: str = Field(..., env="REDIS_URL")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    
    # Service URLs
    api_gateway_url: str = Field(..., env="API_GATEWAY_URL")
    nlp_engine_url: str = Field(..., env="NLP_ENGINE_URL")
    visualization_url: str = Field(..., env="VISUALIZATION_URL")
    alert_manager_url: str = Field(..., env="ALERT_MANAGER_URL")
    email_service_url: str = Field(..., env="EMAIL_SERVICE_URL")
    webhook_service_url: str = Field(..., env="WEBHOOK_SERVICE_URL")
    
    # Service timeouts
    api_timeout: int = Field(default=30, env="API_TIMEOUT")
    itsm_timeout: int = Field(default=60, env="ITSM_TIMEOUT")
    sync_timeout: int = Field(default=300, env="SYNC_TIMEOUT")  # 5 minutes
    
    # Security settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # ServiceNow configuration
    servicenow_instance: Optional[str] = Field(default=None, env="SERVICENOW_INSTANCE")
    servicenow_username: Optional[str] = Field(default=None, env="SERVICENOW_USERNAME")
    servicenow_password: Optional[str] = Field(default=None, env="SERVICENOW_PASSWORD")
    servicenow_api_version: str = Field(default="v1", env="SERVICENOW_API_VERSION")
    servicenow_timeout: int = Field(default=30, env="SERVICENOW_TIMEOUT")
    servicenow_max_retries: int = Field(default=3, env="SERVICENOW_MAX_RETRIES")
    servicenow_tables: List[str] = Field(
        default=["incident", "change_request", "problem", "sc_request"],
        env="SERVICENOW_TABLES"
    )
    
    # Jira configuration
    jira_server: Optional[str] = Field(default=None, env="JIRA_SERVER")
    jira_username: Optional[str] = Field(default=None, env="JIRA_USERNAME")
    jira_api_token: Optional[str] = Field(default=None, env="JIRA_API_TOKEN")
    jira_timeout: int = Field(default=30, env="JIRA_TIMEOUT")
    jira_max_retries: int = Field(default=3, env="JIRA_MAX_RETRIES")
    jira_projects: List[str] = Field(default=[], env="JIRA_PROJECTS")
    jira_issue_types: List[str] = Field(
        default=["Bug", "Task", "Story", "Incident", "Change"],
        env="JIRA_ISSUE_TYPES"
    )
    
    # ITSM integration settings
    max_tickets_per_request: int = Field(default=100, env="MAX_TICKETS_PER_REQUEST")
    max_sync_batch_size: int = Field(default=50, env="MAX_SYNC_BATCH_SIZE")
    sync_interval_minutes: int = Field(default=15, env="SYNC_INTERVAL_MINUTES")
    ticket_cache_ttl: int = Field(default=300, env="TICKET_CACHE_TTL")  # 5 minutes
    
    # Workflow settings
    max_workflow_steps: int = Field(default=20, env="MAX_WORKFLOW_STEPS")
    workflow_timeout: int = Field(default=600, env="WORKFLOW_TIMEOUT")  # 10 minutes
    workflow_retry_attempts: int = Field(default=3, env="WORKFLOW_RETRY_ATTEMPTS")
    workflow_retry_delay: int = Field(default=60, env="WORKFLOW_RETRY_DELAY")  # 1 minute
    
    # Synchronization settings
    sync_enabled: bool = Field(default=True, env="SYNC_ENABLED")
    bidirectional_sync: bool = Field(default=True, env="BIDIRECTIONAL_SYNC")
    conflict_resolution: str = Field(default="manual", env="CONFLICT_RESOLUTION")  # manual, auto, source_wins
    sync_retention_days: int = Field(default=90, env="SYNC_RETENTION_DAYS")
    
    # Rate limiting
    rate_limit_per_user: int = Field(default=500, env="RATE_LIMIT_PER_USER")  # per hour
    rate_limit_per_integration: int = Field(default=1000, env="RATE_LIMIT_PER_INTEGRATION")  # per hour
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9008, env="METRICS_PORT")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Feature flags
    enable_servicenow: bool = Field(default=True, env="ENABLE_SERVICENOW")
    enable_jira: bool = Field(default=True, env="ENABLE_JIRA")
    enable_workflows: bool = Field(default=True, env="ENABLE_WORKFLOWS")
    enable_auto_sync: bool = Field(default=True, env="ENABLE_AUTO_SYNC")
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    
    # Natural language processing
    enable_nlp_ticket_creation: bool = Field(default=True, env="ENABLE_NLP_TICKET_CREATION")
    nlp_confidence_threshold: float = Field(default=0.8, env="NLP_CONFIDENCE_THRESHOLD")
    auto_categorize_tickets: bool = Field(default=True, env="AUTO_CATEGORIZE_TICKETS")
    auto_assign_tickets: bool = Field(default=False, env="AUTO_ASSIGN_TICKETS")
    
    # Security settings
    encrypt_credentials: bool = Field(default=True, env="ENCRYPT_CREDENTIALS")
    require_ssl: bool = Field(default=True, env="REQUIRE_SSL")
    verify_ssl_certificates: bool = Field(default=True, env="VERIFY_SSL_CERTIFICATES")
    allowed_itsm_domains: Optional[List[str]] = Field(default=None, env="ALLOWED_ITSM_DOMAINS")
    
    # Background task settings
    background_task_interval: int = Field(default=60, env="BACKGROUND_TASK_INTERVAL")  # seconds
    cleanup_task_interval: int = Field(default=3600, env="CLEANUP_TASK_INTERVAL")  # 1 hour
    metrics_collection_interval: int = Field(default=300, env="METRICS_COLLECTION_INTERVAL")  # 5 minutes
    
    # Attachment settings
    max_attachment_size: int = Field(default=50 * 1024 * 1024, env="MAX_ATTACHMENT_SIZE")  # 50MB
    allowed_attachment_types: List[str] = Field(
        default=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "gif", "csv", "xlsx"],
        env="ALLOWED_ATTACHMENT_TYPES"
    )
    
    # Notification settings
    notification_channels: List[str] = Field(
        default=["email", "webhook", "slack"],
        env="NOTIFICATION_CHANNELS"
    )
    notification_timeout: int = Field(default=30, env="NOTIFICATION_TIMEOUT")
    
    @validator("servicenow_tables", pre=True)
    def parse_servicenow_tables(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
    
    @validator("jira_projects", pre=True)
    def parse_jira_projects(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v
    
    @validator("jira_issue_types", pre=True)
    def parse_jira_issue_types(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
    
    @validator("allowed_attachment_types", pre=True)
    def parse_allowed_attachment_types(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
    
    @validator("notification_channels", pre=True)
    def parse_notification_channels(cls, v):
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v
    
    @validator("allowed_itsm_domains", pre=True)
    def parse_allowed_itsm_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_config() -> Dict[str, Any]:
    """Get database configuration for SQLAlchemy."""
    return {
        "url": settings.database_url,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "echo": settings.debug,
    }


def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration."""
    return {
        "url": settings.redis_url,
        "timeout": settings.redis_timeout,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    }


def get_servicenow_config() -> Optional[Dict[str, Any]]:
    """Get ServiceNow configuration."""
    if not settings.servicenow_instance:
        return None
    
    return {
        "instance": settings.servicenow_instance,
        "username": settings.servicenow_username,
        "password": settings.servicenow_password,
        "api_version": settings.servicenow_api_version,
        "timeout": settings.servicenow_timeout,
        "max_retries": settings.servicenow_max_retries,
        "tables": settings.servicenow_tables,
        "verify_ssl": settings.verify_ssl_certificates,
    }


def get_jira_config() -> Optional[Dict[str, Any]]:
    """Get Jira configuration."""
    if not settings.jira_server:
        return None
    
    return {
        "server": settings.jira_server,
        "username": settings.jira_username,
        "api_token": settings.jira_api_token,
        "timeout": settings.jira_timeout,
        "max_retries": settings.jira_max_retries,
        "projects": settings.jira_projects,
        "issue_types": settings.jira_issue_types,
        "verify_ssl": settings.verify_ssl_certificates,
    }


def get_sync_config() -> Dict[str, Any]:
    """Get synchronization configuration."""
    return {
        "enabled": settings.sync_enabled,
        "bidirectional": settings.bidirectional_sync,
        "interval_minutes": settings.sync_interval_minutes,
        "batch_size": settings.max_sync_batch_size,
        "timeout": settings.sync_timeout,
        "conflict_resolution": settings.conflict_resolution,
        "retention_days": settings.sync_retention_days,
    }


def get_workflow_config() -> Dict[str, Any]:
    """Get workflow configuration."""
    return {
        "max_steps": settings.max_workflow_steps,
        "timeout": settings.workflow_timeout,
        "retry_attempts": settings.workflow_retry_attempts,
        "retry_delay": settings.workflow_retry_delay,
        "enabled": settings.enable_workflows,
    }