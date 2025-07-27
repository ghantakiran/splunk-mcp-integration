# Base response models used across services
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ResponseMetadata(BaseModel):
    """Standard metadata for all API responses."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    version: str = "1.0"


class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""
    success: bool
    data: Optional[Any] = None
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginationResponse(BaseModel):
    """Standard pagination response."""
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool