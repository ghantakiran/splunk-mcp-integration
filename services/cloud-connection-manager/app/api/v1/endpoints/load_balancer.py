"""
Load balancer management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc

from app.core.database import get_async_session
from app.models.connection_models import (
    LoadBalancerConfig, LoadBalancerConfigCreate, FailoverLog,
    LoadBalancerAlgorithm, EndpointType
)

router = APIRouter()


@router.post("/configs", status_code=status.HTTP_201_CREATED)
async def create_load_balancer_config(
    config_data: LoadBalancerConfigCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new load balancer configuration."""
    try:
        # Check if config with this name already exists
        result = await session.execute(
            select(LoadBalancerConfig).where(LoadBalancerConfig.name == config_data.name)
        )
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Load balancer configuration '{config_data.name}' already exists"
            )
        
        # Create new configuration
        config = LoadBalancerConfig(
            name=config_data.name,
            algorithm=config_data.algorithm,
            health_check_interval=config_data.health_check_interval,
            health_check_timeout=config_data.health_check_timeout,
            failover_timeout=config_data.failover_timeout,
            circuit_breaker_enabled=config_data.circuit_breaker_enabled,
            circuit_breaker_failure_threshold=config_data.circuit_breaker_failure_threshold,
            circuit_breaker_timeout=config_data.circuit_breaker_timeout,
            circuit_breaker_half_open_max_calls=3,
            sticky_sessions=config_data.sticky_sessions,
            session_affinity_timeout=3600,
            retry_attempts=config_data.retry_attempts,
            retry_delay=config_data.retry_delay,
            endpoint_types=[et.value for et in config_data.endpoint_types],
            endpoint_tags=config_data.endpoint_tags,
            description=config_data.description,
            is_active=True
        )
        
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        return {
            "id": config.id,
            "name": config.name,
            "algorithm": config.algorithm.value,
            "created_at": config.created_at,
            "message": "Load balancer configuration created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create load balancer configuration: {str(e)}"
        )


@router.get("/configs")
async def list_load_balancer_configs(
    active_only: bool = Query(True, description="Filter to active configurations only"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session)
):
    """List load balancer configurations."""
    try:
        # Build query
        query = select(LoadBalancerConfig)
        
        if active_only:
            query = query.where(LoadBalancerConfig.is_active == True)
        
        # Add ordering, limit, and offset
        query = query.order_by(desc(LoadBalancerConfig.created_at)).limit(limit).offset(offset)
        
        result = await session.execute(query)
        configs = result.scalars().all()
        
        return [
            {
                "id": config.id,
                "name": config.name,
                "algorithm": config.algorithm.value,
                "health_check_interval": config.health_check_interval,
                "health_check_timeout": config.health_check_timeout,
                "failover_timeout": config.failover_timeout,
                "circuit_breaker_enabled": config.circuit_breaker_enabled,
                "circuit_breaker_failure_threshold": config.circuit_breaker_failure_threshold,
                "circuit_breaker_timeout": config.circuit_breaker_timeout,
                "sticky_sessions": config.sticky_sessions,
                "retry_attempts": config.retry_attempts,
                "retry_delay": config.retry_delay,
                "endpoint_types": config.endpoint_types,
                "endpoint_tags": config.endpoint_tags,
                "is_active": config.is_active,
                "description": config.description,
                "created_at": config.created_at,
                "updated_at": config.updated_at
            }
            for config in configs
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list load balancer configurations: {str(e)}"
        )


