"""
Configuration settings for Slack Bot service.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    app_name: str = "Splunk MCP Slack Bot"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    port: int = Field(default=8004, env="SLACK_BOT_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Slack settings
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    slack_app_token: Optional[str] = Field(None, env="SLACK_APP_TOKEN")
    
    # API Gateway settings
    api_gateway_url: str = Field(default="http://localhost:8000", env="API_GATEWAY_URL")
    api_gateway_timeout: int = Field(default=30, env="API_GATEWAY_TIMEOUT")
    
    # NLP Engine settings
    nlp_engine_url: str = Field(default="http://localhost:8001", env="NLP_ENGINE_URL")
    nlp_engine_timeout: int = Field(default=60, env="NLP_ENGINE_TIMEOUT")
    
    # Visualization service settings
    visualization_url: str = Field(default="http://localhost:8002", env="VISUALIZATION_URL")
    visualization_timeout: int = Field(default=45, env="VISUALIZATION_TIMEOUT")
    
    # Alert Manager settings
    alert_manager_url: str = Field(default="http://localhost:8003", env="ALERT_MANAGER_URL")
    alert_manager_timeout: int = Field(default=30, env="ALERT_MANAGER_TIMEOUT")
    
    # Database settings
    database_url: str = Field(default="postgresql://user:pass@localhost/slack_bot", env="DATABASE_URL")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/3", env="REDIS_URL")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    
    # Security settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Slack bot settings
    max_message_length: int = Field(default=3000, env="MAX_MESSAGE_LENGTH")
    max_query_results: int = Field(default=50, env="MAX_QUERY_RESULTS")
    enable_direct_messages: bool = Field(default=True, env="ENABLE_DIRECT_MESSAGES")
    enable_channel_mentions: bool = Field(default=True, env="ENABLE_CHANNEL_MENTIONS")
    enable_slash_commands: bool = Field(default=True, env="ENABLE_SLASH_COMMANDS")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9004, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()