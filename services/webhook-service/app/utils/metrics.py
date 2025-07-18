"""
Metrics collection utilities for Webhook Service.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func
from prometheus_client import Counter, Histogram, Gauge, generate_latest

from ..core.database import get_db_session
from ..core.redis_client import get_redis_client, RedisCache
from ..core.logging import get_logger
from ..models.webhook_models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookDelivery,
    WebhookMetric,
    DeliveryStatus,
    EventType,
)

logger = get_logger(__name__)

# Prometheus metrics
webhook_events_total = Counter(
    "webhook_events_total",
    "Total webhook events",
    ["event_type", "source"]
)

webhook_deliveries_total = Counter(
    "webhook_deliveries_total",
    "Total webhook deliveries",
    ["status", "endpoint_id"]
)

webhook_delivery_duration = Histogram(
    "webhook_delivery_duration_seconds",
    "Webhook delivery duration",
    ["endpoint_id", "status"]
)

webhook_endpoints_active = Gauge(
    "webhook_endpoints_active",
    "Number of active webhook endpoints"
)

webhook_queue_size = Gauge(
    "webhook_queue_size",
    "Size of webhook delivery queue"
)


class WebhookMetrics:
    """Webhook metrics collector and analyzer."""
    
    def __init__(self):
        self.cache = None
    
    async def _get_cache(self) -> RedisCache:
        """Get Redis cache instance."""
        if not self.cache:
            redis_client = await get_redis_client()
            self.cache = RedisCache(redis_client)
        return self.cache
    
    async def record_event_metric(
        self,
        event_type: EventType,
        source: str,
        endpoint_count: int = 1
    ) -> None:
        """Record event metric."""
        try:
            # Update Prometheus metrics
            webhook_events_total.labels(
                event_type=event_type.value,
                source=source
            ).inc()
            
            # Store in database for historical analysis
            async with get_db_session() as db:
                metric = WebhookMetric(
                    metric_name="event_created",
                    metric_value=1.0,
                    metric_type="counter",
                    tags={
                        "event_type": event_type.value,
                        "source": source,
                        "endpoint_count": endpoint_count
                    },
                    time_bucket="hour"
                )
                
                db.add(metric)
                await db.commit()
            
        except Exception as e:
            logger.error(f"Event metric recording failed: {e}")
    
    async def record_delivery_metric(
        self,
        endpoint_id: str,
        status: DeliveryStatus,
        duration: float = None,
        attempt_number: int = 1
    ) -> None:
        """Record delivery metric."""
        try:
            # Update Prometheus metrics
            webhook_deliveries_total.labels(
                status=status.value,
                endpoint_id=endpoint_id
            ).inc()
            
            if duration is not None:
                webhook_delivery_duration.labels(
                    endpoint_id=endpoint_id,
                    status=status.value
                ).observe(duration / 1000)  # Convert to seconds
            
            # Store in database
            async with get_db_session() as db:
                metric = WebhookMetric(
                    endpoint_id=endpoint_id,
                    metric_name="delivery_completed",
                    metric_value=1.0,
                    metric_type="counter",
                    tags={
                        "status": status.value,
                        "duration_ms": duration,
                        "attempt_number": attempt_number
                    },
                    time_bucket="hour"
                )
                
                db.add(metric)
                await db.commit()
            
        except Exception as e:
            logger.error(f"Delivery metric recording failed: {e}")
    
    async def update_queue_metrics(self) -> None:
        """Update queue size metrics."""
        try:
            from ..core.redis_client import RedisQueue
            
            redis_client = await get_redis_client()
            queue = RedisQueue(redis_client, "webhook_delivery_queue")
            
            queue_size = await queue.size()
            webhook_queue_size.set(queue_size)
            
        except Exception as e:
            logger.error(f"Queue metrics update failed: {e}")
    
    async def update_endpoint_metrics(self) -> None:
        """Update endpoint metrics."""
        try:
            async with get_db_session() as db:
                # Count active endpoints
                stmt = select(func.count(WebhookEndpoint.id)).where(
                    WebhookEndpoint.status == "active"
                )
                active_count = (await db.execute(stmt)).scalar()
                
                webhook_endpoints_active.set(active_count)
                
        except Exception as e:
            logger.error(f"Endpoint metrics update failed: {e}")
    
    async def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get metrics for a specific user."""
        try:
            async with get_db_session() as db:
                # Basic counts
                endpoint_stmt = select(func.count(WebhookEndpoint.id)).where(
                    WebhookEndpoint.user_id == user_id
                )
                total_endpoints = (await db.execute(endpoint_stmt)).scalar()
                
                active_endpoint_stmt = select(func.count(WebhookEndpoint.id)).where(
                    WebhookEndpoint.user_id == user_id,
                    WebhookEndpoint.status == "active"
                )
                active_endpoints = (await db.execute(active_endpoint_stmt)).scalar()
                
                # Today's events and deliveries
                today = datetime.utcnow().date()
                start_of_day = datetime.combine(today, datetime.min.time())
                
                events_today_stmt = select(func.count(WebhookEvent.id)).join(
                    WebhookEndpoint
                ).where(
                    WebhookEndpoint.user_id == user_id,
                    WebhookEvent.created_at >= start_of_day
                )
                events_today = (await db.execute(events_today_stmt)).scalar()
                
                deliveries_today_stmt = select(func.count(WebhookDelivery.id)).join(
                    WebhookEndpoint
                ).where(
                    WebhookEndpoint.user_id == user_id,
                    WebhookDelivery.created_at >= start_of_day
                )
                deliveries_today = (await db.execute(deliveries_today_stmt)).scalar()
                
                # Success rate calculation
                successful_today_stmt = select(func.count(WebhookDelivery.id)).join(
                    WebhookEndpoint
                ).where(
                    WebhookEndpoint.user_id == user_id,
                    WebhookDelivery.created_at >= start_of_day,
                    WebhookDelivery.status == DeliveryStatus.DELIVERED
                )
                successful_today = (await db.execute(successful_today_stmt)).scalar()
                
                success_rate = (successful_today / deliveries_today * 100) if deliveries_today > 0 else 0
                
                # Average response time
                avg_response_stmt = select(func.avg(WebhookDelivery.response_time)).join(
                    WebhookEndpoint
                ).where(
                    WebhookEndpoint.user_id == user_id,
                    WebhookDelivery.created_at >= start_of_day,
                    WebhookDelivery.status == DeliveryStatus.DELIVERED
                )
                avg_response_time = (await db.execute(avg_response_stmt)).scalar() or 0
                
                return {
                    "total_endpoints": total_endpoints,
                    "active_endpoints": active_endpoints,
                    "events_today": events_today,
                    "deliveries_today": deliveries_today,
                    "successful_deliveries_today": successful_today,
                    "failed_deliveries_today": deliveries_today - successful_today,
                    "success_rate": round(success_rate, 2),
                    "average_response_time": round(avg_response_time, 2) if avg_response_time else 0,
                }
                
        except Exception as e:
            logger.error(f"User metrics retrieval failed: {e}")
            raise
    
    async def get_endpoint_metrics(
        self,
        endpoint_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get metrics for a specific endpoint."""
        try:
            async with get_db_session() as db:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Event counts
                events_stmt = select(func.count(WebhookEvent.id)).where(
                    WebhookEvent.endpoint_id == endpoint_id,
                    WebhookEvent.created_at >= start_date
                )
                total_events = (await db.execute(events_stmt)).scalar()
                
                # Delivery metrics
                deliveries_stmt = select(func.count(WebhookDelivery.id)).where(
                    WebhookDelivery.endpoint_id == endpoint_id,
                    WebhookDelivery.created_at >= start_date
                )
                total_deliveries = (await db.execute(deliveries_stmt)).scalar()
                
                successful_stmt = select(func.count(WebhookDelivery.id)).where(
                    WebhookDelivery.endpoint_id == endpoint_id,
                    WebhookDelivery.created_at >= start_date,
                    WebhookDelivery.status == DeliveryStatus.DELIVERED
                )
                successful_deliveries = (await db.execute(successful_stmt)).scalar()
                
                # Response time statistics
                response_time_stats = await db.execute(
                    select(
                        func.min(WebhookDelivery.response_time),
                        func.max(WebhookDelivery.response_time),
                        func.avg(WebhookDelivery.response_time)
                    ).where(
                        WebhookDelivery.endpoint_id == endpoint_id,
                        WebhookDelivery.created_at >= start_date,
                        WebhookDelivery.status == DeliveryStatus.DELIVERED,
                        WebhookDelivery.response_time.isnot(None)
                    )
                )
                min_time, max_time, avg_time = response_time_stats.first()
                
                return {
                    "period_days": days,
                    "total_events": total_events,
                    "total_deliveries": total_deliveries,
                    "successful_deliveries": successful_deliveries,
                    "failed_deliveries": total_deliveries - successful_deliveries,
                    "success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0,
                    "response_time": {
                        "min": min_time or 0,
                        "max": max_time or 0,
                        "avg": avg_time or 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Endpoint metrics retrieval failed: {e}")
            raise
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        try:
            cache = await self._get_cache()
            
            # Check cache first
            cached_metrics = await cache.get("system_metrics")
            if cached_metrics:
                import json
                return json.loads(cached_metrics)
            
            async with get_db_session() as db:
                # Get counts
                total_endpoints = (await db.execute(
                    select(func.count(WebhookEndpoint.id))
                )).scalar()
                
                active_endpoints = (await db.execute(
                    select(func.count(WebhookEndpoint.id)).where(
                        WebhookEndpoint.status == "active"
                    )
                )).scalar()
                
                total_events = (await db.execute(
                    select(func.count(WebhookEvent.id))
                )).scalar()
                
                total_deliveries = (await db.execute(
                    select(func.count(WebhookDelivery.id))
                )).scalar()
                
                successful_deliveries = (await db.execute(
                    select(func.count(WebhookDelivery.id)).where(
                        WebhookDelivery.status == DeliveryStatus.DELIVERED
                    )
                )).scalar()
                
                # Queue size
                from ..core.redis_client import RedisQueue
                redis_client = await get_redis_client()
                queue = RedisQueue(redis_client, "webhook_delivery_queue")
                queue_size = await queue.size()
                
                metrics = {
                    "total_endpoints": total_endpoints,
                    "active_endpoints": active_endpoints,
                    "total_events": total_events,
                    "total_deliveries": total_deliveries,
                    "successful_deliveries": successful_deliveries,
                    "failed_deliveries": total_deliveries - successful_deliveries,
                    "success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0,
                    "queue_size": queue_size,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache for 5 minutes
                import json
                await cache.set(
                    "system_metrics",
                    json.dumps(metrics, default=str),
                    ttl=300
                )
                
                return metrics
                
        except Exception as e:
            logger.error(f"System metrics retrieval failed: {e}")
            raise
    
    async def collect_metrics_periodically(self) -> None:
        """Periodically collect and update metrics."""
        while True:
            try:
                await self.update_endpoint_metrics()
                await self.update_queue_metrics()
                
                # Sleep for 1 minute before next collection
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic metrics collection failed: {e}")
                await asyncio.sleep(60)