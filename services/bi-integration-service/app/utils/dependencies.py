"""
FastAPI dependencies for BI Integration Service.
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_database
from ..core.logging import get_logger

logger = get_logger(__name__)


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user from request state (set by auth middleware)."""
    user_id = getattr(request.state, "user_id", None)
    roles = getattr(request.state, "roles", [])
    permissions = getattr(request.state, "permissions", [])
    token_payload = getattr(request.state, "token_payload", {})
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return {
        "user_id": user_id,
        "roles": roles,
        "permissions": permissions,
        "token_payload": token_payload
    }


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current user if they have admin role."""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def get_integration_user(
    integration_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> Dict[str, Any]:
    """Get current user if they have access to the specified integration."""
    # Import here to avoid circular imports
    from ..services.integration_service import IntegrationService
    
    try:
        service = IntegrationService(db)
        has_access = await service.check_user_access(
            integration_id=integration_id,
            user_id=current_user["user_id"]
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this integration"
            )
        
        return current_user
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to check integration access: {e}",
            extra={
                "integration_id": integration_id,
                "user_id": current_user["user_id"],
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify integration access"
        )


async def check_permission(
    permission: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if current user has the specified permission."""
    user_permissions = current_user.get("permissions", [])
    
    if permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required"
        )
    
    return current_user


def require_permission(permission: str):
    """Decorator to require a specific permission."""
    def dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        return check_permission(permission, current_user)
    
    return dependency


async def get_pagination_params(
    skip: int = 0,
    limit: int = 100,
    max_limit: int = 1000
) -> Dict[str, int]:
    """Get pagination parameters with validation."""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be positive"
        )
    
    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit parameter cannot exceed {max_limit}"
        )
    
    return {
        "skip": skip,
        "limit": limit
    }


async def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


async def validate_uuid(uuid_str: str, field_name: str = "ID") -> str:
    """Validate UUID format."""
    import uuid
    
    try:
        uuid.UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )


async def get_request_context(request: Request) -> Dict[str, Any]:
    """Get request context information."""
    return {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "correlation_id": getattr(request.state, "correlation_id", "unknown")
    }