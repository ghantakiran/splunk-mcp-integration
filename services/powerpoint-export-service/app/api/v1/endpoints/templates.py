#!/usr/bin/env python3
"""
Template management API endpoints for PowerPoint Export Service.

This module provides REST API endpoints for creating, managing, and using
PowerPoint presentation templates.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from structlog import get_logger

from app.core.database import execute_query
from app.models.powerpoint_models import (
    TemplateRequest,
    TemplateResponse,
    TemplateListResponse,
    Theme
)
from app.utils.auth import get_current_user_full


logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=TemplateResponse, summary="Create PowerPoint template")
async def create_template(
    request: TemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Create a new PowerPoint template."""
    user_id = current_user["id"]
    
    try:
        # Check if template name already exists
        check_query = "SELECT id FROM ppt_templates WHERE name = $1 AND is_active = true"
        existing = await execute_query(check_query, request.name, fetch="one")
        
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
        
        # If setting as default, unset other defaults for the same theme
        if request.is_default:
            unset_query = "UPDATE ppt_templates SET is_default = false WHERE theme = $1"
            await execute_query(unset_query, request.theme.value, fetch="none")
        
        # Create template
        create_query = """
            INSERT INTO ppt_templates (
                name, description, theme, template_data, is_default, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at, updated_at
        """
        
        result = await execute_query(
            create_query,
            request.name,
            request.description,
            request.theme.value,
            request.template_data.json(),
            request.is_default,
            user_id,
            fetch="one"
        )
        
        logger.info("Template created", template_id=result["id"], name=request.name, user_id=user_id)
        
        return TemplateResponse(
            template_id=result["id"],
            name=request.name,
            description=request.description,
            theme=request.theme,
            is_default=request.is_default,
            is_active=True,
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create template", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to create template")


