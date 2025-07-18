#!/usr/bin/env python3
"""
Configuration settings for HTML Report Service.

This module contains all configuration settings for the HTML report service,
including database settings, API settings, HTML generation settings, and more.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    DEBUG: bool = False
    API_PORT: int = 8012
    API_HOST: str = "0.0.0.0"
    
    # Database settings
    DATABASE_URL: str = "postgresql://htmlservice:htmlservice@localhost:5432/htmlservice"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    
    # Authentication settings
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # HTML generation settings
    HTML_OUTPUT_DIR: str = "/tmp/html-reports"
    HTML_TEMPLATE_DIR: str = "app/templates"
    HTML_MAX_FILE_SIZE_MB: int = 100
    HTML_TIMEOUT_SECONDS: int = 300
    HTML_CONCURRENT_JOBS: int = 5
    
    # Chart integration settings
    CHART_SERVICE_URL: str = "http://localhost:8002"
    CHART_TIMEOUT_SECONDS: int = 30
    CHART_MAX_WIDTH: int = 1920
    CHART_MAX_HEIGHT: int = 1080
    CHART_FORMAT: str = "png"
    CHART_DPI: int = 300
    
    # Interactive features settings
    ENABLE_INTERACTIVE_CHARTS: bool = True
    ENABLE_DATA_FILTERING: bool = True
    ENABLE_DRILL_DOWN: bool = True
    ENABLE_ANIMATIONS: bool = True
    ENABLE_RESPONSIVE_DESIGN: bool = True
    
    # Template settings
    DEFAULT_TEMPLATE: str = "modern"
    AVAILABLE_TEMPLATES: List[str] = ["modern", "classic", "minimal", "dark", "corporate"]
    
    # Export settings
    EXPORT_FORMATS: List[str] = ["html", "pdf", "png"]
    DEFAULT_EXPORT_FORMAT: str = "html"
    
    # Performance settings
    MAX_CONCURRENT_JOBS: int = 10
    JOB_QUEUE_SIZE: int = 1000
    WORKER_TIMEOUT: int = 300
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 15
    
    # File cleanup settings
    CLEANUP_OLDER_THAN_DAYS: int = 7
    CLEANUP_INTERVAL_HOURS: int = 24
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # JavaScript libraries settings
    ENABLE_PLOTLY: bool = True
    ENABLE_D3: bool = True
    ENABLE_CHARTJS: bool = True
    ENABLE_DATATABLES: bool = True
    ENABLE_BOOTSTRAP: bool = True
    
    # CDN settings
    USE_CDN: bool = True
    CDN_BASE_URL: str = "https://cdnjs.cloudflare.com/ajax/libs"
    
    # Security settings
    ENABLE_CONTENT_FILTERING: bool = True
    MAX_HTML_SIZE_MB: int = 50
    ALLOWED_DOMAINS: List[str] = []
    
    # Monitoring settings
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9012
    
    @field_validator("HTML_OUTPUT_DIR")
    @classmethod
    def validate_output_dir(cls, v):
        """Ensure output directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("HTML_TEMPLATE_DIR")
    @classmethod
    def validate_template_dir(cls, v):
        """Ensure template directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()


# Export commonly used settings
__all__ = ["settings", "Settings"]