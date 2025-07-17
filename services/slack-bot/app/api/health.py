"""
Health check and monitoring endpoints.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..bot.slack_handler import SlackHandler
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# We'll inject the slack_handler when the app starts
slack_handler: SlackHandler = None

def get_slack_handler() -> SlackHandler:
    """Dependency to get slack handler."""
    return slack_handler

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "slack-bot",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(
    handler: SlackHandler = Depends(get_slack_handler)
) -> Dict[str, Any]:
    """Detailed health check with dependencies."""
    try:
        # Check Slack bot health
        slack_healthy = await handler.health_check() if handler else False
        
        # Check backend services
        system_status = await handler.splunk_service.get_system_status() if handler else {"status": "unknown"}
        
        overall_status = "healthy"
        if not slack_healthy:
            overall_status = "degraded"
        if system_status.get("status") == "error":
            overall_status = "error"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "slack-bot",
            "version": "1.0.0",
            "components": {
                "slack_bot": "healthy" if slack_healthy else "unhealthy",
                "backend_services": system_status.get("status", "unknown")
            },
            "backend_services": system_status.get("services", {})
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "slack-bot",
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
            "active_sessions": 0
        }
    }