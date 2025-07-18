"""
BI Integration Service - FastAPI application entry point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import uvicorn

from app.core.config import settings
from app.core.database import init_database, close_database
from app.core.redis_client import init_redis, close_redis
from app.core.logging import setup_logging, get_logger
from app.api.v1.router import api_router
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "bi_integration_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "bi_integration_request_duration_seconds",
    "Time spent processing HTTP requests",
    ["method", "endpoint"]
)

ACTIVE_CONNECTIONS = Gauge(
    "bi_integration_active_connections",
    "Number of active connections"
)

BI_INTEGRATIONS = Gauge(
    "bi_integration_total_integrations",
    "Total number of BI integrations"
)

TABLEAU_CONNECTIONS = Gauge(
    "bi_integration_tableau_connections",
    "Number of active Tableau connections"
)

POWERBI_CONNECTIONS = Gauge(
    "bi_integration_powerbi_connections",
    "Number of active Power BI connections"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting BI Integration Service")
    
    # Initialize database
    logger.info("Initializing database connection")
    await init_database()
    
    # Initialize Redis
    logger.info("Initializing Redis connection")
    await init_redis()
    
    # Log startup configuration
    logger.info(
        "BI Integration Service started successfully",
        extra={
            "environment": settings.environment,
            "debug": settings.debug,
            "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "***",
            "redis_url": settings.redis_url.split("@")[-1] if "@" in settings.redis_url else "***",
            "api_version": settings.api_version,
            "cors_origins": settings.cors_origins
        }
    )
    
    yield
    
    # Shutdown procedures
    logger.info("Shutting down BI Integration Service")
    
    # Close database connections
    logger.info("Closing database connections")
    await close_database()
    
    # Close Redis connections
    logger.info("Closing Redis connections")
    await close_redis()
    
    logger.info("BI Integration Service stopped successfully")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Business Intelligence Integration Service for Splunk MCP",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)

# Add rate limiting middleware if enabled
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)

# Add Prometheus metrics endpoint
if settings.metrics_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time and metrics."""
    import time
    
    start_time = time.time()
    
    # Increment active connections
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        process_time = time.time() - start_time
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # Record error metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=500
        ).inc()
        
        logger.error(
            f"Request processing error: {e}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e)
            }
        )
        
        raise
        
    finally:
        # Decrement active connections
        ACTIVE_CONNECTIONS.dec()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTP_EXCEPTION"
            },
            "metadata": {
                "timestamp": "2025-01-18T10:30:00Z",
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "version": settings.app_version
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "error": str(exc),
            "error_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error" if not settings.debug else str(exc),
                "type": "INTERNAL_SERVER_ERROR"
            },
            "metadata": {
                "timestamp": "2025-01-18T10:30:00Z",
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                "version": settings.app_version
            }
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": "2025-01-18T10:30:00Z"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint."""
    from app.core.database import get_database_health
    from app.core.redis_client import get_redis_health
    
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {},
        "timestamp": "2025-01-18T10:30:00Z"
    }
    
    # Check database health
    try:
        db_health = await get_database_health()
        health_status["components"]["database"] = db_health
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Redis health
    try:
        redis_health = await get_redis_health()
        health_status["components"]["redis"] = redis_health
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    return health_status


@app.get("/info")
async def service_info():
    """Service information endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "api_version": settings.api_version,
        "features": {
            "tableau_integration": True,
            "powerbi_integration": True,
            "metrics_enabled": settings.metrics_enabled,
            "rate_limiting": settings.rate_limit_enabled,
            "debug": settings.debug
        },
        "supported_providers": ["tableau", "powerbi", "looker", "qlik"],
        "timestamp": "2025-01-18T10:30:00Z"
    }


def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        Business Intelligence Integration Service for Splunk MCP
        
        This service provides seamless integration with popular BI tools including:
        - Tableau Server
        - Microsoft Power BI
        - Looker (coming soon)
        - Qlik (coming soon)
        
        ## Features
        - Natural language query integration
        - Automated data source management
        - Real-time data refresh
        - Secure authentication and authorization
        - Comprehensive monitoring and logging
        
        ## Authentication
        All endpoints require JWT authentication. Include the token in the Authorization header:
        ```
        Authorization: Bearer <your_jwt_token>
        ```
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8008,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True,
    )