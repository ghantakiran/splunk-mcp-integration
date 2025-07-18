#!/usr/bin/env python3
"""
HTML Report API endpoints.

This module provides REST API endpoints for HTML report generation,
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
from app.models.html_models import (
    HTMLReportRequest,
    BulkHTMLReportRequest,
    JobResponse,
    JobStatusResponse,
    JobDetailsResponse,
    JobListResponse,
    AnalyticsResponse,
    CapabilitiesResponse,
    JobStatus,
    OutputFormat,
    Template,
    ChartType,
    InteractiveFeature
)
from app.services.html_generator import html_report_generator
from app.utils.auth import get_current_user_full
from app.utils.rate_limiter import check_rate_limit


logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=JobResponse, summary="Generate HTML report")
async def generate_html_report(
    request: HTMLReportRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Generate an HTML report."""
    user_id = current_user["id"]
    
    # Check rate limit
    rate_limit_ok = await check_rate_limit(f"user:{user_id}", settings.RATE_LIMIT_REQUESTS_PER_MINUTE, 60)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        # Create job record in database
        from app.core.database import get_db_session_dependency, create_job
        async with get_db_session_dependency() as session:
            job = await create_job(
                session,
                request.job_name,
                user_id,
                request.report_config.dict(),
                request.data_source.dict(),
                request.output_format.value,
                expires_at
            )
            job_id = job.id
        
        # Start background generation
        background_tasks.add_task(
            html_report_generator.generate_report,
            job_id,
            user_id,
            request.report_config,
            request.data_source.dict(),
            request.output_format
        )
        
        logger.info("HTML report generation job created", job_id=job_id, user_id=user_id)
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="HTML report generation started",
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error("Failed to create HTML report generation job", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to create generation job")


@router.post("/bulk-generate", response_model=List[JobResponse], summary="Generate multiple HTML reports")
async def bulk_generate_html_reports(
    request: BulkHTMLReportRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Generate multiple HTML reports in bulk."""
    user_id = current_user["id"]
    
    # Check rate limit
    rate_limit_ok = await check_rate_limit(f"user:{user_id}", settings.RATE_LIMIT_REQUESTS_PER_MINUTE, 60)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        job_responses = []
        
        for i, job_request in enumerate(request.jobs):
            # Apply bulk settings
            job_request.output_format = request.output_format
            job_request.report_config.template = request.template
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(hours=job_request.expires_in_hours)
            
            # Create job record (mock implementation)
            job_id = i + 1  # In real implementation, this would come from database
            
            # Start background generation
            background_tasks.add_task(
                html_report_generator.generate_report,
                job_id,
                user_id,
                job_request.report_config,
                job_request.data_source.dict(),
                job_request.output_format
            )
            
            job_responses.append(JobResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="HTML report generation started",
                created_at=datetime.utcnow()
            ))
        
        logger.info("Bulk HTML report generation jobs created", count=len(job_responses), user_id=user_id)
        
        return job_responses
    
    except Exception as e:
        logger.error("Failed to create bulk HTML report generation jobs", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to create bulk generation jobs")


@router.get("/jobs", response_model=JobListResponse, summary="List HTML report jobs")
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    output_format: Optional[OutputFormat] = Query(None, description="Filter by output format"),
    template: Optional[Template] = Query(None, description="Filter by template"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """List HTML report jobs for the current user."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation - in real implementation, this would query the database
        jobs = [
            JobDetailsResponse(
                job_id=1,
                job_name="Sample Report",
                status=JobStatus.COMPLETED,
                output_format=OutputFormat.HTML,
                template=Template.MODERN,
                file_path="/tmp/html-reports/report_1.html",
                file_size=1024576,
                chart_count=3,
                table_count=2,
                section_count=5,
                generation_time_ms=5000,
                created_at=datetime.utcnow() - timedelta(hours=1),
                started_at=datetime.utcnow() - timedelta(hours=1),
                completed_at=datetime.utcnow() - timedelta(minutes=50),
                expires_at=datetime.utcnow() + timedelta(hours=23)
            )
        ]
        
        return JobListResponse(
            total=len(jobs),
            page=page,
            page_size=page_size,
            jobs=jobs
        )
    
    except Exception as e:
        logger.error("Failed to list jobs", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/jobs/{job_id}", response_model=JobDetailsResponse, summary="Get HTML report job details")
async def get_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get HTML report job details."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation - in real implementation, this would query the database
        if job_id == 1:
            return JobDetailsResponse(
                job_id=1,
                job_name="Sample Report",
                status=JobStatus.COMPLETED,
                output_format=OutputFormat.HTML,
                template=Template.MODERN,
                file_path="/tmp/html-reports/report_1.html",
                file_size=1024576,
                chart_count=3,
                table_count=2,
                section_count=5,
                generation_time_ms=5000,
                created_at=datetime.utcnow() - timedelta(hours=1),
                started_at=datetime.utcnow() - timedelta(hours=1),
                completed_at=datetime.utcnow() - timedelta(minutes=50),
                expires_at=datetime.utcnow() + timedelta(hours=23)
            )
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job details", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to get job details")


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse, summary="Get HTML report job status")
async def get_job_status(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get HTML report job status and progress."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress_percentage=100.0,
            current_section="Completed",
            total_sections=5,
            runtime_seconds=5.0
        )
    
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post("/jobs/{job_id}/cancel", summary="Cancel HTML report job")
async def cancel_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Cancel an HTML report job."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation
        return {"message": "Job cancelled successfully"}
    
    except Exception as e:
        logger.error("Failed to cancel job", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs/{job_id}/download", summary="Download HTML report file")
async def download_job_file(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Download the generated HTML report file."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation - in real implementation, this would check database and file existence
        file_path = f"{settings.HTML_OUTPUT_DIR}/report_{job_id}.html"
        
        if not os.path.exists(file_path):
            # Create a sample file for demo
            sample_content = """
            <!DOCTYPE html>
            <html>
            <head><title>Sample Report</title></head>
            <body>
                <h1>Sample HTML Report</h1>
                <p>This is a generated HTML report.</p>
            </body>
            </html>
            """
            with open(file_path, 'w') as f:
                f.write(sample_content)
        
        # Determine media type
        media_type = "text/html"
        filename = f"report_{job_id}.html"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
    
    except Exception as e:
        logger.error("Failed to download file", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete("/jobs/{job_id}", summary="Delete HTML report job")
async def delete_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Delete an HTML report job and its associated file."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation
        return {"message": "Job deleted successfully"}
    
    except Exception as e:
        logger.error("Failed to delete job", job_id=job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to delete job")


@router.get("/analytics", response_model=AnalyticsResponse, summary="Get HTML report analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get analytics for HTML report usage."""
    user_id = current_user["id"]
    
    try:
        # Mock implementation
        return AnalyticsResponse(
            period_days=days,
            total_jobs=150,
            successful_jobs=145,
            failed_jobs=5,
            success_rate=96.67,
            avg_generation_time=4500.0,
            avg_file_size=2048000.0,
            avg_chart_count=2.5,
            avg_table_count=1.8,
            usage_by_format={"html": 120, "pdf": 20, "png": 10},
            usage_by_template={"modern": 90, "classic": 30, "minimal": 20, "dark": 10},
            daily_usage=[
                {"date": "2024-01-15", "count": 5},
                {"date": "2024-01-16", "count": 8},
                {"date": "2024-01-17", "count": 12}
            ]
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
    """Get HTML report service capabilities."""
    return CapabilitiesResponse(
        supported_formats=[fmt.value for fmt in OutputFormat],
        supported_templates=[template.value for template in Template],
        supported_chart_types=[chart.value for chart in ChartType],
        supported_interactive_features=[feature.value for feature in InteractiveFeature],
        max_file_size_mb=settings.HTML_MAX_FILE_SIZE_MB,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
        features=[
            "Interactive charts with Plotly.js",
            "Responsive data tables",
            "Custom templates and themes",
            "Real-time filtering and search",
            "Export capabilities",
            "Print-friendly CSS",
            "Dark mode support",
            "Cross-filtering between components",
            "Drill-down interactions",
            "Full-screen mode",
            "Custom branding support"
        ]
    )