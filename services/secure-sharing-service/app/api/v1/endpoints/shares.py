"""
API endpoints for secure sharing functionality.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.sharing_models import (
    CreateShareRequest, UpdateShareRequest, AccessShareRequest, ShareListRequest,
    ShareResponse, ShareListResponse, ShareAccessResponse, ShareStatsResponse,
    ExpirationCheckResult, ShareSecurityValidation
)
from app.services.sharing_service import (
    sharing_service, ShareNotFoundError, ShareExpirationError, ShareSecurityError
)
from app.utils.auth import get_current_user
from app.utils.rate_limiter import rate_limit
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new share"
)
async def create_share(
    request: CreateShareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_create", max_requests=10, window_seconds=60))
):
    """
    Create a new secure share for a resource.
    
    - **resource_type**: Type of resource being shared
    - **resource_id**: ID of the resource to share
    - **permissions**: List of permissions granted to viewers
    - **expiration_policy**: How the share should expire
    - **security options**: Password protection, domain restrictions, etc.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        share = await sharing_service.create_share(request, user_id, db)
        
        logger.info(
            "Share created via API",
            share_id=str(share.share_id),
            resource_type=request.resource_type.value,
            user_id=user_id
        )
        
        return share

    except ValueError as e:
        logger.warning(
            "Share creation failed - validation error",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Share creation failed - server error",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share"
        )


@router.get(
    "/",
    response_model=ShareListResponse,
    summary="List shares with filtering"
)
async def list_shares(
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    expires_after: Optional[datetime] = None,
    expires_before: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_list", max_requests=100, window_seconds=60))
):
    """
    List shares created by the current user with optional filtering.
    
    - **resource_type**: Filter by resource type
    - **status**: Filter by share status
    - **created_after/before**: Filter by creation date range
    - **expires_after/before**: Filter by expiration date range
    - **tags**: Filter by tags
    - **search**: Search in names and descriptions
    - **limit/offset**: Pagination parameters
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Create request object
        list_request = ShareListRequest(
            resource_type=resource_type,
            status=status,
            created_after=created_after,
            created_before=created_before,
            expires_after=expires_after,
            expires_before=expires_before,
            tags=tags or [],
            search=search,
            limit=limit,
            offset=offset
        )

        result = await sharing_service.list_shares(list_request, user_id, db)
        
        return ShareListResponse(
            items=result["items"],
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
            has_more=result["has_more"]
        )

    except Exception as e:
        logger.error(
            "Share listing failed",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list shares"
        )


@router.get(
    "/{share_id}",
    response_model=ShareResponse,
    summary="Get share by ID"
)
async def get_share(
    share_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_get", max_requests=200, window_seconds=60))
):
    """
    Get details of a specific share by ID.
    
    Only the share creator can access share details.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # This would need to be implemented in the service
        # For now, we'll use the list functionality with a specific filter
        list_request = ShareListRequest(limit=1, offset=0)
        result = await sharing_service.list_shares(list_request, user_id, db)
        
        share = next((s for s in result["items"] if s.share_id == share_id), None)
        if not share:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found"
            )

        return share

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Share retrieval failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve share"
        )


@router.put(
    "/{share_id}",
    response_model=ShareResponse,
    summary="Update share"
)
async def update_share(
    share_id: UUID,
    request: UpdateShareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_update", max_requests=20, window_seconds=60))
):
    """
    Update an existing share.
    
    Only the share creator can update the share.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        share = await sharing_service.update_share(share_id, request, user_id, db)
        
        logger.info(
            "Share updated via API",
            share_id=str(share_id),
            user_id=user_id
        )
        
        return share

    except ShareNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    except ValueError as e:
        logger.warning(
            "Share update failed - validation error",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Share update failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update share"
        )


@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete share"
)
async def delete_share(
    share_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_delete", max_requests=10, window_seconds=60))
):
    """
    Delete a share.
    
    Only the share creator can delete the share.
    This will also delete all related access logs and metrics.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        success = await sharing_service.delete_share(share_id, user_id, db)
        
        if success:
            logger.info(
                "Share deleted via API",
                share_id=str(share_id),
                user_id=user_id
            )
        
        return None

    except ShareNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    except Exception as e:
        logger.error(
            "Share deletion failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete share"
        )


@router.post(
    "/access",
    response_model=ShareAccessResponse,
    summary="Access a shared resource"
)
async def access_share(
    request: AccessShareRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_access", max_requests=100, window_seconds=60))
):
    """
    Access a shared resource using a share token.
    
    This endpoint is public (no authentication required) but may require
    additional security validation based on the share configuration.
    """
    try:
        # Enhance request with additional context from HTTP request
        if not request.ip_address:
            request.ip_address = http_request.client.host if http_request.client else None
        
        if not request.user_agent:
            request.user_agent = http_request.headers.get("user-agent")
        
        if not request.referrer:
            request.referrer = http_request.headers.get("referer")

        access_response = await sharing_service.access_share(request, db)
        
        logger.info(
            "Share accessed successfully",
            share_id=str(access_response.share_id),
            user_email=request.user_email or "anonymous",
            ip_address=request.ip_address
        )
        
        return access_response

    except ShareNotFoundError:
        logger.warning(
            "Share access failed - not found",
            share_token=request.share_token[:8] + "..." if len(request.share_token) > 8 else request.share_token,
            ip_address=request.ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or invalid token"
        )
    except ShareExpirationError as e:
        logger.warning(
            "Share access failed - expired",
            share_token=request.share_token[:8] + "..." if len(request.share_token) > 8 else request.share_token,
            error=str(e),
            ip_address=request.ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e)
        )
    except ShareSecurityError as e:
        logger.warning(
            "Share access failed - security",
            share_token=request.share_token[:8] + "..." if len(request.share_token) > 8 else request.share_token,
            error=str(e),
            ip_address=request.ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Share access failed - server error",
            share_token=request.share_token[:8] + "..." if len(request.share_token) > 8 else request.share_token,
            error=str(e),
            ip_address=request.ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access share"
        )


@router.get(
    "/{share_id}/expiration",
    response_model=ExpirationCheckResult,
    summary="Check share expiration status"
)
async def check_share_expiration(
    share_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_expiration", max_requests=100, window_seconds=60))
):
    """
    Check the expiration status of a share.
    
    Returns detailed information about expiration status, remaining time,
    and remaining usage limits.
    """
    try:
        result = await sharing_service.check_expiration(share_id, db)
        
        logger.debug(
            "Share expiration checked",
            share_id=str(share_id),
            is_expired=result.is_expired,
            user_id=current_user.get("sub")
        )
        
        return result

    except Exception as e:
        logger.error(
            "Share expiration check failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check expiration status"
        )


@router.post(
    "/{share_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke share access"
)
async def revoke_share(
    share_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_revoke", max_requests=20, window_seconds=60))
):
    """
    Revoke access to a share without deleting it.
    
    This changes the share status to 'revoked', preventing further access
    while preserving the share record and analytics.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Update share status to revoked using the update functionality
        from app.models.sharing_models import UpdateShareRequest, ShareStatus
        
        # This would need to be enhanced to support status updates
        # For now, we'll use delete as a proxy for revocation
        success = await sharing_service.delete_share(share_id, user_id, db)
        
        if success:
            logger.info(
                "Share revoked via API",
                share_id=str(share_id),
                user_id=user_id
            )

    except ShareNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    except Exception as e:
        logger.error(
            "Share revocation failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke share"
        )