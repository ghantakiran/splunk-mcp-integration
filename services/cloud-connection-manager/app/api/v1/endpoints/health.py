"""
Health monitoring API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.connection_models import HealthStatus, EndpointType

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "cloud-connection-manager",
        "version": "1.0.0",
        "timestamp": "2025-01-16T10:30:00Z"
    }


@router.get("/detailed")
async def detailed_health_check(
    session: AsyncSession = Depends(get_async_session)
):
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "service": "cloud-connection-manager",
        "version": "1.0.0",
        "timestamp": "2025-01-16T10:30:00Z",
        "dependencies": {
            "database": "unknown",
            "redis": "unknown",
            "connection_pools": "unknown",
            "health_monitor": "unknown"
        },
        "metrics": {
            "total_endpoints": 0,
            "healthy_endpoints": 0,
            "active_connections": 0,
            "monitoring_tasks": 0
        }
    }
    
    try:
        # Test database connection
        await session.execute("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
        
        # Note: In a complete implementation, you would check Redis, 
        # connection pools, and other dependencies
        
        # Get basic metrics
        from app.models.connection_models import ConnectionEndpoint, EndpointStatus
        from sqlalchemy import select, func
        
        # Count total and healthy endpoints
        result = await session.execute(
            select(func.count(ConnectionEndpoint.id))
            .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
        )
        total_endpoints = result.scalar() or 0
        
        result = await session.execute(
            select(func.count(ConnectionEndpoint.id))
            .where(
                ConnectionEndpoint.status == EndpointStatus.ACTIVE,
                ConnectionEndpoint.health_status == HealthStatus.HEALTHY
            )
        )
        healthy_endpoints = result.scalar() or 0
        
        health_status["metrics"]["total_endpoints"] = total_endpoints
        health_status["metrics"]["healthy_endpoints"] = healthy_endpoints
        
        # Calculate overall health
        if total_endpoints == 0:
            health_status["status"] = "warning"
        elif healthy_endpoints / total_endpoints < 0.5:
            health_status["status"] = "unhealthy"
        elif healthy_endpoints / total_endpoints < 0.8:
            health_status["status"] = "degraded"
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["dependencies"]["database"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


@router.get("/ready")
async def readiness_probe(
    session: AsyncSession = Depends(get_async_session)
):
    """Kubernetes readiness probe."""
    try:
        # Check database connectivity
        await session.execute("SELECT 1")
        
        return {
            "status": "ready",
            "timestamp": "2025-01-16T10:30:00Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {
        "status": "alive",
        "timestamp": "2025-01-16T10:30:00Z"
    }


@router.get("/endpoints")
async def get_endpoints_health_summary(
    endpoint_type: Optional[EndpointType] = Query(None, description="Filter by endpoint type"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get health summary for all endpoints."""
    try:
        from app.models.connection_models import ConnectionEndpoint, EndpointStatus
        from sqlalchemy import select, func
        
        # Build base query
        query = select(ConnectionEndpoint).where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
        
        if endpoint_type:
            query = query.where(ConnectionEndpoint.endpoint_type == endpoint_type)
        
        result = await session.execute(query)
        endpoints = result.scalars().all()
        
        # Aggregate health statistics
        health_summary = {
            "total_endpoints": len(endpoints),
            "healthy_endpoints": 0,
            "degraded_endpoints": 0,
            "unhealthy_endpoints": 0,
            "unknown_endpoints": 0,
            "by_type": {
                "enterprise": {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0},
                "cloud": {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
            },
            "endpoints": []
        }
        
        for endpoint in endpoints:
            endpoint_type_str = endpoint.endpoint_type.value
            health_status = endpoint.health_status
            
            # Update type counts
            health_summary["by_type"][endpoint_type_str]["total"] += 1
            
            # Update overall and type-specific health counts
            if health_status == HealthStatus.HEALTHY:
                health_summary["healthy_endpoints"] += 1
                health_summary["by_type"][endpoint_type_str]["healthy"] += 1
            elif health_status == HealthStatus.DEGRADED:
                health_summary["degraded_endpoints"] += 1
                health_summary["by_type"][endpoint_type_str]["degraded"] += 1
            elif health_status == HealthStatus.UNHEALTHY:
                health_summary["unhealthy_endpoints"] += 1
                health_summary["by_type"][endpoint_type_str]["unhealthy"] += 1
            else:  # UNKNOWN
                health_summary["unknown_endpoints"] += 1
                health_summary["by_type"][endpoint_type_str]["unknown"] += 1
            
            # Add endpoint details
            health_summary["endpoints"].append({
                "id": endpoint.id,
                "name": endpoint.name,
                "endpoint_type": endpoint_type_str,
                "host": endpoint.host,
                "port": endpoint.port,
                "health_status": health_status.value,
                "last_health_check": endpoint.last_health_check,
                "consecutive_failures": endpoint.consecutive_failures,
                "tenant_id": endpoint.tenant_id
            })
        
        # Calculate health percentage
        if health_summary["total_endpoints"] > 0:
            health_summary["health_percentage"] = round(
                (health_summary["healthy_endpoints"] / health_summary["total_endpoints"]) * 100, 2
            )
        else:
            health_summary["health_percentage"] = 0.0
        
        return health_summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoints health summary: {str(e)}"
        )


