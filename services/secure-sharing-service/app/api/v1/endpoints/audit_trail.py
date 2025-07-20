"""
API endpoints for audit trail management.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.sharing_models import (
    AuditTrailEvent, CreateAuditEventRequest, AuditTrailQuery, AuditTrailResponse,
    AuditTrailStatistics, AuditTrailExportRequest, AuditEventType, AuditEventCategory,
    AuditEventSeverity, ShareType, ShareOperation, PermissionScope
)
from app.services.audit_trail_service import audit_trail_service
from app.utils.auth import get_current_user
from app.utils.rate_limiter import rate_limiter, RateLimitExceeded
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/events", response_model=AuditTrailEvent)
async def create_audit_event(
    request: CreateAuditEventRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    http_request: Request = None
):
    """Create a new audit trail event."""
    try:
        # Rate limiting
        user_id = current_user.get("user_id") or current_user.get("sub")
        client_ip = http_request.client.host if http_request and http_request.client else None
        
        try:
            await rate_limiter.check_rate_limit(
                f"audit_create:{user_id}",
                limit=100,  # 100 events per hour
                window=3600,
                identifier=client_ip
            )
        except RateLimitExceeded as e:
            raise HTTPException(status_code=429, detail=str(e))

        # Add request context if not provided
        if not request.user_id:
            request.user_id = user_id
        if not request.ip_address and client_ip:
            request.ip_address = client_ip
        if not request.user_agent and http_request:
            request.user_agent = http_request.headers.get("user-agent")
        if not request.correlation_id and http_request:
            request.correlation_id = getattr(http_request.state, "correlation_id", None)

        event = await audit_trail_service.log_event(request, db)
        
        return event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create audit event",
            user_id=user_id,
            event_type=request.event_type.value,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to create audit event")


@router.get("/events", response_model=AuditTrailResponse)
async def query_audit_events(
    start_time: Optional[datetime] = Query(None, description="Start time for filtering events"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering events"),
    event_types: Optional[str] = Query(None, description="Comma-separated list of event types"),
    categories: Optional[str] = Query(None, description="Comma-separated list of categories"),
    severities: Optional[str] = Query(None, description="Comma-separated list of severities"),
    user_ids: Optional[str] = Query(None, description="Comma-separated list of user IDs"),
    share_ids: Optional[str] = Query(None, description="Comma-separated list of share IDs"),
    resource_types: Optional[str] = Query(None, description="Comma-separated list of resource types"),
    operations: Optional[str] = Query(None, description="Comma-separated list of operations"),
    scopes: Optional[str] = Query(None, description="Comma-separated list of scopes"),
    authorization_granted: Optional[bool] = Query(None, description="Filter by authorization status"),
    search_query: Optional[str] = Query(None, description="Text search in title and description"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
    limit: int = Query(50, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    sort_by: str = Query("timestamp", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    http_request: Request = None
):
    """Query audit trail events with comprehensive filtering."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        client_ip = http_request.client.host if http_request and http_request.client else None
        
        # Rate limiting
        try:
            await rate_limiter.check_rate_limit(
                f"audit_query:{user_id}",
                limit=200,  # 200 queries per hour
                window=3600,
                identifier=client_ip
            )
        except RateLimitExceeded as e:
            raise HTTPException(status_code=429, detail=str(e))

        # Parse comma-separated parameters
        query = AuditTrailQuery(
            start_time=start_time,
            end_time=end_time,
            event_types=[AuditEventType(t.strip()) for t in event_types.split(",")] if event_types else None,
            categories=[AuditEventCategory(c.strip()) for c in categories.split(",")] if categories else None,
            severities=[AuditEventSeverity(s.strip()) for s in severities.split(",")] if severities else None,
            user_ids=user_ids.split(",") if user_ids else None,
            share_ids=[UUID(id.strip()) for id in share_ids.split(",")] if share_ids else None,
            resource_types=[ShareType(rt.strip()) for rt in resource_types.split(",")] if resource_types else None,
            operations=[ShareOperation(op.strip()) for op in operations.split(",")] if operations else None,
            scopes=[PermissionScope(sc.strip()) for sc in scopes.split(",")] if scopes else None,
            authorization_granted=authorization_granted,
            search_query=search_query,
            tags=tags.split(",") if tags else None,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )

        response = await audit_trail_service.query_events(query, user_id, db)
        
        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(
            "Failed to query audit events",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to query audit events")


@router.get("/events/{event_id}", response_model=AuditTrailEvent)
async def get_audit_event(
    event_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get a specific audit event by ID."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        
        event = await audit_trail_service.get_event_by_id(event_id, user_id, db)
        
        if not event:
            raise HTTPException(status_code=404, detail="Audit event not found")
        
        return event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get audit event",
            event_id=str(event_id),
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get audit event")


@router.get("/statistics", response_model=AuditTrailStatistics)
async def get_audit_statistics(
    start_time: Optional[datetime] = Query(None, description="Start time for statistics"),
    end_time: Optional[datetime] = Query(None, description="End time for statistics"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    http_request: Request = None
):
    """Get comprehensive audit trail statistics."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        client_ip = http_request.client.host if http_request and http_request.client else None
        
        # Rate limiting
        try:
            await rate_limiter.check_rate_limit(
                f"audit_stats:{user_id}",
                limit=50,  # 50 requests per hour
                window=3600,
                identifier=client_ip
            )
        except RateLimitExceeded as e:
            raise HTTPException(status_code=429, detail=str(e))

        statistics = await audit_trail_service.get_statistics(start_time, end_time, user_id, db)
        
        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get audit statistics",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get audit statistics")


@router.post("/cleanup")
async def cleanup_expired_events(
    background_tasks: BackgroundTasks,
    batch_size: Optional[int] = Query(1000, ge=100, le=10000, description="Batch size for cleanup"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Clean up expired audit events (admin only)."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        
        # Check if user has admin permissions
        from app.services.role_permission_service import role_permission_service
        
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.MANAGE_PERMISSIONS, PermissionScope.GLOBAL, db=db
        )
        
        if not permission_check.has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions for cleanup operation")

        # Run cleanup in background
        background_tasks.add_task(
            audit_trail_service.cleanup_expired_events,
            batch_size,
            db
        )
        
        return {
            "message": "Audit trail cleanup started",
            "batch_size": batch_size,
            "started_by": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to start audit cleanup",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to start audit cleanup")


@router.get("/events/share/{share_id}", response_model=AuditTrailResponse)
async def get_share_audit_trail(
    share_id: UUID,
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get audit trail for a specific share."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        
        # Create query for specific share
        query = AuditTrailQuery(
            share_ids=[share_id],
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            sort_by="timestamp",
            sort_order="desc"
        )

        response = await audit_trail_service.query_events(query, user_id, db)
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get share audit trail",
            share_id=str(share_id),
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get share audit trail")


@router.get("/events/user/{target_user_id}", response_model=AuditTrailResponse)
async def get_user_audit_trail(
    target_user_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get audit trail for a specific user."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        
        # Users can only view their own audit trail unless they have admin permissions
        if target_user_id != user_id:
            from app.services.role_permission_service import role_permission_service
            
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
            )
            
            if not permission_check.has_permission:
                raise HTTPException(status_code=403, detail="Insufficient permissions to view other user's audit trail")

        # Create query for specific user
        query = AuditTrailQuery(
            user_ids=[target_user_id],
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            sort_by="timestamp",
            sort_order="desc"
        )

        response = await audit_trail_service.query_events(query, user_id, db)
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get user audit trail",
            target_user_id=target_user_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get user audit trail")


@router.get("/security/events", response_model=AuditTrailResponse)
async def get_security_events(
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    severities: Optional[str] = Query("high,critical", description="Comma-separated list of severities"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get security-related audit events (admin only)."""
    try:
        user_id = current_user.get("user_id") or current_user.get("sub")
        
        # Check if user has security analytics permissions
        from app.services.role_permission_service import role_permission_service
        
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
        )
        
        if not permission_check.has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view security events")

        # Create query for security events
        query = AuditTrailQuery(
            categories=[AuditEventCategory.SECURITY],
            severities=[AuditEventSeverity(s.strip()) for s in severities.split(",")] if severities else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            sort_by="timestamp",
            sort_order="desc"
        )

        response = await audit_trail_service.query_events(query, user_id, db)
        
        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(
            "Failed to get security events",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get security events")


@router.get("/health")
async def audit_trail_health():
    """Health check for audit trail service."""
    try:
        # Check if we can access the database
        db = await get_database()
        
        # Simple query to verify database connectivity
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "audit-trail",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("Audit trail health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "audit-trail",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/capabilities")
async def get_audit_capabilities():
    """Get audit trail service capabilities."""
    return {
        "service": "audit-trail",
        "version": "1.0.0",
        "features": {
            "event_logging": True,
            "comprehensive_filtering": True,
            "statistics": True,
            "security_monitoring": True,
            "retention_management": True,
            "real_time_querying": True
        },
        "supported_event_types": [e.value for e in AuditEventType],
        "supported_categories": [c.value for c in AuditEventCategory],
        "supported_severities": [s.value for s in AuditEventSeverity],
        "supported_operations": [op.value for op in ShareOperation],
        "supported_scopes": [sc.value for sc in PermissionScope],
        "limits": {
            "max_query_limit": 1000,
            "max_events_per_request": 100,
            "rate_limits": {
                "audit_create": "100/hour",
                "audit_query": "200/hour",
                "audit_stats": "50/hour"
            }
        },
        "retention": {
            "default_retention_days": 2555,  # 7 years
            "cleanup_batch_size": 1000,
            "supports_automated_cleanup": True
        }
    }