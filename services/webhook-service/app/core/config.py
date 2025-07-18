"""
Configuration management for Webhook Service.
"""

import os
from typing import List, Optional, Any, Dict
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Webhook service configuration settings."""
    
    # Application settings
    app_name: str = "Splunk MCP Webhook Service"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8007, env="PORT")
    
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
    
    # Service timeouts
    api_timeout: int = Field(default=30, env="API_TIMEOUT")
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    delivery_timeout: int = Field(default=60, env="DELIVERY_TIMEOUT")
    
    # Security settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Webhook settings
    max_webhook_payload_size: int = Field(default=10 * 1024 * 1024, env="MAX_WEBHOOK_PAYLOAD_SIZE")  # 10MB
    max_webhooks_per_user: int = Field(default=50, env="MAX_WEBHOOKS_PER_USER")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    webhook_retry_delay: int = Field(default=300, env="WEBHOOK_RETRY_DELAY")  # 5 minutes
    webhook_delivery_timeout: int = Field(default=30, env="WEBHOOK_DELIVERY_TIMEOUT")
    
    # Event processing settings
    max_events_per_minute: int = Field(default=1000, env="MAX_EVENTS_PER_MINUTE")
    event_batch_size: int = Field(default=100, env="EVENT_BATCH_SIZE")
    event_processing_interval: int = Field(default=10, env="EVENT_PROCESSING_INTERVAL")  # seconds
    event_retention_days: int = Field(default=30, env="EVENT_RETENTION_DAYS")
    
    # Delivery settings
    max_concurrent_deliveries: int = Field(default=50, env="MAX_CONCURRENT_DELIVERIES")
    delivery_retry_exponential_base: float = Field(default=2.0, env="DELIVERY_RETRY_EXPONENTIAL_BASE")
    delivery_retry_max_delay: int = Field(default=3600, env="DELIVERY_RETRY_MAX_DELAY")  # 1 hour
    delivery_queue_size: int = Field(default=10000, env="DELIVERY_QUEUE_SIZE")
    
    # Rate limiting
    rate_limit_per_user: int = Field(default=1000, env="RATE_LIMIT_PER_USER")  # per hour
    rate_limit_per_endpoint: int = Field(default=500, env="RATE_LIMIT_PER_ENDPOINT")  # per hour
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9007, env="METRICS_PORT")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Feature flags
    enable_signature_verification: bool = Field(default=True, env="ENABLE_SIGNATURE_VERIFICATION")
    enable_payload_compression: bool = Field(default=False, env="ENABLE_PAYLOAD_COMPRESSION")
    enable_delivery_tracking: bool = Field(default=True, env="ENABLE_DELIVERY_TRACKING")
    enable_event_filtering: bool = Field(default=True, env="ENABLE_EVENT_FILTERING")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    
    # Security whitelist/blacklist
    allowed_webhook_domains: Optional[List[str]] = Field(default=None, env="ALLOWED_WEBHOOK_DOMAINS")
    blocked_webhook_domains: Optional[List[str]] = Field(default=None, env="BLOCKED_WEBHOOK_DOMAINS")
    allowed_user_agents: Optional[List[str]] = Field(default=None, env="ALLOWED_USER_AGENTS")
    blocked_user_agents: Optional[List[str]] = Field(default=None, env="BLOCKED_USER_AGENTS")
    
    # HTTP client settings
    http_client_timeout: int = Field(default=30, env="HTTP_CLIENT_TIMEOUT")
    http_client_max_connections: int = Field(default=100, env="HTTP_CLIENT_MAX_CONNECTIONS")
    http_client_max_keepalive: int = Field(default=20, env="HTTP_CLIENT_MAX_KEEPALIVE")
    http_client_keepalive_expiry: int = Field(default=5, env="HTTP_CLIENT_KEEPALIVE_EXPIRY")
    
    # Background task settings
    background_task_interval: int = Field(default=60, env="BACKGROUND_TASK_INTERVAL")  # seconds
    cleanup_task_interval: int = Field(default=3600, env="CLEANUP_TASK_INTERVAL")  # 1 hour
    metrics_collection_interval: int = Field(default=300, env="METRICS_COLLECTION_INTERVAL")  # 5 minutes
    
    # Event types configuration
    supported_event_types: List[str] = Field(
        default=[
            "query.completed",
            "alert.triggered",
            "dashboard.created",
            "report.generated",
            "error.occurred",
            "system.status_changed",
            "user.action",
            "data.updated"
        ],
        env="SUPPORTED_EVENT_TYPES"
    )
    
    # Webhook endpoint validation
    webhook_url_schemes: List[str] = Field(
        default=["http", "https"],
        env="WEBHOOK_URL_SCHEMES"
    )
    webhook_required_headers: List[str] = Field(
        default=["User-Agent", "Content-Type"],
        env="WEBHOOK_REQUIRED_HEADERS"
    )
    
    @validator("allowed_webhook_domains", pre=True)
    def parse_allowed_webhook_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    @validator("blocked_webhook_domains", pre=True)
    def parse_blocked_webhook_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    @validator("supported_event_types", pre=True)
    def parse_supported_event_types(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
    
    @validator("webhook_url_schemes", pre=True)
    def parse_webhook_url_schemes(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v
    
    @validator("webhook_required_headers", pre=True)
    def parse_webhook_required_headers(cls, v):
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
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


def get_http_client_config() -> Dict[str, Any]:
    """Get HTTP client configuration for webhook delivery."""
    return {
        "timeout": settings.http_client_timeout,
        "limits": {
            "max_connections": settings.http_client_max_connections,
            "max_keepalive_connections": settings.http_client_max_keepalive,
            "keepalive_expiry": settings.http_client_keepalive_expiry,
        },
        "headers": {
            "User-Agent": f"Splunk-MCP-Webhook-Service/{settings.version}",
            "Accept": "application/json",
        },
    }


def get_webhook_delivery_config() -> Dict[str, Any]:
    """Get webhook delivery configuration."""
    return {
        "timeout": settings.webhook_delivery_timeout,
        "retry_attempts": settings.webhook_retry_attempts,
        "retry_delay": settings.webhook_retry_delay,
        "retry_exponential_base": settings.delivery_retry_exponential_base,
        "retry_max_delay": settings.delivery_retry_max_delay,
        "max_concurrent": settings.max_concurrent_deliveries,
        "queue_size": settings.delivery_queue_size,
    }


def get_event_processing_config() -> Dict[str, Any]:
    """Get event processing configuration."""
    return {
        "max_events_per_minute": settings.max_events_per_minute,
        "batch_size": settings.event_batch_size,
        "processing_interval": settings.event_processing_interval,
        "retention_days": settings.event_retention_days,
        "supported_types": settings.supported_event_types,
    }