@router.get("/endpoints/{endpoint_id}/history")
async def get_endpoint_health_history(
    endpoint_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get health history for a specific endpoint."""
    try:
        from app.models.connection_models import ConnectionEndpoint, ConnectionHealth
        from sqlalchemy import select, desc, and_
        from datetime import datetime, timedelta
        
        # Verify endpoint exists
        result = await session.execute(
            select(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        
        # Get health history
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = await session.execute(
            select(ConnectionHealth)
            .where(
                and_(
                    ConnectionHealth.endpoint_id == endpoint_id,
                    ConnectionHealth.check_timestamp >= since
                )
            )
            .order_by(desc(ConnectionHealth.check_timestamp))
            .limit(1000)  # Limit to prevent excessive data
        )
        health_records = result.scalars().all()
        
        # Calculate summary statistics
        total_checks = len(health_records)
        healthy_checks = len([r for r in health_records if r.health_status == HealthStatus.HEALTHY])
        degraded_checks = len([r for r in health_records if r.health_status == HealthStatus.DEGRADED])
        unhealthy_checks = len([r for r in health_records if r.health_status == HealthStatus.UNHEALTHY])
        
        response_times = [r.response_time_ms for r in health_records if r.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "endpoint_id": endpoint_id,
            "endpoint_name": endpoint.name,
            "period_hours": hours,
            "summary": {
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "degraded_checks": degraded_checks,
                "unhealthy_checks": unhealthy_checks,
                "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None
            },
            "history": [
                {
                    "timestamp": record.check_timestamp,
                    "health_status": record.health_status.value,
                    "response_time_ms": record.response_time_ms,
                    "is_reachable": record.is_reachable,
                    "status_code": record.status_code,
                    "error_message": record.error_message,
                    "cpu_usage": record.cpu_usage,
                    "memory_usage": record.memory_usage,
                    "disk_usage": record.disk_usage,
                    "connection_count": record.connection_count
                }
                for record in health_records
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint health history: {str(e)}"
        )


@router.post("/endpoints/{endpoint_id}/check")
async def trigger_immediate_health_check(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Trigger an immediate health check for an endpoint."""
    try:
        from app.models.connection_models import ConnectionEndpoint
        from sqlalchemy import select
        
        # Verify endpoint exists
        result = await session.execute(
            select(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        
        # Note: In a complete implementation, this would trigger the health monitor
        # to perform an immediate check using app.state.health_monitor
        
        return {
            "message": "Health check triggered",
            "endpoint_id": endpoint_id,
            "endpoint_name": endpoint.name,
            "status": "initiated",
            "note": "Would use HealthMonitor.perform_health_check() in complete implementation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger health check: {str(e)}"
        )