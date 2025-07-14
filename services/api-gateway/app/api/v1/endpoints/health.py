"""
Health check endpoints for system monitoring and diagnostics
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from datetime import datetime
import asyncio
import aiohttp
import time
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from ....core.config import settings
from ....core.logging import get_logger
from ....api.deps import get_async_session, get_redis
from ....models.responses import HealthCheckResponse, StatusResponse, COMMON_RESPONSES

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/status", 
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic system status and availability",
    responses={
        200: {"description": "System is healthy"},
        503: {"description": "System is unavailable", "model": StatusResponse}
    }
)
async def health_check() -> StatusResponse:
    """
    Basic health check endpoint
    
    Returns simple status information for basic monitoring.
    Use `/health/detailed` for comprehensive health information.
    """
    return StatusResponse(
        status="healthy",
        message=f"API Gateway v{settings.app_version} is running normally",
        timestamp=datetime.utcnow()
    )


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Detailed health check with dependency status"""
    
    health_status = {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "dependencies": {}
    }
    
    overall_healthy = True
    
    # Check database connection
    try:
        await db.execute("SELECT 1")
        health_status["dependencies"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # Could add actual timing
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check Redis connection
    try:
        await redis_client.ping()
        health_status["dependencies"]["redis"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check microservices
    services_to_check = [
        ("nlp_engine", settings.nlp_engine_url),
        ("spl_translator", settings.spl_translator_url),
        ("access_control", settings.access_control_url),
        ("visualization", settings.visualization_url),
        ("alert_manager", settings.alert_manager_url),
    ]
    
    async def check_service(name: str, url: str):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{url}/health") as response:
                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "response_time_ms": 0,
                            "status_code": response.status
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "status_code": response.status,
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Check services concurrently
    service_checks = [check_service(name, url) for name, url in services_to_check]
    service_results = await asyncio.gather(*service_checks, return_exceptions=True)
    
    for (name, _), result in zip(services_to_check, service_results):
        if isinstance(result, Exception):
            health_status["dependencies"][name] = {
                "status": "unhealthy",
                "error": str(result)
            }
            overall_healthy = False
        else:
            health_status["dependencies"][name] = result
            if result["status"] != "healthy":
                overall_healthy = False
    
    # Update overall status
    health_status["status"] = "healthy" if overall_healthy else "degraded"
    
    return health_status


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(
    db: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, str]:
    """Kubernetes readiness probe endpoint"""
    try:
        # Check critical dependencies
        await db.execute("SELECT 1")
        await redis_client.ping()
        
        return {"status": "ready"}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {"status": "not ready", "error": str(e)}