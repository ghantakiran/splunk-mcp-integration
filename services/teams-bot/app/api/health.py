"""
Health check and monitoring endpoints for Teams bot.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..bot.teams_handler import TeamsHandler
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# We'll inject the teams_handler when the app starts
teams_handler: TeamsHandler = None

def get_teams_handler() -> TeamsHandler:
    """Dependency to get teams handler."""
    return teams_handler

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "teams-bot",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(
    handler: TeamsHandler = Depends(get_teams_handler)
) -> Dict[str, Any]:
    """Detailed health check with dependencies."""
    try:
        # Check Teams bot health
        teams_healthy = await handler.health_check() if handler else False
        
        # Check backend services
        system_status = await handler.splunk_service.get_system_status() if handler else {"status": "unknown"}
        
        overall_status = "healthy"
        if not teams_healthy:
            overall_status = "degraded"
        if system_status.get("status") == "error":
            overall_status = "error"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "teams-bot",
            "version": "1.0.0",
            "components": {
                "teams_bot": "healthy" if teams_healthy else "unhealthy",
                "backend_services": system_status.get("status", "unknown")
            },
            "backend_services": system_status.get("services", {})
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "teams-bot",
            "version": "1.0.0",
            "error": "Health check failed"
        }

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get basic metrics."""
    # This would integrate with Prometheus metrics
    # For now, return basic placeholder metrics
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "response_time_avg": 0.0,
            "active_sessions": 0,
            "teams_activities_processed": 0
        }
    }