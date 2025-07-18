"""
Configuration management for BI Integration Service.
"""

import os
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "BI Integration Service"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(env="REDIS_URL")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    redis_retry_on_timeout: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Authentication
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_seconds: int = Field(default=3600, env="JWT_EXPIRATION_SECONDS")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_default_limit: int = Field(default=100, env="RATE_LIMIT_DEFAULT_LIMIT")
    rate_limit_default_window: int = Field(default=3600, env="RATE_LIMIT_DEFAULT_WINDOW")
    rate_limit_burst_limit: int = Field(default=50, env="RATE_LIMIT_BURST_LIMIT")
    
    # Metrics
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Tableau Configuration
    tableau_server_url: Optional[str] = Field(default=None, env="TABLEAU_SERVER_URL")
    tableau_site_id: Optional[str] = Field(default="", env="TABLEAU_SITE_ID")
    tableau_username: Optional[str] = Field(default=None, env="TABLEAU_USERNAME")
    tableau_password: Optional[str] = Field(default=None, env="TABLEAU_PASSWORD")
    tableau_token_name: Optional[str] = Field(default=None, env="TABLEAU_TOKEN_NAME")
    tableau_token_value: Optional[str] = Field(default=None, env="TABLEAU_TOKEN_VALUE")
    tableau_api_version: str = Field(default="3.19", env="TABLEAU_API_VERSION")
    tableau_timeout: int = Field(default=300, env="TABLEAU_TIMEOUT")
    tableau_max_retries: int = Field(default=3, env="TABLEAU_MAX_RETRIES")
    tableau_batch_size: int = Field(default=100, env="TABLEAU_BATCH_SIZE")
    
    # Power BI Configuration
    powerbi_tenant_id: Optional[str] = Field(default=None, env="POWERBI_TENANT_ID")
    powerbi_client_id: Optional[str] = Field(default=None, env="POWERBI_CLIENT_ID")
    powerbi_client_secret: Optional[str] = Field(default=None, env="POWERBI_CLIENT_SECRET")
    powerbi_scope: List[str] = Field(
        default=["https://analysis.windows.net/powerbi/api/.default"],
        env="POWERBI_SCOPE"
    )
    powerbi_authority: str = Field(
        default="https://login.microsoftonline.com/",
        env="POWERBI_AUTHORITY"
    )
    powerbi_api_url: str = Field(
        default="https://api.powerbi.com/",
        env="POWERBI_API_URL"
    )
    powerbi_timeout: int = Field(default=300, env="POWERBI_TIMEOUT")
    powerbi_max_retries: int = Field(default=3, env="POWERBI_MAX_RETRIES")
    powerbi_batch_size: int = Field(default=100, env="POWERBI_BATCH_SIZE")
    
    # Data Processing
    max_data_rows: int = Field(default=1000000, env="MAX_DATA_ROWS")
    data_chunk_size: int = Field(default=10000, env="DATA_CHUNK_SIZE")
    extract_timeout: int = Field(default=3600, env="EXTRACT_TIMEOUT")
    refresh_timeout: int = Field(default=1800, env="REFRESH_TIMEOUT")
    
    # File Storage
    temp_dir: str = Field(default="/tmp/bi-integration", env="TEMP_DIR")
    max_file_size_mb: int = Field(default=500, env="MAX_FILE_SIZE_MB")
    cleanup_interval_hours: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    
    # Security
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")
    
    # Background Jobs
    celery_broker_url: str = Field(
        default="redis://localhost:6379/4",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/5",
        env="CELERY_RESULT_BACKEND"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("powerbi_scope", pre=True)
    def parse_powerbi_scope(cls, v):
        """Parse Power BI scope from string or list."""
        if isinstance(v, str):
            return [scope.strip() for scope in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    return {
        "url": settings.database_url,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_recycle": settings.database_pool_recycle,
        "echo": settings.database_echo,
    }


def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration."""
    return {
        "url": settings.redis_url,
        "timeout": settings.redis_timeout,
        "retry_on_timeout": settings.redis_retry_on_timeout,
        "health_check_interval": settings.redis_health_check_interval,
    }


def get_tableau_config() -> Dict[str, Any]:
    """Get Tableau configuration."""
    return {
        "server_url": settings.tableau_server_url,
        "site_id": settings.tableau_site_id,
        "username": settings.tableau_username,
        "password": settings.tableau_password,
        "token_name": settings.tableau_token_name,
        "token_value": settings.tableau_token_value,
        "api_version": settings.tableau_api_version,
        "timeout": settings.tableau_timeout,
        "max_retries": settings.tableau_max_retries,
        "batch_size": settings.tableau_batch_size,
    }


def get_powerbi_config() -> Dict[str, Any]:
    """Get Power BI configuration."""
    return {
        "tenant_id": settings.powerbi_tenant_id,
        "client_id": settings.powerbi_client_id,
        "client_secret": settings.powerbi_client_secret,
        "scope": settings.powerbi_scope,
        "authority": settings.powerbi_authority,
        "api_url": settings.powerbi_api_url,
        "timeout": settings.powerbi_timeout,
        "max_retries": settings.powerbi_max_retries,
        "batch_size": settings.powerbi_batch_size,
    }


def get_security_config() -> Dict[str, Any]:
    """Get security configuration."""
    return {
        "jwt_secret_key": settings.jwt_secret_key,
        "jwt_algorithm": settings.jwt_algorithm,
        "jwt_expiration_seconds": settings.jwt_expiration_seconds,
        "encryption_key": settings.encryption_key,
        "password_min_length": settings.password_min_length,
        "session_timeout": settings.session_timeout,
    }