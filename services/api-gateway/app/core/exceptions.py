"""
Comprehensive exception handling system for the Splunk MCP Integration API.

This module provides a hierarchical exception system with detailed error tracking,
context management, and standardized error responses.
"""

import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorSeverity(str, Enum):
    """Error severity levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification and handling"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"


class ErrorContext(BaseModel):
    """Context information for error tracking and debugging"""
    correlation_id: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    additional_context: Dict[str, Any] = {}


class BaseCustomException(Exception):
    """
    Enhanced base exception class with comprehensive error tracking
    
    Features:
    - Unique error tracking IDs
    - Context preservation
    - Severity and category classification
    - Chain of error causation
    - Structured details for debugging
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
        context: Optional[ErrorContext] = None,
        user_message: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None
    ):
        self.error_id = str(uuid4())
        self.message = message
        self.user_message = user_message or message
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__.lower().replace('exception', '_error')
        self.severity = severity
        self.category = category
        self.context = context
        self.suggestions = suggestions or []
        self.retry_after = retry_after
        self.cause = cause
        self.traceback_info = traceback.format_exc() if cause else None
        self.created_at = datetime.utcnow()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and responses"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "user_message": self.user_message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "suggestions": self.suggestions,
            "retry_after": self.retry_after,
            "created_at": self.created_at.isoformat(),
            "context": self.context.dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None
        }
    
    def with_context(self, context: ErrorContext) -> 'BaseCustomException':
        """Add context to the exception"""
        self.context = context
        return self
    
    def add_suggestion(self, suggestion: str) -> 'BaseCustomException':
        """Add a suggestion to help resolve the error"""
        self.suggestions.append(suggestion)
        return self


# Core Exception Classes with Enhanced Error Handling

class ValidationError(BaseCustomException):
    """Raised when validation fails"""
    
    def __init__(self, message: str, field_errors: Optional[List[Dict[str, Any]]] = None, **kwargs):
        details = kwargs.get('details', {})
        if field_errors:
            details['field_errors'] = field_errors
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_message="Please check your input and try again.",
            suggestions=["Verify all required fields are provided", "Check data format requirements"],
            **kwargs
        )


class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Please check your credentials and try again.",
            suggestions=["Verify your username and password", "Check if your account is active"],
            **kwargs
        )


class AuthorizationError(BaseCustomException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Insufficient permissions", required_permission: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if required_permission:
            details['required_permission'] = required_permission
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUTHORIZATION,
            user_message="You don't have permission to perform this action.",
            suggestions=["Contact your administrator for access", "Check your role permissions"],
            **kwargs
        )


class ResourceNotFoundError(BaseCustomException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        
        message = f"{resource_type.title()} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.USER_ERROR,
            user_message=f"The requested {resource_type} could not be found.",
            suggestions=["Verify the resource ID is correct", "Check if the resource exists"],
            **kwargs
        )


class ResourceExistsError(BaseCustomException):
    """Raised when trying to create a resource that already exists"""
    
    def __init__(self, resource_type: str, identifier: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'resource_type': resource_type,
            'identifier': identifier
        })
        
        message = f"{resource_type.title()} already exists"
        if identifier:
            message += f" ({identifier})"
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.BUSINESS_LOGIC,
            user_message=f"A {resource_type} with this identifier already exists.",
            suggestions=["Use a different identifier", "Update the existing resource instead"],
            **kwargs
        )


class ExternalServiceError(BaseCustomException):
    """Raised when external service call fails"""
    
    def __init__(self, service_name: str, operation: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'service_name': service_name,
            'operation': operation,
            'status_code': status_code
        })
        
        message = f"External service '{service_name}' error"
        if operation:
            message += f" during {operation}"
        
        # Determine retry recommendation based on status code
        retry_suggestions = []
        if status_code:
            if 500 <= status_code < 600:
                retry_suggestions.append("Retry the operation in a few minutes")
            elif status_code == 429:
                retry_suggestions.append("Wait for rate limit to reset")
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            user_message=f"Unable to connect to {service_name}. Please try again later.",
            suggestions=retry_suggestions + ["Check service status", "Contact support if issue persists"],
            retry_after=60 if status_code in [429, 503] else None,
            **kwargs
        )


