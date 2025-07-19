"""
Configuration settings for the Report Scheduling Service.
"""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8016, description="API port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Database Configuration
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database connection pool overflow")
    
    # Redis Configuration
    REDIS_URL: str = Field(..., description="Redis connection URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Redis connection pool size")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_HOURS: int = Field(default=24, description="JWT token expiration hours")
    
    # Security Configuration
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000", description="Allowed CORS origins")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, description="Rate limit per minute")
    RATE_LIMIT_BURST: int = Field(default=20, description="Rate limit burst allowance")
    
    # Report Scheduling Configuration
    MAX_CONCURRENT_JOBS: int = Field(default=10, description="Maximum concurrent report jobs")
    MAX_SCHEDULE_HISTORY: int = Field(default=1000, description="Maximum schedule execution history")
    DEFAULT_TIMEZONE: str = Field(default="UTC", description="Default timezone for schedules")
    MAX_DELIVERY_RETRIES: int = Field(default=3, description="Maximum delivery retry attempts")
    
    # File Storage Configuration
    REPORTS_STORAGE_PATH: str = Field(default="/tmp/scheduled-reports", description="Report storage path")
    MAX_REPORT_SIZE_MB: int = Field(default=100, description="Maximum report file size in MB")
    REPORT_RETENTION_DAYS: int = Field(default=30, description="Report file retention period")
    
    # Email Configuration
    SMTP_HOST: str = Field(default="localhost", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    EMAIL_FROM: str = Field(default="noreply@example.com", description="Default sender email")
    
    # Notification Configuration
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None, description="Slack webhook URL")
    TEAMS_WEBHOOK_URL: Optional[str] = Field(default=None, description="Microsoft Teams webhook URL")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # Celery Configuration (Background Jobs)
    CELERY_BROKER_URL: str = Field(..., description="Celery broker URL (Redis)")
    CELERY_RESULT_BACKEND: str = Field(..., description="Celery result backend URL")
    CELERY_TASK_SERIALIZER: str = Field(default="json", description="Celery task serializer")
    CELERY_RESULT_SERIALIZER: str = Field(default="json", description="Celery result serializer")
    CELERY_TIMEZONE: str = Field(default="UTC", description="Celery timezone")
    
    # External Service URLs
    NLP_ENGINE_URL: str = Field(default="http://localhost:8001", description="NLP Engine service URL")
    VISUALIZATION_SERVICE_URL: str = Field(default="http://localhost:8002", description="Visualization service URL")
    PDF_EXPORT_SERVICE_URL: str = Field(default="http://localhost:8009", description="PDF Export service URL")
    POWERPOINT_EXPORT_SERVICE_URL: str = Field(default="http://localhost:8011", description="PowerPoint Export service URL")
    WORD_EXPORT_SERVICE_URL: str = Field(default="http://localhost:8013", description="Word Export service URL")
    CSV_EXPORT_SERVICE_URL: str = Field(default="http://localhost:8014", description="CSV Export service URL")
    JSON_XML_EXPORT_SERVICE_URL: str = Field(default="http://localhost:8015", description="JSON/XML Export service URL")
    HTML_REPORT_SERVICE_URL: str = Field(default="http://localhost:8012", description="HTML Report service URL")
    EMAIL_SERVICE_URL: str = Field(default="http://localhost:8006", description="Email service URL")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    HEALTH_CHECK_TIMEOUT: int = Field(default=30, description="Health check timeout in seconds")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()