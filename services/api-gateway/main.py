"""
Splunk MCP Integration - API Gateway
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
import time

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, RequestLoggingMiddleware
from app.core.exceptions import BaseCustomException, map_exception_to_http
from app.core.docs import (
    custom_openapi, 
    get_custom_swagger_ui_html, 
    get_custom_redoc_html,
    APIVersionConfig
)
from app.core.versioning import APIVersionMiddleware, add_version_headers
from app.models.responses import (
    HealthCheckResponse, 
    APIVersionResponse, 
    ErrorResponse,
    COMMON_RESPONSES
)
from app.api.v1.api import api_router
from app.db.session import init_db


# Configure logging
configure_logging()
logger = get_logger(__name__)

# Track application startup time
startup_time = time.time()


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
    
    # Store startup time in app state
    app.state.startup_time = startup_time
    
    yield
    
    # Shutdown
    logger.info("Shutting down Splunk MCP Integration API Gateway")


# Create FastAPI application
app = FastAPI(
    title="Splunk MCP Integration API",
    description="API Gateway for Splunk Model Context Protocol Integration",
    version=settings.app_version,
    docs_url=None,  # Custom docs endpoint
    redoc_url=None,  # Custom redoc endpoint
    openapi_url=settings.openapi_url if settings.debug else None,
    lifespan=lifespan,
    responses=COMMON_RESPONSES
)

# Set custom OpenAPI schema
app.openapi = lambda: custom_openapi(app)

# Add versioning middleware
app.add_middleware(APIVersionMiddleware, supported_versions=["1.0.0"])

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


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint
    
    Returns basic API information and status.
    """
    uptime = time.time() - getattr(app.state, 'startup_time', time.time())
    
    return {
        "message": "Splunk MCP Integration API Gateway",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "running",
        "uptime_seconds": round(uptime, 2),
        "api_version": "1.0.0",
        "docs_url": f"{settings.api_v1_prefix}/docs" if settings.debug else None,
        "links": {
            "documentation": f"{settings.api_v1_prefix}/docs",
            "redoc": f"{settings.api_v1_prefix}/redoc",
            "openapi": settings.openapi_url,
            "health": f"{settings.api_v1_prefix}/health/status",
            "version": f"{settings.api_v1_prefix}/version"
        }
    }


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI documentation"""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Documentation not available in production")
    
    return HTMLResponse(
        get_custom_swagger_ui_html(
            openapi_url=settings.openapi_url,
            title="Splunk MCP Integration API - Documentation"
        )
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Custom ReDoc documentation"""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Documentation not available in production")
    
    return HTMLResponse(
        get_custom_redoc_html(
            openapi_url=settings.openapi_url,
            title="Splunk MCP Integration API - Documentation"
        )
    )


@app.get(f"{settings.api_v1_prefix}/version", response_model=APIVersionResponse, tags=["System"])
async def get_api_version():
    """
    Get API version information
    
    Returns comprehensive information about the current API version,
    supported versions, and migration guidance.
    """
    return APIVersionResponse(**APIVersionConfig.get_version_info())


@app.get(f"{settings.api_v1_prefix}/health/detailed", response_model=HealthCheckResponse, tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check endpoint
    
    Returns comprehensive health information including service statuses,
    uptime, and system metrics.
    """
    uptime = time.time() - getattr(app.state, 'startup_time', time.time())
    
    # Check service health (simplified for demo)
    services = {
        "database": "healthy",  # Would implement actual database health check
        "redis": "healthy",     # Would implement actual Redis health check
        "nlp_engine": "healthy" # Would implement actual NLP engine health check
    }
    
    overall_status = "healthy" if all(status == "healthy" for status in services.values()) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        services=services,
        uptime_seconds=round(uptime, 2)
    )


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
    
    response = JSONResponse(
        status_code=http_exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "code": exc.__class__.__name__.lower().replace('exception', '_error'),
                "details": exc.details
            }
        }
    )
    
    # Add version headers
    return add_version_headers(response, request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(
        "Request validation failed",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    
    response = JSONResponse(
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
    
    # Add version headers
    return add_version_headers(response, request)


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
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": "http_error"
            }
        }
    )
    
    # Add version headers
    return add_version_headers(response, request)


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
    
    response = JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "code": "internal_error"
            }
        }
    )
    
    # Add version headers
    return add_version_headers(response, request)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )