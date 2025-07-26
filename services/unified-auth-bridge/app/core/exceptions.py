"""
Custom exceptions for Unified Authentication Bridge
"""

from typing import Any, Dict, Optional


class BaseCustomException(Exception):
    """Base custom exception class"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(BaseCustomException):
    """Authentication related errors"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            **kwargs
        )


class AuthorizationError(BaseCustomException):
    """Authorization related errors"""
    
    def __init__(self, message: str = "Authorization failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            **kwargs
        )


class ValidationError(BaseCustomException):
    """Validation related errors"""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            **kwargs
        )


class ServiceUnavailableError(BaseCustomException):
    """Service unavailable errors"""
    
    def __init__(self, message: str = "Service unavailable", **kwargs):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            **kwargs
        )


class ConfigurationError(BaseCustomException):
    """Configuration related errors"""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            **kwargs
        )