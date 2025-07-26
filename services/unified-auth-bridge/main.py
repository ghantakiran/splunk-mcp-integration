"""
Unified Authentication Bridge Service
Main FastAPI application for coordinating authentication between Splunk Enterprise and Cloud
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
import time

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, RequestLoggingMiddleware
from app.core.exceptions import BaseCustomException
from app.core.exception_handlers import (
    custom_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.models.responses import HealthCheckResponse, APIVersionResponse
from app.api.v1.api import api_router
from app.services.auth_bridge_service import AuthBridgeService

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Track application startup time
startup_time = time.time()

# Global auth bridge service instance
auth_bridge_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global auth_bridge_service
    
    # Startup
    logger.info("Starting Unified Authentication Bridge Service", version=settings.app_version)
    
    # Initialize auth bridge service
    try:
        auth_bridge_service = AuthBridgeService()
        await auth_bridge_service.initialize()
        app.state.auth_bridge_service = auth_bridge_service
        logger.info("Authentication bridge service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize authentication bridge service", error=str(e))
        raise
    
    # Store startup time
    app.state.startup_time = startup_time
    
    yield
    
    # Shutdown
    if auth_bridge_service:
        await auth_bridge_service.cleanup()
    
    logger.info("Shutting down Unified Authentication Bridge Service")


# Create FastAPI application
app = FastAPI(
    title="Unified Authentication Bridge API",
    description="Unified authentication service for hybrid Splunk Enterprise and Cloud deployments",
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


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint
    
    Returns basic API information and status.
    """
    uptime = time.time() - getattr(app.state, 'startup_time', time.time())
    
    return {
        "message": "Unified Authentication Bridge Service",
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
            "health": f"{settings.api_v1_prefix}/health",
            "version": f"{settings.api_v1_prefix}/version"
        }
    }


@app.get(f"{settings.api_v1_prefix}/version", response_model=APIVersionResponse, tags=["System"])
async def get_api_version():
    """Get API version information"""
    return APIVersionResponse(
        version=settings.app_version,
        api_version="1.0.0",
        environment=settings.environment,
        build_timestamp=datetime.utcnow(),
        supported_versions=["1.0.0"],
        deprecated_versions=[],
        sunset_versions=[]
    )


@app.get(f"{settings.api_v1_prefix}/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns service health status including dependent services.
    """
    uptime = time.time() - getattr(app.state, 'startup_time', time.time())
    
    # Check dependent services
    auth_bridge = getattr(app.state, 'auth_bridge_service', None)
    services = {}
    
    if auth_bridge:
        try:
            services = await auth_bridge.check_health()
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            services = {
                "cloud_auth_service": "unhealthy",
                "api_gateway": "unknown",
                "cloud_connection_manager": "unknown"
            }
    
    overall_status = "healthy" if all(
        status in ["healthy", "ok"] for status in services.values()
    ) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        services=services,
        uptime_seconds=round(uptime, 2)
    )


# Exception handlers
app.add_exception_handler(BaseCustomException, custom_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )