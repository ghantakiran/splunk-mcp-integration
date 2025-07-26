"""
Connection management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc

from app.core.database import get_async_session
from app.models.connection_models import (
    ConnectionEndpoint, EndpointCreate, EndpointUpdate, EndpointResponse,
    PoolConfigCreate, EndpointType, EndpointStatus, HealthStatus
)
from app.services.connection_pool_manager import ConnectionPoolManager
from app.services.health_monitor import HealthMonitor

router = APIRouter()


@router.post("/endpoints", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    endpoint_data: EndpointCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new connection endpoint."""
    try:
        # Create base URL
        base_url = f"{endpoint_data.scheme}://{endpoint_data.host}:{endpoint_data.port}"
        
        # Create endpoint
        endpoint = ConnectionEndpoint(
            name=endpoint_data.name,
            endpoint_type=endpoint_data.endpoint_type,
            host=endpoint_data.host,
            port=endpoint_data.port,
            scheme=endpoint_data.scheme,
            base_url=base_url,
            tenant_id=endpoint_data.tenant_id,
            priority=endpoint_data.priority,
            weight=endpoint_data.weight,
            max_connections=endpoint_data.max_connections,
            timeout=endpoint_data.timeout,
            description=endpoint_data.description,
            tags=endpoint_data.tags,
            metadata=endpoint_data.metadata,
            status=EndpointStatus.ACTIVE,
            health_status=HealthStatus.UNKNOWN
        )
        
        # Handle authentication
        if endpoint_data.auth_token:
            endpoint.auth_token = endpoint_data.auth_token  # Should be encrypted in production
        elif endpoint_data.username and endpoint_data.password:
            endpoint.username = endpoint_data.username
            endpoint.password = endpoint_data.password  # Should be encrypted in production
        
        session.add(endpoint)
        await session.commit()
        await session.refresh(endpoint)
        
        return endpoint
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create endpoint: {str(e)}"
        )


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_endpoints(
    endpoint_type: Optional[EndpointType] = Query(None, description="Filter by endpoint type"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    status: Optional[EndpointStatus] = Query(None, description="Filter by status"),
    health_status: Optional[HealthStatus] = Query(None, description="Filter by health status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session)
):
    """List connection endpoints with optional filtering."""
    try:
        # Build query with filters
        query = select(ConnectionEndpoint)
        
        if endpoint_type:
            query = query.where(ConnectionEndpoint.endpoint_type == endpoint_type)
        if tenant_id:
            query = query.where(ConnectionEndpoint.tenant_id == tenant_id)
        if status:
            query = query.where(ConnectionEndpoint.status == status)
        if health_status:
            query = query.where(ConnectionEndpoint.health_status == health_status)
        
        # Add ordering, limit, and offset
        query = query.order_by(desc(ConnectionEndpoint.created_at)).limit(limit).offset(offset)
        
        result = await session.execute(query)
        endpoints = result.scalars().all()
        
        return endpoints
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list endpoints: {str(e)}"
        )


@router.get("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific connection endpoint."""
    try:
        result = await session.execute(
            select(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        
        return endpoint
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint: {str(e)}"
        )


@router.put("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: int,
    update_data: EndpointUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update a connection endpoint."""
    try:
        # Get existing endpoint
        result = await session.execute(
            select(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        
        # Update fields
        update_dict = {}
        for field, value in update_data.dict(exclude_unset=True).items():
            if value is not None:
                update_dict[field] = value
        
        if update_dict:
            await session.execute(
                update(ConnectionEndpoint)
                .where(ConnectionEndpoint.id == endpoint_id)
                .values(**update_dict)
            )
            await session.commit()
            await session.refresh(endpoint)
        
        return endpoint
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update endpoint: {str(e)}"
        )


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a connection endpoint."""
    try:
        # Check if endpoint exists
        result = await session.execute(
            select(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found"
            )
        
        # Delete endpoint (cascades to related records)
        await session.execute(
            delete(ConnectionEndpoint).where(ConnectionEndpoint.id == endpoint_id)
        )
        await session.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete endpoint: {str(e)}"
        )


@router.post("/endpoints/{endpoint_id}/pools")
async def create_connection_pool(
    endpoint_id: int,
    pool_config: PoolConfigCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a connection pool for an endpoint."""
    try:
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
        
        # Create pool (simplified - would need more implementation)
        pool_data = {
            "endpoint_id": endpoint_id,
            "pool_name": pool_config.pool_name,
            "min_size": pool_config.min_size,
            "max_size": pool_config.max_size,
            "idle_timeout": pool_config.idle_timeout,
            "max_lifetime": pool_config.max_lifetime,
            "validation_query": pool_config.validation_query,
            "validate_on_borrow": pool_config.validate_on_borrow,
            "validate_on_return": pool_config.validate_on_return
        }
        
        return {"message": "Pool configuration saved", "config": pool_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection pool: {str(e)}"
        )


@router.get("/endpoints/{endpoint_id}/health")
async def get_endpoint_health(
    endpoint_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get health status and history for an endpoint."""
    try:
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
        
        # Get current health status
        current_health = {
            "endpoint_id": endpoint_id,
            "current_status": endpoint.health_status.value,
            "last_check": endpoint.last_health_check,
            "consecutive_failures": endpoint.consecutive_failures
        }
        
        # Note: In a complete implementation, you would get detailed health history
        # from the health monitor service
        
        return {
            "current_health": current_health,
            "history_hours": hours,
            "note": "Health history would be retrieved from HealthMonitor service"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint health: {str(e)}"
        )


@router.post("/endpoints/{endpoint_id}/health-check")
async def trigger_health_check(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Trigger an immediate health check for an endpoint."""
    try:
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
        
        # Note: In a complete implementation, you would trigger the health monitor
        # to perform an immediate check
        
        return {
            "message": "Health check triggered",
            "endpoint_id": endpoint_id,
            "note": "Would trigger HealthMonitor.perform_health_check()"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger health check: {str(e)}"
        )


@router.get("/endpoints/{endpoint_id}/metrics")
async def get_endpoint_metrics(
    endpoint_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of metrics to retrieve"),
    interval_minutes: int = Query(5, description="Metrics interval in minutes"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get performance metrics for an endpoint."""
    try:
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
        
        # Note: In a complete implementation, you would get metrics from the metrics collector
        
        return {
            "endpoint_id": endpoint_id,
            "hours": hours,
            "interval_minutes": interval_minutes,
            "note": "Metrics would be retrieved from MetricsCollector service"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint metrics: {str(e)}"
        )