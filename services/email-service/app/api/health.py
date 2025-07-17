"""
Health check API endpoints.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.services.database_service import DatabaseService
from app.services.redis_service import RedisService

logger = get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]


class DependencyStatus(BaseModel):
    """Dependency status model."""
    status: str
    response_time_ms: float
    error: str = None


async def check_database_health() -> DependencyStatus:
    """Check database health."""
    start_time = datetime.utcnow()
    try:
        # Simple database query to test connectivity
        from sqlalchemy import text
        db = DatabaseService()
        if db.engine:
            async with db.get_session() as session:
                await session.execute(text("SELECT 1"))
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return DependencyStatus(
                status="healthy",
                response_time_ms=response_time,
            )
        else:
            return DependencyStatus(
                status="unhealthy",
                response_time_ms=0,
                error="Database not initialized",
            )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return DependencyStatus(
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e),
        )


async def check_redis_health() -> DependencyStatus:
    """Check Redis health."""
    start_time = datetime.utcnow()
    try:
        redis = RedisService()
        if redis.client:
            await redis.client.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return DependencyStatus(
                status="healthy",
                response_time_ms=response_time,
            )
        else:
            return DependencyStatus(
                status="unhealthy",
                response_time_ms=0,
                error="Redis not initialized",
            )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return DependencyStatus(
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e),
        )


async def check_smtp_health() -> DependencyStatus:
    """Check SMTP server health."""
    start_time = datetime.utcnow()
    try:
        import aiosmtplib
        from app.core.config import get_smtp_config
        
        smtp_config = get_smtp_config()
        smtp = aiosmtplib.SMTP(
            hostname=smtp_config["hostname"],
            port=smtp_config["port"],
            use_tls=smtp_config["use_tls"],
            timeout=5,  # Short timeout for health check
        )
        
        await smtp.connect()
        await smtp.quit()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return DependencyStatus(
            status="healthy",
            response_time_ms=response_time,
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return DependencyStatus(
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e),
        )


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check all dependencies
        db_health = await check_database_health()
        redis_health = await check_redis_health()
        smtp_health = await check_smtp_health()
        
        # Determine overall status
        dependencies = {
            "database": db_health.dict(),
            "redis": redis_health.dict(),
            "smtp": smtp_health.dict(),
        }
        
        overall_status = "healthy"
        for dep_name, dep_status in dependencies.items():
            if dep_status["status"] != "healthy":
                overall_status = "degraded"
                break
        
        # Get basic metrics
        metrics = {
            "uptime_seconds": 0,  # Would need to track app start time
            "memory_usage_mb": 0,  # Would use psutil
            "cpu_usage_percent": 0,  # Would use psutil
        }
        
        return HealthResponse(
            status=overall_status,
            version=settings.version,
            timestamp=datetime.utcnow(),
            dependencies=dependencies,
            metrics=metrics,
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Quick checks for critical dependencies
        db_health = await check_database_health()
        redis_health = await check_redis_health()
        
        if db_health.status == "healthy" and redis_health.status == "healthy":
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
            
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/dependencies")
async def dependencies_status():
    """Detailed dependency status endpoint."""
    try:
        dependencies = {
            "database": (await check_database_health()).dict(),
            "redis": (await check_redis_health()).dict(),
            "smtp": (await check_smtp_health()).dict(),
        }
        
        return {
            "dependencies": dependencies,
            "timestamp": datetime.utcnow(),
        }
        
    except Exception as e:
        logger.error("Dependencies check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Dependencies check failed")