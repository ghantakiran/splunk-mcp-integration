"""
Configuration settings for Microsoft Teams Bot service.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    app_name: str = "Splunk MCP Teams Bot"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    port: int = Field(default=8005, env="TEAMS_BOT_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Microsoft Teams Bot Framework settings
    microsoft_app_id: str = Field(..., env="MICROSOFT_APP_ID")
    microsoft_app_password: str = Field(..., env="MICROSOFT_APP_PASSWORD")
    microsoft_app_tenant_id: Optional[str] = Field(None, env="MICROSOFT_APP_TENANT_ID")
    
    # Bot Framework settings
    bot_framework_url: str = Field(default="https://smba.trafficmanager.net/teams/", env="BOT_FRAMEWORK_URL")
    bot_framework_timeout: int = Field(default=30, env="BOT_FRAMEWORK_TIMEOUT")
    
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
    database_url: str = Field(default="postgresql://user:pass@localhost/teams_bot", env="DATABASE_URL")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/4", env="REDIS_URL")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    
    # Security settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Teams bot settings
    max_message_length: int = Field(default=28000, env="MAX_MESSAGE_LENGTH")  # Teams limit
    max_query_results: int = Field(default=50, env="MAX_QUERY_RESULTS")
    enable_proactive_messages: bool = Field(default=True, env="ENABLE_PROACTIVE_MESSAGES")
    enable_adaptive_cards: bool = Field(default=True, env="ENABLE_ADAPTIVE_CARDS")
    enable_task_modules: bool = Field(default=True, env="ENABLE_TASK_MODULES")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Teams-specific features
    enable_mentions: bool = Field(default=True, env="ENABLE_MENTIONS")
    enable_channel_messages: bool = Field(default=True, env="ENABLE_CHANNEL_MESSAGES")
    enable_personal_chat: bool = Field(default=True, env="ENABLE_PERSONAL_CHAT")
    enable_group_chat: bool = Field(default=True, env="ENABLE_GROUP_CHAT")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9005, env="METRICS_PORT")
    
    # Activity types to handle
    supported_activity_types: List[str] = Field(
        default=["message", "invoke", "memberAdded", "installationUpdate"],
        env="SUPPORTED_ACTIVITY_TYPES"
    )
    
    # Teams app manifest settings
    teams_app_name: str = Field(default="Splunk MCP Assistant", env="TEAMS_APP_NAME")
    teams_app_description: str = Field(
        default="Natural language interface for Splunk data queries and analysis",
        env="TEAMS_APP_DESCRIPTION"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()