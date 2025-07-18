"""
ITSM Service - Main FastAPI Application.

Provides ITSM tool integration capabilities for the Splunk MCP Integration.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from .core.config import settings
from .core.logging import get_logger
from .core.database import get_database, init_database
from .core.redis_client import get_redis_client, init_redis
from .models import ITSMTicket, ITSMIntegration, ITSMWorkflow
from .services.servicenow_manager import ServiceNowManager
from .services.jira_manager import JiraManager
from .services.workflow_engine import WorkflowEngine
from .services.sync_manager import SyncManager
from .utils.auth import get_current_user, require_permissions
from .utils.rate_limiter import check_rate_limit
from .utils.metrics import ITSMMetrics

logger = get_logger(__name__)

# Prometheus metrics
itsm_requests = Counter("itsm_requests_total", "Total ITSM requests", ["method", "endpoint", "provider"])
itsm_latency = Histogram("itsm_request_duration_seconds", "ITSM request latency")
itsm_tickets = Counter("itsm_tickets_total", "Total ITSM tickets", ["provider", "action", "status"])
itsm_sync_operations = Counter("itsm_sync_operations_total", "Total sync operations", ["provider", "status"])
itsm_errors = Counter("itsm_errors_total", "Total ITSM errors", ["error_type", "provider"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ITSM Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized successfully")
        
        # Start background sync processor
        app.state.sync_processor = asyncio.create_task(start_sync_processor())
        logger.info("Background sync processor started")
        
        logger.info("ITSM Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        logger.info("Shutting down ITSM Service...")
        
        # Cancel background tasks
        if hasattr(app.state, "sync_processor"):
            app.state.sync_processor.cancel()
            try:
                await app.state.sync_processor
            except asyncio.CancelledError:
                pass
        
        logger.info("ITSM Service shutdown complete")


async def start_sync_processor():
    """Start background sync processor."""
    try:
        sync_manager = SyncManager()
        await sync_manager.start_processor()
    except Exception as e:
        logger.error(f"Sync processor failed: {e}")
        raise


app = FastAPI(
    title="Splunk MCP ITSM Service",
    description="ITSM tool integration service for Splunk MCP Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with correlation ID."""
    correlation_id = request.headers.get("x-correlation-id", "unknown")
    start_time = asyncio.get_event_loop().time()
    
    logger_instance = get_logger(__name__).bind(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )
    
    try:
        response = await call_next(request)
        duration = asyncio.get_event_loop().time() - start_time
        
        logger_instance.info(
            "Request completed",
            status_code=response.status_code,
            duration=duration,
        )
        
        # Record metrics
        itsm_requests.labels(
            method=request.method,
            endpoint=request.url.path,
            provider="general"
        ).inc()
        itsm_latency.observe(duration)
        
        return response
        
    except Exception as e:
        duration = asyncio.get_event_loop().time() - start_time
        logger_instance.error(
            "Request failed",
            error=str(e),
            duration=duration,
        )
        itsm_errors.labels(error_type=type(e).__name__, provider="general").inc()
        raise


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    try:
        await check_rate_limit(request)
        return await call_next(request)
    except HTTPException:
        itsm_errors.labels(error_type="rate_limit", provider="general").inc()
        raise


# Dependency injection
async def get_servicenow_manager() -> ServiceNowManager:
    """Get ServiceNow manager instance."""
    db = await get_database()
    redis = await get_redis_client()
    return ServiceNowManager(db, redis)


async def get_jira_manager() -> JiraManager:
    """Get Jira manager instance."""
    db = await get_database()
    redis = await get_redis_client()
    return JiraManager(db, redis)


async def get_workflow_engine() -> WorkflowEngine:
    """Get workflow engine instance."""
    db = await get_database()
    redis = await get_redis_client()
    return WorkflowEngine(db, redis)


async def get_sync_manager() -> SyncManager:
    """Get sync manager instance."""
    return SyncManager()


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "itsm-service", "version": "1.0.0"}


