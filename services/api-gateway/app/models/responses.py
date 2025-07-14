"""
Standard API response models for documentation and consistency
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar, Union
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Error detail model"""
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: ErrorDetail = Field(..., description="Error information")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "message": "Resource not found",
                    "code": "not_found_error",
                    "details": {
                        "resource_id": "123e4567-e89b-12d3-a456-426614174000"
                    }
                }
            }
        }


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response model"""
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Success message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1, le=100)
    total_items: int = Field(..., description="Total number of items", ge=0)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    data: List[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2025-07-13T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "redis": "healthy",
                    "nlp_engine": "healthy"
                },
                "uptime_seconds": 3600.5
            }
        }


class APIVersionResponse(BaseModel):
    """API version information response"""
    current_version: str = Field(..., description="Current API version")
    supported_versions: List[str] = Field(..., description="List of supported API versions")
    prefix: str = Field(..., description="API URL prefix")
    deprecation_policy: str = Field(..., description="Version deprecation policy")
    migration_guide: str = Field(..., description="URL to migration guide")
    
    class Config:
        schema_extra = {
            "example": {
                "current_version": "1.0.0",
                "supported_versions": ["1.0.0"],
                "prefix": "/api/v1",
                "deprecation_policy": "Versions are supported for 12 months after replacement",
                "migration_guide": "https://github.com/ghantakiran/splunk-mcp-integration/blob/main/docs/api/migration.md"
            }
        }


class RateLimitInfo(BaseModel):
    """Rate limit information"""
    limit: int = Field(..., description="Rate limit per time window")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset: datetime = Field(..., description="When the rate limit window resets")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response"""
    error: ErrorDetail = Field(..., description="Rate limit error")
    rate_limit: RateLimitInfo = Field(..., description="Rate limit information")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "message": "Rate limit exceeded",
                    "code": "rate_limit_error"
                },
                "rate_limit": {
                    "limit": 100,
                    "remaining": 0,
                    "reset": "2025-07-13T11:00:00Z",
                    "retry_after": 60
                }
            }
        }


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: ErrorDetail = Field(..., description="Validation error information")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "message": "Request validation failed",
                    "code": "validation_error",
                    "details": {
                        "errors": [
                            {
                                "loc": ["body", "email"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            },
                            {
                                "loc": ["body", "password"],
                                "msg": "ensure this value has at least 8 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }


class StatusResponse(BaseModel):
    """Generic status response"""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Status timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "timestamp": "2025-07-13T10:30:00Z"
            }
        }


class BulkOperationResponse(BaseModel):
    """Bulk operation response model"""
    total: int = Field(..., description="Total number of items processed")
    successful: int = Field(..., description="Number of successfully processed items")
    failed: int = Field(..., description="Number of failed items")
    errors: List[ErrorDetail] = Field(default_factory=list, description="List of errors for failed items")
    message: str = Field(..., description="Overall operation status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "successful": 95,
                "failed": 5,
                "errors": [
                    {
                        "message": "Invalid email format",
                        "code": "validation_error",
                        "details": {"item_id": "item_001"}
                    }
                ],
                "message": "Bulk operation completed with some failures",
                "timestamp": "2025-07-13T10:30:00Z"
            }
        }


class FileUploadResponse(BaseModel):
    """File upload response model"""
    file_id: UUID = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    upload_url: Optional[str] = Field(None, description="URL to access the uploaded file")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Upload status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "data.csv",
                "file_size": 1024000,
                "content_type": "text/csv",
                "upload_url": "/api/v1/files/123e4567-e89b-12d3-a456-426614174000",
                "status": "success",
                "message": "File uploaded successfully",
                "timestamp": "2025-07-13T10:30:00Z"
            }
        }


class SearchResponse(BaseModel, Generic[T]):
    """Search results response model"""
    results: List[T] = Field(..., description="Search results")
    query: str = Field(..., description="Search query used")
    total_results: int = Field(..., description="Total number of matching results")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    facets: Optional[Dict[str, List[Dict[str, Any]]]] = Field(None, description="Search facets")
    suggestions: Optional[List[str]] = Field(None, description="Query suggestions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Search timestamp")


class ExportResponse(BaseModel):
    """Export operation response model"""
    export_id: UUID = Field(..., description="Export operation identifier")
    format: str = Field(..., description="Export format (csv, json, xlsx, pdf)")
    status: str = Field(..., description="Export status")
    file_size: Optional[int] = Field(None, description="Exported file size in bytes")
    download_url: Optional[str] = Field(None, description="URL to download the exported file")
    expires_at: Optional[datetime] = Field(None, description="Download URL expiration time")
    progress: float = Field(..., description="Export progress percentage (0-100)")
    message: str = Field(..., description="Export status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Export timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "export_id": "123e4567-e89b-12d3-a456-426614174000",
                "format": "csv",
                "status": "completed",
                "file_size": 2048000,
                "download_url": "/api/v1/exports/123e4567-e89b-12d3-a456-426614174000/download",
                "expires_at": "2025-07-14T10:30:00Z",
                "progress": 100.0,
                "message": "Export completed successfully",
                "timestamp": "2025-07-13T10:30:00Z"
            }
        }


# Common HTTP status responses for OpenAPI documentation
COMMON_RESPONSES = {
    400: {"model": ValidationErrorResponse, "description": "Bad Request - Invalid input data"},
    401: {"model": ErrorResponse, "description": "Unauthorized - Authentication required"},
    403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
    404: {"model": ErrorResponse, "description": "Not Found - Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflict - Resource already exists"},
    429: {"model": RateLimitResponse, "description": "Too Many Requests - Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Internal Server Error - Unexpected server error"},
    503: {"model": ErrorResponse, "description": "Service Unavailable - Service temporarily unavailable"}
}