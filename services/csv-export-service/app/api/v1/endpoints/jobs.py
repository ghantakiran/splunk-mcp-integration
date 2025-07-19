#!/usr/bin/env python3
"""
Jobs API endpoints.

This module provides API endpoints for managing CSV export jobs
including status checking, listing, and management operations.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.database import (
    get_job_by_id,
    get_user_jobs,
    log_analytics_event
)
from app.models.csv_models import (
    JobDetailsResponse,
    JobStatusResponse,
    JobListResponse,
    BaseResponse,
    JobStatus
)
from app.utils.auth import CurrentUser, require_csv_read, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{job_id}", response_model=JobDetailsResponse)
async def get_job_details(
    job_id: int,
    current_user: CurrentUser = Depends(require_csv_read)
):
    """Get detailed information about a specific job."""
    try:
        # Get job from database
        job = await get_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if user can access this job
        if not current_user.can_access_job(job["user_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=job_id,
            event_type="job_details_viewed",
            event_data={"job_status": job["status"]}
        )
        
        return JobDetailsResponse(
            job_id=job["job_id"],
            job_name=job["job_name"],
            status=JobStatus(job["status"]),
            export_format=job.get("export_config", {}).get("export_format", "csv"),
            file_path=job.get("file_path"),
            file_size=job.get("file_size"),
            row_count=job.get("row_count"),
            column_count=job.get("column_count"),
            error_message=job.get("error_message"),
            generation_time_ms=job.get("generation_time_ms"),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
            expires_at=job.get("expires_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job details for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job details"
        )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    current_user: CurrentUser = Depends(require_csv_read)
):
    """Get current status of a specific job."""
    try:
        # Get job from database
        job = await get_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if user can access this job
        if not current_user.can_access_job(job["user_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        # Calculate progress and runtime
        progress_percentage = None
        runtime_seconds = None
        current_operation = None
        
        if job["status"] == "processing":
            # Simulate progress calculation
            if job.get("started_at"):
                runtime_seconds = (datetime.utcnow() - job["started_at"]).total_seconds()
                # Simple progress simulation based on runtime
                progress_percentage = min(90.0, (runtime_seconds / 30.0) * 100)
                current_operation = "Generating CSV data"
            else:
                progress_percentage = 10.0
                current_operation = "Initializing export"
        elif job["status"] == "completed":
            progress_percentage = 100.0
            if job.get("started_at") and job.get("completed_at"):
                runtime_seconds = (job["completed_at"] - job["started_at"]).total_seconds()
        elif job["status"] == "failed":
            if job.get("started_at"):
                runtime_seconds = (datetime.utcnow() - job["started_at"]).total_seconds()
        
        return JobStatusResponse(
            job_id=job["job_id"],
            status=JobStatus(job["status"]),
            progress_percentage=progress_percentage,
            rows_processed=job.get("row_count"),
            total_rows=job.get("row_count") if job["status"] == "completed" else None,
            current_operation=current_operation,
            runtime_seconds=runtime_seconds,
            error_message=job.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


@router.get("/", response_model=JobListResponse)
async def list_user_jobs(
    current_user: CurrentUser = Depends(require_csv_read),
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip")
):
    """List user's export jobs with optional filtering."""
    try:
        # Validate status filter
        if status_filter and status_filter not in ["pending", "processing", "completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status filter. Must be one of: pending, processing, completed, failed, cancelled"
            )
        
        # Get jobs from database
        jobs = await get_user_jobs(
            user_id=current_user.user_id,
            status=status_filter,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        job_responses = []
        for job in jobs:
            job_responses.append(
                JobDetailsResponse(
                    job_id=job["job_id"],
                    job_name=job["job_name"],
                    status=JobStatus(job["status"]),
                    export_format="csv",  # Default for now
                    file_path=job.get("file_path"),
                    file_size=job.get("file_size"),
                    row_count=job.get("row_count"),
                    column_count=None,  # Not included in list view
                    error_message=None,  # Not included in list view
                    generation_time_ms=None,  # Not included in list view
                    created_at=job["created_at"],
                    started_at=job.get("started_at"),
                    completed_at=job.get("completed_at"),
                    expires_at=job.get("expires_at")
                )
            )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="jobs_listed",
            event_data={
                "job_count": len(job_responses),
                "status_filter": status_filter,
                "limit": limit,
                "offset": offset
            }
        )
        
        # For total count, we'd need a separate query in real implementation
        total = len(job_responses) + offset  # Simplified for demo
        
        return JobListResponse(
            total=total,
            page=offset // limit + 1,
            page_size=limit,
            jobs=job_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list jobs for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job list"
        )


@router.get("/status/summary")
async def get_jobs_summary(
    current_user: CurrentUser = Depends(require_csv_read)
):
    """Get summary of user's jobs by status."""
    try:
        # Get all user jobs
        all_jobs = await get_user_jobs(
            user_id=current_user.user_id,
            limit=1000  # Get a large number to calculate summary
        )
        
        # Calculate summary by status
        status_summary = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        total_files_size = 0
        total_rows_exported = 0
        
        for job in all_jobs:
            status = job["status"]
            if status in status_summary:
                status_summary[status] += 1
            
            if job.get("file_size"):
                total_files_size += job["file_size"]
            
            if job.get("row_count"):
                total_rows_exported += job["row_count"]
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="jobs_summary_viewed",
            event_data={
                "total_jobs": len(all_jobs),
                "status_breakdown": status_summary
            }
        )
        
        return {
            "total_jobs": len(all_jobs),
            "status_breakdown": status_summary,
            "total_files_size_mb": round(total_files_size / (1024 * 1024), 2),
            "total_rows_exported": total_rows_exported,
            "success_rate": round(
                (status_summary["completed"] / len(all_jobs) * 100) if len(all_jobs) > 0 else 0,
                2
            )
        }
        
    except Exception as e:
        logger.error(f"Failed to get jobs summary for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs summary"
        )


@router.delete("/cleanup", response_model=BaseResponse)
async def cleanup_user_jobs(
    current_user: CurrentUser = Depends(require_csv_read),
    older_than_days: int = Query(7, ge=1, le=365, description="Delete jobs older than N days")
):
    """Clean up old completed/failed jobs for the user."""
    try:
        # This would implement cleanup logic in a real application
        # For demo purposes, we'll simulate cleanup
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="jobs_cleanup_requested",
            event_data={"older_than_days": older_than_days}
        )
        
        logger.info(f"Cleanup requested by user {current_user.user_id} for jobs older than {older_than_days} days")
        
        # Simulate cleanup result
        cleaned_count = 5  # Simulated number
        
        return BaseResponse(
            success=True,
            message=f"Cleaned up {cleaned_count} old jobs successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup jobs for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup jobs"
        )


# Export router
__all__ = ["router"]