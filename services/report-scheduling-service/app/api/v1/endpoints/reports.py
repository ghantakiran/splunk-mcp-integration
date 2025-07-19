"""
Report management API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule_models import (
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStatus
)
from app.services.scheduler_service import SchedulerService
from app.utils.auth import get_current_user, check_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/executions",
    response_model=ExecutionListResponse,
    summary="List report executions",
    description="Get a list of report executions with optional filtering"
)
async def list_executions(
    schedule_id: Optional[UUID] = Query(None, description="Filter by schedule ID"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List report executions with optional filtering."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:read")
        
        scheduler_service = SchedulerService(db)
        executions = await scheduler_service.list_executions(
            user_id=current_user["user_id"],
            schedule_id=schedule_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return executions
        
    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get execution by ID",
    description="Retrieve a specific execution by its ID"
)
async def get_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get execution by ID."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:read")
        
        scheduler_service = SchedulerService(db)
        execution = await scheduler_service.get_execution(execution_id, current_user["user_id"])
        
        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/executions/{execution_id}/retry",
    response_model=ExecutionResponse,
    summary="Retry failed execution",
    description="Retry a failed execution"
)
async def retry_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retry failed execution."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:retry")
        
        scheduler_service = SchedulerService(db)
        execution = await scheduler_service.retry_execution(execution_id, current_user["user_id"])
        
        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        
        logger.info(f"Execution retry initiated: {execution_id} by user {current_user['user_id']}")
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/executions/{execution_id}/cancel",
    summary="Cancel running execution",
    description="Cancel a currently running execution"
)
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cancel running execution."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:cancel")
        
        scheduler_service = SchedulerService(db)
        success = await scheduler_service.cancel_execution(execution_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found or cannot be cancelled")
        
        logger.info(f"Execution cancelled: {execution_id} by user {current_user['user_id']}")
        return {"message": "Execution cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/executions/{execution_id}/download",
    summary="Download execution result",
    description="Download the generated report file for an execution"
)
async def download_execution_result(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Download execution result file."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:download")
        
        scheduler_service = SchedulerService(db)
        download_info = await scheduler_service.get_execution_download(execution_id, current_user["user_id"])
        
        if not download_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution result not found")
        
        # In a real implementation, this would return a FileResponse
        # For now, return download information
        return {
            "download_url": download_info.get("download_url"),
            "file_name": download_info.get("file_name"),
            "file_size": download_info.get("file_size"),
            "content_type": download_info.get("content_type"),
            "expires_at": download_info.get("expires_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading execution result {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/executions/{execution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete execution",
    description="Delete an execution and its associated files"
)
async def delete_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete execution."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:delete")
        
        scheduler_service = SchedulerService(db)
        success = await scheduler_service.delete_execution(execution_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        
        logger.info(f"Execution deleted: {execution_id} by user {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/executions/{execution_id}/logs",
    summary="Get execution logs",
    description="Get detailed logs for an execution"
)
async def get_execution_logs(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get execution logs."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:logs")
        
        scheduler_service = SchedulerService(db)
        logs = await scheduler_service.get_execution_logs(execution_id, current_user["user_id"])
        
        if logs is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
        
        return {
            "execution_id": str(execution_id),
            "logs": logs,
            "retrieved_at": scheduler_service._get_current_time().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution logs {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/summary",
    summary="Get report summary",
    description="Get summary statistics for reports"
)
async def get_report_summary(
    schedule_id: Optional[UUID] = Query(None, description="Filter by schedule ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include in summary"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get report summary statistics."""
    try:
        # Check permissions
        await check_permission(current_user, "execution:read")
        
        scheduler_service = SchedulerService(db)
        summary = await scheduler_service.get_report_summary(
            user_id=current_user["user_id"],
            schedule_id=schedule_id,
            days=days
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting report summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")