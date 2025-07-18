"""
Excel Export API Endpoints.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, execute_query
from app.models.excel_models import (
    ExcelExportRequest, BulkExcelExportRequest, ExcelJobResponse,
    ExcelJobStatusResponse, ExcelAnalytics, ExcelCapabilities,
    JobStatus, ExcelFormat, Theme, ChartType
)
from app.models.user_models import User
from app.services.excel_generator import excel_generator
from app.utils.auth import get_current_user_full
from app.utils.rate_limiter import check_rate_limit


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ExcelJobResponse)
async def generate_excel(
    request: ExcelExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_full),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate Excel file from configuration."""
    # Check rate limit
    if not await check_rate_limit(f"excel_generation:{current_user.id}", limit=100):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Create job record
        query = """
            INSERT INTO excel_jobs 
            (user_id, job_name, workbook_config, data_source, output_format, theme, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        job_id = await execute_query(
            query,
            current_user.id,
            request.job_name,
            request.workbook_config.dict(),
            request.data_source,
            request.output_format.value,
            request.theme.value,
            JobStatus.PENDING.value,
            datetime.utcnow()
        )
        
        # Start background generation
        background_tasks.add_task(
            excel_generator.generate_excel,
            job_id,
            request.workbook_config,
            request.data_source,
            request.output_format,
            request.theme,
            request.validation_rules
        )
        
        return ExcelJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Excel generation started",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to start Excel generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start Excel generation: {str(e)}"
        )


@router.post("/bulk-generate", response_model=List[ExcelJobResponse])
async def bulk_generate_excel(
    request: BulkExcelExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_full),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate multiple Excel files in bulk."""
    # Check rate limit
    if not await check_rate_limit(f"bulk_excel_generation:{current_user.id}", limit=10):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        responses = []
        
        for job_data in request.jobs:
            # Create job record
            query = """
                INSERT INTO excel_jobs 
                (user_id, job_name, workbook_config, data_source, output_format, theme, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            job_id = await execute_query(
                query,
                current_user.id,
                job_data["job_name"],
                job_data["workbook_config"],
                job_data["data_source"],
                request.output_format.value,
                request.theme.value,
                JobStatus.PENDING.value,
                datetime.utcnow()
            )
            
            # Start background generation
            background_tasks.add_task(
                excel_generator.generate_excel,
                job_id,
                job_data["workbook_config"],
                job_data["data_source"],
                request.output_format,
                request.theme,
                job_data.get("validation_rules", [])
            )
            
            responses.append(ExcelJobResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="Excel generation started",
                created_at=datetime.utcnow()
            ))
        
        return responses
        
    except Exception as e:
        logger.error(f"Failed to start bulk Excel generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bulk Excel generation: {str(e)}"
        )


@router.get("/jobs", response_model=Dict[str, Any])
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    output_format: Optional[ExcelFormat] = Query(None, description="Filter by format"),
    theme: Optional[Theme] = Query(None, description="Filter by theme"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user_full)
):
    """List user's Excel jobs."""
    try:
        # Build query
        conditions = ["user_id = $1"]
        params = [current_user.id]
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
        count_query = f"""
            SELECT COUNT(*) as total
            FROM excel_jobs
            WHERE {where_clause}
        """
        total = await execute_query(count_query, *params)
        
        # Get jobs
        offset = (page - 1) * page_size
        jobs_query = f"""
            SELECT id, job_name, status, output_format, theme, file_path, file_size,
                   row_count, worksheet_count, chart_count, error_message,
                   generation_time_ms, created_at, started_at, completed_at
            FROM excel_jobs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {page_size} OFFSET {offset}
        """
        jobs = await execute_query(jobs_query, *params)
        
        return {
            "jobs": jobs if isinstance(jobs, list) else [jobs] if jobs else [],
            "total": total if isinstance(total, int) else total.get("total", 0),
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to list Excel jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Excel jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=ExcelJobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get Excel job details."""
    try:
        query = """
            SELECT id, job_name, status, output_format, theme, file_path, file_size,
                   row_count, worksheet_count, chart_count, error_message,
                   generation_time_ms, created_at, started_at, completed_at
            FROM excel_jobs
            WHERE id = $1 AND user_id = $2
        """
        job = await execute_query(query, job_id, current_user.id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return ExcelJobResponse(
            job_id=job["id"],
            status=JobStatus(job["status"]),
            message="Job details retrieved",
            file_path=job["file_path"],
            file_size=job["file_size"],
            row_count=job["row_count"],
            worksheet_count=job["worksheet_count"],
            chart_count=job["chart_count"],
            generation_time_ms=job["generation_time_ms"],
            created_at=job["created_at"],
            completed_at=job["completed_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Excel job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Excel job: {str(e)}"
        )


@router.get("/jobs/{job_id}/status", response_model=ExcelJobStatusResponse)
async def get_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get Excel job status."""
    try:
        # Check if job belongs to user
        query = """
            SELECT id, user_id FROM excel_jobs
            WHERE id = $1 AND user_id = $2
        """
        job = await execute_query(query, job_id, current_user.id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get status from generator
        status = await excel_generator.get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Job status not found")
        
        return ExcelJobStatusResponse(
            job_id=job_id,
            status=JobStatus(status.get("status", "unknown")),
            runtime_seconds=status.get("runtime_seconds"),
            error_message=status.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Excel job status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Excel job status: {str(e)}"
        )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Cancel Excel job."""
    try:
        # Check if job belongs to user
        query = """
            SELECT id, user_id, status FROM excel_jobs
            WHERE id = $1 AND user_id = $2
        """
        job = await execute_query(query, job_id, current_user.id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job can be cancelled
        if job["status"] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")
        
        # Cancel job
        success = await excel_generator.cancel_job(job_id)
        
        if success:
            return {"message": "Job cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel Excel job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel Excel job: {str(e)}"
        )


@router.get("/jobs/{job_id}/download")
async def download_job_file(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Download Excel job file."""
    try:
        # Check if job belongs to user
        query = """
            SELECT id, user_id, job_name, status, file_path FROM excel_jobs
            WHERE id = $1 AND user_id = $2
        """
        job = await execute_query(query, job_id, current_user.id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        if not job["file_path"] or not os.path.exists(job["file_path"]):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        file_path = job["file_path"]
        if file_path.endswith(".xlsx"):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif file_path.endswith(".xls"):
            media_type = "application/vnd.ms-excel"
        elif file_path.endswith(".csv"):
            media_type = "text/csv"
        elif file_path.endswith(".ods"):
            media_type = "application/vnd.oasis.opendocument.spreadsheet"
        else:
            media_type = "application/octet-stream"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"{job['job_name']}.{file_path.split('.')[-1]}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download Excel file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download Excel file: {str(e)}"
        )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Delete Excel job."""
    try:
        # Check if job belongs to user
        query = """
            SELECT id, user_id, status, file_path FROM excel_jobs
            WHERE id = $1 AND user_id = $2
        """
        job = await execute_query(query, job_id, current_user.id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Cancel job if running
        if job["status"] in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]:
            await excel_generator.cancel_job(job_id)
        
        # Delete file if exists
        if job["file_path"] and os.path.exists(job["file_path"]):
            try:
                os.remove(job["file_path"])
            except Exception as e:
                logger.warning(f"Failed to delete file {job['file_path']}: {e}")
        
        # Delete job record
        query = """
            DELETE FROM excel_jobs
            WHERE id = $1
        """
        await execute_query(query, job_id)
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete Excel job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Excel job: {str(e)}"
        )


@router.get("/analytics", response_model=ExcelAnalytics)
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_user_full)
):
    """Get user's Excel analytics."""
    try:
        # Basic statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                AVG(generation_time_ms) as avg_generation_time,
                AVG(file_size) as avg_file_size,
                AVG(row_count) as avg_row_count
            FROM excel_jobs
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
        """
        stats = await execute_query(stats_query, current_user.id, days)
        
        # Usage by format
        format_query = """
            SELECT output_format, COUNT(*) as count
            FROM excel_jobs
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY output_format
        """
        format_stats = await execute_query(format_query, current_user.id, days)
        
        # Usage by theme
        theme_query = """
            SELECT theme, COUNT(*) as count
            FROM excel_jobs
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY theme
        """
        theme_stats = await execute_query(theme_query, current_user.id, days)
        
        # Daily usage
        daily_query = """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM excel_jobs
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        daily_stats = await execute_query(daily_query, current_user.id, days)
        
        # Calculate success rate
        total_jobs = stats.get("total_jobs", 0)
        successful_jobs = stats.get("successful_jobs", 0)
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Format usage data
        usage_by_format = {}
        if format_stats:
            if isinstance(format_stats, list):
                usage_by_format = {stat["output_format"]: stat["count"] for stat in format_stats}
            else:
                usage_by_format = {format_stats["output_format"]: format_stats["count"]}
        
        usage_by_theme = {}
        if theme_stats:
            if isinstance(theme_stats, list):
                usage_by_theme = {stat["theme"]: stat["count"] for stat in theme_stats}
            else:
                usage_by_theme = {theme_stats["theme"]: theme_stats["count"]}
        
        return ExcelAnalytics(
            period_days=days,
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=stats.get("failed_jobs", 0),
            success_rate=success_rate,
            avg_generation_time=stats.get("avg_generation_time", 0) or 0,
            avg_file_size=stats.get("avg_file_size", 0) or 0,
            avg_row_count=stats.get("avg_row_count", 0) or 0,
            usage_by_format=usage_by_format,
            usage_by_theme=usage_by_theme,
            top_templates=[],  # TODO: Implement template analytics
            daily_usage=daily_stats if isinstance(daily_stats, list) else [daily_stats] if daily_stats else []
        )
        
    except Exception as e:
        logger.error(f"Failed to get Excel analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Excel analytics: {str(e)}"
        )


@router.get("/formats")
async def get_supported_formats():
    """Get supported Excel formats."""
    return {
        "formats": [
            {
                "format": "xlsx",
                "name": "Excel Workbook (.xlsx)",
                "description": "Modern Excel format with advanced features"
            },
            {
                "format": "xls",
                "name": "Excel 97-2003 (.xls)",
                "description": "Legacy Excel format"
            },
            {
                "format": "csv",
                "name": "Comma Separated Values (.csv)",
                "description": "Plain text format"
            },
            {
                "format": "ods",
                "name": "OpenDocument Spreadsheet (.ods)",
                "description": "Open standard format"
            }
        ]
    }


@router.get("/capabilities", response_model=ExcelCapabilities)
async def get_capabilities():
    """Get Excel service capabilities."""
    from app.core.config import settings
    
    return ExcelCapabilities(
        supported_formats=[format.value for format in ExcelFormat],
        supported_themes=[theme.value for theme in Theme],
        supported_chart_types=[chart.value for chart in ChartType],
        max_file_size_mb=settings.EXCEL_MAX_FILE_SIZE_MB,
        max_rows=settings.EXCEL_MAX_ROWS,
        max_columns=settings.EXCEL_MAX_COLUMNS,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
        max_worksheets=100,
        max_charts_per_worksheet=20,
        features={
            "formatting": True,
            "charts": True,
            "formulas": settings.ENABLE_FORMULAS,
            "data_validation": settings.ENABLE_DATA_VALIDATION,
            "themes": True,
            "protection": True,
            "multiple_worksheets": True,
            "bulk_export": True,
            "template_system": True
        }
    )