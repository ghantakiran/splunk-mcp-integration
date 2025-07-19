#!/usr/bin/env python3
"""
JSON/XML Export Service - Main Application

This service provides comprehensive JSON and XML data export capabilities
for the Splunk MCP Integration platform with advanced formatting options.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from structlog import get_logger

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import configure_logging
from app.core.redis_client import init_redis, close_redis
from app.utils.rate_limiter import RateLimitHeadersMiddleware

# Configure logging first
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting JSON/XML Export Service...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized")
        
        logger.info("JSON/XML Export Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down JSON/XML Export Service...")
        await close_db()
        await close_redis()
        logger.info("JSON/XML Export Service shut down complete")


# Create FastAPI application
app = FastAPI(
    title="JSON/XML Export Service",
    description="Advanced JSON and XML data export service for Splunk MCP Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting headers middleware
app.add_middleware(RateLimitHeadersMiddleware)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 Not Found handler."""
    logger.warning(
        "Endpoint not found",
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "message": "Endpoint not found",
            "path": request.url.path
        }
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "JSON/XML Export Service",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Advanced JSON and XML data export service for Splunk MCP Integration"
    }


# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        from app.core.database import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        
        # Test Redis connection
        from app.core.redis_client import get_redis
        redis_client = get_redis()
        await redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "json-xml-export-service",
            "version": "1.0.0",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "json-xml-export-service",
                "version": "1.0.0",
                "error": str(e)
            }
        )


# Readiness probe endpoint
@app.get("/ready", include_in_schema=False)
async def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    return {
        "status": "ready",
        "service": "json-xml-export-service"
    }


# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        from app.core.redis_client import get_cache_manager, get_queue_manager
        
        # Get basic metrics
        cache_manager = get_cache_manager()
        queue_manager = get_queue_manager()
        
        # Get queue sizes
        queue_sizes = await queue_manager.get_queue_size()
        
        # Basic metrics (in a real implementation, use prometheus_client)
        metrics_data = {
            "json_xml_export_queue_pending": queue_sizes.get("pending", 0),
            "json_xml_export_queue_processing": queue_sizes.get("processing", 0),
            "json_xml_export_queue_total": queue_sizes.get("total", 0),
            "json_xml_export_service_healthy": 1
        }
        
        return {"metrics": metrics_data}
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Metrics collection failed"}
        )


# Info endpoint
@app.get("/info", include_in_schema=False)
async def service_info():
    """Service information endpoint."""
    return {
        "service": "json-xml-export-service",
        "version": "1.0.0",
        "description": "Advanced JSON and XML data export service",
        "features": [
            "High-performance JSON generation",
            "Professional XML generation with validation",
            "Advanced formatting options",
            "Custom schema support",
            "Flexible structure configuration",
            "Data transformation capabilities",
            "Large dataset handling",
            "Performance optimization"
        ],
        "supported_formats": ["json", "xml", "jsonl", "custom-json", "custom-xml"],
        "supported_encodings": ["utf-8", "utf-16", "latin-1", "ascii"],
        "configuration": {
            "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "rate_limit_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        }
    }


# Include routers
app.include_router(
    v1_router,
    prefix="/api/v1",
    tags=["JSON/XML Export"]
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )