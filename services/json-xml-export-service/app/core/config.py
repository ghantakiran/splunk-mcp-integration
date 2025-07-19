"""
Configuration settings for JSON/XML Export Service.
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = "JSON/XML Export Service"
    APP_VERSION: str = "1.0.0"
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8015, description="API port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost/json_xml_export",
        description="Database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow")
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL"
    )
    
    # JWT settings
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration in minutes"
    )
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        description="Rate limit requests per minute"
    )
    RATE_LIMIT_BURST_SIZE: int = Field(
        default=10,
        description="Rate limit burst size"
    )
    
    # Export settings
    MAX_CONCURRENT_JOBS: int = Field(
        default=10,
        description="Maximum concurrent export jobs"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=100,
        description="Maximum file size in MB"
    )
    DEFAULT_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Default timeout for export operations"
    )
    
    # File storage settings
    EXPORT_STORAGE_PATH: str = Field(
        default="/tmp/json-xml-exports",
        description="Path for storing export files"
    )
    FILE_RETENTION_HOURS: int = Field(
        default=24,
        description="File retention period in hours"
    )
    
    # JSON settings
    JSON_ENSURE_ASCII: bool = Field(
        default=False,
        description="Ensure ASCII in JSON output"
    )
    JSON_INDENT: Optional[int] = Field(
        default=2,
        description="JSON indentation (None for compact)"
    )
    JSON_SORT_KEYS: bool = Field(
        default=True,
        description="Sort keys in JSON output"
    )
    
    # XML settings
    XML_ENCODING: str = Field(
        default="utf-8",
        description="XML encoding"
    )
    XML_PRETTY_PRINT: bool = Field(
        default=True,
        description="Pretty print XML output"
    )
    XML_DECLARATION: bool = Field(
        default=True,
        description="Include XML declaration"
    )
    XML_ROOT_TAG: str = Field(
        default="root",
        description="Default XML root tag"
    )
    XML_ITEM_TAG: str = Field(
        default="item",
        description="Default XML item tag"
    )
    
    # Performance settings
    STREAMING_CHUNK_SIZE: int = Field(
        default=8192,
        description="Streaming chunk size"
    )
    COMPRESSION_ENABLED: bool = Field(
        default=True,
        description="Enable compression for large files"
    )
    
    # Monitoring settings
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    METRICS_PORT: int = Field(
        default=9015,
        description="Metrics endpoint port"
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json|text)"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure export directory exists
os.makedirs(settings.EXPORT_STORAGE_PATH, exist_ok=True)