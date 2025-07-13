"""
Custom exceptions for the application
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status


class BaseCustomException(Exception):
    """Base exception class for custom exceptions"""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Raised when validation fails"""
    pass


class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(BaseCustomException):
    """Raised when authorization fails"""
    pass


class ResourceNotFoundError(BaseCustomException):
    """Raised when a resource is not found"""
    pass


class ResourceExistsError(BaseCustomException):
    """Raised when trying to create a resource that already exists"""
    pass


class ExternalServiceError(BaseCustomException):
    """Raised when external service call fails"""
    pass


class DatabaseError(BaseCustomException):
    """Raised when database operation fails"""
    pass


class ConfigurationError(BaseCustomException):
    """Raised when configuration is invalid"""
    pass


# SPL-specific exceptions
class SPLTranslationError(BaseCustomException):
    """Raised when SPL translation fails"""
    pass


class SPLValidationError(BaseCustomException):
    """Raised when SPL validation fails"""
    pass


class SPLExecutionError(BaseCustomException):
    """Raised when SPL execution fails"""
    pass


# Splunk-specific exceptions
class SplunkConnectionError(BaseCustomException):
    """Raised when Splunk connection fails"""
    pass


class SplunkAuthenticationError(BaseCustomException):
    """Raised when Splunk authentication fails"""
    pass


class SplunkAPIError(BaseCustomException):
    """Raised when Splunk API call fails"""
    pass


# Query-specific exceptions
class QueryTimeoutError(BaseCustomException):
    """Raised when query execution times out"""
    pass


class QueryLimitExceededError(BaseCustomException):
    """Raised when query limits are exceeded"""
    pass


class InvalidQueryError(BaseCustomException):
    """Raised when query is invalid"""
    pass


# Rate limiting exceptions
class RateLimitExceededError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    pass


# Session exceptions
class SessionExpiredError(BaseCustomException):
    """Raised when session has expired"""
    pass


class SessionInvalidError(BaseCustomException):
    """Raised when session is invalid"""
    pass


# File upload exceptions
class FileTooLargeError(BaseCustomException):
    """Raised when uploaded file is too large"""
    pass


class InvalidFileTypeError(BaseCustomException):
    """Raised when uploaded file type is not allowed"""
    pass


# HTTP Exception mappers
def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> HTTPException:
    """Create HTTPException with structured error response"""
    error_detail = {
        "error": {
            "message": message,
            "code": error_code,
            "details": details or {}
        }
    }
    
    return HTTPException(
        status_code=status_code,
        detail=error_detail
    )


# Exception to HTTP status code mapping
EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    ResourceExistsError: status.HTTP_409_CONFLICT,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    SPLTranslationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SPLValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SPLExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    SplunkConnectionError: status.HTTP_502_BAD_GATEWAY,
    SplunkAuthenticationError: status.HTTP_401_UNAUTHORIZED,
    SplunkAPIError: status.HTTP_502_BAD_GATEWAY,
    QueryTimeoutError: status.HTTP_408_REQUEST_TIMEOUT,
    QueryLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    InvalidQueryError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    SessionExpiredError: status.HTTP_401_UNAUTHORIZED,
    SessionInvalidError: status.HTTP_401_UNAUTHORIZED,
    FileTooLargeError: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    InvalidFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}


def map_exception_to_http(exception: BaseCustomException) -> HTTPException:
    """Map custom exception to HTTP exception"""
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exception), 
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    return create_http_exception(
        status_code=status_code,
        message=exception.message,
        details=exception.details,
        error_code=exception.error_code
    )