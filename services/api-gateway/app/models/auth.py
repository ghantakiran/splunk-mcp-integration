"""
Authentication data models and schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID


class UserLogin(BaseModel):
    """User login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(default=False, description="Remember login session")


class UserRegister(BaseModel):
    """User registration request model"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only letters, numbers, hyphens and underscores')
        return v.lower()


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    roles: List[str] = Field(default_factory=list, description="User roles")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class UserProfile(BaseModel):
    """User profile response model"""
    id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: dict = Field(default_factory=dict, description="User permissions")
    preferences: dict = Field(default_factory=dict, description="User preferences")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Total login count")
    timezone: str = Field(default="UTC", description="User timezone")
    language: str = Field(default="en", description="User language")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    expires_at: datetime = Field(..., description="Session expiration time")


class LoginResponse(BaseModel):
    """Login response model"""
    tokens: TokenResponse = Field(..., description="Authentication tokens")
    user: UserProfile = Field(..., description="User profile")
    session: SessionInfo = Field(..., description="Session information")
    message: str = Field(default="Login successful", description="Response message")


class LogoutResponse(BaseModel):
    """Logout response model"""
    message: str = Field(default="Logout successful", description="Response message")
    revoked_tokens: int = Field(default=0, description="Number of tokens revoked")


class AuthStatusResponse(BaseModel):
    """Authentication status response model"""
    authenticated: bool = Field(..., description="Authentication status")
    user: Optional[UserProfile] = Field(None, description="User profile if authenticated")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_expires_at: Optional[datetime] = Field(None, description="Session expiration")


class PasswordStrengthResponse(BaseModel):
    """Password strength validation response"""
    is_valid: bool = Field(..., description="Password validity")
    strength: str = Field(..., description="Password strength level")
    score: int = Field(..., description="Password strength score (0-5)")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class APIKeyRequest(BaseModel):
    """API key generation request model"""
    name: str = Field(..., max_length=100, description="API key name")
    description: Optional[str] = Field(None, max_length=500, description="API key description")
    expires_at: Optional[datetime] = Field(None, description="API key expiration")
    permissions: List[str] = Field(default_factory=list, description="API key permissions")


class APIKeyResponse(BaseModel):
    """API key response model"""
    id: UUID = Field(..., description="API key ID")
    key: str = Field(..., description="API key value (only returned once)")
    name: str = Field(..., description="API key name")
    description: Optional[str] = Field(None, description="API key description")
    permissions: List[str] = Field(default_factory=list, description="API key permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")


class TwoFactorSetupRequest(BaseModel):
    """Two-factor authentication setup request"""
    method: str = Field(..., description="2FA method (totp, sms, email)")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS")


class TwoFactorVerifyRequest(BaseModel):
    """Two-factor authentication verification request"""
    code: str = Field(..., min_length=6, max_length=8, description="2FA verification code")
    method: str = Field(..., description="2FA method used")


class DeviceInfo(BaseModel):
    """Device information for trusted devices"""
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(..., description="Device type (web, mobile, desktop)")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="IP address")
    location: Optional[str] = Field(None, description="Geographic location")
    trusted: bool = Field(default=False, description="Trusted device status")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")