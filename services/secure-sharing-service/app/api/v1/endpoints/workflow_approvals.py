"""
API endpoints for workflow approval functionality.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.database import get_database
from app.models.sharing_models import (
    CreateApprovalWorkflowRequest, CreateApprovalRequestRequest, ApprovalActionRequest,
    ApprovalWorkflowResponse, ApprovalRequestResponse, ApprovalActionResponse,
    ApprovalWorkflowListRequest, ApprovalRequestListRequest, ApprovalStatistics
)
from app.services.workflow_approval_service import workflow_approval_service, WorkflowApprovalError, ApprovalNotFoundError
from app.utils.auth import get_current_user
from app.utils.rate_limiter import rate_limiter
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/workflows", response_model=ApprovalWorkflowResponse)
async def create_approval_workflow(
    request: CreateApprovalWorkflowRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Create a new approval workflow."""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(
            f"create_workflow:{current_user}", 
            max_requests=10, 
            window_seconds=3600
        )
        
        result = await workflow_approval_service.create_workflow(request, current_user, db)
        
        logger.info(
            "Approval workflow created via API",
            workflow_id=str(result.workflow_id),
            user_id=current_user
        )
        
        return result
        
    except WorkflowApprovalError as e:
        logger.warning("Workflow creation failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to create approval workflow", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/workflows/{workflow_id}", response_model=ApprovalWorkflowResponse)
async def get_approval_workflow(
    workflow_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get approval workflow by ID."""
    try:
        result = await workflow_approval_service.get_workflow(workflow_id, current_user, db)
        
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        return result
        
    except WorkflowApprovalError as e:
        logger.warning("Workflow access failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("Failed to get approval workflow", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/workflows", response_model=Dict[str, Any])
async def list_approval_workflows(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    search: Optional[str] = Query(None, description="Search workflows by name or description"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=200, description="Number of workflows to return"),
    offset: int = Query(0, ge=0, description="Number of workflows to skip"),
    sort_by: str = Query("created_at", regex="^(name|created_at|updated_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """List approval workflows with filtering and pagination."""
    try:
        # Parse tags
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        request = ApprovalWorkflowListRequest(
            is_active=is_active,
            created_by=created_by,
            search=search,
            tags=tag_list,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        result = await workflow_approval_service.list_workflows(request, current_user, db)
        
        return result
        
    except Exception as e:
        logger.error("Failed to list approval workflows", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/requests", response_model=ApprovalRequestResponse)
async def create_approval_request(
    request: CreateApprovalRequestRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Create a new approval request."""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(
            f"create_approval_request:{current_user}", 
            max_requests=50, 
            window_seconds=3600
        )
        
        result = await workflow_approval_service.create_approval_request(request, current_user, db)
        
        logger.info(
            "Approval request created via API",
            request_id=str(result.request_id),
            user_id=current_user
        )
        
        return result
        
    except ApprovalNotFoundError as e:
        logger.warning("Approval request creation failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except WorkflowApprovalError as e:
        logger.warning("Approval request creation failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to create approval request", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get approval request by ID."""
    try:
        # Get request from list with single item filter
        list_request = ApprovalRequestListRequest(limit=1, offset=0)
        result = await workflow_approval_service.list_approval_requests(list_request, current_user, db)
        
        # Find the specific request
        for item in result["items"]:
            if item.request_id == request_id:
                return item
        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
        
    except Exception as e:
        logger.error("Failed to get approval request", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/requests", response_model=Dict[str, Any])
async def list_approval_requests(
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    requested_by: Optional[str] = Query(None, description="Filter by requester"),
    assigned_to: Optional[str] = Query(None, description="Filter by current approver"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date (after)"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date (before)"),
    due_after: Optional[datetime] = Query(None, description="Filter by due date (after)"),
    due_before: Optional[datetime] = Query(None, description="Filter by due date (before)"),
    search: Optional[str] = Query(None, description="Search requests by justification or business case"),
    limit: int = Query(50, ge=1, le=200, description="Number of requests to return"),
    offset: int = Query(0, ge=0, description="Number of requests to skip"),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|priority|status)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """List approval requests with filtering and pagination."""
    try:
        from app.models.sharing_models import WorkflowStatus
        
        # Parse status
        status_enum = None
        if status:
            try:
                status_enum = WorkflowStatus(status)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status}")
        
        request = ApprovalRequestListRequest(
            workflow_id=workflow_id,
            status=status_enum,
            priority=priority,
            requested_by=requested_by,
            assigned_to=assigned_to,
            created_after=created_after,
            created_before=created_before,
            due_after=due_after,
            due_before=due_before,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        result = await workflow_approval_service.list_approval_requests(request, current_user, db)
        
        return result
        
    except Exception as e:
        logger.error("Failed to list approval requests", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/requests/{request_id}/actions", response_model=ApprovalActionResponse)
async def take_approval_action(
    request_id: UUID,
    action_request: ApprovalActionRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Take action on an approval request."""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(
            f"approval_action:{current_user}", 
            max_requests=100, 
            window_seconds=3600
        )
        
        result = await workflow_approval_service.take_action(request_id, action_request, current_user, db)
        
        logger.info(
            "Approval action taken via API",
            action_id=str(result.action_id),
            request_id=str(request_id),
            action=action_request.action.value,
            user_id=current_user
        )
        
        return result
        
    except ApprovalNotFoundError as e:
        logger.warning("Approval action failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except WorkflowApprovalError as e:
        logger.warning("Approval action failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to take approval action", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/statistics", response_model=ApprovalStatistics)
async def get_approval_statistics(
    start_time: Optional[datetime] = Query(None, description="Start time for statistics"),
    end_time: Optional[datetime] = Query(None, description="End time for statistics"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get approval workflow statistics."""
    try:
        result = await workflow_approval_service.get_approval_statistics(
            current_user, start_time, end_time, db
        )
        
        return result
        
    except WorkflowApprovalError as e:
        logger.warning("Statistics access failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("Failed to get approval statistics", error=str(e), user_id=current_user)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Health check endpoint for workflow approvals."""
    try:
        # Basic health check
        from app.core.database import get_database
        db = await get_database()
        
        # Test database connectivity with a simple query
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "service": "workflow-approvals",
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": {
                    "database": "healthy"
                }
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "workflow-approvals",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/capabilities")
async def get_capabilities():
    """Get workflow approval service capabilities."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "service": "workflow-approvals",
            "version": "1.0.0",
            "features": {
                "workflow_management": True,
                "multi_level_approval": True,
                "escalation": True,
                "notifications": True,
                "statistics": True,
                "audit_trail": True
            },
            "supported_approval_levels": [
                "none", "single", "multi_level", "unanimous", "majority"
            ],
            "supported_triggers": [
                "sensitive_data", "external_sharing", "high_risk_resource",
                "manager_approval", "compliance_review", "security_review", "custom_rule"
            ],
            "supported_actions": [
                "approve", "reject", "request_changes", "delegate", "withdraw"
            ],
            "limits": {
                "max_workflows_per_user": 100,
                "max_approvers_per_workflow": 50,
                "max_approval_requests_per_hour": 1000,
                "max_request_size_mb": 10
            },
            "notifications": {
                "channels": ["email", "slack", "teams", "webhook"],
                "types": ["request_created", "approval_needed", "approved", "rejected", "escalated", "reminder"]
            }
        }
    )