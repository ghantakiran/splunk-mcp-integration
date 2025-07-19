#!/usr/bin/env python3
"""
Word Export Service - Main Application

This service provides Word document generation capabilities
for the Splunk MCP Integration platform.
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

from app.api.v1.endpoints.word_export import router as word_export_router
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
    logger.info("Starting Word Export Service...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized")
        
        logger.info("Word Export Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Word Export Service...")
        await close_db()
        await close_redis()
        logger.info("Word Export Service shut down complete")


# Create FastAPI application
app = FastAPI(
    title="Word Export Service",
    description="Word document generation service for Splunk MCP Integration",
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
        "service": "Word Export Service",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Word document generation service for Splunk MCP Integration"
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
            "service": "word-export-service",
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
                "service": "word-export-service",
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
        "service": "word-export-service"
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
            "word_export_queue_pending": queue_sizes["pending"],
            "word_export_queue_processing": queue_sizes["processing"],
            "word_export_queue_total": queue_sizes["total"],
            "word_export_service_healthy": 1
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
        "service": "word-export-service",
        "version": "1.0.0",
        "description": "Word document generation service",
        "features": [
            "Professional Word document generation",
            "Custom templates and themes",
            "Chart and table embedding",
            "Advanced formatting and styling",
            "Header and footer customization",
            "Page layout management",
            "Table of contents generation",
            "Watermark and branding support"
        ],
        "supported_formats": ["docx"],
        "supported_templates": ["professional", "corporate", "academic", "report", "minimal"],
        "configuration": {
            "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
            "max_file_size_mb": settings.WORD_MAX_FILE_SIZE_MB,
            "rate_limit_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        }
    }


# Include routers
app.include_router(
    word_export_router,
    prefix="/api/v1/word-export",
    tags=["Word Export"]
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )