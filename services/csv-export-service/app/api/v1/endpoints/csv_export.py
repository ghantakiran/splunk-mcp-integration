#!/usr/bin/env python3
"""
CSV Export API endpoints.

This module provides API endpoints for CSV export operations including
export creation, validation, and file management.
"""

import asyncio
import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import create_export_job, log_analytics_event
from app.core.redis_client import get_queue_manager
from app.models.csv_models import (
    CSVExportRequest, 
    BulkCSVExportRequest,
    JobResponse,
    ValidationResponse,
    CapabilitiesResponse,
    BaseResponse,
    ErrorResponse
)
from app.services.csv_generator import csv_generator
from app.utils.auth import CurrentUser, require_csv_create, require_csv_read, get_current_user
from app.utils.rate_limiter import check_user_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=JobResponse)
async def create_csv_export(
    request: CSVExportRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_csv_create)
):
    """Create a new CSV export job."""
    try:
        # Check rate limit
        await check_user_rate_limit(
            current_user.user_id, 
            "/api/v1/export", 
            current_user.role
        )
        
        # Create correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Create job in database
        job_id = await create_export_job(
            user_id=current_user.user_id,
            job_name=request.job_name,
            data_source=request.data_source.model_dump(),
            export_config=request.export_config.model_dump(),
            priority=request.priority,
            expires_in_hours=request.expires_in_hours
        )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=job_id,
            event_type="export_job_created",
            event_data={
                "job_name": request.job_name,
                "export_format": request.export_config.export_format,
                "priority": request.priority,
                "correlation_id": correlation_id
            }
        )
        
        # Add job to processing queue
        queue_manager = get_queue_manager()
        await queue_manager.enqueue(
            "csv_export",
            {
                "job_id": job_id,
                "user_id": current_user.user_id,
                "job_name": request.job_name,
                "data_source": request.data_source.model_dump(),
                "export_config": request.export_config.model_dump(),
                "correlation_id": correlation_id
            },
            priority=request.priority
        )
        
        # Start background processing
        background_tasks.add_task(process_csv_export, job_id, current_user.user_id, request)
        
        logger.info(
            f"CSV export job {job_id} created for user {current_user.user_id}",
            extra={"job_id": job_id, "user_id": current_user.user_id, "correlation_id": correlation_id}
        )
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message="CSV export job created successfully",
            created_at=asyncio.get_running_loop().time()
        )
        
    except Exception as e:
        logger.error(f"Failed to create CSV export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create export job: {str(e)}"
        )


@router.post("/bulk", response_model=JobResponse)
async def create_bulk_csv_export(
    request: BulkCSVExportRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_csv_create)
):
    """Create multiple CSV export jobs."""
    try:
        # Check rate limit with higher cost
        await check_user_rate_limit(
            current_user.user_id, 
            "/api/v1/export/bulk", 
            current_user.role
        )
        
        if len(request.jobs) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 20 jobs allowed in bulk export"
            )
        
        correlation_id = str(uuid.uuid4())
        job_ids = []
        
        # Create all jobs
        for job_request in request.jobs:
            job_id = await create_export_job(
                user_id=current_user.user_id,
                job_name=job_request.job_name,
                data_source=job_request.data_source.model_dump(),
                export_config=job_request.export_config.model_dump(),
                priority=job_request.priority,
                expires_in_hours=job_request.expires_in_hours
            )
            job_ids.append(job_id)
            
            # Add to queue
            queue_manager = get_queue_manager()
            await queue_manager.enqueue(
                "csv_export",
                {
                    "job_id": job_id,
                    "user_id": current_user.user_id,
                    "job_name": job_request.job_name,
                    "data_source": job_request.data_source.model_dump(),
                    "export_config": job_request.export_config.model_dump(),
                    "correlation_id": correlation_id,
                    "bulk_export": True,
                    "archive_name": request.archive_name
                },
                priority=job_request.priority
            )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="bulk_export_created",
            event_data={
                "job_count": len(request.jobs),
                "job_ids": job_ids,
                "archive_name": request.archive_name,
                "correlation_id": correlation_id
            }
        )
        
        logger.info(f"Bulk CSV export created: {len(request.jobs)} jobs for user {current_user.user_id}")
        
        return JobResponse(
            job_id=job_ids[0] if job_ids else 0,  # Return first job ID
            status="pending",
            message=f"Bulk export created: {len(request.jobs)} jobs",
            created_at=asyncio.get_running_loop().time()
        )
        
    except Exception as e:
        logger.error(f"Failed to create bulk CSV export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk export: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_export_data(
    request: CSVExportRequest,
    current_user: CurrentUser = Depends(require_csv_read)
):
    """Validate data source and export configuration."""
    try:
        # Check rate limit
        await check_user_rate_limit(
            current_user.user_id, 
            "/api/v1/export/validate", 
            current_user.role
        )
        
        # Validate data source and configuration
        validation_result = await csv_generator.validate_data(
            data_source=request.data_source.model_dump(),
            config=request.export_config
        )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="export_validation",
            event_data={
                "is_valid": validation_result["is_valid"],
                "row_count": validation_result["row_count"],
                "column_count": validation_result["column_count"],
                "issues_count": len(validation_result["issues"])
            }
        )
        
        return ValidationResponse(**validation_result)
        
    except Exception as e:
        logger.error(f"Failed to validate export data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_export_capabilities():
    """Get service capabilities and supported formats."""
    try:
        return CapabilitiesResponse(
            supported_formats=settings.EXPORT_FORMATS,
            supported_encodings=settings.SUPPORTED_ENCODINGS,
            supported_delimiters=settings.SUPPORTED_DELIMITERS,
            max_file_size_mb=settings.CSV_MAX_FILE_SIZE_MB,
            max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
            max_rows_per_file=settings.CSV_MAX_ROWS_PER_FILE,
            features=[
                "Advanced formatting options",
                "Custom encoding support",
                "Flexible delimiter configuration",
                "Header customization",
                "Data transformation",
                "Compression support",
                "Large dataset handling",
                "Batch processing",
                "Performance optimization",
                "Rate limiting",
                "User authentication",
                "Analytics tracking"
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service capabilities"
        )


@router.get("/{job_id}/download")
async def download_export_file(
    job_id: int,
    current_user: CurrentUser = Depends(require_csv_read)
):
    """Download exported CSV file."""
    try:
        from app.core.database import get_job_by_id
        
        # Get job details
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
        
        # Check job status
        if job["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job not completed. Status: {job['status']}"
            )
        
        # Check if file exists
        file_path = job["file_path"]
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Log download event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=job_id,
            event_type="file_downloaded",
            event_data={
                "file_path": file_path,
                "file_size": job.get("file_size", 0)
            }
        )
        
        # Return file
        filename = f"{job['job_name']}_{job_id}.{file_path.split('.')[-1]}"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.delete("/{job_id}", response_model=BaseResponse)
async def cancel_export_job(
    job_id: int,
    current_user: CurrentUser = Depends(require_csv_create)
):
    """Cancel a pending or processing export job."""
    try:
        from app.core.database import get_job_by_id, update_job_status
        
        # Get job details
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
        
        # Check if job can be cancelled
        if job["status"] in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job['status']}"
            )
        
        # Update job status
        await update_job_status(job_id, "cancelled")
        
        # Remove from queue if pending
        if job["status"] == "pending":
            queue_manager = get_queue_manager()
            await queue_manager.mark_completed("csv_export", str(job_id))
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=job_id,
            event_type="job_cancelled",
            event_data={"previous_status": job["status"]}
        )
        
        logger.info(f"Job {job_id} cancelled by user {current_user.user_id}")
        
        return BaseResponse(
            success=True,
            message="Job cancelled successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


async def process_csv_export(job_id: int, user_id: int, request: CSVExportRequest):
    """Background task to process CSV export."""
    try:
        # Generate CSV file
        success, file_path, error_message = await csv_generator.generate_csv(
            job_id=job_id,
            user_id=user_id,
            data_source=request.data_source.model_dump(),
            export_config=request.export_config,
            job_name=request.job_name
        )
        
        if success:
            logger.info(f"CSV export job {job_id} completed successfully")
        else:
            logger.error(f"CSV export job {job_id} failed: {error_message}")
            
    except Exception as e:
        logger.error(f"Background CSV export processing failed for job {job_id}: {e}")


# Export router
__all__ = ["router"]