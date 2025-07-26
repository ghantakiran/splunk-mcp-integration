"""
Cloud instance management endpoints
Provides CRUD operations for Splunk Cloud instances and connection management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import aiohttp
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.models.responses import StandardResponse, SuccessResponse, ErrorResponse
from app.models.cloud import (
    CloudInstanceCreate,
    CloudInstanceUpdate,
    CloudInstanceResponse,
    CloudInstanceWithHealth,
    CloudConnectionRequest,
    CloudConnectionResponse,
    CloudHealthCheck,
    CloudMetrics
)
from app.services.cloud_service import CloudService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/instances", 
             response_model=SuccessResponse[CloudInstanceResponse],
             status_code=status.HTTP_201_CREATED,
             summary="Create Splunk Cloud instance")
async def create_cloud_instance(
    instance_data: CloudInstanceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudInstanceResponse]:
    """
    Create a new Splunk Cloud instance configuration.
    
    This endpoint allows administrators to register new Splunk Cloud instances
    that can be used for dynamic routing and load balancing.
    
    Args:
        instance_data: Cloud instance configuration data
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Created cloud instance information
        
    Raises:
        HTTPException: If creation fails or user lacks permissions
    """
    try:
        # Check if user has permission to create cloud instances
        if not current_user.is_admin and not current_user.has_permission("cloud:create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create cloud instances"
            )
        
        cloud_service = CloudService()
        
        # Create instance through Cloud Connection Manager
        instance = await cloud_service.create_instance(
            instance_data=instance_data,
            created_by=current_user.id
        )
        
        logger.info(
            "Cloud instance created successfully",
            instance_id=instance.id,
            name=instance.name,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=instance,
            message="Cloud instance created successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create cloud instance", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cloud instance"
        )


@router.get("/instances",
            response_model=SuccessResponse[List[CloudInstanceWithHealth]])
async def list_cloud_instances(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    include_health: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[List[CloudInstanceWithHealth]]:
    """
    List all Splunk Cloud instances with optional filtering.
    
    Args:
        limit: Maximum number of instances to return
        offset: Number of instances to skip
        tenant_id: Filter by tenant ID
        status: Filter by instance status
        include_health: Include health information
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        List of cloud instances with health information
    """
    try:
        cloud_service = CloudService()
        
        instances = await cloud_service.list_instances(
            limit=limit,
            offset=offset,
            tenant_id=tenant_id,
            status=status,
            include_health=include_health,
            user_id=current_user.id
        )
        
        logger.info(
            "Cloud instances retrieved successfully",
            count=len(instances),
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=instances,
            message=f"Retrieved {len(instances)} cloud instances"
        )
    
    except Exception as e:
        logger.error("Failed to list cloud instances", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cloud instances"
        )


@router.get("/instances/{instance_id}",
            response_model=SuccessResponse[CloudInstanceWithHealth])
async def get_cloud_instance(
    instance_id: int,
    include_metrics: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudInstanceWithHealth]:
    """
    Get detailed information about a specific cloud instance.
    
    Args:
        instance_id: Cloud instance ID
        include_metrics: Include performance metrics
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Detailed cloud instance information
        
    Raises:
        HTTPException: If instance not found or access denied
    """
    try:
        cloud_service = CloudService()
        
        instance = await cloud_service.get_instance(
            instance_id=instance_id,
            include_metrics=include_metrics,
            user_id=current_user.id
        )
        
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found"
            )
        
        logger.info(
            "Cloud instance retrieved successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=instance,
            message="Cloud instance retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get cloud instance",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cloud instance"
        )


@router.put("/instances/{instance_id}",
            response_model=SuccessResponse[CloudInstanceResponse])
async def update_cloud_instance(
    instance_id: int,
    instance_data: CloudInstanceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudInstanceResponse]:
    """
    Update a Splunk Cloud instance configuration.
    
    Args:
        instance_id: Cloud instance ID to update
        instance_data: Updated instance configuration
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Updated cloud instance information
        
    Raises:
        HTTPException: If update fails or user lacks permissions
    """
    try:
        # Check if user has permission to update cloud instances
        if not current_user.is_admin and not current_user.has_permission("cloud:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update cloud instances"
            )
        
        cloud_service = CloudService()
        
        instance = await cloud_service.update_instance(
            instance_id=instance_id,
            instance_data=instance_data,
            updated_by=current_user.id
        )
        
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found"
            )
        
        logger.info(
            "Cloud instance updated successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=instance,
            message="Cloud instance updated successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update cloud instance",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cloud instance"
        )


@router.delete("/instances/{instance_id}",
               response_model=SuccessResponse[Dict[str, Any]])
async def delete_cloud_instance(
    instance_id: int,
    force: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Delete a Splunk Cloud instance.
    
    Args:
        instance_id: Cloud instance ID to delete
        force: Force deletion even if instance is in use
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: If deletion fails or user lacks permissions
    """
    try:
        # Check if user has permission to delete cloud instances
        if not current_user.is_admin and not current_user.has_permission("cloud:delete"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete cloud instances"
            )
        
        cloud_service = CloudService()
        
        success = await cloud_service.delete_instance(
            instance_id=instance_id,
            force=force,
            deleted_by=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found"
            )
        
        logger.info(
            "Cloud instance deleted successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data={"instance_id": instance_id, "deleted": True},
            message="Cloud instance deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete cloud instance",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cloud instance"
        )


