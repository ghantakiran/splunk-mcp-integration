"""
BI Integration management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_database
from ....core.logging import get_logger
from ....models.bi_models import (
    BIIntegrationCreate,
    BIIntegrationUpdate,
    BIIntegrationResponse,
    BIProvider,
    IntegrationStatus
)
from ....services.integration_service import IntegrationService
from ....utils.dependencies import get_current_user

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[BIIntegrationResponse])
async def get_integrations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    provider: Optional[BIProvider] = Query(None),
    status: Optional[IntegrationStatus] = Query(None),
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Get list of BI integrations for the current user."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        integrations = await service.get_user_integrations(
            user_id=user_id,
            skip=skip,
            limit=limit,
            provider=provider,
            status=status
        )
        
        logger.info(
            f"Retrieved {len(integrations)} BI integrations",
            extra={
                "user_id": user_id,
                "skip": skip,
                "limit": limit,
                "provider": provider.value if provider else None,
                "status": status.value if status else None,
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return integrations
        
    except Exception as e:
        logger.error(
            f"Failed to retrieve BI integrations: {e}",
            extra={
                "user_id": user_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve BI integrations"
        )


@router.post("/", response_model=BIIntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    request: Request,
    integration_data: BIIntegrationCreate,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Create a new BI integration."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        integration = await service.create_integration(
            user_id=user_id,
            integration_data=integration_data
        )
        
        logger.info(
            f"Created BI integration: {integration.id}",
            extra={
                "user_id": user_id,
                "integration_id": integration.id,
                "provider": integration.provider.value,
                "name": integration.name,
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return integration
        
    except ValueError as e:
        logger.warning(
            f"Invalid integration data: {e}",
            extra={
                "user_id": user_id,
                "provider": integration_data.provider.value,
                "name": integration_data.name,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Failed to create BI integration: {e}",
            extra={
                "user_id": user_id,
                "provider": integration_data.provider.value,
                "name": integration_data.name,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create BI integration"
        )


@router.get("/{integration_id}", response_model=BIIntegrationResponse)
async def get_integration(
    request: Request,
    integration_id: str,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific BI integration."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        integration = await service.get_integration(
            integration_id=integration_id,
            user_id=user_id
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(
            f"Retrieved BI integration: {integration_id}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "provider": integration.provider.value,
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return integration
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to retrieve BI integration: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve BI integration"
        )


@router.put("/{integration_id}", response_model=BIIntegrationResponse)
async def update_integration(
    request: Request,
    integration_id: str,
    integration_data: BIIntegrationUpdate,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Update a BI integration."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        integration = await service.update_integration(
            integration_id=integration_id,
            user_id=user_id,
            integration_data=integration_data
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(
            f"Updated BI integration: {integration_id}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "provider": integration.provider.value,
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return integration
        
    except HTTPException:
        raise
        
    except ValueError as e:
        logger.warning(
            f"Invalid integration update data: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Failed to update BI integration: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update BI integration"
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    request: Request,
    integration_id: str,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Delete a BI integration."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        success = await service.delete_integration(
            integration_id=integration_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(
            f"Deleted BI integration: {integration_id}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to delete BI integration: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete BI integration"
        )


@router.post("/{integration_id}/test", response_model=dict)
async def test_integration(
    request: Request,
    integration_id: str,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Test a BI integration connection."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        result = await service.test_integration(
            integration_id=integration_id,
            user_id=user_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(
            f"Tested BI integration: {integration_id}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "test_success": result.get("success", False),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to test BI integration: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test BI integration"
        )


@router.post("/{integration_id}/sync", response_model=dict)
async def sync_integration(
    request: Request,
    integration_id: str,
    force: bool = Query(False, description="Force full sync"),
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user),
):
    """Synchronize a BI integration."""
    user_id = current_user["user_id"]
    
    try:
        service = IntegrationService(db)
        result = await service.sync_integration(
            integration_id=integration_id,
            user_id=user_id,
            force=force
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(
            f"Synchronized BI integration: {integration_id}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "force": force,
                "sync_success": result.get("success", False),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to sync BI integration: {e}",
            extra={
                "user_id": user_id,
                "integration_id": integration_id,
                "error": str(e),
                "correlation_id": getattr(request.state, "correlation_id", "unknown")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync BI integration"
        )