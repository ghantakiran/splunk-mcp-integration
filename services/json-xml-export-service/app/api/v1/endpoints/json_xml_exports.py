"""
JSON/XML export API endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from structlog import get_logger

from app.models.json_xml_models import (
    BulkExportRequest,
    ExportCapabilities,
    ExportJob,
    ExportJobCreate,
    ExportJobList,
    ExportJobResponse,
    ExportRequest,
    ErrorResponse
)
from app.services.json_xml_generator import JsonXmlExportGenerator
from app.utils.auth import get_current_user, require_permission, Permissions
from app.utils.rate_limiter import (
    rate_limit_bulk_export,
    rate_limit_download,
    rate_limit_export_create
)

logger = get_logger(__name__)

router = APIRouter()

# Global generator instance
export_generator = JsonXmlExportGenerator()


@router.post(
    "/generate",
    response_model=ExportJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate JSON/XML Export",
    description="Create a new JSON or XML export job with the specified configuration."
)
async def create_export(
    request: Request,
    export_request: ExportRequest,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_CREATE))
) -> ExportJobResponse:
    """Create a new export job."""
    try:
        # Apply rate limiting
        await rate_limit_export_create(request, user["user_id"])
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Mock data for demonstration (in production, this would come from data source)
        mock_data = [
            {"id": 1, "name": "Sample Record 1", "timestamp": "2025-01-01T10:00:00Z", "value": 100},
            {"id": 2, "name": "Sample Record 2", "timestamp": "2025-01-01T11:00:00Z", "value": 200},
            {"id": 3, "name": "Sample Record 3", "timestamp": "2025-01-01T12:00:00Z", "value": 300}
        ]
        
        # Validate export configuration
        validation_result = await export_generator.validate_export_size(
            mock_data,
            export_request.export_config
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Export validation failed: {'; '.join(validation_result['warnings'])}"
            )
        
        # Generate export
        export_result = await export_generator.generate_export(
            data=mock_data,
            config=export_request.export_config,
            job_id=job_id,
            filename=export_request.filename
        )
        
        # Create job response
        job = ExportJob(
            job_id=job_id,
            user_id=user["user_id"],
            status="completed",
            format=export_request.export_config.format,
            filename=export_result["filename"],
            file_path=export_result["file_path"],
            file_size=export_result["file_size"],
            records_processed=export_result["records_processed"],
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            metadata=export_request.metadata
        )
        
        logger.info(
            "Export job created successfully",
            job_id=job_id,
            user_id=user["user_id"],
            format=export_request.export_config.format,
            file_size=export_result["file_size"]
        )
        
        return ExportJobResponse(
            success=True,
            job=job,
            download_url=f"/api/v1/json-xml-exports/jobs/{job_id}/download"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Export creation failed",
            error=str(e),
            user_id=user["user_id"],
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export creation failed"
        )


@router.post(
    "/bulk-generate",
    response_model=List[ExportJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Generate Exports",
    description="Create multiple export jobs in a single request."
)
async def create_bulk_exports(
    request: Request,
    bulk_request: BulkExportRequest,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_CREATE))
) -> List[ExportJobResponse]:
    """Create multiple export jobs."""
    try:
        # Apply rate limiting
        await rate_limit_bulk_export(request, user["user_id"])
        
        results = []
        
        for export_request in bulk_request.exports:
            try:
                # Use shared config if provided
                if bulk_request.shared_config:
                    export_request.export_config = bulk_request.shared_config
                
                # Create individual export
                job_response = await create_export(request, export_request, user)
                results.append(job_response)
                
            except Exception as e:
                logger.error(f"Bulk export item failed: {e}")
                # Create failed job response
                failed_job = ExportJob(
                    job_id=str(uuid.uuid4()),
                    user_id=user["user_id"],
                    status="failed",
                    format=export_request.export_config.format,
                    error_message=str(e),
                    created_at=datetime.utcnow()
                )
                results.append(ExportJobResponse(success=False, job=failed_job))
        
        logger.info(
            "Bulk export completed",
            user_id=user["user_id"],
            total_jobs=len(results),
            successful_jobs=sum(1 for r in results if r.success)
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Bulk export failed",
            error=str(e),
            user_id=user["user_id"],
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk export failed"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=ExportJobResponse,
    summary="Get Export Job",
    description="Retrieve information about a specific export job."
)
async def get_export_job(
    job_id: str,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_READ))
) -> ExportJobResponse:
    """Get export job details."""
    # In production, this would query the database
    # For now, return a mock response
    mock_job = ExportJob(
        job_id=job_id,
        user_id=user["user_id"],
        status="completed",
        format="json",
        filename=f"export_{job_id}.json",
        file_size=1024,
        records_processed=100,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    
    return ExportJobResponse(
        success=True,
        job=mock_job,
        download_url=f"/api/v1/json-xml-exports/jobs/{job_id}/download"
    )


@router.get(
    "/jobs",
    response_model=ExportJobList,
    summary="List Export Jobs",
    description="List export jobs for the current user with pagination."
)
async def list_export_jobs(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    format_filter: Optional[str] = None,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_READ))
) -> ExportJobList:
    """List export jobs."""
    # In production, this would query the database with filters
    # For now, return mock data
    mock_jobs = [
        ExportJob(
            job_id=f"job_{i}",
            user_id=user["user_id"],
            status="completed",
            format="json",
            filename=f"export_{i}.json",
            file_size=1024 * i,
            records_processed=100 * i,
            created_at=datetime.utcnow()
        )
        for i in range(1, 6)
    ]
    
    return ExportJobList(
        success=True,
        jobs=mock_jobs,
        total=len(mock_jobs),
        page=page,
        page_size=page_size
    )


@router.get(
    "/jobs/{job_id}/download",
    response_class=FileResponse,
    summary="Download Export File",
    description="Download the generated export file."
)
async def download_export_file(
    request: Request,
    job_id: str,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_READ))
) -> FileResponse:
    """Download export file."""
    try:
        # Apply rate limiting
        await rate_limit_download(request, user["user_id"])
        
        # In production, this would:
        # 1. Query database for job details
        # 2. Verify user owns the job or has permission
        # 3. Check if file exists
        # 4. Return the actual file
        
        # For demonstration, create a simple JSON file
        import tempfile
        import json
        
        sample_data = [
            {"id": 1, "name": "Sample Export", "timestamp": datetime.utcnow().isoformat()},
            {"id": 2, "name": "Demo Data", "timestamp": datetime.utcnow().isoformat()}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f, indent=2)
            temp_path = f.name
        
        logger.info(
            "File download initiated",
            job_id=job_id,
            user_id=user["user_id"]
        )
        
        return FileResponse(
            path=temp_path,
            filename=f"export_{job_id}.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "File download failed",
            job_id=job_id,
            user_id=user["user_id"],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File download failed"
        )


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Export Job",
    description="Delete an export job and its associated file."
)
async def delete_export_job(
    job_id: str,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_DELETE))
) -> None:
    """Delete export job."""
    # In production, this would:
    # 1. Query database for job
    # 2. Verify ownership/permissions
    # 3. Delete file from storage
    # 4. Delete database record
    
    logger.info(
        "Export job deleted",
        job_id=job_id,
        user_id=user["user_id"]
    )


@router.get(
    "/capabilities",
    response_model=ExportCapabilities,
    summary="Get Export Capabilities",
    description="Get information about supported export formats and limits."
)
async def get_export_capabilities() -> ExportCapabilities:
    """Get export capabilities."""
    return ExportCapabilities(
        supported_formats=["json", "xml", "jsonl", "custom-json", "custom-xml"],
        supported_encodings=["utf-8", "utf-16", "latin-1", "ascii"],
        supported_compressions=["gzip", "zip"],
        max_file_size_mb=100,
        max_records=1000000,
        features=[
            "Custom JSON formatting",
            "XML schema validation",
            "Field mapping and transformation",
            "Data flattening",
            "Compression support",
            "Bulk export operations",
            "Real-time processing",
            "Metadata inclusion"
        ]
    )


@router.post(
    "/validate",
    summary="Validate Export Configuration",
    description="Validate export configuration before creating a job."
)
async def validate_export_config(
    export_request: ExportRequest,
    user: dict = Depends(require_permission(Permissions.JSON_XML_EXPORT_READ))
) -> dict:
    """Validate export configuration."""
    try:
        # Mock data for validation
        mock_data = [{"sample": "data"}] * 1000
        
        validation_result = await export_generator.validate_export_size(
            mock_data,
            export_request.export_config
        )
        
        return {
            "success": True,
            "valid": validation_result["valid"],
            "estimated_size_mb": validation_result["estimated_size_mb"],
            "record_count": validation_result["record_count"],
            "warnings": validation_result["warnings"]
        }
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation failed"
        )