@app.get("/health/detailed")
async def detailed_health_check(
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager)
):
    """Detailed health check with dependency status."""
    try:
        # Check database
        db_status = await servicenow_manager.check_database_health()
        
        # Check Redis
        redis_status = await servicenow_manager.check_redis_health()
        
        # Check ITSM connections
        servicenow_status = await servicenow_manager.check_connection()
        
        return {
            "status": "healthy" if all([db_status, redis_status]) else "unhealthy",
            "service": "itsm-service",
            "version": "1.0.0",
            "dependencies": {
                "database": "healthy" if db_status else "unhealthy",
                "redis": "healthy" if redis_status else "unhealthy",
                "servicenow": "healthy" if servicenow_status else "unhealthy",
            },
            "timestamp": "2025-01-16T10:30:00Z",
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-16T10:30:00Z",
            }
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


# ServiceNow integration endpoints
@app.post("/itsm/servicenow/tickets")
async def create_servicenow_ticket(
    ticket_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:create"])),
):
    """Create a ServiceNow ticket."""
    try:
        ticket = await servicenow_manager.create_ticket(
            ticket_data,
            current_user.id,
        )
        
        # Update metrics
        itsm_tickets.labels(
            provider="servicenow",
            action="create",
            status="success"
        ).inc()
        
        return {
            "success": True,
            "data": ticket,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "ticket_id": ticket.get("sys_id"),
                "provider": "servicenow"
            },
        }
        
    except Exception as e:
        logger.error("ServiceNow ticket creation failed", error=str(e))
        itsm_tickets.labels(
            provider="servicenow",
            action="create",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="ServiceNow ticket creation failed")


@app.get("/itsm/servicenow/tickets")
async def list_servicenow_tickets(
    state: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:read"])),
):
    """List ServiceNow tickets."""
    try:
        tickets = await servicenow_manager.list_tickets(
            user_id=current_user.id,
            state=state,
            assigned_to=assigned_to,
            limit=limit,
            offset=offset,
        )
        
        return {
            "success": True,
            "data": tickets,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(tickets),
                "provider": "servicenow"
            },
        }
        
    except Exception as e:
        logger.error("ServiceNow ticket listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="ServiceNow ticket listing failed")


@app.get("/itsm/servicenow/tickets/{ticket_id}")
async def get_servicenow_ticket(
    ticket_id: str,
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:read"])),
):
    """Get ServiceNow ticket details."""
    try:
        ticket = await servicenow_manager.get_ticket(ticket_id, current_user.id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="ServiceNow ticket not found")
        
        return {
            "success": True,
            "data": ticket,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "ticket_id": ticket_id,
                "provider": "servicenow"
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ServiceNow ticket retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="ServiceNow ticket retrieval failed")


@app.put("/itsm/servicenow/tickets/{ticket_id}")
async def update_servicenow_ticket(
    ticket_id: str,
    ticket_data: Dict[str, Any],
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:update"])),
):
    """Update ServiceNow ticket."""
    try:
        ticket = await servicenow_manager.update_ticket(
            ticket_id,
            ticket_data,
            current_user.id,
        )
        
        if not ticket:
            raise HTTPException(status_code=404, detail="ServiceNow ticket not found")
        
        # Update metrics
        itsm_tickets.labels(
            provider="servicenow",
            action="update",
            status="success"
        ).inc()
        
        return {
            "success": True,
            "data": ticket,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "ticket_id": ticket_id,
                "provider": "servicenow"
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ServiceNow ticket update failed", error=str(e))
        itsm_tickets.labels(
            provider="servicenow",
            action="update",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="ServiceNow ticket update failed")


# Jira integration endpoints
@app.post("/itsm/jira/issues")
async def create_jira_issue(
    issue_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    jira_manager: JiraManager = Depends(get_jira_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:create"])),
):
    """Create a Jira issue."""
    try:
        issue = await jira_manager.create_issue(
            issue_data,
            current_user.id,
        )
        
        # Update metrics
        itsm_tickets.labels(
            provider="jira",
            action="create",
            status="success"
        ).inc()
        
        return {
            "success": True,
            "data": issue,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "issue_id": issue.get("id"),
                "provider": "jira"
            },
        }
        
    except Exception as e:
        logger.error("Jira issue creation failed", error=str(e))
        itsm_tickets.labels(
            provider="jira",
            action="create",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Jira issue creation failed")


@app.get("/itsm/jira/issues")
async def list_jira_issues(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    project: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    jira_manager: JiraManager = Depends(get_jira_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:read"])),
):
    """List Jira issues."""
    try:
        issues = await jira_manager.list_issues(
            user_id=current_user.id,
            status=status,
            assignee=assignee,
            project=project,
            limit=limit,
            offset=offset,
        )
        
        return {
            "success": True,
            "data": issues,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(issues),
                "provider": "jira"
            },
        }
        
    except Exception as e:
        logger.error("Jira issue listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Jira issue listing failed")


# Workflow automation endpoints
@app.post("/itsm/workflows")
async def create_workflow(
    workflow_data: Dict[str, Any],
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:workflow:create"])),
):
    """Create an ITSM workflow."""
    try:
        workflow = await workflow_engine.create_workflow(
            workflow_data,
            current_user.id,
        )
        
        return {
            "success": True,
            "data": workflow,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "workflow_id": workflow.get("id"),
            },
        }
        
    except Exception as e:
        logger.error("Workflow creation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Workflow creation failed")


@app.get("/itsm/workflows")
async def list_workflows(
    active_only: bool = True,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:workflow:read"])),
):
    """List ITSM workflows."""
    try:
        workflows = await workflow_engine.list_workflows(
            current_user.id,
            active_only=active_only,
        )
        
        return {
            "success": True,
            "data": workflows,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(workflows),
            },
        }
        
    except Exception as e:
        logger.error("Workflow listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Workflow listing failed")


@app.post("/itsm/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    execution_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:workflow:execute"])),
):
    """Execute an ITSM workflow."""
    try:
        # Execute workflow in background
        background_tasks.add_task(
            workflow_engine.execute_workflow,
            workflow_id,
            execution_data,
            current_user.id
        )
        
        return {
            "success": True,
            "message": "Workflow execution initiated",
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "workflow_id": workflow_id,
            },
        }
        
    except Exception as e:
        logger.error("Workflow execution failed", error=str(e))
        raise HTTPException(status_code=500, detail="Workflow execution failed")


