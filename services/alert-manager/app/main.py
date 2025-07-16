"""
Main FastAPI application for Alert Management service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .api.v1.endpoints import router as api_router

# Configure logging
configure_logging()
logger = get_logger("alert_manager")

# Create FastAPI application
app = FastAPI(
    title="Alert Management Service",
    description="Comprehensive alerting system for Splunk MCP integration",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
    )

# Include API routes
app.include_router(
    api_router,
    prefix=settings.api_prefix,
    tags=["alerts"]
)


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "Starting Alert Management service",
        version=settings.service_version,
        debug=settings.debug,
        port=settings.port
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Alert Management service")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "alert-manager",
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "alert-manager",
        "version": settings.service_version
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )