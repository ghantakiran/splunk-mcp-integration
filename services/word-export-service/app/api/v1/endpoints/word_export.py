#!/usr/bin/env python3
"""
Word Export API endpoints.

This module contains all REST API endpoints for Word document generation,
including job management, template operations, and analytics.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Response
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import (
    get_db_session,
    create_job,
    get_job,
    get_user_jobs,
    create_template,
    get_templates,
    get_analytics,
    log_analytics_event
)
from app.core.redis_client import get_cache_manager, get_queue_manager
from app.models.word_models import (
    WordExportRequest,
    BulkWordExportRequest,
    TemplateRequest,
    JobResponse,
    JobStatusResponse,
    JobDetailsResponse,
    JobListResponse,
    AnalyticsResponse,
    CapabilitiesResponse,
    TemplateResponse,
    TemplateListResponse,
    BaseResponse,
    ErrorResponse
)
from app.services.word_generator import word_document_generator
from app.utils.auth import get_current_user, get_admin_user, UserContext
from app.utils.rate_limiter import apply_user_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_word_export_job(
    request: WordExportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user)
):
    """Create a new Word export job."""
    try:
        # Apply rate limiting
        from fastapi import Request
        # Note: In real implementation, you'd get the Request object
        # await apply_user_rate_limit(request, current_user.user_id)
        
        async with get_db_session() as session:
            # Create job in database
            job_id = await create_job(
                session=session,
                job_name=request.job_name,
                user_id=current_user.user_id,
                document_config=request.document_config.model_dump(),
                data_source=request.data_source.model_dump(),
                output_format=request.output_format.value,
                expires_in_hours=request.expires_in_hours
            )
            
            # Add job to queue for processing
            queue_manager = get_queue_manager()
            job_data = {
                "job_id": job_id,
                "user_id": current_user.user_id,
                "document_config": request.document_config.model_dump(),
                "data_source": request.data_source.model_dump(),
                "output_format": request.output_format.value
            }
            
            await queue_manager.enqueue("word_export", job_data)
            
            # Log analytics event
            await log_analytics_event(
                session=session,
                user_id=current_user.user_id,
                job_id=job_id,
                event_type="job_created",
                event_data={"job_name": request.job_name, "template": request.document_config.template.value}
            )
            
            # Schedule background processing
            background_tasks.add_task(process_word_export_job, job_data)
            
            logger.info(f"Created Word export job {job_id} for user {current_user.user_id}")
            
            return JobResponse(
                job_id=job_id,
                status="pending",
                message="Word export job created successfully",
                created_at=datetime.utcnow()
            )
    
    except Exception as e:
        logger.error(f"Failed to create Word export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Word export job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobDetailsResponse)
async def get_word_export_job(
    job_id: int,
    current_user: UserContext = Depends(get_current_user)
):
    """Get details of a specific Word export job."""
    try:
        async with get_db_session() as session:
            job = await get_job(session, job_id, current_user.user_id)
            
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            return JobDetailsResponse(
                job_id=job.id,
                job_name=job.job_name,
                status=job.status,
                output_format=job.output_format,
                template=job.template,
                file_path=job.file_path,
                file_size=job.file_size,
                page_count=job.page_count,
                chart_count=job.chart_count,
                table_count=job.table_count,
                section_count=job.section_count,
                error_message=job.error_message,
                generation_time_ms=job.generation_time_ms,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                expires_at=job.expires_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job details: {str(e)}"
        )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    current_user: UserContext = Depends(get_current_user)
):
    """Get status of a specific Word export job."""
    try:
        async with get_db_session() as session:
            job = await get_job(session, job_id, current_user.user_id)
            
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # Calculate progress and runtime
            progress_percentage = None
            runtime_seconds = None
            
            if job.status == "processing" and job.started_at:
                runtime_seconds = (datetime.utcnow() - job.started_at).total_seconds()
                # Estimate progress based on runtime (simplified)
                progress_percentage = min(95.0, runtime_seconds / 30.0 * 100)  # Assume 30s average
            
            elif job.status == "completed":
                progress_percentage = 100.0
                if job.started_at and job.completed_at:
                    runtime_seconds = (job.completed_at - job.started_at).total_seconds()
            
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
                progress_percentage=progress_percentage,
                runtime_seconds=runtime_seconds,
                error_message=job.error_message
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs", response_model=JobListResponse)
async def list_user_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    current_user: UserContext = Depends(get_current_user)
):
    """List Word export jobs for the current user."""
    try:
        async with get_db_session() as session:
            jobs, total_count = await get_user_jobs(
                session=session,
                user_id=current_user.user_id,
                page=page,
                page_size=page_size,
                status_filter=status_filter
            )
            
            job_list = [
                JobDetailsResponse(
                    job_id=job.id,
                    job_name=job.job_name,
                    status=job.status,
                    output_format=job.output_format,
                    template=job.template,
                    file_path=job.file_path,
                    file_size=job.file_size,
                    page_count=job.page_count,
                    chart_count=job.chart_count,
                    table_count=job.table_count,
                    section_count=job.section_count,
                    error_message=job.error_message,
                    generation_time_ms=job.generation_time_ms,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    expires_at=job.expires_at
                )
                for job in jobs
            ]
            
            return JobListResponse(
                total=total_count,
                page=page,
                page_size=page_size,
                jobs=job_list
            )
    
    except Exception as e:
        logger.error(f"Failed to list jobs for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}/download")
async def download_word_document(
    job_id: int,
    current_user: UserContext = Depends(get_current_user)
):
    """Download the generated Word document."""
    try:
        async with get_db_session() as session:
            job = await get_job(session, job_id, current_user.user_id)
            
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            if job.status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job is not completed yet"
                )
            
            if not job.file_path or not os.path.exists(job.file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generated file not found"
                )
            
            # Check if file has expired
            if job.expires_at and datetime.utcnow() > job.expires_at:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="File has expired"
                )
            
            # Log download event
            await log_analytics_event(
                session=session,
                user_id=current_user.user_id,
                job_id=job_id,
                event_type="file_downloaded"
            )
            
            # Determine filename
            filename = f"{job.job_name.replace(' ', '_')}_{job_id}.{job.output_format}"
            
            logger.info(f"User {current_user.user_id} downloading file for job {job_id}")
            
            return FileResponse(
                path=job.file_path,
                filename=filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.post("/bulk", response_model=List[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_word_export(
    request: BulkWordExportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user)
):
    """Create multiple Word export jobs in bulk."""
    try:
        if len(request.jobs) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 jobs allowed in bulk request"
            )
        
        job_responses = []
        
        async with get_db_session() as session:
            for job_request in request.jobs:
                # Apply template from bulk request if not specified in individual job
                if hasattr(job_request.document_config, 'template') and not job_request.document_config.template:
                    job_request.document_config.template = request.template
                
                # Create job
                job_id = await create_job(
                    session=session,
                    job_name=job_request.job_name,
                    user_id=current_user.user_id,
                    document_config=job_request.document_config.model_dump(),
                    data_source=job_request.data_source.model_dump(),
                    output_format=request.output_format.value,
                    expires_in_hours=job_request.expires_in_hours
                )
                
                # Add to queue
                queue_manager = get_queue_manager()
                job_data = {
                    "job_id": job_id,
                    "user_id": current_user.user_id,
                    "document_config": job_request.document_config.model_dump(),
                    "data_source": job_request.data_source.model_dump(),
                    "output_format": request.output_format.value
                }
                
                await queue_manager.enqueue("word_export", job_data)
                
                # Schedule background processing
                background_tasks.add_task(process_word_export_job, job_data)
                
                job_responses.append(JobResponse(
                    job_id=job_id,
                    status="pending",
                    message="Word export job created successfully",
                    created_at=datetime.utcnow()
                ))
            
            # Log bulk creation event
            await log_analytics_event(
                session=session,
                user_id=current_user.user_id,
                job_id=0,  # No specific job ID for bulk
                event_type="bulk_jobs_created",
                event_data={"job_count": len(request.jobs)}
            )
        
        logger.info(f"Created {len(request.jobs)} bulk Word export jobs for user {current_user.user_id}")
        return job_responses
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bulk Word export jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk jobs: {str(e)}"
        )


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_word_template(
    request: TemplateRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """Create a new Word document template."""
    try:
        async with get_db_session() as session:
            template_id = await create_template(
                session=session,
                name=request.name,
                description=request.description,
                template_type=request.template_type.value,
                template_data=request.template_data.model_dump(),
                created_by=current_user.user_id,
                is_default=request.is_default
            )
            
            logger.info(f"Created template {template_id}: {request.name}")
            
            return TemplateResponse(
                template_id=template_id,
                name=request.name,
                description=request.description,
                template_type=request.template_type,
                is_default=request.is_default,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    active_only: bool = Query(True, description="Only return active templates"),
    current_user: UserContext = Depends(get_current_user)
):
    """List available Word document templates."""
    try:
        async with get_db_session() as session:
            templates = await get_templates(session, active_only=active_only)
            
            template_list = [
                TemplateResponse(
                    template_id=template.id,
                    name=template.name,
                    description=template.description,
                    template_type=template.template_type,
                    is_default=template.is_default,
                    is_active=template.is_active,
                    created_at=template.created_at,
                    updated_at=template.updated_at
                )
                for template in templates
            ]
            
            return TemplateListResponse(
                total=len(template_list),
                templates=template_list
            )
    
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_word_export_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: UserContext = Depends(get_current_user)
):
    """Get Word export analytics for the current user."""
    try:
        async with get_db_session() as session:
            analytics_data = await get_analytics(
                session=session,
                user_id=current_user.user_id,
                days=days
            )
            
            return AnalyticsResponse(**analytics_data)
    
    except Exception as e:
        logger.error(f"Failed to get analytics for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_service_capabilities():
    """Get Word export service capabilities."""
    return CapabilitiesResponse(
        supported_formats=settings.EXPORT_FORMATS,
        supported_templates=settings.AVAILABLE_TEMPLATES,
        supported_chart_types=["bar", "column", "line", "pie", "area", "scatter"],
        max_file_size_mb=settings.WORD_MAX_FILE_SIZE_MB,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
        max_document_pages=settings.MAX_DOCUMENT_PAGES,
        features=[
            "Professional document generation",
            "Custom templates and themes",
            "Chart and table embedding",
            "Advanced formatting and styling",
            "Header and footer customization",
            "Page layout management",
            "Table of contents generation",
            "Watermark and branding support"
        ]
    )


@router.delete("/jobs/{job_id}", response_model=BaseResponse)
async def cancel_word_export_job(
    job_id: int,
    current_user: UserContext = Depends(get_current_user)
):
    """Cancel a pending or processing Word export job."""
    try:
        async with get_db_session() as session:
            job = await get_job(session, job_id, current_user.user_id)
            
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            if job.status in ["completed", "failed", "cancelled"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel job with status: {job.status}"
                )
            
            # Update job status to cancelled
            from app.core.database import update_job_status
            await update_job_status(
                session=session,
                job_id=job_id,
                status="cancelled",
                completed_at=datetime.utcnow()
            )
            
            # Log cancellation event
            await log_analytics_event(
                session=session,
                user_id=current_user.user_id,
                job_id=job_id,
                event_type="job_cancelled"
            )
            
            logger.info(f"Cancelled job {job_id} for user {current_user.user_id}")
            
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
            detail=f"Failed to cancel job: {str(e)}"
        )


async def process_word_export_job(job_data: dict):
    """Background task to process Word export job."""
    job_id = job_data["job_id"]
    
    try:
        logger.info(f"Processing Word export job {job_id}")
        
        # Generate the Word document
        success, file_path, error_message = await word_document_generator.generate_document(
            job_id=job_id,
            user_id=job_data["user_id"],
            document_config=job_data["document_config"],
            data_source=job_data["data_source"],
            output_format=job_data["output_format"]
        )
        
        if success:
            logger.info(f"Word export job {job_id} completed successfully")
        else:
            logger.error(f"Word export job {job_id} failed: {error_message}")
        
        # Mark job as completed in queue
        queue_manager = get_queue_manager()
        await queue_manager.complete_job("word_export", job_data)
        
    except Exception as e:
        logger.error(f"Failed to process Word export job {job_id}: {e}")
        
        # Update job status to failed
        try:
            async with get_db_session() as session:
                from app.core.database import update_job_status
                await update_job_status(
                    session=session,
                    job_id=job_id,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
        except Exception as db_error:
            logger.error(f"Failed to update job status for {job_id}: {db_error}")


# Export router
__all__ = ["router"]