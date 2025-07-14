"""
Enhanced exception handlers and middleware for comprehensive error handling.

This module provides middleware and handlers for processing exceptions,
logging errors, and creating standardized error responses.
"""

import traceback
from typing import Any, Dict
from uuid import uuid4

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as PydanticValidationError

from .exceptions import (
    BaseCustomException,
    ErrorContext,
    ErrorTracker,
    ErrorMetrics,
    map_exception_to_http,
    create_detailed_http_exception,
    validation_error
)
from .logging import get_logger
from .versioning import add_version_headers

logger = get_logger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive exception handling middleware that:
    - Captures all unhandled exceptions
    - Creates error context from request
    - Logs errors with appropriate severity
    - Returns standardized error responses
    - Tracks error metrics
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle any exceptions"""
        correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id
        
        try:
            response = await call_next(request)
            return response
            
        except BaseCustomException as exc:
            # Handle our custom exceptions
            return await self._handle_custom_exception(request, exc, correlation_id)
            
        except Exception as exc:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(request, exc, correlation_id)
    
    async def _handle_custom_exception(
        self, 
        request: Request, 
        exc: BaseCustomException, 
        correlation_id: str
    ) -> JSONResponse:
        """Handle custom exceptions with context"""
        
        # Add request context to exception if not already present
        if not exc.context:
            exc.with_context(self._create_error_context(request, correlation_id))
        
        # Log the exception based on severity
        self._log_exception(exc, request)
        
        # Track metrics
        self._track_error_metrics(exc)
        
        # Create HTTP response
        http_exc = map_exception_to_http(exc)
        response = JSONResponse(
            status_code=http_exc.status_code,
            content=http_exc.detail,
            headers=http_exc.headers
        )
        
        # Add version headers
        return add_version_headers(response, request)
    
    async def _handle_unexpected_exception(
        self, 
        request: Request, 
        exc: Exception, 
        correlation_id: str
    ) -> JSONResponse:
        """Handle unexpected exceptions"""
        
        # Log the unexpected exception
        logger.error(
            "Unexpected exception occurred",
            path=request.url.path,
            method=request.method,
            correlation_id=correlation_id,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            exc_info=True
        )
        
        # Create a generic error response (don't expose internal errors)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": "Internal server error",
                    "user_message": "An unexpected error occurred. Please try again later.",
                    "code": "internal_server_error",
                    "error_id": correlation_id,
                    "severity": "critical",
                    "category": "system_error",
                    "suggestions": [
                        "Try again in a few minutes",
                        "Contact support if the issue persists"
                    ]
                }
            }
        )
        
        return add_version_headers(response, request)
    
    def _create_error_context(self, request: Request, correlation_id: str) -> ErrorContext:
        """Create error context from request"""
        user_id = getattr(request.state, 'user_id', None)
        session_id = getattr(request.state, 'session_id', None)
        
        return ErrorTracker.create_context(
            correlation_id=correlation_id,
            user_id=user_id,
            session_id=session_id,
            request_path=str(request.url.path),
            request_method=request.method,
            user_agent=request.headers.get("user-agent"),
            ip_address=self._get_client_ip(request)
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (when behind a proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        return getattr(request.client, "host", "unknown")
    
    def _log_exception(self, exc: BaseCustomException, request: Request):
        """Log exception with appropriate severity level"""
        log_data = {
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "severity": exc.severity.value,
            "category": exc.category.value,
            "path": request.url.path,
            "method": request.method,
            "message": exc.message,
            "details": exc.details
        }
        
        if exc.context:
            log_data.update({
                "user_id": exc.context.user_id,
                "session_id": exc.context.session_id,
                "correlation_id": exc.context.correlation_id
            })
        
        # Log based on severity
        if exc.severity.value == "critical":
            logger.critical("Critical exception occurred", **log_data, exc_info=True)
        elif exc.severity.value == "high":
            logger.error("High severity exception occurred", **log_data)
        elif exc.severity.value == "medium":
            logger.warning("Medium severity exception occurred", **log_data)
        else:
            logger.info("Low severity exception occurred", **log_data)
    
    def _track_error_metrics(self, exc: BaseCustomException):
        """Track error metrics for monitoring"""
        # This would integrate with your metrics system (Prometheus, etc.)
        tags = ErrorMetrics.get_metric_tags(exc)
        
        # Example metric tracking (implement with your metrics library)
        # metrics.increment("api.errors.total", tags=tags)
        
        if ErrorMetrics.should_alert(exc):
            # Trigger alert for high/critical errors
            # alerting.send_alert(exc)
            pass


# FastAPI Exception Handlers

async def custom_exception_handler(request: Request, exc: BaseCustomException) -> JSONResponse:
    """Handle custom exceptions in FastAPI"""
    correlation_id = getattr(request.state, 'correlation_id', str(uuid4()))
    
    # Add context if not present
    if not exc.context:
        user_id = getattr(request.state, 'user_id', None)
        session_id = getattr(request.state, 'session_id', None)
        
        context = ErrorTracker.create_context(
            correlation_id=correlation_id,
            user_id=user_id,
            session_id=session_id,
            request_path=str(request.url.path),
            request_method=request.method,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.headers.get("x-forwarded-for", "unknown")
        )
        exc.with_context(context)
    
    # Log the exception
    logger.error(
        "Custom exception occurred",
        error_id=exc.error_id,
        error_code=exc.error_code,
        severity=exc.severity.value,
        category=exc.category.value,
        path=request.url.path,
        method=request.method,
        message=exc.message,
        details=exc.details,
        user_id=exc.context.user_id if exc.context else None
    )
    
    # Create HTTP response
    http_exc = map_exception_to_http(exc)
    response = JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers=http_exc.headers
    )
    
    # Add version headers
    return add_version_headers(response, request)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors"""
    correlation_id = getattr(request.state, 'correlation_id', str(uuid4()))
    
    # Convert Pydantic validation errors to our format
    field_errors = []
    for error in exc.errors():
        field_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    # Create our validation error
    validation_exc = validation_error(
        message="Request validation failed",
        field_errors=field_errors
    )
    
    # Add context
    context = ErrorTracker.create_context(
        correlation_id=correlation_id,
        user_id=getattr(request.state, 'user_id', None),
        session_id=getattr(request.state, 'session_id', None),
        request_path=str(request.url.path),
        request_method=request.method,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.headers.get("x-forwarded-for", "unknown")
    )
    validation_exc.with_context(context)
    
    # Log validation error
    logger.warning(
        "Request validation failed",
        error_id=validation_exc.error_id,
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        field_errors=field_errors
    )
    
    # Create HTTP response
    http_exc = map_exception_to_http(validation_exc)
    response = JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )
    
    return add_version_headers(response, request)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', str(uuid4()))
    
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
        correlation_id=correlation_id
    )
    
    # Create enhanced error response
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
                "user_message": exc.detail if isinstance(exc.detail, str) else "An error occurred",
                "code": "http_error",
                "error_id": correlation_id,
                "severity": "medium",
                "category": "user_error" if 400 <= exc.status_code < 500 else "system_error"
            }
        }
    )
    
    return add_version_headers(response, request)


async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', str(uuid4()))
    
    logger.warning(
        "Starlette HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
        correlation_id=correlation_id
    )
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "user_message": exc.detail,
                "code": "http_error",
                "error_id": correlation_id,
                "severity": "medium",
                "category": "user_error" if 400 <= exc.status_code < 500 else "system_error"
            }
        }
    )
    
    return add_version_headers(response, request)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', str(uuid4()))
    
    logger.error(
        "Unexpected exception occurred",
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        exc_info=True
    )
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "user_message": "An unexpected error occurred. Please try again later.",
                "code": "internal_server_error",
                "error_id": correlation_id,
                "severity": "critical",
                "category": "system_error",
                "suggestions": [
                    "Try again in a few minutes",
                    "Contact support if the issue persists"
                ]
            }
        }
    )
    
    return add_version_headers(response, request)