"""
PDF Export Service - FastAPI Application

A comprehensive PDF generation service for the Splunk MCP platform,
providing advanced PDF creation with custom layouts, chart embedding,
and enterprise-grade security.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import uvicorn
import structlog
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import create_db_pool, close_db_pool
from app.core.redis_client import create_redis_pool, close_redis_pool
from app.api.v1.router import api_router
from app.utils.auth import verify_token
from app.utils.metrics import setup_metrics
from app.utils.rate_limiter import RateLimiter

# Initialize structured logging
logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('pdf_export_requests_total', 'Total PDF export requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('pdf_export_request_duration_seconds', 'PDF export request duration')
ACTIVE_CONNECTIONS = Gauge('pdf_export_active_connections', 'Active PDF export connections')
PDF_GENERATION_COUNT = Counter('pdf_export_generation_total', 'Total PDF generations', ['template_type', 'status'])
PDF_GENERATION_DURATION = Histogram('pdf_export_generation_duration_seconds', 'PDF generation duration', ['template_type'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler."""
    logger.info("Starting PDF Export Service")
    
    # Initialize database pool
    await create_db_pool()
    logger.info("Database pool created")
    
    # Initialize Redis pool
    await create_redis_pool()
    logger.info("Redis pool created")
    
    # Start Prometheus metrics server
    if settings.METRICS_ENABLED:
        start_http_server(settings.METRICS_PORT)
        logger.info(f"Prometheus metrics server started on port {settings.METRICS_PORT}")
    
    # Setup rate limiter
    app.state.rate_limiter = RateLimiter()
    
    logger.info("PDF Export Service startup complete")
    yield
    
    # Cleanup
    logger.info("Shutting down PDF Export Service")
    await close_db_pool()
    await close_redis_pool()
    logger.info("PDF Export Service shutdown complete")

def create_app() -> FastAPI:
    """Create FastAPI application with all configuration."""
    
    # Setup logging
    setup_logging()
    
    # Create FastAPI app
    app = FastAPI(
        title="PDF Export Service",
        description="Advanced PDF generation service for Splunk MCP platform",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Add middleware for metrics and request tracking
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add request processing time and metrics."""
        start_time = asyncio.get_event_loop().time()
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = await call_next(request)
            process_time = asyncio.get_event_loop().time() - start_time
            
            # Add headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Service-Name"] = "pdf-export-service"
            
            # Update metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            REQUEST_DURATION.observe(process_time)
            
            return response
        except Exception as e:
            process_time = asyncio.get_event_loop().time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            REQUEST_DURATION.observe(process_time)
            raise
        finally:
            ACTIVE_CONNECTIONS.dec()
    
    # Add rate limiting middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Rate limiting middleware."""
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/health/detailed", "/metrics"]:
            return await call_next(request)
        
        # Extract user ID from token
        user_id = None
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                user_id = payload.get("sub")
        except Exception:
            pass
        
        # Apply rate limiting
        if user_id:
            rate_limiter = request.app.state.rate_limiter
            is_allowed = await rate_limiter.is_allowed(
                user_id,
                limit=settings.RATE_LIMIT_DEFAULT_LIMIT,
                window=settings.RATE_LIMIT_DEFAULT_WINDOW
            )
            
            if not is_allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"}
                )
        
        return await call_next(request)
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_PREFIX)
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check."""
        return {"status": "healthy", "service": "pdf-export-service", "version": "1.0.0"}
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with dependency status."""
        from app.core.database import get_db_pool
        from app.core.redis_client import get_redis_pool
        
        health_status = {
            "status": "healthy",
            "service": "pdf-export-service",
            "version": "1.0.0",
            "dependencies": {}
        }
        
        # Check database
        try:
            db_pool = get_db_pool()
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                health_status["dependencies"]["database"] = "healthy"
            else:
                health_status["dependencies"]["database"] = "unhealthy"
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Check Redis
        try:
            redis_pool = get_redis_pool()
            if redis_pool:
                await redis_pool.ping()
                health_status["dependencies"]["redis"] = "healthy"
            else:
                health_status["dependencies"]["redis"] = "unhealthy"
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"
        
        return health_status
    
    # Error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        logger.error("Validation error", request=request.url.path, errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "errors": [{"code": "VALIDATION_ERROR", "message": "Invalid input parameters", "details": exc.errors()}]
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.error("HTTP error", request=request.url.path, status_code=exc.status_code, detail=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "errors": [{"code": "HTTP_ERROR", "message": exc.detail}]
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error("Unexpected error", request=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "errors": [{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}]
            }
        )
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.DEBUG,
        access_log=True,
        log_config=None,  # Use our custom logging configuration
    )