@router.get("/configs/{config_id}")
async def get_load_balancer_config(
    config_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific load balancer configuration."""
    try:
        result = await session.execute(
            select(LoadBalancerConfig).where(LoadBalancerConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Load balancer configuration not found"
            )
        
        return {
            "id": config.id,
            "name": config.name,
            "algorithm": config.algorithm.value,
            "health_check_interval": config.health_check_interval,
            "health_check_timeout": config.health_check_timeout,
            "failover_timeout": config.failover_timeout,
            "circuit_breaker_enabled": config.circuit_breaker_enabled,
            "circuit_breaker_failure_threshold": config.circuit_breaker_failure_threshold,
            "circuit_breaker_timeout": config.circuit_breaker_timeout,
            "circuit_breaker_half_open_max_calls": config.circuit_breaker_half_open_max_calls,
            "sticky_sessions": config.sticky_sessions,
            "session_affinity_timeout": config.session_affinity_timeout,
            "retry_attempts": config.retry_attempts,
            "retry_delay": config.retry_delay,
            "endpoint_types": config.endpoint_types,
            "endpoint_tags": config.endpoint_tags,
            "is_active": config.is_active,
            "description": config.description,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get load balancer configuration: {str(e)}"
        )


@router.put("/configs/{config_id}")
async def update_load_balancer_config(
    config_id: int,
    update_data: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session)
):
    """Update a load balancer configuration."""
    try:
        # Get existing configuration
        result = await session.execute(
            select(LoadBalancerConfig).where(LoadBalancerConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Load balancer configuration not found"
            )
        
        # Update allowed fields
        allowed_fields = {
            "algorithm", "health_check_interval", "health_check_timeout",
            "failover_timeout", "circuit_breaker_enabled", 
            "circuit_breaker_failure_threshold", "circuit_breaker_timeout",
            "sticky_sessions", "retry_attempts", "retry_delay",
            "endpoint_types", "endpoint_tags", "is_active", "description"
        }
        
        update_dict = {}
        for field, value in update_data.items():
            if field in allowed_fields and value is not None:
                # Handle enum conversion
                if field == "algorithm" and isinstance(value, str):
                    try:
                        update_dict[field] = LoadBalancerAlgorithm(value)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid algorithm: {value}"
                        )
                else:
                    update_dict[field] = value
        
        if update_dict:
            await session.execute(
                update(LoadBalancerConfig)
                .where(LoadBalancerConfig.id == config_id)
                .values(**update_dict)
            )
            await session.commit()
            await session.refresh(config)
        
        return {
            "id": config.id,
            "name": config.name,
            "message": "Load balancer configuration updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update load balancer configuration: {str(e)}"
        )


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_load_balancer_config(
    config_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a load balancer configuration."""
    try:
        # Check if configuration exists
        result = await session.execute(
            select(LoadBalancerConfig).where(LoadBalancerConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Load balancer configuration not found"
            )
        
        # Delete configuration (cascades to related records)
        await session.execute(
            delete(LoadBalancerConfig).where(LoadBalancerConfig.id == config_id)
        )
        await session.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete load balancer configuration: {str(e)}"
        )


@router.get("/configs/{config_id}/failover-logs")
async def get_failover_logs(
    config_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of logs to retrieve"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get failover logs for a load balancer configuration."""
    try:
        # Verify configuration exists
        result = await session.execute(
            select(LoadBalancerConfig).where(LoadBalancerConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Load balancer configuration not found"
            )
        
        # Build query for failover logs
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(FailoverLog).where(
            FailoverLog.config_id == config_id,
            FailoverLog.event_timestamp >= since
        )
        
        if event_type:
            query = query.where(FailoverLog.event_type == event_type)
        
        query = query.order_by(desc(FailoverLog.event_timestamp)).limit(limit).offset(offset)
        
        result = await session.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "id": log.id,
                "event_timestamp": log.event_timestamp,
                "event_type": log.event_type,
                "source_endpoint_id": log.source_endpoint_id,
                "target_endpoint_id": log.target_endpoint_id,
                "reason": log.reason,
                "error_message": log.error_message,
                "response_time_ms": log.response_time_ms,
                "retry_count": log.retry_count,
                "request_details": log.request_details,
                "system_metrics": log.system_metrics
            }
            for log in logs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get failover logs: {str(e)}"
        )


@router.get("/stats")
async def get_load_balancer_stats(
    config_name: Optional[str] = Query(None, description="Filter by configuration name"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get load balancer statistics and status."""
    try:
        # This would integrate with the ConnectionPoolManager to get real stats
        # For now, return a placeholder structure
        
        stats = {
            "total_configurations": 0,
            "active_configurations": 0,
            "configurations": [],
            "overall_health": "healthy",
            "last_updated": "2025-01-16T10:30:00Z"
        }
        
        # Get configuration count
        result = await session.execute(select(LoadBalancerConfig))
        all_configs = result.scalars().all()
        
        stats["total_configurations"] = len(all_configs)
        stats["active_configurations"] = len([c for c in all_configs if c.is_active])
        
        # Filter by name if specified
        if config_name:
            all_configs = [c for c in all_configs if c.name == config_name]
        
        # Add configuration details
        stats["configurations"] = [
            {
                "id": config.id,
                "name": config.name,
                "algorithm": config.algorithm.value,
                "is_active": config.is_active,
                "endpoint_count": 0,  # Would get from ConnectionPoolManager
                "healthy_endpoints": 0,  # Would get from HealthMonitor
                "last_failover": None  # Would get from recent logs
            }
            for config in all_configs
        ]
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get load balancer statistics: {str(e)}"
        )