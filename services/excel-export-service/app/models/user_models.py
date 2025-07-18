"""
User models for Excel Export Service.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model."""
    id: int = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(default=None, description="Full name")
    is_active: bool = Field(default=True, description="Is active")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")


class UserCreate(BaseModel):
    """User creation model."""
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(default=None, description="Full name")
    password: str = Field(description="User password")


class UserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = Field(default=None, description="Full name")
    is_active: Optional[bool] = Field(default=None, description="Is active")
    permissions: Optional[Dict[str, Any]] = Field(default=None, description="User permissions")


class UserResponse(BaseModel):
    """User response model."""
    id: int = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(description="Full name")
    is_active: bool = Field(description="Is active")
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")