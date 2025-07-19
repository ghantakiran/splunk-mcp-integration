"""
API endpoints for report schedule management.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from app.models.schedule_models import (
    CreateScheduleRequest, UpdateScheduleRequest, ScheduleResponse,
    ExecutionResponse, ScheduleStatus
)
from app.services.scheduler_service import SchedulerService
from app.utils.auth import get_current_user, require_permission
from app.utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report schedule"
)
@rate_limit("schedule_create", cost=2)
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:create"))
):
    """
    Create a new report schedule with automated delivery configuration.
    
    **Required Permissions:** `report_schedule:create`
    
    **Rate Limit:** 30 requests per minute (cost: 2)
    
    **Request Body:**
    - **name**: Schedule name (required)
    - **description**: Optional description
    - **schedule_config**: Cron expression and scheduling configuration
    - **report_config**: Report generation configuration
    - **delivery_configs**: List of delivery method configurations
    - **tags**: Optional tags for organization
    - **metadata**: Additional metadata
    
    **Returns:**
    - **success**: Operation success indicator
    - **schedule**: Created schedule details
    - **message**: Success message
    """
    try:
        scheduler_service = SchedulerService()
        
        schedule = await scheduler_service.create_schedule(
            request=request,
            user_id=current_user["user_id"]
        )
        
        logger.info(
            f"Created schedule {schedule.schedule_id} for user {current_user['user_id']}"
        )
        
        return {
            "success": True,
            "schedule": schedule.dict(),
            "message": "Schedule created successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Invalid schedule creation request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to create schedule"}
        )


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List user's report schedules"
)
@rate_limit("schedule_list")
async def list_schedules(
    status_filter: Optional[ScheduleStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:read"))
):
    """
    List report schedules for the authenticated user.
    
    **Required Permissions:** `report_schedule:read`
    
    **Rate Limit:** 60 requests per minute
    
    **Query Parameters:**
    - **status**: Filter by schedule status (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    
    **Returns:**
    - **success**: Operation success indicator
    - **schedules**: List of schedules
    - **total**: Total number of schedules
    - **page**: Current page number
    - **page_size**: Items per page
    - **total_pages**: Total number of pages
    """
    try:
        scheduler_service = SchedulerService()
        
        result = await scheduler_service.list_schedules(
            user_id=current_user["user_id"],
            status=status_filter,
            page=page,
            page_size=page_size
        )
        
        return {
            "success": True,
            **result
        }
        
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to list schedules"}
        )


@router.get(
    "/{schedule_id}",
    response_model=Dict[str, Any],
    summary="Get a specific report schedule"
)
@rate_limit("schedule_read")
async def get_schedule(
    schedule_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:read"))
):
    """
    Get details of a specific report schedule.
    
    **Required Permissions:** `report_schedule:read`
    
    **Rate Limit:** 60 requests per minute
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Returns:**
    - **success**: Operation success indicator
    - **schedule**: Schedule details
    """
    try:
        scheduler_service = SchedulerService()
        
        schedule = await scheduler_service.get_schedule(
            schedule_id=schedule_id,
            user_id=current_user["user_id"]
        )
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Schedule not found"}
            )
        
        return {
            "success": True,
            "schedule": schedule.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to get schedule"}
        )


@router.put(
    "/{schedule_id}",
    response_model=Dict[str, Any],
    summary="Update a report schedule"
)
@rate_limit("schedule_update", cost=2)
async def update_schedule(
    schedule_id: UUID,
    request: UpdateScheduleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:update"))
):
    """
    Update an existing report schedule.
    
    **Required Permissions:** `report_schedule:update`
    
    **Rate Limit:** 30 requests per minute (cost: 2)
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Request Body:**
    - All fields are optional - only provided fields will be updated
    - **name**: Schedule name
    - **description**: Schedule description
    - **schedule_config**: Scheduling configuration
    - **report_config**: Report generation configuration
    - **delivery_configs**: Delivery method configurations
    - **status**: Schedule status
    - **tags**: Schedule tags
    - **metadata**: Additional metadata
    
    **Returns:**
    - **success**: Operation success indicator
    - **schedule**: Updated schedule details
    - **message**: Success message
    """
    try:
        scheduler_service = SchedulerService()
        
        schedule = await scheduler_service.update_schedule(
            schedule_id=schedule_id,
            request=request,
            user_id=current_user["user_id"]
        )
        
        logger.info(f"Updated schedule {schedule_id}")
        
        return {
            "success": True,
            "schedule": schedule.dict(),
            "message": "Schedule updated successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Invalid schedule update request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to update schedule"}
        )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a report schedule"
)
@rate_limit("schedule_delete", cost=3)
async def delete_schedule(
    schedule_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:delete"))
):
    """
    Delete a report schedule and cancel all pending executions.
    
    **Required Permissions:** `report_schedule:delete`
    
    **Rate Limit:** 20 requests per minute (cost: 3)
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Returns:**
    - HTTP 204 No Content on success
    - HTTP 404 Not Found if schedule doesn't exist
    """
    try:
        scheduler_service = SchedulerService()
        
        deleted = await scheduler_service.delete_schedule(
            schedule_id=schedule_id,
            user_id=current_user["user_id"]
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Schedule not found"}
            )
        
        logger.info(f"Deleted schedule {schedule_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to delete schedule"}
        )


@router.post(
    "/{schedule_id}/execute",
    response_model=Dict[str, Any],
    summary="Execute a schedule immediately"
)
@rate_limit("schedule_execute", cost=5)
async def execute_schedule(
    schedule_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:execute"))
):
    """
    Execute a report schedule immediately, outside of its normal schedule.
    
    **Required Permissions:** `report_schedule:execute`
    
    **Rate Limit:** 10 requests per minute (cost: 5)
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Returns:**
    - **success**: Operation success indicator
    - **execution**: Execution details
    - **message**: Success message
    """
    try:
        scheduler_service = SchedulerService()
        
        execution = await scheduler_service.execute_schedule(schedule_id)
        
        logger.info(f"Executed schedule {schedule_id} - execution {execution.execution_id}")
        
        return {
            "success": True,
            "execution": execution.dict(),
            "message": "Schedule executed successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Invalid schedule execution request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to execute schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to execute schedule"}
        )


@router.get(
    "/{schedule_id}/executions",
    response_model=Dict[str, Any],
    summary="List executions for a schedule"
)
@rate_limit("schedule_executions")
async def list_schedule_executions(
    schedule_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:read"))
):
    """
    List execution history for a specific schedule.
    
    **Required Permissions:** `report_schedule:read`
    
    **Rate Limit:** 60 requests per minute
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    
    **Returns:**
    - **success**: Operation success indicator
    - **executions**: List of executions
    - **total**: Total number of executions
    - **page**: Current page number
    - **page_size**: Items per page
    - **total_pages**: Total number of pages
    """
    try:
        # First verify the schedule exists and belongs to the user
        scheduler_service = SchedulerService()
        
        schedule = await scheduler_service.get_schedule(
            schedule_id=schedule_id,
            user_id=current_user["user_id"]
        )
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Schedule not found"}
            )
        
        # Get executions (would implement this method in SchedulerService)
        # For now, return placeholder
        return {
            "success": True,
            "executions": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list executions for schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to list executions"}
        )


@router.patch(
    "/{schedule_id}/status",
    response_model=Dict[str, Any],
    summary="Update schedule status"
)
@rate_limit("schedule_status_update")
async def update_schedule_status(
    schedule_id: UUID,
    status_value: ScheduleStatus,
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_permission("report_schedule:update"))
):
    """
    Update the status of a report schedule (activate, pause, disable).
    
    **Required Permissions:** `report_schedule:update`
    
    **Rate Limit:** 60 requests per minute
    
    **Path Parameters:**
    - **schedule_id**: Schedule UUID
    
    **Request Body:**
    - **status**: New schedule status (active, paused, disabled, error)
    
    **Returns:**
    - **success**: Operation success indicator
    - **schedule**: Updated schedule details
    - **message**: Success message
    """
    try:
        scheduler_service = SchedulerService()
        
        update_request = UpdateScheduleRequest(status=status_value)
        
        schedule = await scheduler_service.update_schedule(
            schedule_id=schedule_id,
            request=update_request,
            user_id=current_user["user_id"]
        )
        
        logger.info(f"Updated schedule {schedule_id} status to {status_value}")
        
        return {
            "success": True,
            "schedule": schedule.dict(),
            "message": f"Schedule status updated to {status_value}"
        }
        
    except ValueError as e:
        logger.warning(f"Invalid status update request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": "Failed to update schedule status"}
        )