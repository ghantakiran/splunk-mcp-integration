"""
Configuration management for PDF Export Service.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, validator
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    APP_NAME: str = "PDF Export Service"
    APP_VERSION: str = "1.0.0"
    
    # API
    API_PORT: int = 8009
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://pdfservice:pdfservice@localhost:5432/pdfservice"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TIMEOUT: int = 5
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    # Authentication
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8009"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_LIMIT: int = 100
    RATE_LIMIT_DEFAULT_WINDOW: int = 3600
    RATE_LIMIT_BURST_LIMIT: int = 50
    
    # Metrics
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9009
    
    # PDF Generation
    PDF_OUTPUT_DIR: str = "/tmp/pdf-exports"
    PDF_TEMPLATE_DIR: str = "app/templates"
    PDF_MAX_FILE_SIZE_MB: int = 100
    PDF_MAX_PAGES: int = 1000
    PDF_TIMEOUT_SECONDS: int = 300
    PDF_DPI: int = 300
    PDF_QUALITY: str = "high"
    
    # Chart Integration
    CHART_SERVICE_URL: str = "http://localhost:8002"
    CHART_TIMEOUT_SECONDS: int = 30
    CHART_MAX_WIDTH: int = 1200
    CHART_MAX_HEIGHT: int = 800
    CHART_FORMAT: str = "png"
    
    # Template Engine
    TEMPLATE_ENGINE: str = "jinja2"
    TEMPLATE_CACHE_SIZE: int = 100
    TEMPLATE_CACHE_TTL: int = 3600
    
    # File Storage
    TEMP_DIR: str = "/tmp/pdf-export"
    MAX_FILE_SIZE_MB: int = 500
    CLEANUP_INTERVAL_HOURS: int = 24
    STORAGE_RETENTION_DAYS: int = 7
    
    # Security
    ENCRYPTION_KEY: str = "your-encryption-key-here"
    PASSWORD_MIN_LENGTH: int = 8
    SESSION_TIMEOUT: int = 3600
    MAX_CONCURRENT_GENERATIONS: int = 10
    
    # Background Jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/4"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/5"
    
    # Weasyprint Configuration
    WEASYPRINT_BASE_URL: str = "/"
    WEASYPRINT_PRESENTATIONAL_HINTS: bool = True
    WEASYPRINT_OPTIMIZE_IMAGES: bool = True
    
    # PDF Formats
    SUPPORTED_FORMATS: List[str] = ["pdf", "html", "png", "jpg"]
    DEFAULT_FORMAT: str = "pdf"
    
    # Template Types
    TEMPLATE_TYPES: Dict[str, str] = {
        "report": "Standard Report Template",
        "dashboard": "Dashboard Template",
        "chart": "Chart Template",
        "table": "Table Template",
        "custom": "Custom Template"
    }
    
    # Layout Options
    PAGE_SIZES: Dict[str, tuple] = {
        "a4": (210, 297),
        "letter": (216, 279),
        "legal": (216, 356),
        "a3": (297, 420),
        "tabloid": (279, 432)
    }
    
    PAGE_ORIENTATIONS: List[str] = ["portrait", "landscape"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("CORS_ALLOW_METHODS", pre=True)
    def assemble_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str) and v != "*":
            return [method.strip() for method in v.split(",")]
        return v
    
    @validator("CORS_ALLOW_HEADERS", pre=True)
    def assemble_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str) and v != "*":
            return [header.strip() for header in v.split(",")]
        return v
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key."""
        if v == "your-super-secret-jwt-key-here":
            return secrets.token_urlsafe(32)
        return v
    
    @validator("ENCRYPTION_KEY")
    def validate_encryption_key(cls, v):
        """Validate encryption key."""
        if v == "your-encryption-key-here":
            return secrets.token_urlsafe(32)
        return v
    
    @validator("PDF_OUTPUT_DIR", "TEMP_DIR")
    def validate_directories(cls, v):
        """Ensure directories exist."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @validator("PDF_DPI")
    def validate_dpi(cls, v):
        """Validate DPI range."""
        if v < 72 or v > 600:
            raise ValueError("DPI must be between 72 and 600")
        return v
    
    @validator("PDF_QUALITY")
    def validate_quality(cls, v):
        """Validate PDF quality."""
        valid_qualities = ["low", "medium", "high", "ultra"]
        if v not in valid_qualities:
            raise ValueError(f"Quality must be one of: {valid_qualities}")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()