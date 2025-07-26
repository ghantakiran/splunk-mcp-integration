"""
Status and monitoring endpoints for unified auth bridge
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.core.logging import get_logger
from app.services.auth_bridge_service import AuthBridgeService
from app.models.auth import AuthBridgeStatus
from app.models.responses import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


def get_auth_bridge_service(request: Request) -> AuthBridgeService:
    """Get auth bridge service from app state"""
    return request.app.state.auth_bridge_service


@router.get("/providers", response_model=SuccessResponse[AuthBridgeStatus])
async def get_provider_status(
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[AuthBridgeStatus]:
    """
    Get authentication provider status and configuration
    
    Returns information about available authentication providers,
    their health status, and bridge configuration.
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Provider status requested",
            correlation_id=correlation_id
        )
        
        provider_status = await auth_bridge.get_provider_status()
        health_summary = await auth_bridge.check_health()
        
        # Convert to AuthBridgeStatus format
        from app.models.auth import AuthMode, ProviderStatus
        
        providers = {}
        for name, provider_info in provider_status.get("providers", {}).items():
            providers[name] = ProviderStatus(
                type=provider_info["type"],
                name=provider_info["name"],
                url=provider_info["url"],
                priority=provider_info["priority"],
                status=provider_info["status"],
                health=health_summary.get(f"{name}_auth_service", "unknown") if name == "cloud" else health_summary.get("splunk_enterprise", "unknown")
            )
        
        bridge_status = AuthBridgeStatus(
            mode=AuthMode(provider_status["mode"]),
            priority_order=provider_status["priority_order"],
            fallback_enabled=provider_status["fallback_enabled"],
            cache_ttl=provider_status["cache_ttl"],
            providers=providers,
            health_summary=health_summary
        )
        
        logger.info(
            "Provider status retrieved",
            providers=list(providers.keys()),
            mode=provider_status["mode"],
            correlation_id=correlation_id
        )
        
        return SuccessResponse(
            data=bridge_status,
            message="Provider status retrieved successfully"
        )
        
    except Exception as e:
        logger.error(
            "Provider status error",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Provider status service error"
        )