"""
Splunk MCP Integration - API Gateway
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, RequestLoggingMiddleware
from app.core.exceptions import BaseCustomException, map_exception_to_http
from app.api.v1.api import api_router
from app.db.session import init_db


# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Splunk MCP Integration API Gateway", version=settings.app_version)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Splunk MCP Integration API Gateway")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="API Gateway for Splunk Model Context Protocol Integration",
    version=settings.app_version,
    docs_url=settings.docs_url if settings.debug else None,
    redoc_url=settings.redoc_url if settings.debug else None,
    openapi_url=settings.openapi_url if settings.debug else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Splunk MCP Integration API Gateway",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "running",
        "docs_url": f"{settings.api_v1_prefix}/docs" if settings.debug else None
    }


# Exception handlers
@app.exception_handler(BaseCustomException)
async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """Handle custom exceptions"""
    http_exc = map_exception_to_http(exc)
    logger.error(
        "Custom exception occurred",
        path=request.url.path,
        method=request.method,
        exception=exc.__class__.__name__,
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(
        "Request validation failed",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Request validation failed",
                "code": "validation_error",
                "details": {
                    "errors": exc.errors()
                }
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": "http_error"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        "Unexpected exception occurred",
        path=request.url.path,
        method=request.method,
        exception=exc.__class__.__name__,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "code": "internal_error"
            }
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )