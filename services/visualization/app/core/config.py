"""
Configuration management for Visualization Service
"""
from functools import lru_cache
from typing import Optional, List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = Field(default="Splunk MCP Visualization Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Settings
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Database Settings
    database_url: str = Field(default="postgresql://postgres:password@localhost:5432/splunk_mcp", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Chart Generation Settings
    chart_max_width: int = Field(default=1920, env="CHART_MAX_WIDTH")
    chart_max_height: int = Field(default=1080, env="CHART_MAX_HEIGHT")
    chart_max_data_points: int = Field(default=10000, env="CHART_MAX_DATA_POINTS")
    chart_timeout_seconds: int = Field(default=30, env="CHART_TIMEOUT_SECONDS")
    
    # Export Settings
    export_max_file_size_mb: int = Field(default=50, env="EXPORT_MAX_FILE_SIZE_MB")
    export_formats: List[str] = Field(default=["png", "pdf", "svg", "html"], env="EXPORT_FORMATS")
    
    # Performance Settings
    chart_cache_ttl_seconds: int = Field(default=300, env="CHART_CACHE_TTL_SECONDS")
    max_concurrent_renders: int = Field(default=10, env="MAX_CONCURRENT_RENDERS")
    
    # Security Settings
    secret_key: str = Field(default="your-secret-key-change-this", env="SECRET_KEY")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # External Services
    splunk_host: Optional[str] = Field(default=None, env="SPLUNK_HOST")
    splunk_token: Optional[str] = Field(default=None, env="SPLUNK_TOKEN")
    
    # NLP Engine Integration
    nlp_engine_url: str = Field(default="http://localhost:8001", env="NLP_ENGINE_URL")
    nlp_engine_timeout: int = Field(default=30, env="NLP_ENGINE_TIMEOUT")
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance
settings = get_settings()