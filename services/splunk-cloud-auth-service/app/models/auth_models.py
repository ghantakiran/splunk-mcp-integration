"""
Authentication models for Splunk Cloud Authentication Service
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
from sqlalchemy import String, Text, JSON, DateTime, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.core.database import Base


class AuthProviderType(str, Enum):
    """Authentication provider types"""
    OAUTH2 = "oauth2"
    SAML2 = "saml2"
    JWT = "jwt"
    BASIC = "basic"


class AuthFlowType(str, Enum):
    """OAuth 2.0 flow types"""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    DEVICE_CODE = "device_code"
    REFRESH_TOKEN = "refresh_token"


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    ID_TOKEN = "id_token"
    AUTHORIZATION = "authorization"


# SQLAlchemy Models
class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    # Override default ID to use UUID
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # User identification
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Authentication fields
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Multi-tenant support
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # OAuth/SAML fields
    provider_type: Mapped[Optional[AuthProviderType]] = mapped_column(
        SQLEnum(AuthProviderType),
        nullable=True
    )
    provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Security fields
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # User preferences
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class AuthSession(Base):
    """Authentication session model"""
    __tablename__ = "auth_sessions"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Session identification
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Session data
    access_token_jti: Mapped[Optional[str]] = mapped_column(String(255))
    refresh_token_jti: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Session timing
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Session state
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(255))


class OAuthClient(Base):
    """OAuth 2.0 client model"""
    __tablename__ = "oauth_clients"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Client identification
    client_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Multi-tenant support
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # OAuth configuration
    redirect_uris: Mapped[List[str]] = mapped_column(JSON)
    allowed_scopes: Mapped[List[str]] = mapped_column(JSON)
    allowed_grant_types: Mapped[List[str]] = mapped_column(JSON)
    
    # Client metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    logo_uri: Mapped[Optional[str]] = mapped_column(String(500))
    terms_of_service_uri: Mapped[Optional[str]] = mapped_column(String(500))
    privacy_policy_uri: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Security settings
    require_pkce: Mapped[bool] = mapped_column(Boolean, default=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True)
    token_endpoint_auth_method: Mapped[str] = mapped_column(
        String(50), 
        default="client_secret_basic"
    )


class AuthorizationCode(Base):
    """OAuth 2.0 authorization code model"""
    __tablename__ = "authorization_codes"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Authorization code data
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # OAuth parameters
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(String(500))
    state: Mapped[Optional[str]] = mapped_column(String(255))
    
    # PKCE support
    code_challenge: Mapped[Optional[str]] = mapped_column(String(255))
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Code lifecycle
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# Pydantic Models for API
class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    tenant_id: Optional[str] = None
    
    @validator("username")
    def validate_username(cls, v):
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("Username can only contain alphanumeric characters, underscores, hyphens, and dots")
        return v.lower()


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str
    tenant_id: Optional[str] = None


class UserResponse(BaseModel):
    """User response model"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_verified: bool
    is_superuser: bool
    tenant_id: Optional[str]
    provider_type: Optional[AuthProviderType]
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class OAuthClientCreate(BaseModel):
    """OAuth client creation model"""
    client_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    redirect_uris: List[str] = Field(..., min_items=1)
    allowed_scopes: List[str] = Field(default=["openid", "profile", "email"])
    allowed_grant_types: List[str] = Field(default=["authorization_code", "refresh_token"])
    tenant_id: Optional[str] = None
    require_pkce: bool = True
    is_confidential: bool = True


class OAuthClientResponse(BaseModel):
    """OAuth client response model"""
    id: str
    client_id: str
    client_name: str
    description: Optional[str]
    redirect_uris: List[str]
    allowed_scopes: List[str]
    allowed_grant_types: List[str]
    tenant_id: Optional[str]
    require_pkce: bool
    is_confidential: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """OAuth token response model"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class TokenIntrospectionResponse(BaseModel):
    """Token introspection response model"""
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    jti: Optional[str] = None


class AuthSessionResponse(BaseModel):
    """Authentication session response model"""
    session_id: str
    user_id: str
    tenant_id: Optional[str]
    ip_address: Optional[str]
    device_id: Optional[str]
    last_activity: datetime
    expires_at: datetime
    is_revoked: bool
    
    class Config:
        from_attributes = True