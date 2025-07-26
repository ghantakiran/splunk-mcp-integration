"""
Authentication models for unified auth bridge
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider types"""
    CLOUD = "cloud"
    ENTERPRISE = "enterprise"
    NONE = "none"


class AuthMode(str, Enum):
    """Authentication modes"""
    HYBRID = "hybrid"
    ENTERPRISE_ONLY = "enterprise_only"
    CLOUD_ONLY = "cloud_only"


class AuthResult(str, Enum):
    """Authentication result types"""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class AuthRequest(BaseModel):
    """Authentication request model"""
    username: str = Field(..., min_length=1, max_length=255, description="Username")
    password: str = Field(..., min_length=1, max_length=255, description="Password")
    tenant_id: Optional[str] = Field(None, max_length=100, description="Cloud tenant ID")
    client_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Client information")
    preferred_provider: Optional[AuthProvider] = Field(None, description="Preferred authentication provider")
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username format"""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "username": "john.doe",
                "password": "secure_password123",
                "tenant_id": "acme-corp",
                "client_info": {
                    "user_agent": "Mozilla/5.0...",
                    "ip_address": "192.168.1.100"
                },
                "preferred_provider": "cloud"
            }
        }


class UserProfile(BaseModel):
    """User profile from authentication provider"""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    tenant_id: Optional[str] = Field(None, description="Cloud tenant ID")
    provider: AuthProvider = Field(..., description="Authentication provider")
    accessible_indexes: List[str] = Field(default_factory=list, description="Accessible Splunk indexes")
    profile_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional profile data")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "john.doe@acme.com",
                "username": "john.doe",
                "email": "john.doe@acme.com",
                "full_name": "John Doe",
                "roles": ["analyst", "user"],
                "permissions": {
                    "search": True,
                    "create_alerts": True,
                    "admin": False
                },
                "tenant_id": "acme-corp",
                "provider": "cloud",
                "accessible_indexes": ["main", "security", "web"]
            }
        }


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool = Field(..., description="Authentication success status")
    provider: AuthProvider = Field(..., description="Authentication provider used")
    user_profile: Optional[UserProfile] = Field(None, description="User profile information")
    token: Optional[str] = Field(None, description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    error_message: Optional[str] = Field(None, description="Error message if authentication failed")
    provider_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "provider": "cloud",
                "user_profile": {
                    "user_id": "john.doe@acme.com",
                    "username": "john.doe",
                    "email": "john.doe@acme.com",
                    "full_name": "John Doe",
                    "roles": ["analyst"],
                    "tenant_id": "acme-corp",
                    "provider": "cloud"
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-01-24T12:00:00Z"
            }
        }


class TokenValidationRequest(BaseModel):
    """Token validation request"""
    token: str = Field(..., min_length=1, description="Token to validate")
    provider: Optional[AuthProvider] = Field(None, description="Expected provider")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "provider": "cloud"
            }
        }


class TokenValidationResponse(BaseModel):
    """Token validation response"""
    valid: bool = Field(..., description="Token validity status")
    user_profile: Optional[UserProfile] = Field(None, description="User profile if valid")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    
    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "user_profile": {
                    "user_id": "john.doe@acme.com",
                    "username": "john.doe",
                    "provider": "cloud"
                },
                "expires_at": "2025-01-24T12:00:00Z"
            }
        }


class LogoutRequest(BaseModel):
    """Logout request"""
    token: str = Field(..., min_length=1, description="Token to logout")
    provider: Optional[AuthProvider] = Field(None, description="Provider to logout from")
    logout_all: bool = Field(default=False, description="Logout from all providers")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "provider": "cloud",
                "logout_all": False
            }
        }


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool = Field(..., description="Logout success status")
    providers_logged_out: List[AuthProvider] = Field(default_factory=list, description="Providers logged out from")
    error_message: Optional[str] = Field(None, description="Error message if logout failed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "providers_logged_out": ["cloud"],
                "error_message": None
            }
        }


class ProviderStatus(BaseModel):
    """Authentication provider status"""
    type: AuthProvider = Field(..., description="Provider type")
    name: str = Field(..., description="Provider name")
    url: str = Field(..., description="Provider URL")
    priority: int = Field(..., description="Provider priority")
    status: str = Field(..., description="Provider status")
    health: Optional[str] = Field(None, description="Health status")
    last_check: Optional[datetime] = Field(None, description="Last health check time")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "cloud",
                "name": "Splunk Cloud",
                "url": "http://cloud-auth-service:8017",
                "priority": 1,
                "status": "active",
                "health": "healthy",
                "last_check": "2025-01-24T10:30:00Z"
            }
        }


class AuthBridgeStatus(BaseModel):
    """Authentication bridge status"""
    mode: AuthMode = Field(..., description="Authentication mode")
    priority_order: List[str] = Field(..., description="Provider priority order")
    fallback_enabled: bool = Field(..., description="Fallback authentication enabled")
    cache_ttl: int = Field(..., description="Authentication cache TTL in seconds")
    providers: Dict[str, ProviderStatus] = Field(..., description="Provider statuses")
    health_summary: Optional[Dict[str, str]] = Field(None, description="Overall health summary")
    
    class Config:
        schema_extra = {
            "example": {
                "mode": "hybrid",
                "priority_order": ["cloud", "enterprise"],
                "fallback_enabled": True,
                "cache_ttl": 300,
                "providers": {
                    "cloud": {
                        "type": "cloud",
                        "name": "Splunk Cloud",
                        "status": "active",
                        "health": "healthy"
                    },
                    "enterprise": {
                        "type": "enterprise",
                        "name": "Splunk Enterprise",
                        "status": "active",
                        "health": "healthy"
                    }
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., min_length=1, description="Refresh token")
    provider: Optional[AuthProvider] = Field(None, description="Provider to refresh with")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "provider": "cloud"
            }
        }


class RefreshTokenResponse(BaseModel):
    """Refresh token response"""
    success: bool = Field(..., description="Refresh success status")
    token: Optional[str] = Field(None, description="New access token")
    refresh_token: Optional[str] = Field(None, description="New refresh token")
    expires_at: Optional[datetime] = Field(None, description="New token expiration time")
    provider: Optional[AuthProvider] = Field(None, description="Provider used for refresh")
    error_message: Optional[str] = Field(None, description="Error message if refresh failed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-01-24T12:00:00Z",
                "provider": "cloud"
            }
        }


class AuthMetrics(BaseModel):
    """Authentication metrics"""
    total_attempts: int = Field(default=0, description="Total authentication attempts")
    successful_attempts: int = Field(default=0, description="Successful authentication attempts")
    failed_attempts: int = Field(default=0, description="Failed authentication attempts")
    provider_breakdown: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Provider-specific metrics")
    cache_hits: int = Field(default=0, description="Authentication cache hits")
    cache_misses: int = Field(default=0, description="Authentication cache misses")
    average_response_time_ms: float = Field(default=0.0, description="Average response time in milliseconds")
    period: str = Field(..., description="Metrics time period")
    
    class Config:
        schema_extra = {
            "example": {
                "total_attempts": 1000,
                "successful_attempts": 950,
                "failed_attempts": 50,
                "provider_breakdown": {
                    "cloud": {"success": 800, "failure": 20},
                    "enterprise": {"success": 150, "failure": 30}
                },
                "cache_hits": 500,
                "cache_misses": 500,
                "average_response_time_ms": 250.5,
                "period": "last_24_hours"
            }
        }