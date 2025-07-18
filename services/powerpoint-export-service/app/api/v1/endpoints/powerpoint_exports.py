#!/usr/bin/env python3
"""
PowerPoint export API endpoints.

This module provides REST API endpoints for PowerPoint generation,
job management, and analytics.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from structlog import get_logger

from app.core.config import settings
from app.core.database import execute_query
from app.models.powerpoint_models import (
    PowerPointExportRequest,
    BulkPowerPointExportRequest,
    JobResponse,
    JobStatusResponse,
    JobDetailsResponse,
    JobListResponse,
    AnalyticsResponse,
    CapabilitiesResponse,
    JobStatus,
    OutputFormat,
    Theme,
    ChartType,
    AnimationType,
    TransitionType
)
from app.services.powerpoint_generator import powerpoint_generator
from app.utils.auth import get_current_user_full
from app.utils.rate_limiter import check_rate_limit


logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=JobResponse, summary="Generate PowerPoint presentation")
async def generate_powerpoint(
    request: PowerPointExportRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Generate a PowerPoint presentation."""
    user_id = current_user["id"]
    
    # Check rate limit
    rate_limit_ok = await check_rate_limit(f"user:{user_id}", settings.RATE_LIMIT_REQUESTS_PER_MINUTE, 60)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        # Create job record
        query = """
            INSERT INTO ppt_export_jobs (
                job_name, user_id, presentation_config, data_source, 
                output_format, theme, expires_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        
        job_id = await execute_query(
            query,
            request.job_name,
            user_id,
            request.presentation_config.json(),
            request.data_source.json(),
            request.output_format.value,
            request.presentation_config.theme.value,
            expires_at,
            fetch="val"
        )
        
        # Start background generation
        background_tasks.add_task(
            powerpoint_generator.generate_presentation,
            job_id,
            user_id,
            request.presentation_config,
            request.output_format,
            request.data_source.dict()
        )
        
        logger.info("PowerPoint generation job created", job_id=job_id, user_id=user_id)
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="PowerPoint generation started",
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error("Failed to create PowerPoint generation job", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to create generation job")


@router.post("/bulk-generate", response_model=List[JobResponse], summary="Generate multiple PowerPoint presentations")
async def bulk_generate_powerpoint(
    request: BulkPowerPointExportRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Generate multiple PowerPoint presentations in bulk."""
    user_id = current_user["id"]
    
    # Check rate limit
    rate_limit_ok = await check_rate_limit(f"user:{user_id}", settings.RATE_LIMIT_REQUESTS_PER_MINUTE, 60)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        job_responses = []
        
        for job_request in request.jobs:
            # Apply bulk settings
            job_request.output_format = request.output_format
            job_request.presentation_config.theme = request.theme
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(hours=job_request.expires_in_hours)
            
            # Create job record
            query = """
                INSERT INTO ppt_export_jobs (
                    job_name, user_id, presentation_config, data_source, 
                    output_format, theme, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """
            
            job_id = await execute_query(
                query,
                job_request.job_name,
                user_id,
                job_request.presentation_config.json(),
                job_request.data_source.json(),
                job_request.output_format.value,
                job_request.presentation_config.theme.value,
                expires_at,
                fetch="val"
            )
            
            # Start background generation
            background_tasks.add_task(
                powerpoint_generator.generate_presentation,
                job_id,
                user_id,
                job_request.presentation_config,
                job_request.output_format,
                job_request.data_source.dict()
            )
            
            job_responses.append(JobResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="PowerPoint generation started",
                created_at=datetime.utcnow()
            ))
        
        logger.info("Bulk PowerPoint generation jobs created", count=len(job_responses), user_id=user_id)
        
        return job_responses
    
    except Exception as e:
        logger.error("Failed to create bulk PowerPoint generation jobs", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to create bulk generation jobs")


@router.get("/jobs", response_model=JobListResponse, summary="List PowerPoint export jobs")
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    output_format: Optional[OutputFormat] = Query(None, description="Filter by output format"),
    theme: Optional[Theme] = Query(None, description="Filter by theme"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """List PowerPoint export jobs for the current user."""
    user_id = current_user["id"]
    
    try:
        # Build filter conditions
        conditions = ["user_id = $1"]
        params = [user_id]
        param_count = 1
        
        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status.value)
        
        if output_format:
            param_count += 1
            conditions.append(f"output_format = ${param_count}")
            params.append(output_format.value)
        
        if theme:
            param_count += 1
            conditions.append(f"theme = ${param_count}")
            params.append(theme.value)
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ppt_export_jobs WHERE {where_clause}"
        total = await execute_query(count_query, *params, fetch="val")
        
        # Get jobs
        offset = (page - 1) * page_size
        jobs_query = f"""
            SELECT id, job_name, status, output_format, theme, file_path, file_size,
                   slide_count, chart_count, animation_count, error_message, 
                   generation_time_ms, created_at, started_at, completed_at, expires_at
            FROM ppt_export_jobs 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        params.extend([page_size, offset])
        
        jobs_data = await execute_query(jobs_query, *params, fetch="all")
        
        # Convert to response models
        jobs = [
            JobDetailsResponse(
                job_id=job["id"],
                job_name=job["job_name"],
                status=JobStatus(job["status"]),
                output_format=OutputFormat(job["output_format"]),
                theme=Theme(job["theme"]),
                file_path=job["file_path"],
                file_size=job["file_size"],
                slide_count=job["slide_count"],
                chart_count=job["chart_count"],
                animation_count=job["animation_count"],
                error_message=job["error_message"],
                generation_time_ms=job["generation_time_ms"],
                created_at=job["created_at"],
                started_at=job["started_at"],
                completed_at=job["completed_at"],
                expires_at=job["expires_at"]
            )
            for job in jobs_data
        ]
        
        return JobListResponse(
            total=total,
            page=page,
            page_size=page_size,
            jobs=jobs
        )
    
    except Exception as e:
        logger.error("Failed to list jobs", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/jobs/{job_id}", response_model=JobDetailsResponse, summary="Get PowerPoint export job details")
async def get_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get PowerPoint export job details."""
    user_id = current_user["id"]
    
    try:
        query = """
            SELECT id, job_name, status, output_format, theme, file_path, file_size,
                   slide_count, chart_count, animation_count, error_message, 
                   generation_time_ms, created_at, started_at, completed_at, expires_at
            FROM ppt_export_jobs 
            WHERE id = $1 AND user_id = $2
        """
        
        job_data = await execute_query(query, job_id, user_id, fetch="one")
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobDetailsResponse(
            job_id=job_data["id"],
            job_name=job_data["job_name"],
            status=JobStatus(job_data["status"]),
            output_format=OutputFormat(job_data["output_format"]),
            theme=Theme(job_data["theme"]),
            file_path=job_data["file_path"],
            file_size=job_data["file_size"],
            slide_count=job_data["slide_count"],
            chart_count=job_data["chart_count"],
            animation_count=job_data["animation_count"],
            error_message=job_data["error_message"],
            generation_time_ms=job_data["generation_time_ms"],
            created_at=job_data["created_at"],
            started_at=job_data["started_at"],
            completed_at=job_data["completed_at"],
            expires_at=job_data["expires_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job details", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to get job details")


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse, summary="Get PowerPoint export job status")
async def get_job_status(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get PowerPoint export job status and progress."""
    user_id = current_user["id"]
    
    try:
        # Verify job ownership
        verify_query = "SELECT id FROM ppt_export_jobs WHERE id = $1 AND user_id = $2"
        job_exists = await execute_query(verify_query, job_id, user_id, fetch="one")
        
        if not job_exists:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get live status from generator
        status_data = await powerpoint_generator.get_job_status(job_id)
        
        if status_data:
            return JobStatusResponse(**status_data)
        
        # Fall back to database status
        db_query = "SELECT status FROM ppt_export_jobs WHERE id = $1"
        db_status = await execute_query(db_query, job_id, fetch="val")
        
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(db_status) if db_status else JobStatus.PENDING
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post("/jobs/{job_id}/cancel", summary="Cancel PowerPoint export job")
async def cancel_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Cancel a PowerPoint export job."""
    user_id = current_user["id"]
    
    try:
        # Verify job ownership and get current status
        verify_query = "SELECT status FROM ppt_export_jobs WHERE id = $1 AND user_id = $2"
        job_data = await execute_query(verify_query, job_id, user_id, fetch="one")
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        current_status = JobStatus(job_data["status"])
        
        if current_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")
        
        # Cancel the job
        success = await powerpoint_generator.cancel_job(job_id)
        
        if success:
            return {"message": "Job cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Job could not be cancelled")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs/{job_id}/download", summary="Download PowerPoint export file")
async def download_job_file(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Download the generated PowerPoint file."""
    user_id = current_user["id"]
    
    try:
        # Get job details
        query = """
            SELECT job_name, status, file_path, output_format 
            FROM ppt_export_jobs 
            WHERE id = $1 AND user_id = $2
        """
        
        job_data = await execute_query(query, job_id, user_id, fetch="one")
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        file_path = job_data["file_path"]
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        output_format = job_data["output_format"]
        media_type_mapping = {
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg"
        }
        media_type = media_type_mapping.get(output_format, "application/octet-stream")
        
        # Generate filename
        job_name = job_data["job_name"].replace(" ", "_")
        filename = f"{job_name}_{job_id}.{output_format}"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download file", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete("/jobs/{job_id}", summary="Delete PowerPoint export job")
async def delete_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Delete a PowerPoint export job and its associated file."""
    user_id = current_user["id"]
    
    try:
        # Get job details
        query = "SELECT status, file_path FROM ppt_export_jobs WHERE id = $1 AND user_id = $2"
        job_data = await execute_query(query, job_id, user_id, fetch="one")
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Cancel if still running
        if job_data["status"] in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]:
            await powerpoint_generator.cancel_job(job_id)
        
        # Delete file if exists
        file_path = job_data["file_path"]
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete job record
        delete_query = "DELETE FROM ppt_export_jobs WHERE id = $1 AND user_id = $2"
        await execute_query(delete_query, job_id, user_id, fetch="none")
        
        return {"message": "Job deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete job", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to delete job")


@router.get("/analytics", response_model=AnalyticsResponse, summary="Get PowerPoint export analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get analytics for PowerPoint export usage."""
    user_id = current_user["id"]
    
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Basic statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                AVG(CASE WHEN generation_time_ms IS NOT NULL THEN generation_time_ms END) as avg_generation_time,
                AVG(CASE WHEN file_size IS NOT NULL THEN file_size END) as avg_file_size,
                AVG(CASE WHEN slide_count IS NOT NULL THEN slide_count END) as avg_slide_count
            FROM ppt_export_jobs 
            WHERE user_id = $1 AND created_at >= $2
        """
        
        stats = await execute_query(stats_query, user_id, start_date, fetch="one")
        
        # Usage by format
        format_query = """
            SELECT output_format, COUNT(*) as count
            FROM ppt_export_jobs 
            WHERE user_id = $1 AND created_at >= $2
            GROUP BY output_format
            ORDER BY count DESC
        """
        
        format_stats = await execute_query(format_query, user_id, start_date, fetch="all")
        
        # Usage by theme
        theme_query = """
            SELECT theme, COUNT(*) as count
            FROM ppt_export_jobs 
            WHERE user_id = $1 AND created_at >= $2
            GROUP BY theme
            ORDER BY count DESC
        """
        
        theme_stats = await execute_query(theme_query, user_id, start_date, fetch="all")
        
        # Daily usage
        daily_query = """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM ppt_export_jobs 
            WHERE user_id = $1 AND created_at >= $2
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        
        daily_stats = await execute_query(daily_query, user_id, start_date, fetch="all")
        
        # Calculate success rate
        total_jobs = stats["total_jobs"] or 0
        successful_jobs = stats["successful_jobs"] or 0
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return AnalyticsResponse(
            period_days=days,
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=stats["failed_jobs"] or 0,
            success_rate=round(success_rate, 2),
            avg_generation_time=stats["avg_generation_time"] or 0,
            avg_file_size=stats["avg_file_size"] or 0,
            avg_slide_count=stats["avg_slide_count"] or 0,
            usage_by_format={row["output_format"]: row["count"] for row in format_stats},
            usage_by_theme={row["theme"]: row["count"] for row in theme_stats},
            daily_usage=[{"date": row["date"], "count": row["count"]} for row in daily_stats]
        )
    
    except Exception as e:
        logger.error("Failed to get analytics", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to get analytics")


@router.get("/formats", summary="Get supported output formats")
async def get_supported_formats():
    """Get list of supported output formats."""
    formats = [
        {"format": fmt.value, "name": fmt.value.upper(), "description": f"{fmt.value.upper()} format"}
        for fmt in OutputFormat
    ]
    return {"formats": formats}


@router.get("/capabilities", response_model=CapabilitiesResponse, summary="Get service capabilities")
async def get_capabilities():
    """Get PowerPoint export service capabilities."""
    return CapabilitiesResponse(
        supported_formats=[fmt.value for fmt in OutputFormat],
        supported_themes=[theme.value for theme in Theme],
        supported_chart_types=[chart.value for chart in ChartType],
        supported_animations=[anim.value for anim in AnimationType],
        supported_transitions=[trans.value for trans in TransitionType],
        max_file_size_mb=settings.PPT_MAX_FILE_SIZE_MB,
        max_slides=settings.PPT_MAX_SLIDES,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
        features=[
            "Custom themes",
            "Chart embedding",
            "Image support",
            "Table creation",
            "Animations",
            "Transitions",
            "Multiple layouts",
            "Batch generation",
            "Format conversion",
            "Template system"
        ]
    )
