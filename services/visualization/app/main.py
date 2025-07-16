"""
Visualization Service Main Application

FastAPI application for the Splunk MCP Visualization Service that provides
intelligent chart generation, dashboard creation, and data visualization
capabilities with automatic chart type selection.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .api.v1 import endpoints

# Configure logging
configure_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Intelligent visualization service for Splunk MCP integration",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        """Add correlation ID to all requests"""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        
        # Add to logger context
        logger._correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests and responses"""
        start_time = time.time()
        
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler"""
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method,
            correlation_id=correlation_id,
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "correlation_id": correlation_id,
                "detail": str(exc) if settings.debug else "An unexpected error occurred"
            }
        )
    
    # Include routers
    app.include_router(
        endpoints.router,
        prefix=settings.api_v1_prefix,
        tags=["visualization"]
    )
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Application startup event"""
        logger.info(
            "Visualization service starting up",
            version=settings.app_version,
            debug=settings.debug,
            environment="development" if settings.debug else "production"
        )
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event"""
        logger.info("Visualization service shutting down")
    
    return app


# Create application instance
app = create_application()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "visualization",
        "version": settings.app_version,
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": f"{settings.api_v1_prefix}/docs"
    }