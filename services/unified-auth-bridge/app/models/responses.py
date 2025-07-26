"""
Standard response models for Unified Authentication Bridge API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response format"""
    success: bool = Field(..., description="Request success status")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class SuccessResponse(StandardResponse[T]):
    """Success response format"""
    success: bool = Field(True, description="Success status")


class ErrorResponse(StandardResponse[None]):
    """Error response format"""
    success: bool = Field(False, description="Error status")
    data: None = Field(None, description="No data for error responses")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Dependent service statuses")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class APIVersionResponse(BaseModel):
    """API version information response"""
    version: str = Field(..., description="Current service version")
    api_version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment")
    build_timestamp: datetime = Field(..., description="Build timestamp")
    supported_versions: List[str] = Field(default_factory=list, description="Supported API versions")
    deprecated_versions: List[str] = Field(default_factory=list, description="Deprecated API versions")
    sunset_versions: List[str] = Field(default_factory=list, description="Sunset API versions")