@router.get("/", response_model=TemplateListResponse, summary="List PowerPoint templates")
async def list_templates(
    theme: Optional[Theme] = Query(None, description="Filter by theme"),
    is_default: Optional[bool] = Query(None, description="Filter by default status"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """List available PowerPoint templates."""
    user_id = current_user["id"]
    
    try:
        # Build filter conditions
        conditions = []
        params = []
        param_count = 0
        
        if theme:
            param_count += 1
            conditions.append(f"theme = ${param_count}")
            params.append(theme.value)
        
        if is_default is not None:
            param_count += 1
            conditions.append(f"is_default = ${param_count}")
            params.append(is_default)
        
        if is_active is not None:
            param_count += 1
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ppt_templates {where_clause}"
        total = await execute_query(count_query, *params, fetch="val")
        
        # Get templates
        templates_query = f"""
            SELECT id, name, description, theme, is_default, is_active, created_at, updated_at
            FROM ppt_templates {where_clause}
            ORDER BY is_default DESC, name ASC
        """
        
        templates_data = await execute_query(templates_query, *params, fetch="all")
        
        # Convert to response models
        templates = [
            TemplateResponse(
                template_id=template["id"],
                name=template["name"],
                description=template["description"],
                theme=Theme(template["theme"]),
                is_default=template["is_default"],
                is_active=template["is_active"],
                created_at=template["created_at"],
                updated_at=template["updated_at"]
            )
            for template in templates_data
        ]
        
        return TemplateListResponse(
            total=total,
            templates=templates
        )
    
    except Exception as e:
        logger.error("Failed to list templates", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/{template_id}", response_model=TemplateResponse, summary="Get PowerPoint template details")
async def get_template(
    template_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Get PowerPoint template details."""
    try:
        query = """
            SELECT id, name, description, theme, template_data, is_default, is_active, 
                   created_at, updated_at
            FROM ppt_templates 
            WHERE id = $1 AND is_active = true
        """
        
        template_data = await execute_query(query, template_id, fetch="one")
        
        if not template_data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return TemplateResponse(
            template_id=template_data["id"],
            name=template_data["name"],
            description=template_data["description"],
            theme=Theme(template_data["theme"]),
            is_default=template_data["is_default"],
            is_active=template_data["is_active"],
            created_at=template_data["created_at"],
            updated_at=template_data["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template")


@router.put("/{template_id}", response_model=TemplateResponse, summary="Update PowerPoint template")
async def update_template(
    template_id: int,
    request: TemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Update a PowerPoint template."""
    user_id = current_user["id"]
    
    try:
        # Check if template exists and user has permission
        check_query = "SELECT created_by FROM ppt_templates WHERE id = $1 AND is_active = true"
        template_data = await execute_query(check_query, template_id, fetch="one")
        
        if not template_data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if user can modify (owner or admin)
        if template_data["created_by"] != user_id and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Not authorized to modify this template")
        
        # Check if new name conflicts with existing templates
        name_check_query = "SELECT id FROM ppt_templates WHERE name = $1 AND id != $2 AND is_active = true"
        existing = await execute_query(name_check_query, request.name, template_id, fetch="one")
        
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
        
        # If setting as default, unset other defaults for the same theme
        if request.is_default:
            unset_query = "UPDATE ppt_templates SET is_default = false WHERE theme = $1 AND id != $2"
            await execute_query(unset_query, request.theme.value, template_id, fetch="none")
        
        # Update template
        update_query = """
            UPDATE ppt_templates 
            SET name = $2, description = $3, theme = $4, template_data = $5, 
                is_default = $6, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING created_at, updated_at
        """
        
        result = await execute_query(
            update_query,
            template_id,
            request.name,
            request.description,
            request.theme.value,
            request.template_data.json(),
            request.is_default,
            fetch="one"
        )
        
        logger.info("Template updated", template_id=template_id, name=request.name, user_id=user_id)
        
        return TemplateResponse(
            template_id=template_id,
            name=request.name,
            description=request.description,
            theme=request.theme,
            is_default=request.is_default,
            is_active=True,
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update template", template_id=template_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to update template")


@router.delete("/{template_id}", summary="Delete PowerPoint template")
async def delete_template(
    template_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Delete a PowerPoint template (soft delete)."""
    user_id = current_user["id"]
    
    try:
        # Check if template exists and user has permission
        check_query = "SELECT created_by, is_default FROM ppt_templates WHERE id = $1 AND is_active = true"
        template_data = await execute_query(check_query, template_id, fetch="one")
        
        if not template_data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if user can delete (owner or admin)
        if template_data["created_by"] != user_id and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Not authorized to delete this template")
        
        # Prevent deletion of default templates unless admin
        if template_data["is_default"] and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=400, detail="Cannot delete default template")
        
        # Soft delete template
        delete_query = "UPDATE ppt_templates SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = $1"
        await execute_query(delete_query, template_id, fetch="none")
        
        logger.info("Template deleted", template_id=template_id, user_id=user_id)
        
        return {"message": "Template deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete template", template_id=template_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to delete template")


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, summary="Duplicate PowerPoint template")
async def duplicate_template(
    template_id: int,
    new_name: str = Query(..., description="Name for the new template"),
    current_user: Dict[str, Any] = Depends(get_current_user_full)
):
    """Create a duplicate of an existing PowerPoint template."""
    user_id = current_user["id"]
    
    try:
        # Get original template
        get_query = """
            SELECT name, description, theme, template_data
            FROM ppt_templates 
            WHERE id = $1 AND is_active = true
        """
        
        original = await execute_query(get_query, template_id, fetch="one")
        
        if not original:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if new name already exists
        check_query = "SELECT id FROM ppt_templates WHERE name = $1 AND is_active = true"
        existing = await execute_query(check_query, new_name, fetch="one")
        
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
        
        # Create duplicate
        create_query = """
            INSERT INTO ppt_templates (
                name, description, theme, template_data, is_default, created_by
            ) VALUES ($1, $2, $3, $4, false, $5)
            RETURNING id, created_at, updated_at
        """
        
        result = await execute_query(
            create_query,
            new_name,
            f"Copy of {original['description']}" if original["description"] else f"Copy of {original['name']}",
            original["theme"],
            original["template_data"],
            user_id,
            fetch="one"
        )
        
        logger.info("Template duplicated", 
                   original_id=template_id, 
                   new_id=result["id"], 
                   new_name=new_name, 
                   user_id=user_id)
        
        return TemplateResponse(
            template_id=result["id"],
            name=new_name,
            description=f"Copy of {original['description']}" if original["description"] else f"Copy of {original['name']}",
            theme=Theme(original["theme"]),
            is_default=False,
            is_active=True,
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to duplicate template", template_id=template_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to duplicate template")
