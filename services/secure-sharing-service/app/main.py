"""
Main FastAPI application for the Secure Sharing Service.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from app.core.config import settings
from app.core.database import create_tables, drop_tables
from app.api.v1.endpoints import shares
from app.utils.rate_limiter import rate_limiter, cleanup_expired_rate_limits
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Secure Sharing Service", version=settings.VERSION)
    
    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise
    
    # Initialize background tasks if enabled
    if settings.BACKGROUND_TASKS_ENABLED:
        logger.info("Background tasks enabled")
        # In a real implementation, you would start background tasks here
    
    yield
    
    # Shutdown
    logger.info("Shutting down Secure Sharing Service")
    
    # Close rate limiter connection
    try:
        await rate_limiter.close()
        logger.info("Rate limiter connection closed")
    except Exception as e:
        logger.error("Error closing rate limiter", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Add trusted host middleware
if settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests with correlation ID."""
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    # Start timer
    start_time = time.time()
    
    # Extract user info if available
    user_id = None
    try:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from app.utils.auth import verify_token
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            user_id = payload.get("sub") or payload.get("user_id")
    except Exception:
        pass  # No user authentication
    
    # Log request
    logger.info(
        "HTTP request started",
        correlation_id=correlation_id,
        method=request.method,
        url=str(request.url),
        user_id=user_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "HTTP request completed",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            user_id=user_id
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
        
    except Exception as e:
        # Calculate duration
        duration = time.time() - start_time
        
        # Log error
        logger.error(
            "HTTP request failed",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            duration_ms=round(duration * 1000, 2),
            error=str(e),
            user_id=user_id
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "correlation_id": correlation_id
            },
            headers={"X-Correlation-ID": correlation_id}
        )


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    # HSTS header for HTTPS
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# Include API routers
app.include_router(
    shares.router,
    prefix=f"{settings.API_V1_STR}/shares",
    tags=["shares"]
)


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": time.time()
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    # Check database connection
    try:
        from app.core.database import get_database
        db = await get_database()
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_status = "unhealthy"
    
    # Check Redis connection
    try:
        redis_client = await rate_limiter.get_redis()
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        redis_status = "unhealthy"
    
    # Overall status
    is_ready = db_status == "healthy" and redis_status == "healthy"
    
    response_data = {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": {
            "database": db_status,
            "redis": redis_status
        },
        "timestamp": time.time()
    }
    
    if not is_ready:
        return JSONResponse(
            status_code=503,
            content=response_data
        )
    
    return response_data


# Metrics endpoint for Prometheus
if settings.METRICS_ENABLED:
    @app.get("/metrics", tags=["monitoring"])
    async def metrics():
        """Prometheus metrics endpoint."""
        # In a real implementation, you would use prometheus_client
        # For now, return basic metrics in text format
        metrics_data = f"""
# HELP secure_sharing_requests_total Total number of HTTP requests
# TYPE secure_sharing_requests_total counter
secure_sharing_requests_total 1

# HELP secure_sharing_request_duration_seconds Request duration in seconds
# TYPE secure_sharing_request_duration_seconds histogram
secure_sharing_request_duration_seconds_bucket{{le="0.1"}} 1
secure_sharing_request_duration_seconds_bucket{{le="0.5"}} 1
secure_sharing_request_duration_seconds_bucket{{le="1.0"}} 1
secure_sharing_request_duration_seconds_bucket{{le="+Inf"}} 1
secure_sharing_request_duration_seconds_count 1
secure_sharing_request_duration_seconds_sum 0.1

# HELP secure_sharing_shares_total Total number of shares created
# TYPE secure_sharing_shares_total counter
secure_sharing_shares_total 0

# HELP secure_sharing_share_accesses_total Total number of share accesses
# TYPE secure_sharing_share_accesses_total counter
secure_sharing_share_accesses_total 0
"""
        return Response(
            content=metrics_data,
            media_type="text/plain"
        )


# API information endpoint
@app.get(f"{settings.API_V1_STR}/info", tags=["info"])
async def api_info():
    """Get API information and capabilities."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "api_version": "v1",
        "features": {
            "share_creation": True,
            "password_protection": True,
            "domain_restrictions": True,
            "user_allowlists": True,
            "expiration_policies": [
                "never",
                "after_time",
                "after_views",
                "after_downloads",
                "combined"
            ],
            "access_methods": [
                "link",
                "token",
                "email_invite",
                "embedded"
            ],
            "supported_resource_types": [
                "report",
                "dashboard",
                "chart",
                "query_result",
                "schedule",
                "dataset"
            ],
            "permissions": [
                "view",
                "download",
                "interact",
                "comment",
                "edit"
            ]
        },
        "limits": {
            "max_shares_per_user": settings.MAX_SHARES_PER_USER,
            "max_share_duration_days": settings.MAX_SHARE_DURATION_DAYS,
            "default_expiration_hours": settings.DEFAULT_EXPIRATION_HOURS,
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB
        },
        "endpoints": {
            "documentation": f"{settings.API_V1_STR}/docs",
            "openapi": f"{settings.API_V1_STR}/openapi.json",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics" if settings.METRICS_ENABLED else None
        }
    }


# Root endpoint
@app.get("/", tags=["info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "api_docs": f"{settings.API_V1_STR}/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )