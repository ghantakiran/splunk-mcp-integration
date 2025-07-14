"""
Configuration management for NLP Engine service
"""

import os
from typing import List, Optional, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = Field(default="splunk-mcp-nlp-engine", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    openapi_url: str = Field(default="/api/v1/openapi.json", env="OPENAPI_URL")
    
    # AI/ML Service Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4096, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    openai_timeout: int = Field(default=30, env="OPENAI_TIMEOUT")
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=4096, env="ANTHROPIC_MAX_TOKENS")
    anthropic_temperature: float = Field(default=0.1, env="ANTHROPIC_TEMPERATURE")
    
    # NLP Configuration
    default_ai_provider: str = Field(default="openai", env="DEFAULT_AI_PROVIDER")
    enable_context_memory: bool = Field(default=True, env="ENABLE_CONTEXT_MEMORY")
    max_context_length: int = Field(default=8192, env="MAX_CONTEXT_LENGTH")
    conversation_timeout: int = Field(default=1800, env="CONVERSATION_TIMEOUT")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://nlp_user:nlp_password@localhost:5432/splunk_mcp_nlp",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/2", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=2, env="REDIS_DB")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    # Security Configuration
    secret_key: str = Field(env="SECRET_KEY")
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # CORS Configuration
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Monitoring and Logging
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")
    log_json_format: bool = Field(default=True, env="LOG_JSON_FORMAT")
    
    # Rate Limiting
    rate_limiting_enabled: bool = Field(default=True, env="RATE_LIMITING_ENABLED")
    default_rate_limit: int = Field(default=100, env="DEFAULT_RATE_LIMIT")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    # Splunk Integration
    splunk_api_base_url: Optional[str] = Field(default=None, env="SPLUNK_API_BASE_URL")
    splunk_api_token: Optional[str] = Field(default=None, env="SPLUNK_API_TOKEN")
    splunk_verify_ssl: bool = Field(default=True, env="SPLUNK_VERIFY_SSL")
    splunk_timeout: int = Field(default=30, env="SPLUNK_TIMEOUT")
    
    # Performance Configuration
    worker_processes: int = Field(default=1, env="WORKER_PROCESSES")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=120, env="REQUEST_TIMEOUT")
    enable_async_processing: bool = Field(default=True, env="ENABLE_ASYNC_PROCESSING")
    
    # Development Settings
    reload_on_change: bool = Field(default=True, env="RELOAD_ON_CHANGE")
    enable_debug_endpoints: bool = Field(default=True, env="ENABLE_DEBUG_ENDPOINTS")
    mock_ai_responses: bool = Field(default=False, env="MOCK_AI_RESPONSES")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith("[") and v.endswith("]"):
                # Handle JSON-like string
                return eval(v)
            else:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("default_ai_provider")
    def validate_ai_provider(cls, v):
        """Validate AI provider choice"""
        valid_providers = ["openai", "anthropic"]
        if v not in valid_providers:
            raise ValueError(f"AI provider must be one of: {valid_providers}")
        return v
    
    @validator("openai_temperature", "anthropic_temperature")
    def validate_temperature(cls, v):
        """Validate temperature range"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic"""
        return self.database_url.replace("+asyncpg", "")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings