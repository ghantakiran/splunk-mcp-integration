"""
Configuration management for Splunk Cloud Authentication Service
"""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = Field(default="splunk-cloud-auth-service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8017, env="PORT")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://cloud_auth_user:cloud_auth_password@localhost:5432/splunk_mcp_cloud_auth",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/7", env="REDIS_URL")
    
    # JWT Configuration
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # OAuth 2.0 Configuration
    oauth_client_id: Optional[str] = Field(default=None, env="OAUTH_CLIENT_ID")
    oauth_client_secret: Optional[str] = Field(default=None, env="OAUTH_CLIENT_SECRET")
    oauth_authorization_url: str = Field(
        default="https://auth.scp.splunk.com/oauth2/authorize",
        env="OAUTH_AUTHORIZATION_URL"
    )
    oauth_token_url: str = Field(
        default="https://auth.scp.splunk.com/oauth2/token",
        env="OAUTH_TOKEN_URL"
    )
    oauth_redirect_uri: str = Field(
        default="http://localhost:8017/api/v1/oauth/callback",
        env="OAUTH_REDIRECT_URI"
    )
    oauth_scope: str = Field(default="openid profile email", env="OAUTH_SCOPE")
    
    # SAML 2.0 Configuration
    saml_sp_entity_id: str = Field(
        default="https://splunk-mcp.company.com/saml/metadata",
        env="SAML_SP_ENTITY_ID"
    )
    saml_sp_acs_url: str = Field(
        default="https://splunk-mcp.company.com/api/v1/saml/acs",
        env="SAML_SP_ACS_URL"
    )
    saml_sp_sls_url: str = Field(
        default="https://splunk-mcp.company.com/api/v1/saml/sls",
        env="SAML_SP_SLS_URL"
    )
    saml_idp_metadata_url: Optional[str] = Field(default=None, env="SAML_IDP_METADATA_URL")
    saml_private_key_path: Optional[str] = Field(default=None, env="SAML_PRIVATE_KEY_PATH")
    saml_certificate_path: Optional[str] = Field(default=None, env="SAML_CERTIFICATE_PATH")
    
    # Splunk Cloud Configuration
    splunk_cloud_base_url: str = Field(
        default="https://{tenant}.splunkcloud.com",
        env="SPLUNK_CLOUD_BASE_URL"
    )
    splunk_cloud_api_version: str = Field(default="v1", env="SPLUNK_CLOUD_API_VERSION")
    splunk_cloud_timeout: int = Field(default=30, env="SPLUNK_CLOUD_TIMEOUT")
    
    # Encryption Configuration
    encryption_key: str = Field(default="your-encryption-key", env="ENCRYPTION_KEY")
    encryption_algorithm: str = Field(default="AES-256-GCM", env="ENCRYPTION_ALGORITHM")
    
    # Rate Limiting Configuration
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    
    # Multi-Tenant Configuration
    enable_multi_tenant: bool = Field(default=True, env="ENABLE_MULTI_TENANT")
    default_tenant_quota_users: int = Field(default=100, env="DEFAULT_TENANT_QUOTA_USERS")
    default_tenant_quota_requests_per_hour: int = Field(
        default=10000, 
        env="DEFAULT_TENANT_QUOTA_REQUESTS_PER_HOUR"
    )
    
    # Security Configuration
    password_min_length: int = Field(default=12, env="PASSWORD_MIN_LENGTH")
    password_require_special: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=30, env="LOCKOUT_DURATION_MINUTES")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9017, env="METRICS_PORT")
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()