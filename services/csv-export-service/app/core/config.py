#!/usr/bin/env python3
"""
Configuration settings for CSV Export Service.

This module contains all configuration settings for the CSV export service,
including database settings, API settings, CSV generation settings, and more.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    DEBUG: bool = False
    API_PORT: int = 8014
    API_HOST: str = "0.0.0.0"
    
    # Database settings
    DATABASE_URL: str = "postgresql://csvservice:csvservice@localhost:5432/csvservice"
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
    
    # CSV generation settings
    CSV_OUTPUT_DIR: str = "/tmp/csv-exports"
    CSV_TEMPLATE_DIR: str = "app/templates"
    CSV_MAX_FILE_SIZE_MB: int = 500
    CSV_TIMEOUT_SECONDS: int = 300
    CSV_CONCURRENT_JOBS: int = 10
    
    # CSV format settings
    CSV_DEFAULT_ENCODING: str = "utf-8"
    CSV_DEFAULT_DELIMITER: str = ","
    CSV_DEFAULT_QUOTE_CHAR: str = "\""
    CSV_DEFAULT_ESCAPE_CHAR: str = "\\"
    CSV_DEFAULT_LINE_TERMINATOR: str = "\n"
    CSV_MAX_ROWS_PER_FILE: int = 1000000
    CSV_MAX_COLUMNS: int = 1000
    
    # Data processing settings
    ENABLE_DATA_VALIDATION: bool = True
    ENABLE_DATA_TRANSFORMATION: bool = True
    ENABLE_LARGE_FILE_STREAMING: bool = True
    ENABLE_COMPRESSION: bool = True
    
    # Supported encodings
    SUPPORTED_ENCODINGS: List[str] = [
        "utf-8", "utf-16", "utf-16-le", "utf-16-be", 
        "utf-32", "latin-1", "ascii", "cp1252", "iso-8859-1"
    ]
    
    # Supported delimiters
    SUPPORTED_DELIMITERS: List[str] = [",", ";", "\t", "|", ":", "^", "~"]
    
    # Export formats
    EXPORT_FORMATS: List[str] = ["csv", "tsv", "pipe", "custom"]
    DEFAULT_EXPORT_FORMAT: str = "csv"
    
    # Performance settings
    MAX_CONCURRENT_JOBS: int = 15
    JOB_QUEUE_SIZE: int = 1000
    WORKER_TIMEOUT: int = 300
    CHUNK_SIZE: int = 10000
    MEMORY_LIMIT_MB: int = 1000
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    
    # File cleanup settings
    CLEANUP_OLDER_THAN_DAYS: int = 7
    CLEANUP_INTERVAL_HOURS: int = 24
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Compression settings
    ENABLE_GZIP_COMPRESSION: bool = True
    ENABLE_ZIP_COMPRESSION: bool = True
    COMPRESSION_LEVEL: int = 6
    
    # Security settings
    ENABLE_CONTENT_FILTERING: bool = True
    MAX_FIELD_LENGTH: int = 32768
    ALLOWED_DOMAINS: List[str] = []
    
    # Data validation settings
    VALIDATE_ENCODING: bool = True
    VALIDATE_FIELD_TYPES: bool = True
    VALIDATE_FIELD_LENGTHS: bool = True
    HANDLE_NULL_VALUES: bool = True
    NULL_VALUE_REPLACEMENT: str = ""
    
    # Advanced features
    ENABLE_CUSTOM_FORMATTERS: bool = True
    ENABLE_DATA_FILTERS: bool = True
    ENABLE_COLUMN_MAPPING: bool = True
    ENABLE_BATCH_PROCESSING: bool = True
    
    # Monitoring settings
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9014
    
    @field_validator("CSV_OUTPUT_DIR")
    @classmethod
    def validate_output_dir(cls, v):
        """Ensure output directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("CSV_TEMPLATE_DIR")
    @classmethod
    def validate_template_dir(cls, v):
        """Ensure template directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("CSV_DEFAULT_ENCODING")
    @classmethod
    def validate_encoding(cls, v):
        """Validate default encoding is supported."""
        try:
            "test".encode(v)
            return v
        except (LookupError, ValueError):
            raise ValueError(f"Unsupported encoding: {v}")
    
    @field_validator("CSV_MAX_ROWS_PER_FILE")
    @classmethod
    def validate_max_rows(cls, v):
        """Validate maximum rows per file."""
        if v <= 0:
            raise ValueError("Maximum rows per file must be positive")
        if v > 10000000:  # 10 million rows
            raise ValueError("Maximum rows per file too large")
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