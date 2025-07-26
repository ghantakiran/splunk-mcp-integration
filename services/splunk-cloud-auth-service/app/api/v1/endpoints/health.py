"""
Health check endpoints for Splunk Cloud Authentication Service
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and Redis connectivity"""
    
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database health check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Redis health check
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # OAuth configuration check
    oauth_healthy = True
    oauth_messages = []
    
    if not settings.oauth_client_id:
        oauth_healthy = False
        oauth_messages.append("OAuth client ID not configured")
    
    if not settings.oauth_client_secret:
        oauth_healthy = False
        oauth_messages.append("OAuth client secret not configured")
    
    health_status["checks"]["oauth_config"] = {
        "status": "healthy" if oauth_healthy else "warning",
        "message": "OAuth configuration complete" if oauth_healthy else "; ".join(oauth_messages)
    }
    
    # JWT configuration check
    jwt_healthy = True
    jwt_messages = []
    
    if settings.jwt_secret_key == "your-secret-key":
        jwt_healthy = False
        jwt_messages.append("JWT secret key using default value")
    
    health_status["checks"]["jwt_config"] = {
        "status": "healthy" if jwt_healthy else "warning",
        "message": "JWT configuration secure" if jwt_healthy else "; ".join(jwt_messages)
    }
    
    # Update overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    elif not oauth_healthy or not jwt_healthy:
        health_status["status"] = "warning"
    
    # Return appropriate HTTP status
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe endpoint"""
    
    try:
        # Check database connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        # Check Redis connectivity
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "not_ready",
                "error": str(e)
            }
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}