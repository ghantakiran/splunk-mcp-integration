"""
API endpoints for schedule version management.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.versioning_models import (
    CreateVersionRequest, RestoreVersionRequest, CompareVersionsRequest,
    HistoryFilterRequest, VersionResponse, VersionListResponse,
    VersionComparisonResponse, HistoryEventResponse, HistoryResponse,
    VersionStatsResponse, HistoryStatsResponse, RestoreResult,
    HistoryEventType
)
from app.services.versioning_service import VersioningService
from app.utils.auth import get_current_user, check_permission

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    request: CreateVersionRequest,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new version of a schedule.
    
    Creates a snapshot of the current schedule configuration as a new version.
    This allows tracking changes over time and enables rollback functionality.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:update")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Create version
        version = await versioning_service.create_version(
            request=request,
            user_id=current_user["user_id"],
            correlation_id=current_user.get("correlation_id")
        )
        
        logger.info(f"Created version for schedule {request.schedule_id} by user {current_user['user_id']}")
        
        return version
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create version"
        )


@router.get("/schedule/{schedule_id}", response_model=VersionListResponse)
async def get_schedule_versions(
    schedule_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    include_archived: bool = Query(False, description="Include archived versions"),
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all versions for a specific schedule.
    
    Returns a paginated list of versions for the specified schedule,
    ordered by version number in descending order (newest first).
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:read")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Get versions
        versions = await versioning_service.get_versions(
            schedule_id=schedule_id,
            limit=limit,
            offset=offset,
            include_archived=include_archived
        )
        
        return versions
        
    except Exception as e:
        logger.error(f"Error getting schedule versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schedule versions"
        )


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: UUID,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific version by ID.
    
    Returns detailed information about a specific version including
    the complete configuration snapshot.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:read")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Get version
        version = await versioning_service.get_version(version_id)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found"
            )
        
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get version"
        )


@router.post("/compare", response_model=VersionComparisonResponse)
async def compare_versions(
    request: CompareVersionsRequest,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Compare two versions to see differences.
    
    Performs a detailed comparison between two versions and returns
    the differences in configuration, including added, removed, and modified fields.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:read")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Compare versions
        comparison = await versioning_service.compare_versions(request)
        
        logger.info(f"Compared versions {request.version_id_1} and {request.version_id_2}")
        
        return comparison
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare versions"
        )


@router.post("/restore", response_model=RestoreResult)
async def restore_version(
    request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Restore a schedule to a previous version.
    
    Creates a backup of the current state, then restores the schedule
    to the specified version. This operation creates new version entries
    for both the backup and the restore.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:update")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Restore version
        result = await versioning_service.restore_version(
            request=request,
            user_id=current_user["user_id"],
            correlation_id=current_user.get("correlation_id")
        )
        
        logger.info(f"Restored version {request.version_id} by user {current_user['user_id']}")
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error restoring version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore version"
        )


@router.get("/schedule/{schedule_id}/stats", response_model=VersionStatsResponse)
async def get_version_stats(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get version statistics for a schedule.
    
    Returns comprehensive statistics about versions including counts,
    user activity, size information, and timeline data.
    """
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Get stats
        stats = await versioning_service.get_version_stats(schedule_id)
        
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting version stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get version statistics"
        )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    schedule_id: Optional[UUID] = Query(None, description="Filter by schedule ID"),
    event_types: Optional[List[HistoryEventType]] = Query(None, description="Filter by event types"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=1000, description="Results limit"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get history events with filtering.
    
    Returns a paginated list of history events that can be filtered by
    schedule, event type, date range, and user.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:read")
        
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            from datetime import datetime
            parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        
        if end_date:
            from datetime import datetime
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        # Create filter request
        filter_request = HistoryFilterRequest(
            schedule_id=schedule_id,
            event_types=event_types,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Get history
        history = await versioning_service.get_history(filter_request)
        
        return history
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get history"
        )


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: UUID,
    db: AsyncSession = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a specific version.
    
    Soft deletes a version by marking it as archived. The version
    configuration is preserved for audit purposes but is no longer
    available for normal operations.
    
    Note: Current versions cannot be deleted.
    """
    try:
        # Check permissions
        await check_permission(current_user, "schedule:delete")
        
        # Create versioning service
        versioning_service = VersioningService(db)
        
        # Get the version first to check if it exists and is not current
        version = await versioning_service.get_version(version_id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found"
            )
        
        if version.is_current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the current version"
            )
        
        # Archive the version (soft delete)
        from app.models.versioning_models import VersionAction
        await versioning_service._create_history_event(
            schedule_id=version.schedule_id,
            event_type=HistoryEventType.VERSION_CHANGE,
            event_title=f"Version {version.version_number} archived",
            event_description="Version marked as archived (soft delete)",
            user_id=current_user["user_id"],
            correlation_id=current_user.get("correlation_id"),
            version_id=version_id,
            event_data={
                "action": VersionAction.ARCHIVED.value,
                "version_number": version.version_number,
                "archived_by": current_user["user_id"]
            }
        )
        
        # Update the version in database
        from app.core.database import ScheduleVersion
        version_record = await db.get(ScheduleVersion, version_id)
        if version_record:
            version_record.action = VersionAction.ARCHIVED
            await db.commit()
        
        logger.info(f"Archived version {version_id} by user {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete version"
        )