"""
PDF export endpoints for PDF Export Service.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
import structlog

from app.models.pdf_models import (
    PDFGenerationRequest, PDFGenerationResponse, PDFJob, PDFJobList,
    PDFBulkGenerationRequest, JobStatus, OutputFormat
)
from app.models.user_models import User
from app.utils.auth import get_current_user_full, require_permission
from app.utils.rate_limiter import check_rate_limit, get_rate_limit_headers
from app.services.pdf_generator import pdf_generator
from app.core.database import execute_query
from app.core.redis_client import get_redis_connection

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/pdf-exports", tags=["PDF Exports"])


@router.post("/generate", response_model=PDFGenerationResponse)
async def generate_pdf(
    request: PDFGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_full)
):
    """Generate PDF from template and data."""
    try:
        # Check rate limit
        if not await check_rate_limit(str(current_user.id), "pdf_generation"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for PDF generation"
            )
        
        # Create job record
        job_id = await execute_query(
            """
            INSERT INTO pdf_export_jobs (user_id, template_id, job_name, status, parameters, 
                                       data_source, output_format)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            current_user.id,
            request.template_id,
            request.job_name,
            JobStatus.PENDING.value,
            request.parameters,
            request.data_source,
            request.output_format.value,
            fetchval=True
        )
        
        # Start PDF generation in background
        background_tasks.add_task(
            pdf_generator.generate_pdf,
            job_id,
            request.template_id,
            request.parameters,
            request.data_source,
            request.output_format,
            request.layout_config
        )
        
        # Log generation request
        logger.info(
            "PDF generation requested",
            job_id=job_id,
            user_id=current_user.id,
            template_id=request.template_id,
            output_format=request.output_format.value
        )
        
        return PDFGenerationResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="PDF generation started",
            created_at=datetime.now()
        )
        
    except Exception as e:
        logger.error("PDF generation request failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/bulk-generate", response_model=List[PDFGenerationResponse])
async def bulk_generate_pdf(
    request: PDFBulkGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_full)
):
    """Generate multiple PDFs from template and data."""
    try:
        # Check rate limit
        if not await check_rate_limit(str(current_user.id), "bulk_operations"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for bulk operations"
            )
        
        responses = []
        
        for i, job_data in enumerate(request.jobs):
            # Create job record
            job_id = await execute_query(
                """
                INSERT INTO pdf_export_jobs (user_id, template_id, job_name, status, parameters, 
                                           data_source, output_format)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                current_user.id,
                request.template_id,
                job_data.get('job_name', f'Bulk Job {i+1}'),
                JobStatus.PENDING.value,
                job_data.get('parameters', {}),
                job_data.get('data_source', {}),
                request.output_format.value,
                fetchval=True
            )
            
            # Start PDF generation in background
            background_tasks.add_task(
                pdf_generator.generate_pdf,
                job_id,
                request.template_id,
                job_data.get('parameters', {}),
                job_data.get('data_source', {}),
                request.output_format
            )
            
            responses.append(PDFGenerationResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="PDF generation started",
                created_at=datetime.now()
            ))
        
        logger.info(
            "Bulk PDF generation requested",
            job_count=len(request.jobs),
            user_id=current_user.id,
            template_id=request.template_id
        )
        
        return responses
        
    except Exception as e:
        logger.error("Bulk PDF generation failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Bulk PDF generation failed: {str(e)}")


@router.get("/jobs", response_model=PDFJobList)
async def list_jobs(
    status: Optional[JobStatus] = None,
    template_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_full)
):
    """List PDF export jobs for current user."""
    try:
        # Build query conditions
        conditions = ["user_id = $1"]
        params = [current_user.id]
        param_count = 2
        
        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status.value)
            param_count += 1
        
        if template_id:
            conditions.append(f"template_id = ${param_count}")
            params.append(template_id)
            param_count += 1
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        total_count = await execute_query(
            f"SELECT COUNT(*) FROM pdf_export_jobs WHERE {where_clause}",
            *params,
            fetchval=True
        )
        
        # Get jobs
        offset = (page - 1) * page_size
        jobs = await execute_query(
            f"""
            SELECT * FROM pdf_export_jobs 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
            """,
            *params,
            page_size,
            offset,
            fetch=True
        )
        
        return PDFJobList(
            jobs=[PDFJob(**dict(job)) for job in jobs],
            total=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list jobs", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/jobs/{job_id}", response_model=PDFJob)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get PDF export job details."""
    try:
        job = await execute_query(
            "SELECT * FROM pdf_export_jobs WHERE id = $1 AND user_id = $2",
            job_id,
            current_user.id,
            fetchrow=True
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return PDFJob(**dict(job))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job", job_id=job_id, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get PDF export job status."""
    try:
        # Check job ownership
        job = await execute_query(
            "SELECT id FROM pdf_export_jobs WHERE id = $1 AND user_id = $2",
            job_id,
            current_user.id,
            fetchrow=True
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get status from generator
        status = await pdf_generator.get_job_status(job_id)
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Cancel PDF export job."""
    try:
        # Check job ownership
        job = await execute_query(
            "SELECT id, status FROM pdf_export_jobs WHERE id = $1 AND user_id = $2",
            job_id,
            current_user.id,
            fetchrow=True
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")
        
        # Cancel job
        cancelled = await pdf_generator.cancel_job(job_id)
        
        if cancelled:
            logger.info("Job cancelled", job_id=job_id, user_id=current_user.id)
            return {"message": "Job cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Job could not be cancelled")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", job_id=job_id, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs/{job_id}/download")
async def download_job_file(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Download PDF export job file."""
    try:
        # Get job details
        job = await execute_query(
            "SELECT * FROM pdf_export_jobs WHERE id = $1 AND user_id = $2",
            job_id,
            current_user.id,
            fetchrow=True
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        if not job['file_path'] or not os.path.exists(job['file_path']):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        file_extension = os.path.splitext(job['file_path'])[1].lower()
        media_type_map = {
            '.pdf': 'application/pdf',
            '.html': 'text/html',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        # Generate download filename
        download_filename = f"{job['job_name']}{file_extension}"
        
        logger.info(
            "File downloaded",
            job_id=job_id,
            user_id=current_user.id,
            filename=download_filename
        )
        
        return FileResponse(
            job['file_path'],
            media_type=media_type,
            filename=download_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download file", job_id=job_id, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Delete PDF export job."""
    try:
        # Check job ownership
        job = await execute_query(
            "SELECT id, file_path, status FROM pdf_export_jobs WHERE id = $1 AND user_id = $2",
            job_id,
            current_user.id,
            fetchrow=True
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Cancel job if running
        if job['status'] in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]:
            await pdf_generator.cancel_job(job_id)
        
        # Delete file if exists
        if job['file_path'] and os.path.exists(job['file_path']):
            try:
                os.remove(job['file_path'])
            except Exception as e:
                logger.warning("Failed to delete file", file_path=job['file_path'], error=str(e))
        
        # Delete job record
        await execute_query(
            "DELETE FROM pdf_export_jobs WHERE id = $1",
            job_id
        )
        
        logger.info("Job deleted", job_id=job_id, user_id=current_user.id)
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete job", job_id=job_id, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to delete job")


@router.get("/analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_full)
):
    """Get PDF export analytics for current user."""
    try:
        # Get job statistics
        stats = await execute_query(
            """
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                AVG(generation_time_ms) as avg_generation_time,
                SUM(file_size) as total_file_size,
                SUM(page_count) as total_pages
            FROM pdf_export_jobs 
            WHERE user_id = $1 
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """,
            current_user.id,
            days,
            fetchrow=True
        )
        
        # Get usage by format
        format_stats = await execute_query(
            """
            SELECT output_format, COUNT(*) as count
            FROM pdf_export_jobs 
            WHERE user_id = $1 
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY output_format
            """,
            current_user.id,
            days,
            fetch=True
        )
        
        # Get usage by template
        template_stats = await execute_query(
            """
            SELECT pt.name, COUNT(*) as count
            FROM pdf_export_jobs pj
            JOIN pdf_templates pt ON pj.template_id = pt.id
            WHERE pj.user_id = $1 
            AND pj.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY pt.name
            ORDER BY count DESC
            LIMIT 10
            """,
            current_user.id,
            days,
            fetch=True
        )
        
        # Get daily usage
        daily_stats = await execute_query(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM pdf_export_jobs 
            WHERE user_id = $1 
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            current_user.id,
            days,
            fetch=True
        )
        
        return {
            "period_days": days,
            "total_jobs": stats['total_jobs'] or 0,
            "successful_jobs": stats['successful_jobs'] or 0,
            "failed_jobs": stats['failed_jobs'] or 0,
            "success_rate": (stats['successful_jobs'] / max(stats['total_jobs'], 1)) * 100 if stats['total_jobs'] else 0,
            "avg_generation_time_ms": float(stats['avg_generation_time']) if stats['avg_generation_time'] else 0,
            "total_file_size_mb": float(stats['total_file_size']) / (1024 * 1024) if stats['total_file_size'] else 0,
            "total_pages": stats['total_pages'] or 0,
            "usage_by_format": {row['output_format']: row['count'] for row in format_stats},
            "top_templates": [{"name": row['name'], "count": row['count']} for row in template_stats],
            "daily_usage": [{"date": row['date'].isoformat(), "count": row['count']} for row in daily_stats]
        }
        
    except Exception as e:
        logger.error("Failed to get analytics", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get analytics")


@router.get("/formats")
async def get_supported_formats():
    """Get supported output formats."""
    return {
        "formats": [
            {
                "format": OutputFormat.PDF.value,
                "name": "PDF",
                "description": "Portable Document Format",
                "mime_type": "application/pdf"
            },
            {
                "format": OutputFormat.HTML.value,
                "name": "HTML",
                "description": "HyperText Markup Language",
                "mime_type": "text/html"
            },
            {
                "format": OutputFormat.PNG.value,
                "name": "PNG",
                "description": "Portable Network Graphics",
                "mime_type": "image/png"
            },
            {
                "format": OutputFormat.JPG.value,
                "name": "JPG",
                "description": "Joint Photographic Experts Group",
                "mime_type": "image/jpeg"
            }
        ]
    }


@router.get("/capabilities")
async def get_capabilities():
    """Get PDF service capabilities."""
    return {
        "supported_formats": [format.value for format in OutputFormat],
        "max_file_size_mb": settings.PDF_MAX_FILE_SIZE_MB,
        "max_pages": settings.PDF_MAX_PAGES,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_GENERATIONS,
        "supported_page_sizes": list(settings.PAGE_SIZES.keys()),
        "supported_orientations": settings.PAGE_ORIENTATIONS,
        "template_types": list(settings.TEMPLATE_TYPES.keys())
    }