"""
Configuration management for Unified Authentication Bridge Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = Field(default="Unified Authentication Bridge", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8019, env="PORT")
    
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
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Redis for caching and session management
    redis_url: str = Field(..., env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=9, env="REDIS_DB")  # Use DB 9 for auth bridge
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # External Services
    api_gateway_url: str = Field(default="http://api-gateway:8000", env="API_GATEWAY_URL")
    cloud_auth_service_url: str = Field(default="http://cloud-auth-service:8017", env="CLOUD_AUTH_SERVICE_URL")
    cloud_connection_manager_url: str = Field(default="http://cloud-connection-manager:8018", env="CLOUD_CONNECTION_MANAGER_URL")
    nlp_engine_url: str = Field(default="http://nlp-engine:8001", env="NLP_ENGINE_URL")
    
    # Splunk Configuration
    # Enterprise Splunk
    splunk_enterprise_host: Optional[str] = Field(default=None, env="SPLUNK_ENTERPRISE_HOST")
    splunk_enterprise_port: int = Field(default=8089, env="SPLUNK_ENTERPRISE_PORT")
    splunk_enterprise_scheme: str = Field(default="https", env="SPLUNK_ENTERPRISE_SCHEME")
    splunk_enterprise_username: Optional[str] = Field(default=None, env="SPLUNK_ENTERPRISE_USERNAME")
    splunk_enterprise_password: Optional[str] = Field(default=None, env="SPLUNK_ENTERPRISE_PASSWORD")
    splunk_enterprise_token: Optional[str] = Field(default=None, env="SPLUNK_ENTERPRISE_TOKEN")
    
    # Cloud Splunk defaults
    splunk_cloud_base_url: str = Field(default="https://api.splunkcloud.com", env="SPLUNK_CLOUD_BASE_URL")
    splunk_cloud_api_version: str = Field(default="v1", env="SPLUNK_CLOUD_API_VERSION")
    
    # Authentication Bridge Configuration
    auth_bridge_mode: str = Field(default="hybrid", env="AUTH_BRIDGE_MODE")  # hybrid, enterprise_only, cloud_only
    auth_priority: List[str] = Field(default=["cloud", "enterprise"], env="AUTH_PRIORITY")  # Priority order for auth attempts
    auth_fallback_enabled: bool = Field(default=True, env="AUTH_FALLBACK_ENABLED")
    auth_cache_ttl: int = Field(default=300, env="AUTH_CACHE_TTL")  # 5 minutes
    
    # Session Management
    session_timeout_minutes: int = Field(default=60, env="SESSION_TIMEOUT_MINUTES")
    max_sessions_per_user: int = Field(default=5, env="MAX_SESSIONS_PER_USER")
    session_bridge_enabled: bool = Field(default=True, env="SESSION_BRIDGE_ENABLED")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=200, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    
    # Health Check Configuration
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=10, env="HEALTH_CHECK_TIMEOUT")
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    metrics_path: str = "/metrics"
    
    # Logging
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("auth_priority", pre=True)
    def parse_auth_priority(cls, v):
        if isinstance(v, str):
            return [priority.strip() for priority in v.split(",")]
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @validator("auth_bridge_mode")
    def validate_auth_bridge_mode(cls, v):
        valid_modes = ["hybrid", "enterprise_only", "cloud_only"]
        if v not in valid_modes:
            raise ValueError(f"Auth bridge mode must be one of: {valid_modes}")
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