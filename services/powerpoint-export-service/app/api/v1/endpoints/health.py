#!/usr/bin/env python3
"""
Health check endpoints for PowerPoint Export Service.

This module provides health check endpoints for monitoring the service
and its dependencies.
"""

from fastapi import APIRouter, HTTPException
from structlog import get_logger

from app.core.database import get_db_connection
from app.core.redis_client import get_redis_connection


logger = get_logger(__name__)
router = APIRouter()


@router.get("/", summary="Basic health check")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "powerpoint-export-service",
        "version": "1.0.0"
    }


@router.get("/detailed", summary="Detailed health check with dependencies")
async def detailed_health_check():
    """Detailed health check including dependency status."""
    health_status = {
        "status": "healthy",
        "service": "powerpoint-export-service",
        "version": "1.0.0",
        "dependencies": {}
    }
    
    # Check database connection
    try:
        async with get_db_connection() as conn:
            await conn.execute("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        async with get_redis_connection() as redis:
            await redis.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready", summary="Readiness probe")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check if service is ready to accept requests
        async with get_db_connection() as conn:
            await conn.execute("SELECT 1")
        
        async with get_redis_connection() as redis:
            await redis.ping()
        
        return {"status": "ready"}
    
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail={"status": "not ready", "error": str(e)})


@router.get("/live", summary="Liveness probe")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}
