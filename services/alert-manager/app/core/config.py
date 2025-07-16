"""
Configuration management for Alert Management service.
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Service Configuration
    service_name: str = "alert-manager"
    service_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8003
    reload: bool = False
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/splunk_mcp"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Alert Processing Configuration
    alert_evaluation_interval: int = 60  # seconds
    max_alerts_per_rule: int = 100
    correlation_window: int = 300  # seconds
    alert_retention_days: int = 90
    
    # Notification Configuration
    notification_retry_attempts: int = 3
    notification_retry_delay: int = 5  # seconds
    notification_batch_size: int = 50
    notification_rate_limit: int = 100  # per minute
    
    # Email Configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "alerts@example.com"
    smtp_from_name: str = "Splunk MCP Alerts"
    
    # Slack Configuration
    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    
    # Microsoft Teams Configuration
    teams_webhook_url: Optional[str] = None
    
    # SMS Configuration (via Twilio)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    
    # Webhook Configuration
    webhook_timeout: int = 30  # seconds
    webhook_retry_attempts: int = 3
    webhook_verify_ssl: bool = True
    
    # Security Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    encryption_key: Optional[str] = None
    
    # API Configuration
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # External Service URLs
    nlp_service_url: str = "http://localhost:8001"
    api_gateway_url: str = "http://localhost:8000"
    visualization_service_url: str = "http://localhost:8002"
    
    # Monitoring Configuration
    enable_metrics: bool = True
    metrics_port: int = 9003
    health_check_interval: int = 30  # seconds
    
    @validator('cors_origins', pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip() for i in v.split(',')]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ValueError('Database URL must start with postgresql:// or postgresql+asyncpg://')
        return v
    
    @validator('redis_url')
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        if not v.startswith('redis://'):
            raise ValueError('Redis URL must start with redis://')
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()