class DatabaseError(BaseCustomException):
    """Raised when database operation fails"""
    
    def __init__(self, operation: str, table: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'operation': operation,
            'table': table
        })
        
        message = f"Database {operation} failed"
        if table:
            message += f" on {table}"
        
        super().__init__(
            message=message,
            details=details,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE,
            user_message="A database error occurred. Please try again later.",
            suggestions=["Retry the operation", "Contact support if issue persists"],
            **kwargs
        )


class ConfigurationError(BaseCustomException):
    """Raised when configuration is invalid"""
    
    def __init__(self, config_key: str, **kwargs):
        details = kwargs.get('details', {})
        details['config_key'] = config_key
        
        super().__init__(
            message=f"Invalid configuration for '{config_key}'",
            details=details,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            user_message="A configuration error occurred. Please contact support.",
            suggestions=["Check configuration file", "Contact administrator"],
            **kwargs
        )


# SPL-specific exceptions
class SPLTranslationError(BaseCustomException):
    """Raised when SPL translation fails"""
    
    def __init__(self, query: str, reason: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'original_query': query,
            'translation_failure_reason': reason
        })
        
        super().__init__(
            message=f"Failed to translate natural language query to SPL",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC,
            user_message="Unable to understand your query. Please rephrase it.",
            suggestions=[
                "Try using simpler language",
                "Be more specific about what you're looking for",
                "Use field names that exist in your data"
            ],
            **kwargs
        )


class SPLValidationError(BaseCustomException):
    """Raised when SPL validation fails"""
    
    def __init__(self, spl_query: str, validation_errors: Optional[List[str]] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'spl_query': spl_query,
            'validation_errors': validation_errors or []
        })
        
        super().__init__(
            message="Generated SPL query failed validation",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            user_message="The generated query has syntax errors.",
            suggestions=["Rephrase your natural language query", "Check field names and syntax"],
            **kwargs
        )


class SPLExecutionError(BaseCustomException):
    """Raised when SPL execution fails"""
    
    def __init__(self, spl_query: str, execution_error: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'spl_query': spl_query,
            'execution_error': execution_error
        })
        
        super().__init__(
            message="SPL query execution failed",
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            user_message="Unable to execute your query. Please try again.",
            suggestions=["Check if the data exists", "Try a simpler query", "Verify time range"],
            **kwargs
        )


# Splunk-specific exceptions
class SplunkConnectionError(BaseCustomException):
    """Raised when Splunk connection fails"""
    
    def __init__(self, splunk_host: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if splunk_host:
            details['splunk_host'] = splunk_host
        
        super().__init__(
            message="Failed to connect to Splunk",
            details=details,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.EXTERNAL_SERVICE,
            user_message="Unable to connect to Splunk. Please try again later.",
            suggestions=["Check network connectivity", "Verify Splunk is running", "Contact administrator"],
            retry_after=30,
            **kwargs
        )


class SplunkAuthenticationError(BaseCustomException):
    """Raised when Splunk authentication fails"""
    
    def __init__(self, username: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if username:
            details['username'] = username
        
        super().__init__(
            message="Splunk authentication failed",
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Unable to authenticate with Splunk. Please check your credentials.",
            suggestions=["Verify Splunk credentials", "Check if account is active", "Contact administrator"],
            **kwargs
        )


class SplunkAPIError(BaseCustomException):
    """Raised when Splunk API call fails"""
    
    def __init__(self, endpoint: str, status_code: Optional[int] = None, response_text: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'endpoint': endpoint,
            'status_code': status_code,
            'response_text': response_text
        })
        
        super().__init__(
            message=f"Splunk API error on {endpoint}",
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            user_message="Splunk API error occurred. Please try again.",
            suggestions=["Retry the operation", "Check Splunk service status"],
            retry_after=30 if status_code in [429, 503] else None,
            **kwargs
        )


# Query-specific exceptions
class QueryTimeoutError(BaseCustomException):
    """Raised when query execution times out"""
    
    def __init__(self, timeout_seconds: int, query: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'timeout_seconds': timeout_seconds,
            'query': query
        })
        
        super().__init__(
            message=f"Query timed out after {timeout_seconds} seconds",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PERFORMANCE,
            user_message="Your query is taking too long. Please try a more specific query.",
            suggestions=[
                "Use a shorter time range",
                "Add more specific filters",
                "Limit the number of results"
            ],
            **kwargs
        )


