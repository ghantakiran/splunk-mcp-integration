"""
Webhook Service - Main FastAPI Application.

Provides webhook management and delivery capabilities for the Splunk MCP Integration.
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
from .models import WebhookEndpoint, WebhookEvent, WebhookDelivery
from .services.webhook_manager import WebhookManager
from .services.event_processor import EventProcessor
from .services.delivery_service import DeliveryService
from .utils.auth import get_current_user, require_permissions
from .utils.rate_limiter import check_rate_limit
from .utils.metrics import WebhookMetrics

logger = get_logger(__name__)

# Prometheus metrics
webhook_requests = Counter("webhook_requests_total", "Total webhook requests", ["method", "endpoint"])
webhook_latency = Histogram("webhook_request_duration_seconds", "Webhook request latency")
webhook_deliveries = Counter("webhook_deliveries_total", "Total webhook deliveries", ["status"])
webhook_errors = Counter("webhook_errors_total", "Total webhook errors", ["error_type"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Webhook Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized successfully")
        
        # Start background task processor
        app.state.task_processor = asyncio.create_task(start_background_processor())
        logger.info("Background task processor started")
        
        logger.info("Webhook Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        logger.info("Shutting down Webhook Service...")
        
        # Cancel background tasks
        if hasattr(app.state, "task_processor"):
            app.state.task_processor.cancel()
            try:
                await app.state.task_processor
            except asyncio.CancelledError:
                pass
        
        logger.info("Webhook Service shutdown complete")


async def start_background_processor():
    """Start background task processor for webhook delivery."""
    try:
        delivery_service = DeliveryService()
        await delivery_service.start_processor()
    except Exception as e:
        logger.error(f"Background processor failed: {e}")
        raise


app = FastAPI(
    title="Splunk MCP Webhook Service",
    description="Webhook management and delivery service for Splunk MCP Integration",
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
    
    logger = get_logger(__name__).bind(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )
    
    try:
        response = await call_next(request)
        duration = asyncio.get_event_loop().time() - start_time
        
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration=duration,
        )
        
        # Record metrics
        webhook_requests.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()
        webhook_latency.observe(duration)
        
        return response
        
    except Exception as e:
        duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            "Request failed",
            error=str(e),
            duration=duration,
        )
        webhook_errors.labels(error_type=type(e).__name__).inc()
        raise


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    try:
        await check_rate_limit(request)
        return await call_next(request)
    except HTTPException:
        webhook_errors.labels(error_type="rate_limit").inc()
        raise


# Dependency injection
async def get_webhook_manager() -> WebhookManager:
    """Get webhook manager instance."""
    db = await get_database()
    redis = await get_redis_client()
    return WebhookManager(db, redis)


async def get_event_processor() -> EventProcessor:
    """Get event processor instance."""
    db = await get_database()
    redis = await get_redis_client()
    return EventProcessor(db, redis)


async def get_delivery_service() -> DeliveryService:
    """Get delivery service instance."""
    return DeliveryService()


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "webhook-service", "version": "1.0.0"}


@app.get("/health/detailed")
async def detailed_health_check(
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Detailed health check with dependency status."""
    try:
        # Check database
        db_status = await webhook_manager.check_database_health()
        
        # Check Redis
        redis_status = await webhook_manager.check_redis_health()
        
        return {
            "status": "healthy" if all([db_status, redis_status]) else "unhealthy",
            "service": "webhook-service",
            "version": "1.0.0",
            "dependencies": {
                "database": "healthy" if db_status else "unhealthy",
                "redis": "healthy" if redis_status else "unhealthy",
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


# Webhook endpoint management
@app.post("/webhooks/endpoints")
async def create_webhook_endpoint(
    endpoint_data: Dict[str, Any],
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:create"])),
):
    """Create a new webhook endpoint."""
    try:
        endpoint = await webhook_manager.create_endpoint(
            endpoint_data,
            current_user.id,
        )
        
        return {
            "success": True,
            "data": endpoint,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "endpoint_id": endpoint.get("id"),
            },
        }
        
    except Exception as e:
        logger.error("Webhook endpoint creation failed", error=str(e))
        webhook_errors.labels(error_type="endpoint_creation").inc()
        raise HTTPException(status_code=500, detail="Webhook endpoint creation failed")


@app.get("/webhooks/endpoints")
async def list_webhook_endpoints(
    active_only: bool = True,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """List webhook endpoints for the current user."""
    try:
        endpoints = await webhook_manager.list_endpoints(
            current_user.id,
            active_only=active_only,
        )
        
        return {
            "success": True,
            "data": endpoints,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(endpoints),
            },
        }
        
    except Exception as e:
        logger.error("Webhook endpoint listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook endpoint listing failed")


@app.get("/webhooks/endpoints/{endpoint_id}")
async def get_webhook_endpoint(
    endpoint_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """Get webhook endpoint details."""
    try:
        endpoint = await webhook_manager.get_endpoint(endpoint_id, current_user.id)
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {
            "success": True,
            "data": endpoint,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "endpoint_id": endpoint_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook endpoint retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook endpoint retrieval failed")


@app.put("/webhooks/endpoints/{endpoint_id}")
async def update_webhook_endpoint(
    endpoint_id: str,
    endpoint_data: Dict[str, Any],
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:update"])),
):
    """Update webhook endpoint."""
    try:
        endpoint = await webhook_manager.update_endpoint(
            endpoint_id,
            endpoint_data,
            current_user.id,
        )
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {
            "success": True,
            "data": endpoint,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "endpoint_id": endpoint_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook endpoint update failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook endpoint update failed")


@app.delete("/webhooks/endpoints/{endpoint_id}")
async def delete_webhook_endpoint(
    endpoint_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:delete"])),
):
    """Delete webhook endpoint."""
    try:
        success = await webhook_manager.delete_endpoint(endpoint_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {
            "success": True,
            "message": "Webhook endpoint deleted successfully",
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "endpoint_id": endpoint_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook endpoint deletion failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook endpoint deletion failed")


# Event processing endpoints
@app.post("/webhooks/events/trigger")
async def trigger_webhook_event(
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    event_processor: EventProcessor = Depends(get_event_processor),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:trigger"])),
):
    """Trigger a webhook event manually."""
    try:
        event = await event_processor.create_event(
            event_data,
            current_user.id,
        )
        
        # Process event in background
        background_tasks.add_task(
            event_processor.process_event,
            event["id"]
        )
        
        return {
            "success": True,
            "data": event,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "event_id": event.get("id"),
            },
        }
        
    except Exception as e:
        logger.error("Webhook event triggering failed", error=str(e))
        webhook_errors.labels(error_type="event_trigger").inc()
        raise HTTPException(status_code=500, detail="Webhook event triggering failed")


@app.get("/webhooks/events")
async def list_webhook_events(
    endpoint_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    event_processor: EventProcessor = Depends(get_event_processor),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """List webhook events."""
    try:
        events = await event_processor.list_events(
            user_id=current_user.id,
            endpoint_id=endpoint_id,
            limit=limit,
            offset=offset,
        )
        
        return {
            "success": True,
            "data": events,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(events),
                "limit": limit,
                "offset": offset,
            },
        }
        
    except Exception as e:
        logger.error("Webhook event listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook event listing failed")


@app.get("/webhooks/events/{event_id}")
async def get_webhook_event(
    event_id: str,
    event_processor: EventProcessor = Depends(get_event_processor),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """Get webhook event details."""
    try:
        event = await event_processor.get_event(event_id, current_user.id)
        
        if not event:
            raise HTTPException(status_code=404, detail="Webhook event not found")
        
        return {
            "success": True,
            "data": event,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "event_id": event_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook event retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook event retrieval failed")


# Delivery management endpoints
@app.get("/webhooks/deliveries")
async def list_webhook_deliveries(
    endpoint_id: Optional[str] = None,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    delivery_service: DeliveryService = Depends(get_delivery_service),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """List webhook deliveries."""
    try:
        deliveries = await delivery_service.list_deliveries(
            user_id=current_user.id,
            endpoint_id=endpoint_id,
            event_id=event_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        
        return {
            "success": True,
            "data": deliveries,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "count": len(deliveries),
                "limit": limit,
                "offset": offset,
            },
        }
        
    except Exception as e:
        logger.error("Webhook delivery listing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook delivery listing failed")


@app.get("/webhooks/deliveries/{delivery_id}")
async def get_webhook_delivery(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:read"])),
):
    """Get webhook delivery details."""
    try:
        delivery = await delivery_service.get_delivery(delivery_id, current_user.id)
        
        if not delivery:
            raise HTTPException(status_code=404, detail="Webhook delivery not found")
        
        return {
            "success": True,
            "data": delivery,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "delivery_id": delivery_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook delivery retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook delivery retrieval failed")


@app.post("/webhooks/deliveries/{delivery_id}/retry")
async def retry_webhook_delivery(
    delivery_id: str,
    background_tasks: BackgroundTasks,
    delivery_service: DeliveryService = Depends(get_delivery_service),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:retry"])),
):
    """Retry a failed webhook delivery."""
    try:
        delivery = await delivery_service.get_delivery(delivery_id, current_user.id)
        
        if not delivery:
            raise HTTPException(status_code=404, detail="Webhook delivery not found")
        
        if delivery["status"] != "failed":
            raise HTTPException(status_code=400, detail="Only failed deliveries can be retried")
        
        # Retry delivery in background
        background_tasks.add_task(
            delivery_service.retry_delivery,
            delivery_id
        )
        
        return {
            "success": True,
            "message": "Webhook delivery retry initiated",
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "delivery_id": delivery_id,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook delivery retry failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook delivery retry failed")


# Analytics and metrics endpoints
@app.get("/webhooks/analytics/overview")
async def get_webhook_analytics(
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:analytics"])),
):
    """Get webhook analytics overview."""
    try:
        analytics = await webhook_manager.get_analytics(current_user.id)
        
        return {
            "success": True,
            "data": analytics,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": current_user.id,
            },
        }
        
    except Exception as e:
        logger.error("Webhook analytics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook analytics retrieval failed")


@app.get("/webhooks/analytics/metrics")
async def get_webhook_metrics(
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["webhook:analytics"])),
):
    """Get detailed webhook metrics."""
    try:
        metrics = WebhookMetrics()
        data = await metrics.get_user_metrics(current_user.id)
        
        return {
            "success": True,
            "data": data,
            "metadata": {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": current_user.id,
            },
        }
        
    except Exception as e:
        logger.error("Webhook metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook metrics retrieval failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )