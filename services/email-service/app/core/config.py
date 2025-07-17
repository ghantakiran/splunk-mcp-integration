"""
Configuration management for Email Service.
"""

import os
from typing import List, Optional, Any, Dict
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Email service configuration settings."""
    
    # Application settings
    app_name: str = "Splunk MCP Email Service"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8006, env="PORT")
    
    # Email server configuration
    smtp_host: str = Field(..., env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(..., env="SMTP_USERNAME")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, env="SMTP_USE_SSL")
    smtp_timeout: int = Field(default=30, env="SMTP_TIMEOUT")
    
    # Email settings
    from_email: str = Field(..., env="FROM_EMAIL")
    from_name: str = Field(default="Splunk MCP Assistant", env="FROM_NAME")
    reply_to_email: Optional[str] = Field(default=None, env="REPLY_TO_EMAIL")
    max_attachment_size: int = Field(default=25 * 1024 * 1024, env="MAX_ATTACHMENT_SIZE")  # 25MB
    allowed_attachment_types: List[str] = Field(
        default=["pdf", "xlsx", "csv", "png", "jpg", "html"],
        env="ALLOWED_ATTACHMENT_TYPES"
    )
    
    # IMAP configuration for email processing
    imap_host: Optional[str] = Field(default=None, env="IMAP_HOST")
    imap_port: int = Field(default=993, env="IMAP_PORT")
    imap_username: Optional[str] = Field(default=None, env="IMAP_USERNAME")
    imap_password: Optional[str] = Field(default=None, env="IMAP_PASSWORD")
    imap_use_ssl: bool = Field(default=True, env="IMAP_USE_SSL")
    imap_folder: str = Field(default="INBOX", env="IMAP_FOLDER")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis configuration
    redis_url: str = Field(..., env="REDIS_URL")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    
    # Service URLs
    api_gateway_url: str = Field(..., env="API_GATEWAY_URL")
    nlp_engine_url: str = Field(..., env="NLP_ENGINE_URL")
    visualization_url: str = Field(..., env="VISUALIZATION_URL")
    alert_manager_url: str = Field(..., env="ALERT_MANAGER_URL")
    
    # Service timeouts
    api_timeout: int = Field(default=30, env="API_TIMEOUT")
    nlp_timeout: int = Field(default=60, env="NLP_TIMEOUT")
    visualization_timeout: int = Field(default=45, env="VISUALIZATION_TIMEOUT")
    alert_timeout: int = Field(default=30, env="ALERT_TIMEOUT")
    
    # Security settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Email processing settings
    max_email_size: int = Field(default=50 * 1024 * 1024, env="MAX_EMAIL_SIZE")  # 50MB
    max_query_length: int = Field(default=10000, env="MAX_QUERY_LENGTH")
    max_results_per_email: int = Field(default=1000, env="MAX_RESULTS_PER_EMAIL")
    email_check_interval: int = Field(default=60, env="EMAIL_CHECK_INTERVAL")  # seconds
    
    # Template settings
    template_directory: str = Field(default="app/templates", env="TEMPLATE_DIRECTORY")
    default_template: str = Field(default="default.html", env="DEFAULT_TEMPLATE")
    
    # Report settings
    report_timeout: int = Field(default=300, env="REPORT_TIMEOUT")  # 5 minutes
    max_report_size: int = Field(default=100 * 1024 * 1024, env="MAX_REPORT_SIZE")  # 100MB
    supported_formats: List[str] = Field(
        default=["html", "pdf", "csv", "xlsx"],
        env="SUPPORTED_FORMATS"
    )
    
    # Rate limiting
    rate_limit_per_user: int = Field(default=100, env="RATE_LIMIT_PER_USER")  # per hour
    rate_limit_per_domain: int = Field(default=500, env="RATE_LIMIT_PER_DOMAIN")  # per hour
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9006, env="METRICS_PORT")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Feature flags
    enable_imap_processing: bool = Field(default=False, env="ENABLE_IMAP_PROCESSING")
    enable_attachments: bool = Field(default=True, env="ENABLE_ATTACHMENTS")
    enable_html_emails: bool = Field(default=True, env="ENABLE_HTML_EMAILS")
    enable_email_threading: bool = Field(default=True, env="ENABLE_EMAIL_THREADING")
    enable_auto_responses: bool = Field(default=True, env="ENABLE_AUTO_RESPONSES")
    
    # Security whitelist/blacklist
    allowed_domains: Optional[List[str]] = Field(default=None, env="ALLOWED_DOMAINS")
    blocked_domains: Optional[List[str]] = Field(default=None, env="BLOCKED_DOMAINS")
    allowed_users: Optional[List[str]] = Field(default=None, env="ALLOWED_USERS")
    blocked_users: Optional[List[str]] = Field(default=None, env="BLOCKED_USERS")
    
    @validator("allowed_attachment_types", pre=True)
    def parse_attachment_types(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",")]
        return v
    
    @validator("supported_formats", pre=True)
    def parse_supported_formats(cls, v):
        if isinstance(v, str):
            return [f.strip() for f in v.split(",")]
        return v
    
    @validator("allowed_domains", pre=True)
    def parse_allowed_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    @validator("blocked_domains", pre=True)
    def parse_blocked_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_config() -> Dict[str, Any]:
    """Get database configuration for SQLAlchemy."""
    return {
        "url": settings.database_url,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "echo": settings.debug,
    }


def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration."""
    return {
        "url": settings.redis_url,
        "timeout": settings.redis_timeout,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    }


def get_smtp_config() -> Dict[str, Any]:
    """Get SMTP configuration for email sending."""
    return {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_username,
        "password": settings.smtp_password,
        "use_tls": settings.smtp_use_tls,
        "use_ssl": settings.smtp_use_ssl,
        "timeout": settings.smtp_timeout,
    }


def get_imap_config() -> Optional[Dict[str, Any]]:
    """Get IMAP configuration for email processing."""
    if not settings.imap_host:
        return None
    
    return {
        "hostname": settings.imap_host,
        "port": settings.imap_port,
        "username": settings.imap_username,
        "password": settings.imap_password,
        "use_ssl": settings.imap_use_ssl,
        "folder": settings.imap_folder,
    }