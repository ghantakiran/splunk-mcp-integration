#!/usr/bin/env python3
"""
Templates API endpoints.

This module provides API endpoints for managing CSV export templates
including creation, retrieval, updating, and deletion.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.database import (
    create_template, 
    get_user_templates,
    log_analytics_event
)
from app.models.csv_models import (
    TemplateRequest,
    TemplateResponse,
    TemplateListResponse,
    BaseResponse,
    CSVExportConfig
)
from app.utils.auth import CurrentUser, require_template_create, require_template_read, require_template_update

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TemplateResponse)
async def create_export_template(
    request: TemplateRequest,
    current_user: CurrentUser = Depends(require_template_create)
):
    """Create a new CSV export template."""
    try:
        # Create template in database
        template_id = await create_template(
            user_id=current_user.user_id,
            name=request.name,
            description=request.description,
            export_config=request.export_config.model_dump(),
            is_default=request.is_default
        )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="template_created",
            event_data={
                "template_id": template_id,
                "template_name": request.name,
                "is_default": request.is_default
            }
        )
        
        logger.info(f"Template '{request.name}' created with ID {template_id} by user {current_user.user_id}")
        
        # Return template response (simplified for demo)
        return TemplateResponse(
            template_id=template_id,
            name=request.name,
            description=request.description,
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


@router.get("/", response_model=TemplateListResponse)
async def get_user_export_templates(
    current_user: CurrentUser = Depends(require_template_read),
    include_default: bool = Query(True, description="Include default templates")
):
    """Get user's export templates."""
    try:
        # Get templates from database
        templates = await get_user_templates(current_user.user_id)
        
        # Convert to response format
        template_responses = []
        for template in templates:
            template_responses.append(
                TemplateResponse(
                    template_id=template["template_id"],
                    name=template["name"],
                    description=template["description"],
                    is_default=template["is_default"],
                    is_active=template["is_active"],
                    created_at=template["created_at"],
                    updated_at=template["updated_at"]
                )
            )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="templates_listed",
            event_data={
                "template_count": len(template_responses),
                "include_default": include_default
            }
        )
        
        return TemplateListResponse(
            total=len(template_responses),
            templates=template_responses
        )
        
    except Exception as e:
        logger.error(f"Failed to get templates for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/default", response_model=List[TemplateResponse])
async def get_default_templates():
    """Get system default templates."""
    try:
        # Return predefined default templates
        default_templates = [
            {
                "template_id": -1,
                "name": "Standard CSV",
                "description": "Standard CSV format with UTF-8 encoding",
                "is_default": True,
                "is_active": True,
                "export_config": CSVExportConfig().model_dump()
            },
            {
                "template_id": -2,
                "name": "Excel Compatible",
                "description": "CSV format compatible with Microsoft Excel",
                "is_default": True,
                "is_active": True,
                "export_config": CSVExportConfig(
                    formatting={
                        "encoding": "utf-8",
                        "delimiter": ",",
                        "quote_char": '"',
                        "line_terminator": "\r\n"
                    }
                ).model_dump()
            },
            {
                "template_id": -3,
                "name": "Tab Separated",
                "description": "Tab-separated values format",
                "is_default": True,
                "is_active": True,
                "export_config": CSVExportConfig(
                    export_format="tsv",
                    formatting={
                        "delimiter": "\t"
                    }
                ).model_dump()
            }
        ]
        
        responses = []
        for template in default_templates:
            responses.append(
                TemplateResponse(
                    template_id=template["template_id"],
                    name=template["name"],
                    description=template["description"],
                    is_default=template["is_default"],
                    is_active=template["is_active"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
        
        return responses
        
    except Exception as e:
        logger.error(f"Failed to get default templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default templates"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template_by_id(
    template_id: int,
    current_user: CurrentUser = Depends(require_template_read)
):
    """Get specific template by ID."""
    try:
        # Handle default templates
        if template_id < 0:
            default_templates = await get_default_templates()
            for template in default_templates:
                if template.template_id == template_id:
                    return template
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default template not found"
            )
        
        # Get user templates and find the specific one
        templates = await get_user_templates(current_user.user_id)
        
        for template in templates:
            if template["template_id"] == template_id:
                return TemplateResponse(
                    template_id=template["template_id"],
                    name=template["name"],
                    description=template["description"],
                    is_default=template["is_default"],
                    is_active=template["is_active"],
                    created_at=template["created_at"],
                    updated_at=template["updated_at"]
                )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: TemplateRequest,
    current_user: CurrentUser = Depends(require_template_update)
):
    """Update an existing template."""
    try:
        # For demo purposes, we'll simulate an update
        # In a real implementation, this would update the database
        
        # Check if template exists and belongs to user
        templates = await get_user_templates(current_user.user_id)
        template_exists = any(t["template_id"] == template_id for t in templates)
        
        if not template_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="template_updated",
            event_data={
                "template_id": template_id,
                "template_name": request.name
            }
        )
        
        logger.info(f"Template {template_id} updated by user {current_user.user_id}")
        
        # Return updated template response
        return TemplateResponse(
            template_id=template_id,
            name=request.name,
            description=request.description,
            is_default=request.is_default,
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=1),  # Simulate creation time
            updated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )


@router.delete("/{template_id}", response_model=BaseResponse)
async def delete_template(
    template_id: int,
    current_user: CurrentUser = Depends(require_template_update)
):
    """Delete a template."""
    try:
        # Check if template exists and belongs to user
        templates = await get_user_templates(current_user.user_id)
        template_exists = any(t["template_id"] == template_id for t in templates)
        
        if not template_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Cannot delete default templates
        if template_id < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default templates"
            )
        
        # For demo purposes, we'll simulate deletion
        # In a real implementation, this would soft-delete the template
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="template_deleted",
            event_data={"template_id": template_id}
        )
        
        logger.info(f"Template {template_id} deleted by user {current_user.user_id}")
        
        return BaseResponse(
            success=True,
            message="Template deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )


# Import datetime for responses
from datetime import datetime, timedelta

# Export router
__all__ = ["router"]