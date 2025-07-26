"""
Exception handlers for Unified Authentication Bridge
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from .exceptions import BaseCustomException
from .logging import get_logger

logger = get_logger(__name__)


async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """Handle custom exceptions"""
    
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.error(
        "Custom exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "metadata": {
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions"""
    
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            },
            "metadata": {
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": {}
            },
            "metadata": {
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": {}
            },
            "metadata": {
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method
            }
        }
    )