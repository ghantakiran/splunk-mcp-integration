"""
Configuration settings for the Secure Sharing Service.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8016
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Secure Sharing Service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Secure resource sharing with expiration and access control"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/secure_sharing"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_CONNECTION_TIMEOUT: int = 5
    
    # Authentication Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security Configuration
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000"
    ]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Service Authentication
    SERVICE_AUTH_TOKEN: str = "your-service-token-change-in-production"
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 100
    DEFAULT_RATE_LIMIT_WINDOW: int = 60
    RATE_LIMIT_REDIS_PREFIX: str = "rate_limit:"
    
    # Share Configuration
    SHARE_BASE_URL: str = "http://localhost:8016"
    DEFAULT_SHARE_TOKEN_LENGTH: int = 32
    DEFAULT_INVITATION_TOKEN_LENGTH: int = 64
    MAX_SHARES_PER_USER: int = 1000
    MAX_SHARE_DURATION_DAYS: int = 365
    DEFAULT_EXPIRATION_HOURS: int = 168  # 7 days
    
    # File Storage Configuration
    FILE_STORAGE_PATH: str = "/tmp/secure_shares"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "csv", 
        "json", "xml", "html", "png", "jpg", "jpeg"
    ]
    
    # External Services
    NLP_ENGINE_URL: str = "http://localhost:8001"
    VISUALIZATION_SERVICE_URL: str = "http://localhost:8002"
    API_GATEWAY_URL: str = "http://localhost:8000"
    EMAIL_SERVICE_URL: str = "http://localhost:8006"
    SLACK_BOT_URL: str = "http://localhost:8004"
    TEAMS_BOT_URL: str = "http://localhost:8005"
    
    # Export Services
    PDF_EXPORT_SERVICE_URL: str = "http://localhost:8009"
    POWERPOINT_EXPORT_SERVICE_URL: str = "http://localhost:8011"
    WORD_EXPORT_SERVICE_URL: str = "http://localhost:8013"
    HTML_REPORT_SERVICE_URL: str = "http://localhost:8012"
    CSV_EXPORT_SERVICE_URL: str = "http://localhost:8014"
    
    # Notification Configuration
    EMAIL_ENABLED: bool = True
    SLACK_ENABLED: bool = True
    TEAMS_ENABLED: bool = True
    WEBHOOK_ENABLED: bool = True
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9016
    HEALTH_CHECK_ENABLED: bool = True
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "midnight"
    LOG_RETENTION: int = 30
    
    # Background Tasks Configuration
    BACKGROUND_TASKS_ENABLED: bool = True
    CLEANUP_INTERVAL_HOURS: int = 1
    METRICS_COLLECTION_INTERVAL_MINUTES: int = 15
    EXPIRATION_CHECK_INTERVAL_MINUTES: int = 30
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300
    CACHE_ENABLED: bool = True
    CACHE_PREFIX: str = "secure_sharing:"
    
    # Analytics Configuration
    ANALYTICS_ENABLED: bool = True
    ANALYTICS_RETENTION_DAYS: int = 90
    ANONYMOUS_ANALYTICS: bool = True
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ft.strip().lower() for ft in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a Redis connection string")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Development settings
class DevelopmentSettings(Settings):
    """Development-specific settings."""
    
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    # Use local services
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/secure_sharing_dev"
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # Relaxed security for development
    JWT_SECRET_KEY: str = "dev-secret-key-not-for-production"
    SERVICE_AUTH_TOKEN: str = "dev-service-token"
    
    # Enable all features for testing
    RATE_LIMIT_ENABLED: bool = False
    METRICS_ENABLED: bool = True
    BACKGROUND_TASKS_ENABLED: bool = True


# Testing settings
class TestingSettings(Settings):
    """Testing-specific settings."""
    
    DEBUG: bool = True
    LOG_LEVEL: str = "WARNING"
    
    # Use test databases
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/secure_sharing_test"
    REDIS_URL: str = "redis://localhost:6379/2"
    
    # Fast expiration for tests
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    CACHE_TTL_SECONDS: int = 10
    
    # Disable background tasks and external services
    BACKGROUND_TASKS_ENABLED: bool = False
    EMAIL_ENABLED: bool = False
    SLACK_ENABLED: bool = False
    TEAMS_ENABLED: bool = False
    WEBHOOK_ENABLED: bool = False
    RATE_LIMIT_ENABLED: bool = False


# Production settings
class ProductionSettings(Settings):
    """Production-specific settings."""
    
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security settings
    ALLOWED_HOSTS: List[str] = ["api.company.com", "shares.company.com"]
    SHARE_BASE_URL: str = "https://shares.company.com"
    
    # Performance settings
    DATABASE_POOL_SIZE: int = 50
    DATABASE_MAX_OVERFLOW: int = 100
    REDIS_POOL_SIZE: int = 50
    
    # Enhanced security
    CORS_CREDENTIALS: bool = True
    RATE_LIMIT_ENABLED: bool = True
    
    # Production file storage
    FILE_STORAGE_PATH: str = "/app/data/shares"
    
    @validator("JWT_SECRET_KEY")
    def validate_production_secret(cls, v):
        if v == "your-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed in production")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        return v
    
    @validator("SERVICE_AUTH_TOKEN")
    def validate_production_service_token(cls, v):
        if v == "your-service-token-change-in-production":
            raise ValueError("SERVICE_AUTH_TOKEN must be changed in production")
        if len(v) < 32:
            raise ValueError("SERVICE_AUTH_TOKEN must be at least 32 characters in production")
        return v


def get_settings() -> Settings:
    """Get settings based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Use environment-specific settings
settings = get_settings()