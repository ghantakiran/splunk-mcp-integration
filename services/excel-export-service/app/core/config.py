"""
Configuration settings for Excel Export Service.
"""

import os
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    DEBUG: bool = Field(default=False, env="DEBUG")
    API_PORT: int = Field(default=8010, env="API_PORT")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://excelservice:excelservice@localhost:5432/excelservice",
        env="DATABASE_URL"
    )
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # Authentication settings
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Excel generation settings
    EXCEL_OUTPUT_DIR: str = Field(
        default="/tmp/excel-exports",
        env="EXCEL_OUTPUT_DIR"
    )
    EXCEL_TEMPLATE_DIR: str = Field(
        default="app/templates",
        env="EXCEL_TEMPLATE_DIR"
    )
    EXCEL_MAX_FILE_SIZE_MB: int = Field(default=100, env="EXCEL_MAX_FILE_SIZE_MB")
    EXCEL_MAX_ROWS: int = Field(default=1000000, env="EXCEL_MAX_ROWS")
    EXCEL_MAX_COLUMNS: int = Field(default=16384, env="EXCEL_MAX_COLUMNS")
    EXCEL_TIMEOUT_SECONDS: int = Field(default=300, env="EXCEL_TIMEOUT_SECONDS")
    
    # Chart integration settings
    CHART_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        env="CHART_SERVICE_URL"
    )
    CHART_TIMEOUT_SECONDS: int = Field(default=30, env="CHART_TIMEOUT_SECONDS")
    CHART_MAX_WIDTH: int = Field(default=1200, env="CHART_MAX_WIDTH")
    CHART_MAX_HEIGHT: int = Field(default=800, env="CHART_MAX_HEIGHT")
    CHART_FORMAT: str = Field(default="png", env="CHART_FORMAT")
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # File cleanup settings
    CLEANUP_OLDER_THAN_DAYS: int = Field(default=7, env="CLEANUP_OLDER_THAN_DAYS")
    CLEANUP_INTERVAL_HOURS: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Performance settings
    MAX_CONCURRENT_JOBS: int = Field(default=10, env="MAX_CONCURRENT_JOBS")
    JOB_QUEUE_SIZE: int = Field(default=1000, env="JOB_QUEUE_SIZE")
    
    # Theme settings
    DEFAULT_THEME: str = Field(default="office", env="DEFAULT_THEME")
    AVAILABLE_THEMES: list = Field(
        default=["office", "modern", "colorful", "dark", "light"],
        env="AVAILABLE_THEMES"
    )
    
    # Data validation settings
    ENABLE_DATA_VALIDATION: bool = Field(default=True, env="ENABLE_DATA_VALIDATION")
    MAX_VALIDATION_RULES: int = Field(default=100, env="MAX_VALIDATION_RULES")
    
    # Formula settings
    ENABLE_FORMULAS: bool = Field(default=True, env="ENABLE_FORMULAS")
    SAFE_FORMULA_FUNCTIONS: list = Field(
        default=["SUM", "AVERAGE", "COUNT", "MAX", "MIN", "IF", "VLOOKUP", "HLOOKUP"],
        env="SAFE_FORMULA_FUNCTIONS"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure output directory exists
os.makedirs(settings.EXCEL_OUTPUT_DIR, exist_ok=True)