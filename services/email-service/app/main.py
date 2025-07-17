"""
Email Service - FastAPI Application.

This service provides comprehensive email integration for the Splunk MCP platform,
enabling natural language queries via email, automated reports, and alert notifications.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.logging import get_logger, add_correlation_id, add_request_context
from app.api import health, emails, reports, users, subscriptions
from app.services.database_service import DatabaseService
from app.services.redis_service import RedisService
from app.services.email_processor import EmailProcessor
from app.services.report_generator import ReportGenerator
from app.utils.auth import verify_jwt_token
from app.utils.rate_limiter import RateLimiter
from app.utils.metrics import setup_metrics, get_metrics_registry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    logger.info("Starting Email Service", version=settings.version)
    
    # Initialize services
    try:
        # Initialize database
        db_service = DatabaseService()
        await db_service.initialize()
        app.state.db = db_service
        
        # Initialize Redis
        redis_service = RedisService()
        await redis_service.initialize()
        app.state.redis = redis_service
        
        # Initialize rate limiter
        rate_limiter = RateLimiter(redis_service)
        app.state.rate_limiter = rate_limiter
        
        # Initialize email processor
        email_processor = EmailProcessor(db_service, redis_service)
        await email_processor.initialize()
        app.state.email_processor = email_processor
        
        # Initialize report generator
        report_generator = ReportGenerator(db_service, redis_service)
        await report_generator.initialize()
        app.state.report_generator = report_generator
        
        # Setup metrics
        metrics_registry = setup_metrics()
        app.state.metrics = metrics_registry
        
        # Start background tasks if enabled
        if settings.enable_imap_processing:
            task = asyncio.create_task(email_processor.start_imap_processing())
            app.state.imap_task = task
        
        logger.info("Email Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start Email Service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Email Service")
    
    try:
        # Stop background tasks
        if hasattr(app.state, 'imap_task'):
            app.state.imap_task.cancel()
            try:
                await app.state.imap_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup services
        if hasattr(app.state, 'email_processor'):
            await app.state.email_processor.cleanup()
        
        if hasattr(app.state, 'report_generator'):
            await app.state.report_generator.cleanup()
        
        if hasattr(app.state, 'redis'):
            await app.state.redis.cleanup()
        
        if hasattr(app.state, 'db'):
            await app.state.db.cleanup()
        
        logger.info("Email Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Email integration service for Splunk MCP platform",
    version=settings.version,
    openapi_url="/openapi.json" if settings.debug else None,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Add request logging and correlation ID."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Add correlation ID to response headers
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    # Log request
    logger.info(
        "Request processed",
        **add_correlation_id(correlation_id),
        **add_request_context(
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        ),
        status_code=response.status_code,
    )
    
    return response


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unhandled error",
            error=str(e),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "details": str(e) if settings.debug else None,
                },
                "metadata": {
                    "timestamp": "2025-01-16T10:30:00Z",
                    "correlation_id": request.headers.get("X-Correlation-ID"),
                    "version": settings.version,
                },
            },
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "correlation_id": request.headers.get("X-Correlation-ID"),
                "version": settings.version,
            },
        },
    )


# Dependency providers
async def get_database() -> DatabaseService:
    """Get database service dependency."""
    return app.state.db


async def get_redis() -> RedisService:
    """Get Redis service dependency."""
    return app.state.redis


async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter dependency."""
    return app.state.rate_limiter


async def get_email_processor() -> EmailProcessor:
    """Get email processor dependency."""
    return app.state.email_processor


async def get_report_generator() -> ReportGenerator:
    """Get report generator dependency."""
    return app.state.report_generator


async def get_current_user(
    request: Request,
    db: DatabaseService = Depends(get_database),
):
    """Get current authenticated user."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        payload = verify_jwt_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Get user from database
        user = await db.get_user(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        return user
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# API Routes
app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

app.include_router(
    emails.router,
    prefix="/emails",
    tags=["Emails"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=["Subscriptions"],
    dependencies=[Depends(get_current_user)],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "healthy",
        "timestamp": "2025-01-16T10:30:00Z",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    registry = app.state.metrics
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/webhooks/email")
async def email_webhook(
    request: Request,
    email_processor: EmailProcessor = Depends(get_email_processor),
):
    """Handle incoming email webhooks."""
    try:
        # Parse webhook payload
        payload = await request.json()
        
        # Process webhook
        result = await email_processor.process_webhook(payload)
        
        return {
            "success": True,
            "data": result,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "correlation_id": request.headers.get("X-Correlation-ID"),
            },
        }
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.post("/process/email")
async def process_email_query(
    query_data: Dict[str, Any],
    email_processor: EmailProcessor = Depends(get_email_processor),
    current_user = Depends(get_current_user),
):
    """Process email query manually."""
    try:
        result = await email_processor.process_query_email(
            query_data,
            current_user.id,
        )
        
        return {
            "success": True,
            "data": result,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "query_id": result.get("query_id"),
            },
        }
    except Exception as e:
        logger.error("Email query processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Email query processing failed")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )