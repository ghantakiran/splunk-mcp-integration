"""
FastAPI application for NLP Engine service
"""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .api.v1.endpoints import router as v1_router
from .api.v1.context_endpoints import router as context_router


# Configure logging before importing other modules
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting NLP Engine service", version=settings.app_version)
    
    # Startup tasks
    try:
        # Initialize AI providers
        from .ai import ai_manager
        available_providers = list(ai_manager.providers.keys())
        logger.info(f"Initialized AI providers: {available_providers}")
        
        # Perform any other startup tasks here
        logger.info("NLP Engine service startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down NLP Engine service")


# Create FastAPI application
app = FastAPI(
    title="Splunk MCP NLP Engine",
    description="Natural Language Processing service for Splunk MCP integration",
    version=settings.app_version,
    openapi_url=settings.openapi_url,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add trusted host middleware for security
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*"]
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log HTTP requests and responses"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "HTTP request started",
        method=request.method,
        path=request.url.path,
        query_params=str(request.url.query) if request.url.query else None,
        client_ip=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "HTTP request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "HTTP request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            process_time=process_time
        )
        raise


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": time.time()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error" if settings.is_production else str(exc),
                "timestamp": time.time()
            }
        }
    )


# Include API routers
app.include_router(
    v1_router,
    prefix=settings.api_v1_prefix,
    tags=["v1"]
)

app.include_router(
    context_router,
    prefix=settings.api_v1_prefix,
    tags=["context"]
)

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with service information"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "docs_url": "/docs",
        "openapi_url": settings.openapi_url
    }


@app.get("/ping", tags=["System"])
async def ping() -> Dict[str, str]:
    """Simple ping endpoint for health monitoring"""
    return {"status": "pong", "timestamp": str(time.time())}


if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload_on_change and settings.is_development,
        log_level=settings.log_level.lower(),
        access_log=True
    )