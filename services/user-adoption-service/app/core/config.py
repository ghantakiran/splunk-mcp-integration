#!/usr/bin/env python3
"""
Configuration settings for User Adoption Service
===============================================
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    APP_NAME: str = "User Adoption and Feedback Collection Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8017"))
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:pass@localhost:5432/splunk_mcp"
    )
    DATABASE_ECHO: bool = ENVIRONMENT == "development"
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/8")
    REDIS_TTL: int = 3600  # 1 hour default TTL
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.yourdomain.com"
    ]
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # External service settings
    API_GATEWAY_URL: str = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    NLP_ENGINE_URL: str = os.getenv("NLP_ENGINE_URL", "http://localhost:8001")
    
    # Email settings for feedback notifications
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    
    # Slack settings for feedback notifications
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_FEEDBACK_CHANNEL: str = os.getenv("SLACK_FEEDBACK_CHANNEL", "#user-feedback")
    
    # Analytics and monitoring
    ENABLE_ANALYTICS: bool = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ANALYTICS_RETENTION_DAYS: int = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))
    
    # Feedback collection settings
    FEEDBACK_AUTO_SURVEY_INTERVAL: int = int(os.getenv("FEEDBACK_AUTO_SURVEY_INTERVAL", "14"))  # days
    FEEDBACK_MIN_SESSION_TIME: int = int(os.getenv("FEEDBACK_MIN_SESSION_TIME", "300"))  # seconds
    FEEDBACK_RESPONSE_RATE_TARGET: float = float(os.getenv("FEEDBACK_RESPONSE_RATE_TARGET", "0.25"))
    
    # Onboarding settings
    ONBOARDING_STEPS_TOTAL: int = 8
    ONBOARDING_COMPLETION_THRESHOLD: float = 0.8  # 80% completion
    ONBOARDING_TIMEOUT_DAYS: int = 30
    
    # Feature adoption tracking
    TRACK_FEATURE_USAGE: bool = True
    FEATURE_ADOPTION_WINDOW_DAYS: int = 7
    FEATURE_RETENTION_METRICS: bool = True
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a valid Redis URL")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()