@router.post("/connection",
             response_model=SuccessResponse[CloudConnectionResponse])
async def get_optimal_connection(
    connection_request: CloudConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudConnectionResponse]:
    """
    Get optimal Splunk Cloud connection based on requirements.
    
    This endpoint leverages the Cloud Connection Manager to provide
    the best available connection for the specified requirements.
    
    Args:
        connection_request: Connection requirements
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Optimal connection information
        
    Raises:
        HTTPException: If no suitable connection is available
    """
    try:
        cloud_service = CloudService()
        
        connection = await cloud_service.get_optimal_connection(
            tenant_id=connection_request.tenant_id,
            endpoint_type=connection_request.endpoint_type,
            session_id=connection_request.session_id,
            lb_config_name=connection_request.lb_config_name,
            user_id=current_user.id
        )
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No healthy cloud instances available"
            )
        
        logger.info(
            "Optimal cloud connection retrieved",
            endpoint_id=connection.endpoint_id,
            tenant_id=connection_request.tenant_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=connection,
            message="Optimal connection retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get optimal connection",
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get optimal connection"
        )


@router.get("/instances/{instance_id}/health",
            response_model=SuccessResponse[CloudHealthCheck])
async def get_instance_health(
    instance_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudHealthCheck]:
    """
    Get health information for a specific cloud instance.
    
    Args:
        instance_id: Cloud instance ID
        hours: Number of hours of health history to include
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Cloud instance health information
    """
    try:
        cloud_service = CloudService()
        
        health = await cloud_service.get_instance_health(
            instance_id=instance_id,
            hours=hours
        )
        
        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found"
            )
        
        logger.info(
            "Instance health retrieved successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=health,
            message="Instance health retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get instance health",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve instance health"
        )


@router.post("/instances/{instance_id}/health-check",
             response_model=SuccessResponse[CloudHealthCheck])
async def trigger_health_check(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudHealthCheck]:
    """
    Trigger an immediate health check for a cloud instance.
    
    Args:
        instance_id: Cloud instance ID
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Updated health check results
    """
    try:
        cloud_service = CloudService()
        
        health = await cloud_service.trigger_health_check(
            instance_id=instance_id,
            triggered_by=current_user.id
        )
        
        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found"
            )
        
        logger.info(
            "Health check triggered successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=health,
            message="Health check completed successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to trigger health check",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger health check"
        )


@router.get("/instances/{instance_id}/metrics",
            response_model=SuccessResponse[CloudMetrics])
async def get_instance_metrics(
    instance_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[CloudMetrics]:
    """
    Get performance metrics for a cloud instance.
    
    Args:
        instance_id: Cloud instance ID
        hours: Number of hours of metrics to include
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Cloud instance performance metrics
    """
    try:
        cloud_service = CloudService()
        
        metrics = await cloud_service.get_instance_metrics(
            instance_id=instance_id,
            hours=hours
        )
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cloud instance not found or no metrics available"
            )
        
        logger.info(
            "Instance metrics retrieved successfully",
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=metrics,
            message="Instance metrics retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get instance metrics",
            instance_id=instance_id,
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve instance metrics"
        )


@router.get("/health-summary",
            response_model=SuccessResponse[Dict[str, Any]])
async def get_health_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get overall health summary for all cloud instances.
    
    Args:
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Overall health summary across all instances
    """
    try:
        cloud_service = CloudService()
        
        summary = await cloud_service.get_health_summary()
        
        logger.info(
            "Health summary retrieved successfully",
            healthy_instances=summary.get("healthy_instances", 0),
            total_instances=summary.get("total_instances", 0),
            user_id=current_user.id
        )
        
        return SuccessResponse(
            data=summary,
            message="Health summary retrieved successfully"
        )
    
    except Exception as e:
        logger.error(
            "Failed to get health summary",
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health summary"
        )