# Synchronization endpoints
@app.post("/itsm/sync/start")
async def start_sync(
    sync_config: Dict[str, Any],
    background_tasks: BackgroundTasks,
    sync_manager: SyncManager = Depends(get_sync_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:sync"])),
):
    """Start ITSM synchronization."""
    try:
        # Start sync in background
        background_tasks.add_task(
            sync_manager.start_sync,
            sync_config,
            current_user.id
        )
        
        return {
            "success": True,
            "message": "Synchronization started",
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": current_user.id,
            },
        }
        
    except Exception as e:
        logger.error("Sync start failed", error=str(e))
        raise HTTPException(status_code=500, detail="Sync start failed")


@app.get("/itsm/sync/status")
async def get_sync_status(
    sync_manager: SyncManager = Depends(get_sync_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:sync"])),
):
    """Get synchronization status."""
    try:
        status = await sync_manager.get_sync_status(current_user.id)
        
        return {
            "success": True,
            "data": status,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": current_user.id,
            },
        }
        
    except Exception as e:
        logger.error("Sync status retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Sync status retrieval failed")


# Analytics and reporting endpoints
@app.get("/itsm/analytics/overview")
async def get_itsm_analytics(
    days: int = 30,
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:analytics"])),
):
    """Get ITSM analytics overview."""
    try:
        analytics = await servicenow_manager.get_analytics(current_user.id, days)
        
        return {
            "success": True,
            "data": analytics,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": current_user.id,
                "period_days": days,
            },
        }
        
    except Exception as e:
        logger.error("ITSM analytics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="ITSM analytics retrieval failed")


@app.get("/itsm/integrations")
async def list_integrations(
    active_only: bool = True,
    servicenow_manager: ServiceNowManager = Depends(get_servicenow_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["itsm:read"])),
):
    """List ITSM integrations."""
    try:
        integrations = await servicenow_manager.list_integrations(
            current_user.id,
            active_only=active_only,
        )
        
        return {
            "success": True,
            "data": integrations,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(integrations),
            },
        }
        
    except Exception as e:
        logger.error("Integration listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Integration listing failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )