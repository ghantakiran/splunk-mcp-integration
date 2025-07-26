"""
Token models for Splunk Cloud Authentication Service
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import String, Text, JSON, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base


class TokenStatus(str, Enum):
    """Token status enumeration"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class TokenScope(str, Enum):
    """Token scope enumeration"""
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    OFFLINE_ACCESS = "offline_access"
    SPLUNK_SEARCH = "splunk:search"
    SPLUNK_ADMIN = "splunk:admin"
    SPLUNK_READ = "splunk:read"
    SPLUNK_WRITE = "splunk:write"


# SQLAlchemy Models
class TokenBlacklist(Base):
    """Token blacklist for revoked tokens"""
    __tablename__ = "token_blacklist"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Token identification
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Token metadata
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Revocation details
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_by: Mapped[Optional[str]] = mapped_column(String(36))
    revocation_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Token expiration (for cleanup)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Additional context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)


class TokenUsageLog(Base):
    """Token usage logging for analytics and security"""
    __tablename__ = "token_usage_logs"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Token identification
    jti: Mapped[str] = mapped_column(String(255), nullable=False)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Usage context
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Request details
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    
    # Client information
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timing information
    request_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_time_ms: Mapped[Optional[int]] = mapped_column()
    
    # Geolocation (if available)
    country: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Additional metadata
    scope: Mapped[Optional[str]] = mapped_column(String(500))
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class RefreshTokenFamily(Base):
    """Refresh token family for token rotation tracking"""
    __tablename__ = "refresh_token_families"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Family identification
    family_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    # User and client context
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Current token
    current_jti: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Family lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_rotated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_count: Mapped[int] = mapped_column(default=0)
    
    # Family status
    is_compromised: Mapped[bool] = mapped_column(Boolean, default=False)
    compromised_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    compromised_reason: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Security context
    initial_ip: Mapped[Optional[str]] = mapped_column(String(45))
    last_ip: Mapped[Optional[str]] = mapped_column(String(45))
    allowed_ips: Mapped[Optional[list]] = mapped_column(JSON)


# Pydantic Models for API
class TokenInfo(BaseModel):
    """Token information model"""
    jti: str
    token_type: str
    user_id: str
    client_id: str
    tenant_id: Optional[str] = None
    scope: Optional[str] = None
    expires_at: datetime
    issued_at: datetime
    
    class Config:
        from_attributes = True


class TokenRevocationRequest(BaseModel):
    """Token revocation request model"""
    token: str = Field(..., min_length=1)
    token_type_hint: Optional[str] = Field(None, regex="^(access_token|refresh_token)$")
    revocation_reason: str = Field(default="user_requested")


class TokenUsageStats(BaseModel):
    """Token usage statistics model"""
    token_count: int
    active_tokens: int
    revoked_tokens: int
    expired_tokens: int
    usage_last_24h: int
    unique_clients: int
    unique_users: int
    average_session_duration_minutes: Optional[float] = None


class TokenAnalytics(BaseModel):
    """Token analytics model"""
    period_start: datetime
    period_end: datetime
    total_requests: int
    unique_tokens: int
    top_endpoints: list[Dict[str, Any]]
    client_distribution: Dict[str, int]
    geographic_distribution: Dict[str, int]
    error_rate: float
    average_response_time_ms: float


class RefreshTokenRotationResponse(BaseModel):
    """Refresh token rotation response"""
    new_access_token: str
    new_refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    rotation_count: int
    family_id: str


class TokenSecurityEvent(BaseModel):
    """Token security event model"""
    event_type: str = Field(..., regex="^(suspicious_usage|token_reuse|geographic_anomaly|rate_limit_exceeded)$")
    token_jti: str
    user_id: str
    client_id: str
    tenant_id: Optional[str] = None
    description: str
    severity: str = Field(..., regex="^(low|medium|high|critical)$")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class TokenValidationResult(BaseModel):
    """Token validation result model"""
    is_valid: bool
    token_info: Optional[TokenInfo] = None
    validation_errors: list[str] = Field(default_factory=list)
    security_warnings: list[str] = Field(default_factory=list)
    requires_rotation: bool = False
    
    class Config:
        from_attributes = True