class QueryLimitExceededError(BaseCustomException):
    """Raised when query limits are exceeded"""
    
    def __init__(self, limit_type: str, limit_value: int, current_value: int, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'limit_type': limit_type,
            'limit_value': limit_value,
            'current_value': current_value
        })
        
        super().__init__(
            message=f"{limit_type} limit exceeded: {current_value} > {limit_value}",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC,
            user_message=f"Query exceeds {limit_type} limit.",
            suggestions=[
                f"Reduce {limit_type} to under {limit_value}",
                "Use more specific filters"
            ],
            **kwargs
        )


class InvalidQueryError(BaseCustomException):
    """Raised when query is invalid"""
    
    def __init__(self, query: str, reason: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'query': query,
            'reason': reason
        })
        
        super().__init__(
            message="Invalid query format",
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_message="Your query format is invalid. Please rephrase it.",
            suggestions=["Check query syntax", "Use supported query patterns"],
            **kwargs
        )


# Rate limiting exceptions
class RateLimitExceededError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window_seconds: int, retry_after: int, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'limit': limit,
            'window_seconds': window_seconds,
            'retry_after': retry_after
        })
        
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds} seconds",
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.BUSINESS_LOGIC,
            user_message="You're making too many requests. Please wait before trying again.",
            suggestions=[f"Wait {retry_after} seconds before retrying"],
            retry_after=retry_after,
            **kwargs
        )


# Session exceptions
class SessionExpiredError(BaseCustomException):
    """Raised when session has expired"""
    
    def __init__(self, session_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if session_id:
            details['session_id'] = session_id
        
        super().__init__(
            message="Session has expired",
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Your session has expired. Please log in again.",
            suggestions=["Log in again", "Enable 'Remember me' for longer sessions"],
            **kwargs
        )


class SessionInvalidError(BaseCustomException):
    """Raised when session is invalid"""
    
    def __init__(self, session_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if session_id:
            details['session_id'] = session_id
        
        super().__init__(
            message="Invalid session",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Your session is invalid. Please log in again.",
            suggestions=["Log in again", "Clear browser cache and cookies"],
            **kwargs
        )


# File upload exceptions
class FileTooLargeError(BaseCustomException):
    """Raised when uploaded file is too large"""
    
    def __init__(self, file_size: int, max_size: int, filename: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'file_size': file_size,
            'max_size': max_size,
            'filename': filename
        })
        
        super().__init__(
            message=f"File too large: {file_size} bytes (max: {max_size} bytes)",
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_message=f"File is too large. Maximum size is {max_size // (1024*1024)} MB.",
            suggestions=["Compress the file", "Split into smaller files"],
            **kwargs
        )


class InvalidFileTypeError(BaseCustomException):
    """Raised when uploaded file type is not allowed"""
    
    def __init__(self, file_type: str, allowed_types: List[str], filename: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'file_type': file_type,
            'allowed_types': allowed_types,
            'filename': filename
        })
        
        super().__init__(
            message=f"Invalid file type: {file_type}",
            details=details,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_message=f"File type '{file_type}' is not allowed.",
            suggestions=[f"Use one of these file types: {', '.join(allowed_types)}"],
            **kwargs
        )


# Enhanced Error Response Utilities

class ErrorTracker:
    """Utility class for tracking and analyzing errors"""
    
    @staticmethod
    def create_context(
        correlation_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        **additional_context
    ) -> ErrorContext:
        """Create error context from request information"""
        return ErrorContext(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            request_path=request_path,
            request_method=request_method,
            user_agent=user_agent,
            ip_address=ip_address,
            additional_context=additional_context
        )


def create_detailed_http_exception(
    status_code: int,
    message: str,
    user_message: Optional[str] = None,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    retry_after: Optional[int] = None,
    error_id: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None
) -> HTTPException:
    """Create HTTPException with comprehensive error response structure"""
    
    error_response = {
        "error": {
            "message": message,
            "user_message": user_message or message,
            "code": error_code or "unknown_error",
            "details": details or {},
            "error_id": error_id or str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity or ErrorSeverity.MEDIUM.value,
            "category": category or ErrorCategory.SYSTEM_ERROR.value
        }
    }
    
    # Add optional fields
    if suggestions:
        error_response["error"]["suggestions"] = suggestions
    if retry_after:
        error_response["error"]["retry_after"] = retry_after
    
    return HTTPException(
        status_code=status_code,
        detail=error_response,
        headers={"Retry-After": str(retry_after)} if retry_after else None
    )


def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> HTTPException:
    """Create HTTPException with basic structured error response (backward compatibility)"""
    return create_detailed_http_exception(
        status_code=status_code,
        message=message,
        error_code=error_code,
        details=details
    )


