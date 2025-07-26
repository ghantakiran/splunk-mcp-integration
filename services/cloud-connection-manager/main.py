"""
Cloud Connection Manager Service
Handles dynamic endpoint routing, connection pooling, and health monitoring
for Splunk Enterprise and Cloud instances.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_db, close_db
from app.core.redis_client import init_redis, close_redis
from app.api.v1.router import api_router
from app.services.health_monitor import HealthMonitor
from app.services.connection_pool_manager import ConnectionPoolManager
from app.services.metrics_collector import MetricsCollector

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Global service instances
health_monitor: HealthMonitor = None
connection_pool_manager: ConnectionPoolManager = None
metrics_collector: MetricsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global health_monitor, connection_pool_manager, metrics_collector
    
    logger.info("Starting Cloud Connection Manager Service...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized successfully")
        
        # Initialize connection pool manager
        connection_pool_manager = ConnectionPoolManager()
        await connection_pool_manager.initialize()
        logger.info("Connection pool manager initialized")
        
        # Initialize health monitor
        health_monitor = HealthMonitor(connection_pool_manager)
        await health_monitor.start()
        logger.info("Health monitor started")
        
        # Initialize metrics collector
        metrics_collector = MetricsCollector(connection_pool_manager, health_monitor)
        await metrics_collector.start()
        logger.info("Metrics collector started")
        
        # Store instances in app state
        app.state.health_monitor = health_monitor
        app.state.connection_pool_manager = connection_pool_manager
        app.state.metrics_collector = metrics_collector
        
        logger.info("Cloud Connection Manager Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Cloud Connection Manager Service...")
        
        try:
            if metrics_collector:
                await metrics_collector.stop()
                logger.info("Metrics collector stopped")
            
            if health_monitor:
                await health_monitor.stop()
                logger.info("Health monitor stopped")
            
            if connection_pool_manager:
                await connection_pool_manager.cleanup()
                logger.info("Connection pool manager cleaned up")
            
            # Close Redis connection
            await close_redis()
            logger.info("Redis connection closed")
            
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
        
        logger.info("Cloud Connection Manager Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Cloud Connection Manager Service",
    description="Dynamic endpoint routing, connection pooling, and health monitoring for Splunk instances",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add correlation ID to all requests."""
    import uuid
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Add to response headers
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    start_time = asyncio.get_event_loop().time()
    
    logger.info(
        f"Request started",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    logger.info(
        f"Request completed",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4)
        }
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url)
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "correlation_id": correlation_id,
            "error_code": "INTERNAL_ERROR"
        }
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "Cloud Connection Manager",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "health_url": "/api/v1/health"
    }


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    """OpenAPI schema endpoint."""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "cloud-connection-manager",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )