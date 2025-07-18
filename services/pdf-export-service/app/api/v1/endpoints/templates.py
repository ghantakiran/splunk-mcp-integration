"""
Template management endpoints for PDF Export Service.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
import structlog
import json

from app.models.pdf_models import (
    TemplateCreateRequest, TemplateUpdateRequest, PDFTemplate, PDFTemplateList,
    PDFPreview, PDFPreviewRequest, TemplateType
)
from app.models.user_models import User
from app.utils.auth import get_current_user_full, require_permission
from app.utils.rate_limiter import check_rate_limit
from app.services.template_service import template_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("/", response_model=PDFTemplate)
async def create_template(
    request: TemplateCreateRequest,
    current_user: User = Depends(get_current_user_full)
):
    """Create new PDF template."""
    try:
        # Check permissions
        if not check_permission(current_user.permissions, "template:create"):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Check rate limit
        if not await check_rate_limit(str(current_user.id), "template_creation"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for template creation"
            )
        
        # Create template
        template = await template_service.create_template(
            request.dict(),
            current_user.id
        )
        
        logger.info(
            "Template created",
            template_id=template['id'],
            user_id=current_user.id,
            name=request.name
        )
        
        return PDFTemplate(**template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create template", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("/", response_model=PDFTemplateList)
async def list_templates(
    template_type: Optional[TemplateType] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_full)
):
    """List PDF templates."""
    try:
        # Get templates
        result = await template_service.list_templates(
            user_id=current_user.id,
            template_type=template_type,
            is_active=is_active,
            page=page,
            page_size=page_size
        )
        
        return PDFTemplateList(
            templates=[PDFTemplate(**template) for template in result['templates']],
            total=result['total'],
            page=result['page'],
            page_size=result['page_size']
        )
        
    except Exception as e:
        logger.error("Failed to list templates", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/types")
async def get_template_types():
    """Get available template types."""
    return await template_service.get_template_types()


@router.get("/defaults")
async def get_default_templates(
    template_type: Optional[TemplateType] = None
):
    """Get default templates."""
    try:
        templates = await template_service.get_default_templates(template_type)
        return [PDFTemplate(**template) for template in templates]
        
    except Exception as e:
        logger.error("Failed to get default templates", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get default templates")


@router.get("/{template_id}", response_model=PDFTemplate)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get PDF template by ID."""
    try:
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check access permissions
        if (template['created_by'] != current_user.id and 
            not template['is_default'] and 
            not check_permission(current_user.permissions, "template:read")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return PDFTemplate(**template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template")


@router.put("/{template_id}", response_model=PDFTemplate)
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    current_user: User = Depends(get_current_user_full)
):
    """Update PDF template."""
    try:
        # Get existing template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check permissions
        if (template['created_by'] != current_user.id and 
            not check_permission(current_user.permissions, "template:update")):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Update template
        updated_template = await template_service.update_template(
            template_id,
            request.dict(exclude_unset=True),
            current_user.id
        )
        
        logger.info(
            "Template updated",
            template_id=template_id,
            user_id=current_user.id
        )
        
        return PDFTemplate(**updated_template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Delete PDF template."""
    try:
        # Get existing template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check permissions
        if (template['created_by'] != current_user.id and 
            not check_permission(current_user.permissions, "template:delete")):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Delete template
        success = await template_service.delete_template(template_id, current_user.id)
        
        if success:
            logger.info(
                "Template deleted",
                template_id=template_id,
                user_id=current_user.id
            )
            return {"message": "Template deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete template")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete template")


@router.post("/{template_id}/preview", response_model=PDFPreview)
async def preview_template(
    template_id: int,
    request: PDFPreviewRequest,
    current_user: User = Depends(get_current_user_full)
):
    """Preview PDF template with sample data."""
    try:
        # Get template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check access permissions
        if (template['created_by'] != current_user.id and 
            not template['is_default'] and 
            not check_permission(current_user.permissions, "template:read")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Generate preview
        preview = await template_service.preview_template(
            template_id,
            {**request.parameters, **request.sample_data}
        )
        
        return PDFPreview(**preview)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to preview template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to preview template: {str(e)}")


@router.post("/{template_id}/duplicate", response_model=PDFTemplate)
async def duplicate_template(
    template_id: int,
    new_name: str = Query(...),
    current_user: User = Depends(get_current_user_full)
):
    """Duplicate existing template."""
    try:
        # Check permissions
        if not check_permission(current_user.permissions, "template:create"):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Get existing template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check access permissions
        if (template['created_by'] != current_user.id and 
            not template['is_default'] and 
            not check_permission(current_user.permissions, "template:read")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Duplicate template
        new_template = await template_service.duplicate_template(
            template_id,
            new_name,
            current_user.id
        )
        
        logger.info(
            "Template duplicated",
            original_id=template_id,
            new_id=new_template['id'],
            user_id=current_user.id
        )
        
        return PDFTemplate(**new_template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to duplicate template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to duplicate template: {str(e)}")


@router.get("/{template_id}/analytics")
async def get_template_analytics(
    template_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Get template usage analytics."""
    try:
        # Get template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check access permissions
        if (template['created_by'] != current_user.id and 
            not check_permission(current_user.permissions, "analytics:read")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get analytics
        analytics = await template_service.get_template_analytics(template_id)
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template analytics", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template analytics")


@router.get("/{template_id}/export")
async def export_template(
    template_id: int,
    current_user: User = Depends(get_current_user_full)
):
    """Export template as JSON."""
    try:
        # Get template
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check access permissions
        if (template['created_by'] != current_user.id and 
            not template['is_default'] and 
            not check_permission(current_user.permissions, "template:read")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Export template
        export_data = await template_service.export_template(template_id)
        
        logger.info(
            "Template exported",
            template_id=template_id,
            user_id=current_user.id
        )
        
        return JSONResponse(
            content=export_data,
            headers={
                'Content-Disposition': f'attachment; filename="template_{template_id}.json"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export template")


@router.post("/import", response_model=PDFTemplate)
async def import_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_full)
):
    """Import template from JSON file."""
    try:
        # Check permissions
        if not check_permission(current_user.permissions, "template:create"):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Read file content
        content = await file.read()
        
        # Parse JSON
        try:
            template_data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        
        # Import template
        template = await template_service.import_template(template_data, current_user.id)
        
        logger.info(
            "Template imported",
            template_id=template['id'],
            user_id=current_user.id,
            filename=file.filename
        )
        
        return PDFTemplate(**template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import template", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Failed to import template: {str(e)}")


@router.post("/validate")
async def validate_template(
    template_content: str,
    current_user: User = Depends(get_current_user_full)
):
    """Validate template content."""
    try:
        # Validate template
        await template_service._validate_template_content(template_content)
        
        return {"valid": True, "message": "Template is valid"}
        
    except Exception as e:
        return {"valid": False, "message": str(e)}


def check_permission(permissions: Dict[str, Any], required_permission: str) -> bool:
    """Check if user has required permission."""
    # This is a simplified implementation
    # In production, you would implement proper RBAC
    return True  # For now, allow all operations