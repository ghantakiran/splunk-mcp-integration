"""
Configuration settings for Cloud Connection Manager Service.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic service configuration
    SERVICE_NAME: str = "cloud-connection-manager"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8018
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://ccm_user:ccm_password@localhost:5432/cloud_connection_manager"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/8"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 8
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_SOCKET_KEEPALIVE: bool = True
    REDIS_SOCKET_KEEPALIVE_OPTIONS: Dict[str, int] = {}
    
    # Connection pooling configuration
    CONNECTION_POOL_SIZE: int = 50
    CONNECTION_POOL_MAX_SIZE: int = 200
    CONNECTION_IDLE_TIMEOUT: int = 300  # 5 minutes
    CONNECTION_MAX_LIFETIME: int = 3600  # 1 hour
    CONNECTION_RETRY_ATTEMPTS: int = 3
    CONNECTION_RETRY_DELAY: float = 1.0
    CONNECTION_HEALTH_CHECK_INTERVAL: int = 30  # seconds
    
    # Load balancing configuration
    LOAD_BALANCER_ALGORITHM: str = "round_robin"  # round_robin, least_connections, weighted_round_robin
    LOAD_BALANCER_HEALTH_CHECK_TIMEOUT: int = 10  # seconds
    LOAD_BALANCER_FAILOVER_TIMEOUT: int = 30  # seconds
    LOAD_BALANCER_CIRCUIT_BREAKER_ENABLED: bool = True
    LOAD_BALANCER_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    LOAD_BALANCER_CIRCUIT_BREAKER_TIMEOUT: int = 60  # seconds
    
    # Health monitoring configuration
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_CHECK_TIMEOUT: int = 10  # seconds
    HEALTH_CHECK_RETRIES: int = 3
    HEALTH_DEGRADED_THRESHOLD: float = 0.7  # 70% success rate
    HEALTH_UNHEALTHY_THRESHOLD: float = 0.3  # 30% success rate
    
    # Metrics collection configuration
    METRICS_COLLECTION_INTERVAL: int = 60  # seconds
    METRICS_RETENTION_DAYS: int = 30
    METRICS_AGGREGATION_INTERVALS: List[str] = ["1m", "5m", "15m", "1h", "1d"]
    
    # Authentication configuration
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate limiting configuration
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    RATE_LIMIT_ENABLED: bool = True
    
    # Security configuration
    CORS_ENABLED: bool = True
    HTTPS_ONLY: bool = False
    SECURE_COOKIES: bool = False
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: Optional[str] = None
    LOG_ROTATION_SIZE: str = "100MB"
    LOG_ROTATION_TIME: str = "1d"
    LOG_RETENTION_COUNT: int = 30
    
    # External service URLs
    CLOUD_AUTH_SERVICE_URL: str = "http://localhost:8017"
    API_GATEWAY_URL: str = "http://localhost:8000"
    NLP_ENGINE_URL: str = "http://localhost:8001"
    
    # Splunk Cloud configuration
    SPLUNK_CLOUD_BASE_URL: str = "https://api.splunkcloud.com"
    SPLUNK_CLOUD_API_VERSION: str = "v1"
    SPLUNK_CLOUD_DEFAULT_TIMEOUT: int = 30
    
    # Default Splunk Enterprise configuration
    SPLUNK_ENTERPRISE_DEFAULT_PORT: int = 8089
    SPLUNK_ENTERPRISE_DEFAULT_SCHEME: str = "https"
    SPLUNK_ENTERPRISE_DEFAULT_TIMEOUT: int = 30
    
    # Circuit breaker configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: str = "RequestException"
    
    # Performance monitoring thresholds
    RESPONSE_TIME_WARNING_THRESHOLD: float = 1.0  # seconds
    RESPONSE_TIME_CRITICAL_THRESHOLD: float = 3.0  # seconds
    ERROR_RATE_WARNING_THRESHOLD: float = 0.05  # 5%
    ERROR_RATE_CRITICAL_THRESHOLD: float = 0.10  # 10%
    
    # Connection endpoint types
    SUPPORTED_ENDPOINT_TYPES: List[str] = ["enterprise", "cloud"]
    DEFAULT_ENDPOINT_TYPE: str = "enterprise"
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string if needed."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("REDIS_SOCKET_KEEPALIVE_OPTIONS", pre=True)
    def parse_redis_keepalive_options(cls, v):
        """Parse Redis keepalive options."""
        if isinstance(v, str):
            # Parse from environment variable format: "TCP_KEEPIDLE=1,TCP_KEEPINTVL=3,TCP_KEEPCNT=5"
            options = {}
            if v:
                for option in v.split(","):
                    if "=" in option:
                        key, value = option.split("=", 1)
                        options[key.strip()] = int(value.strip())
            return options
        return v or {}
    
    @validator("LOAD_BALANCER_ALGORITHM")
    def validate_load_balancer_algorithm(cls, v):
        """Validate load balancer algorithm."""
        valid_algorithms = ["round_robin", "least_connections", "weighted_round_robin", "random"]
        if v not in valid_algorithms:
            raise ValueError(f"Invalid load balancer algorithm. Must be one of: {valid_algorithms}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator("LOG_FORMAT")
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ["json", "text", "structured"]
        if v not in valid_formats:
            raise ValueError(f"Invalid log format. Must be one of: {valid_formats}")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        # Environment variable mappings
        fields = {
            "DATABASE_URL": {"env": ["DATABASE_URL", "CCM_DATABASE_URL"]},
            "REDIS_URL": {"env": ["REDIS_URL", "CCM_REDIS_URL"]},
            "JWT_SECRET_KEY": {"env": ["JWT_SECRET_KEY", "CCM_JWT_SECRET_KEY"]},
            "CLOUD_AUTH_SERVICE_URL": {"env": ["CLOUD_AUTH_SERVICE_URL", "CCM_CLOUD_AUTH_SERVICE_URL"]}
        }


# Create global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get the database URL with proper formatting."""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get the Redis URL with proper formatting."""
    return settings.REDIS_URL


def get_connection_pool_config() -> Dict[str, Any]:
    """Get connection pool configuration."""
    return {
        "pool_size": settings.CONNECTION_POOL_SIZE,
        "max_size": settings.CONNECTION_POOL_MAX_SIZE,
        "idle_timeout": settings.CONNECTION_IDLE_TIMEOUT,
        "max_lifetime": settings.CONNECTION_MAX_LIFETIME,
        "retry_attempts": settings.CONNECTION_RETRY_ATTEMPTS,
        "retry_delay": settings.CONNECTION_RETRY_DELAY,
        "health_check_interval": settings.CONNECTION_HEALTH_CHECK_INTERVAL
    }


def get_load_balancer_config() -> Dict[str, Any]:
    """Get load balancer configuration."""
    return {
        "algorithm": settings.LOAD_BALANCER_ALGORITHM,
        "health_check_timeout": settings.LOAD_BALANCER_HEALTH_CHECK_TIMEOUT,
        "failover_timeout": settings.LOAD_BALANCER_FAILOVER_TIMEOUT,
        "circuit_breaker_enabled": settings.LOAD_BALANCER_CIRCUIT_BREAKER_ENABLED,
        "circuit_breaker_failure_threshold": settings.LOAD_BALANCER_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        "circuit_breaker_timeout": settings.LOAD_BALANCER_CIRCUIT_BREAKER_TIMEOUT
    }


def get_health_monitor_config() -> Dict[str, Any]:
    """Get health monitor configuration."""
    return {
        "check_interval": settings.HEALTH_CHECK_INTERVAL,
        "check_timeout": settings.HEALTH_CHECK_TIMEOUT,
        "check_retries": settings.HEALTH_CHECK_RETRIES,
        "degraded_threshold": settings.HEALTH_DEGRADED_THRESHOLD,
        "unhealthy_threshold": settings.HEALTH_UNHEALTHY_THRESHOLD
    }


def get_metrics_config() -> Dict[str, Any]:
    """Get metrics collection configuration."""
    return {
        "collection_interval": settings.METRICS_COLLECTION_INTERVAL,
        "retention_days": settings.METRICS_RETENTION_DAYS,
        "aggregation_intervals": settings.METRICS_AGGREGATION_INTERVALS
    }