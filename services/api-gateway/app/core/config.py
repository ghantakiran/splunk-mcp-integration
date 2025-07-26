"""
Application configuration management
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = Field(default="Splunk MCP Integration API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32)
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_days: int = Field(default=7, env="JWT_REFRESH_EXPIRE_DAYS")
    jwt_refresh_expire_days_extended: int = Field(default=30, env="JWT_REFRESH_EXPIRE_DAYS_EXTENDED")
    
    # User Registration
    registration_enabled: bool = Field(default=True, env="REGISTRATION_ENABLED")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # Session Management
    session_timeout_minutes: int = Field(default=60, env="SESSION_TIMEOUT_MINUTES")
    max_sessions_per_user: int = Field(default=5, env="MAX_SESSIONS_PER_USER")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # External Services
    nlp_engine_url: str = Field(default="http://nlp-engine:8000", env="NLP_ENGINE_URL")
    spl_translator_url: str = Field(default="http://spl-translator:8000", env="SPL_TRANSLATOR_URL")
    access_control_url: str = Field(default="http://access-control:8000", env="ACCESS_CONTROL_URL")
    visualization_url: str = Field(default="http://visualization:8000", env="VISUALIZATION_URL")
    alert_manager_url: str = Field(default="http://alert-manager:8000", env="ALERT_MANAGER_URL")
    
    # Cloud Services
    cloud_connection_manager_url: str = Field(default="http://cloud-connection-manager:8018", env="CLOUD_CONNECTION_MANAGER_URL")
    cloud_auth_service_url: str = Field(default="http://cloud-auth-service:8017", env="CLOUD_AUTH_SERVICE_URL")
    
    # Splunk Configuration
    splunk_host: Optional[str] = Field(default=None, env="SPLUNK_HOST")
    splunk_token: Optional[str] = Field(default=None, env="SPLUNK_TOKEN")
    splunk_username: Optional[str] = Field(default=None, env="SPLUNK_USERNAME")
    splunk_password: Optional[str] = Field(default=None, env="SPLUNK_PASSWORD")
    splunk_verify_ssl: bool = Field(default=True, env="SPLUNK_VERIFY_SSL")
    splunk_timeout: int = Field(default=30, env="SPLUNK_TIMEOUT")
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    metrics_path: str = "/metrics"
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # File Upload
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=["csv", "json", "txt"],
        env="ALLOWED_FILE_TYPES"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_file_types", pre=True)
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance
settings = get_settings()