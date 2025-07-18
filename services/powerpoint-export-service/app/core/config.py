#!/usr/bin/env python3
"""
Configuration settings for PowerPoint Export Service.

This module contains all configuration settings for the PowerPoint export service,
including database settings, API settings, PowerPoint generation settings, and more.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    DEBUG: bool = False
    API_PORT: int = 8011
    API_HOST: str = "0.0.0.0"
    
    # Database settings
    DATABASE_URL: str = "postgresql://pptservice:pptservice@localhost:5432/pptservice"
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
    
    # PowerPoint generation settings
    PPT_OUTPUT_DIR: str = "/tmp/ppt-exports"
    PPT_TEMPLATE_DIR: str = "app/templates"
    PPT_MAX_FILE_SIZE_MB: int = 200
    PPT_MAX_SLIDES: int = 100
    PPT_TIMEOUT_SECONDS: int = 600
    PPT_CONCURRENT_JOBS: int = 5
    
    # Chart integration settings
    CHART_SERVICE_URL: str = "http://localhost:8002"
    CHART_TIMEOUT_SECONDS: int = 30
    CHART_MAX_WIDTH: int = 1920
    CHART_MAX_HEIGHT: int = 1080
    CHART_FORMAT: str = "png"
    CHART_DPI: int = 300
    
    # Slide layout settings
    SLIDE_WIDTH: int = 10  # inches
    SLIDE_HEIGHT: int = 7.5  # inches
    SLIDE_MARGIN: float = 0.5  # inches
    
    # Theme settings
    DEFAULT_THEME: str = "office"
    AVAILABLE_THEMES: List[str] = ["office", "modern", "colorful", "dark", "minimal"]
    
    # Animation settings
    ENABLE_ANIMATIONS: bool = True
    DEFAULT_ANIMATION: str = "fade"
    AVAILABLE_ANIMATIONS: List[str] = ["fade", "slide", "zoom", "flip", "none"]
    
    # Transition settings
    ENABLE_TRANSITIONS: bool = True
    DEFAULT_TRANSITION: str = "fade"
    AVAILABLE_TRANSITIONS: List[str] = ["fade", "slide", "push", "cover", "uncover", "none"]
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 50
    RATE_LIMIT_BURST: int = 10
    
    # File cleanup settings
    CLEANUP_OLDER_THAN_DAYS: int = 7
    CLEANUP_INTERVAL_HOURS: int = 24
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Performance settings
    MAX_CONCURRENT_JOBS: int = 10
    JOB_QUEUE_SIZE: int = 1000
    WORKER_TIMEOUT: int = 300
    
    # Font settings
    DEFAULT_FONT_FAMILY: str = "Calibri"
    DEFAULT_FONT_SIZE: int = 18
    AVAILABLE_FONTS: List[str] = ["Calibri", "Arial", "Times New Roman", "Helvetica", "Georgia"]
    
    # Color scheme settings
    DEFAULT_COLOR_SCHEME: str = "blue"
    AVAILABLE_COLOR_SCHEMES: List[str] = ["blue", "red", "green", "orange", "purple", "teal"]
    
    # Template settings
    ENABLE_CUSTOM_TEMPLATES: bool = True
    MAX_TEMPLATE_SIZE_MB: int = 50
    TEMPLATE_CACHE_TTL: int = 3600
    
    # Export settings
    EXPORT_FORMATS: List[str] = ["pptx", "pdf", "png", "jpg"]
    DEFAULT_EXPORT_FORMAT: str = "pptx"
    
    # Security settings
    ENABLE_CONTENT_FILTERING: bool = True
    MAX_TEXT_LENGTH: int = 10000
    ALLOWED_IMAGE_FORMATS: List[str] = ["png", "jpg", "jpeg", "gif", "bmp"]
    
    # Monitoring settings
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9011
    
    @field_validator("PPT_OUTPUT_DIR")
    @classmethod
    def validate_output_dir(cls, v):
        """Ensure output directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("PPT_TEMPLATE_DIR")
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