# Enhanced Exception to HTTP status code mapping
EXCEPTION_STATUS_MAP = {
    # Core exceptions
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    ResourceExistsError: status.HTTP_409_CONFLICT,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # SPL-specific exceptions
    SPLTranslationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SPLValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SPLExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Splunk-specific exceptions
    SplunkConnectionError: status.HTTP_502_BAD_GATEWAY,
    SplunkAuthenticationError: status.HTTP_401_UNAUTHORIZED,
    SplunkAPIError: status.HTTP_502_BAD_GATEWAY,
    
    # Query-specific exceptions
    QueryTimeoutError: status.HTTP_408_REQUEST_TIMEOUT,
    QueryLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    InvalidQueryError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    
    # Rate limiting and session exceptions
    RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    SessionExpiredError: status.HTTP_401_UNAUTHORIZED,
    SessionInvalidError: status.HTTP_401_UNAUTHORIZED,
    
    # File upload exceptions
    FileTooLargeError: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    InvalidFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}


def map_exception_to_http(exception: BaseCustomException) -> HTTPException:
    """Map custom exception to comprehensive HTTP exception"""
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exception), 
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    return create_detailed_http_exception(
        status_code=status_code,
        message=exception.message,
        user_message=exception.user_message,
        error_code=exception.error_code,
        details=exception.details,
        suggestions=exception.suggestions,
        retry_after=exception.retry_after,
        error_id=exception.error_id,
        severity=exception.severity.value,
        category=exception.category.value
    )


# Error Analysis and Monitoring Utilities

class ErrorMetrics:
    """Utility class for error metrics and monitoring"""
    
    @staticmethod
    def should_alert(exception: BaseCustomException) -> bool:
        """Determine if an exception should trigger an alert"""
        return exception.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
    
    @staticmethod
    def get_metric_tags(exception: BaseCustomException) -> Dict[str, str]:
        """Get metric tags for monitoring systems"""
        return {
            "error_code": exception.error_code,
            "severity": exception.severity.value,
            "category": exception.category.value,
            "exception_type": type(exception).__name__
        }
    
    @staticmethod
    def is_retryable(exception: BaseCustomException) -> bool:
        """Determine if an operation should be retried for this exception"""
        retryable_categories = {
            ErrorCategory.EXTERNAL_SERVICE,
            ErrorCategory.NETWORK,
            ErrorCategory.PERFORMANCE
        }
        
        retryable_types = {
            ExternalServiceError,
            SplunkConnectionError,
            SplunkAPIError,
            QueryTimeoutError,
            DatabaseError
        }
        
        return (
            exception.category in retryable_categories or
            type(exception) in retryable_types or
            exception.retry_after is not None
        )


# Common Exception Factory Functions

def validation_error(
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None,
    field_errors: Optional[List[Dict[str, Any]]] = None
) -> ValidationError:
    """Create a validation error with field-specific information"""
    details = {}
    if field:
        details['field'] = field
    if value is not None:
        details['value'] = str(value)
    
    return ValidationError(
        message=message,
        details=details,
        field_errors=field_errors
    )


def not_found_error(resource_type: str, resource_id: Optional[str] = None) -> ResourceNotFoundError:
    """Create a resource not found error"""
    return ResourceNotFoundError(
        resource_type=resource_type,
        resource_id=resource_id
    )


def unauthorized_error(message: str = "Authentication required") -> AuthenticationError:
    """Create an authentication error"""
    return AuthenticationError(message=message)


def forbidden_error(
    message: str = "Insufficient permissions",
    required_permission: Optional[str] = None
) -> AuthorizationError:
    """Create an authorization error"""
    return AuthorizationError(
        message=message,
        required_permission=required_permission
    )


def service_unavailable_error(
    service_name: str,
    operation: Optional[str] = None,
    retry_after: int = 60
) -> ExternalServiceError:
    """Create a service unavailable error"""
    return ExternalServiceError(
        service_name=service_name,
        operation=operation,
        status_code=503,
        retry_after=retry_after
    )


def rate_limit_error(
    limit: int,
    window_seconds: int = 3600,
    retry_after: int = 60
) -> RateLimitExceededError:
    """Create a rate limit exceeded error"""
    return RateLimitExceededError(
        limit=limit,
        window_seconds=window_seconds,
        retry_after=retry_after
    )