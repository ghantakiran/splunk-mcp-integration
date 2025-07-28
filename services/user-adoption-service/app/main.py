#!/usr/bin/env python3
"""
User Adoption and Feedback Collection Service
============================================
Comprehensive service for tracking user onboarding, adoption metrics, and feedback collection
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db, close_db, get_db
from app.core.logging_config import setup_logging
from app.api.v1.endpoints import adoption, feedback, analytics, onboarding
from app.utils.auth import get_current_user
from app.utils.rate_limiter import RateLimiter

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting User Adoption Service...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down User Adoption Service...")
    await close_db()
    logger.info("Database connections closed")

# Create FastAPI application
app = FastAPI(
    title="User Adoption and Feedback Collection Service",
    description="Comprehensive service for tracking user onboarding, adoption metrics, and feedback collection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
rate_limiter = RateLimiter()
app.add_middleware(rate_limiter.middleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-adoption-service",
        "version": "1.0.0",
        "timestamp": asyncio.get_event_loop().time()
    }

# API Routes
app.include_router(
    onboarding.router,
    prefix="/api/v1/onboarding",
    tags=["onboarding"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    adoption.router,
    prefix="/api/v1/adoption",
    tags=["adoption"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    feedback.router,
    prefix="/api/v1/feedback",
    tags=["feedback"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)]
)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error"
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )