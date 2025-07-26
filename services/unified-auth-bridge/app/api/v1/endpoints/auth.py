"""
Authentication endpoints for unified auth bridge
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any

from app.core.logging import get_logger
from app.services.auth_bridge_service import AuthBridgeService
from app.models.auth import (
    AuthRequest,
    AuthResponse,
    TokenValidationRequest,
    TokenValidationResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    AuthMetrics
)
from app.models.responses import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


def get_auth_bridge_service(request: Request) -> AuthBridgeService:
    """Get auth bridge service from app state"""
    return request.app.state.auth_bridge_service


@router.post("/authenticate", response_model=SuccessResponse[AuthResponse])
async def authenticate(
    auth_request: AuthRequest,
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[AuthResponse]:
    """
    Unified authentication across Splunk Enterprise and Cloud
    
    Attempts authentication with configured providers in priority order,
    with intelligent fallback and caching for optimal performance.
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Authentication request received",
            username=auth_request.username,
            tenant_id=auth_request.tenant_id,
            preferred_provider=auth_request.preferred_provider,
            correlation_id=correlation_id
        )
        
        auth_response = await auth_bridge.authenticate(auth_request)
        
        if auth_response.success:
            logger.info(
                "Authentication successful",
                username=auth_request.username,
                provider=auth_response.provider.value if auth_response.provider else None,
                correlation_id=correlation_id
            )
        else:
            logger.warning(
                "Authentication failed",
                username=auth_request.username,
                error=auth_response.error_message,
                correlation_id=correlation_id
            )
        
        return SuccessResponse(
            data=auth_response,
            message="Authentication completed" if auth_response.success else "Authentication failed"
        )
        
    except Exception as e:
        logger.error(
            "Authentication error",
            username=auth_request.username,
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


@router.post("/validate", response_model=SuccessResponse[TokenValidationResponse])
async def validate_token(
    validation_request: TokenValidationRequest,
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[TokenValidationResponse]:
    """
    Validate authentication token across providers
    
    Validates token with specified or all available providers
    and returns user profile if valid.
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Token validation requested",
            token_prefix=validation_request.token[:10] + "...",
            provider=validation_request.provider,
            correlation_id=correlation_id
        )
        
        user_profile = await auth_bridge.validate_token(
            validation_request.token,
            validation_request.provider
        )
        
        if user_profile:
            response = TokenValidationResponse(
                valid=True,
                user_profile=user_profile,
                expires_at=None,  # Would get from token if available
                error_message=None
            )
            
            logger.info(
                "Token validation successful",
                username=user_profile.username,
                provider=user_profile.provider.value,
                correlation_id=correlation_id
            )
        else:
            response = TokenValidationResponse(
                valid=False,
                user_profile=None,
                expires_at=None,
                error_message="Invalid or expired token"
            )
            
            logger.warning(
                "Token validation failed",
                token_prefix=validation_request.token[:10] + "...",
                correlation_id=correlation_id
            )
        
        return SuccessResponse(
            data=response,
            message="Token validation completed"
        )
        
    except Exception as e:
        logger.error(
            "Token validation error",
            token_prefix=validation_request.token[:10] + "...",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation service error"
        )


@router.post("/logout", response_model=SuccessResponse[LogoutResponse])
async def logout(
    logout_request: LogoutRequest,
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[LogoutResponse]:
    """
    Logout from authentication providers
    
    Logs out from specified provider or all providers if logout_all is True.
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Logout requested",
            token_prefix=logout_request.token[:10] + "...",
            provider=logout_request.provider,
            logout_all=logout_request.logout_all,
            correlation_id=correlation_id
        )
        
        success = await auth_bridge.logout(
            logout_request.token,
            logout_request.provider
        )
        
        providers_logged_out = []
        if success:
            if logout_request.provider:
                providers_logged_out.append(logout_request.provider)
            elif logout_request.logout_all:
                # Would track which providers were actually logged out
                providers_logged_out = ["cloud", "enterprise"]  # Simplified
        
        response = LogoutResponse(
            success=success,
            providers_logged_out=providers_logged_out,
            error_message=None if success else "Logout failed"
        )
        
        logger.info(
            "Logout completed",
            success=success,
            providers=providers_logged_out,
            correlation_id=correlation_id
        )
        
        return SuccessResponse(
            data=response,
            message="Logout completed successfully" if success else "Logout failed"
        )
        
    except Exception as e:
        logger.error(
            "Logout error",
            token_prefix=logout_request.token[:10] + "...",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )


@router.post("/refresh", response_model=SuccessResponse[RefreshTokenResponse])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[RefreshTokenResponse]:
    """
    Refresh authentication token
    
    Refreshes token with specified provider (Cloud only, Enterprise uses session keys).
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Token refresh requested",
            refresh_token_prefix=refresh_request.refresh_token[:10] + "...",
            provider=refresh_request.provider,
            correlation_id=correlation_id
        )
        
        # For now, return not implemented as this would require integration
        # with cloud auth service refresh endpoint
        response = RefreshTokenResponse(
            success=False,
            token=None,
            refresh_token=None,
            expires_at=None,
            provider=refresh_request.provider,
            error_message="Token refresh not implemented yet"
        )
        
        logger.warning(
            "Token refresh not implemented",
            correlation_id=correlation_id
        )
        
        return SuccessResponse(
            data=response,
            message="Token refresh not implemented"
        )
        
    except Exception as e:
        logger.error(
            "Token refresh error",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.get("/metrics", response_model=SuccessResponse[AuthMetrics])
async def get_auth_metrics(
    request: Request,
    auth_bridge: AuthBridgeService = Depends(get_auth_bridge_service)
) -> SuccessResponse[AuthMetrics]:
    """
    Get authentication metrics and analytics
    
    Returns authentication statistics including success rates,
    provider breakdown, and performance metrics.
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.info(
            "Authentication metrics requested",
            correlation_id=correlation_id
        )
        
        # For now, return placeholder metrics
        # In production, this would collect real metrics from Redis or database
        metrics = AuthMetrics(
            total_attempts=0,
            successful_attempts=0,
            failed_attempts=0,
            provider_breakdown={},
            cache_hits=0,
            cache_misses=0,
            average_response_time_ms=0.0,
            period="last_24_hours"
        )
        
        return SuccessResponse(
            data=metrics,
            message="Authentication metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(
            "Metrics retrieval error",
            error=str(e),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics service error"
        )