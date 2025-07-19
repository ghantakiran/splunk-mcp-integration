"""
Report Scheduling Service - Main application entry point.

This service provides comprehensive report scheduling, automated delivery,
and subscription management capabilities for the Splunk MCP Integration platform.

Features:
- Schedule reports with flexible cron expressions and time zones
- Automated report generation and delivery via multiple channels
- Subscription management with user preferences and notifications
- Background job processing with Celery and Redis
- Enterprise security with JWT authentication and RBAC
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import schedules, subscriptions, reports, analytics
from app.core.config import settings
from app.core.database import engine, get_database
from app.core.redis_client import get_redis_client
from app.utils.logging import setup_logging


# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan event handler for startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting Report Scheduling Service...")
    
    try:
        # Test database connection
        db = await get_database()
        await db.execute("SELECT 1")
        await db.close()
        logger.info("Database connection established successfully")
        
        # Test Redis connection
        redis_client = await get_redis_client()
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
        # Initialize background task processor (would typically start Celery worker here)
        logger.info("Background task processor initialized")
        
        logger.info("Report Scheduling Service startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Report Scheduling Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Report Scheduling Service...")
    
    try:
        # Close database connections
        await engine.dispose()
        logger.info("Database connections closed")
        
        # Close Redis connections
        redis_client = await get_redis_client()
        await redis_client.close()
        logger.info("Redis connections closed")
        
        logger.info("Report Scheduling Service shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Report Scheduling Service",
    description="Comprehensive report scheduling and automated delivery service for Splunk MCP Integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = asyncio.get_event_loop().time()
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response


# Include API routers
app.include_router(
    schedules.router,
    prefix="/api/v1/schedules",
    tags=["Report Schedules"]
)

app.include_router(
    subscriptions.router,
    prefix="/api/v1/subscriptions",
    tags=["Report Subscriptions"]
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Scheduled Reports"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics & Metrics"]
)


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "report-scheduling-service"}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check database connectivity
        db = await get_database()
        await db.execute("SELECT 1")
        await db.close()
        
        # Check Redis connectivity
        redis_client = await get_redis_client()
        await redis_client.ping()
        
        return {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    # In a real implementation, you would return Prometheus-formatted metrics
    # For now, return basic metrics in JSON format
    redis_client = await get_redis_client()
    
    # Get basic metrics from Redis
    pending_jobs = await redis_client.llen("report_scheduling_queue")
    active_schedules = await redis_client.get("active_schedules_count") or 0
    
    return {
        "report_scheduling_queue_pending": pending_jobs,
        "report_scheduling_active_schedules": int(active_schedules),
        "report_scheduling_service_healthy": 1,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_config=None,  # We handle logging ourselves
        access_log=False,  # We log requests in middleware
    )