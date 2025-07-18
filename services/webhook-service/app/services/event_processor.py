"""
Event processing service for the Webhook Service.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from ..core.logging import get_logger, add_event_context, add_webhook_context
from ..core.database import get_db_session
from ..core.redis_client import RedisCache
from ..models.webhook_models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookDelivery,
    EventType,
    WebhookStatus,
    WebhookEventCreate,
    WebhookEventResponse,
)

logger = get_logger(__name__)


class EventProcessor:
    """Processes webhook events and manages event lifecycle."""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.cache = RedisCache(redis_client)
    
    async def create_event(
        self,
        event_data: Dict[str, Any],
        user_id: str,
        endpoint_id: str = None,
    ) -> Dict[str, Any]:
        """Create a new webhook event."""
        try:
            # Validate event data
            create_data = WebhookEventCreate(**event_data)
            
            # Create event record
            event = WebhookEvent(
                endpoint_id=endpoint_id,
                event_type=create_data.event_type,
                source=create_data.source,
                payload=create_data.payload,
                metadata=create_data.metadata,
            )
            
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            
            logger.info(
                "Webhook event created",
                **add_event_context(
                    event.id,
                    event.event_type.value,
                    event.source,
                    len(json.dumps(event.payload))
                )
            )
            
            # Process event if endpoint_id is provided
            if endpoint_id:
                await self.process_event(event.id)
            else:
                # Find matching endpoints and process
                await self._process_event_for_matching_endpoints(event)
            
            return self._event_to_dict(event)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Event creation failed: {e}")
            raise
    
    async def process_event(self, event_id: str) -> None:
        """Process a webhook event for delivery."""
        try:
            async with get_db_session() as db:
                # Get event with endpoint
                stmt = select(WebhookEvent).where(
                    WebhookEvent.id == event_id
                ).options(selectinload(WebhookEvent.endpoint))
                
                result = await db.execute(stmt)
                event = result.scalar_one_or_none()
                
                if not event:
                    logger.error(f"Event not found: {event_id}")
                    return
                
                if event.processed:
                    logger.warning(f"Event already processed: {event_id}")
                    return
                
                # Process for specific endpoint or find matching endpoints
                if event.endpoint_id:
                    await self._schedule_delivery_for_endpoint(event, event.endpoint)
                else:
                    await self._process_event_for_matching_endpoints(event)
                
                # Mark event as processed
                event.processed = True
                event.processed_at = datetime.utcnow()
                await db.commit()
                
                logger.info(
                    "Event processed successfully",
                    **add_event_context(event.id, event.event_type.value, event.source)
                )
                
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            raise
    
    async def get_event(
        self,
        event_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get event details."""
        try:
            # Check if user has access to this event
            stmt = select(WebhookEvent).join(WebhookEndpoint).where(
                WebhookEvent.id == event_id,
                WebhookEndpoint.user_id == user_id
            )
            result = await self.db.execute(stmt)
            event = result.scalar_one_or_none()
            
            if event:
                return self._event_to_dict(event)
            return None
            
        except Exception as e:
            logger.error(f"Event retrieval failed: {e}")
            raise
    
    async def list_events(
        self,
        user_id: str,
        endpoint_id: str = None,
        event_type: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List webhook events for a user."""
        try:
            # Build query
            stmt = select(WebhookEvent).join(WebhookEndpoint).where(
                WebhookEndpoint.user_id == user_id
            )
            
            if endpoint_id:
                stmt = stmt.where(WebhookEvent.endpoint_id == endpoint_id)
            
            if event_type:
                stmt = stmt.where(WebhookEvent.event_type == EventType(event_type))
            
            stmt = stmt.offset(offset).limit(limit).order_by(
                WebhookEvent.created_at.desc()
            )
            
            result = await self.db.execute(stmt)
            events = result.scalars().all()
            
            return [self._event_to_dict(event) for event in events]
            
        except Exception as e:
            logger.error(f"Event listing failed: {e}")
            raise
    
    async def trigger_system_event(
        self,
        event_type: EventType,
        source: str,
        payload: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Trigger a system-wide event to all matching endpoints."""
        try:
            # Create event without specific endpoint
            event = WebhookEvent(
                event_type=event_type,
                source=source,
                payload=payload,
                metadata=metadata or {},
            )
            
            async with get_db_session() as db:
                db.add(event)
                await db.commit()
                await db.refresh(event)
                
                # Process for all matching endpoints
                await self._process_event_for_matching_endpoints(event)
                
                # Mark as processed
                event.processed = True
                event.processed_at = datetime.utcnow()
                await db.commit()
                
                logger.info(
                    "System event triggered",
                    **add_event_context(event.id, event_type.value, source)
                )
                
        except Exception as e:
            logger.error(f"System event trigger failed: {e}")
            raise
    
    async def cleanup_old_events(self, retention_days: int = 30) -> int:
        """Clean up old events."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Delete old events
            stmt = delete(WebhookEvent).where(
                WebhookEvent.created_at < cutoff_date,
                WebhookEvent.processed == True
            )
            
            result = await self.db.execute(stmt)
            deleted_count = result.rowcount
            await self.db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Event cleanup failed: {e}")
            raise
    
    async def get_event_statistics(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get event statistics for a user."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get event counts by type
            stmt = select(
                WebhookEvent.event_type,
                func.count(WebhookEvent.id).label('count')
            ).join(WebhookEndpoint).where(
                WebhookEndpoint.user_id == user_id,
                WebhookEvent.created_at >= start_date
            ).group_by(WebhookEvent.event_type)
            
            result = await self.db.execute(stmt)
            event_counts = {row[0].value: row[1] for row in result}
            
            # Get total events
            total_stmt = select(func.count(WebhookEvent.id)).join(
                WebhookEndpoint
            ).where(
                WebhookEndpoint.user_id == user_id,
                WebhookEvent.created_at >= start_date
            )
            total_events = (await self.db.execute(total_stmt)).scalar()
            
            # Get processed events
            processed_stmt = select(func.count(WebhookEvent.id)).join(
                WebhookEndpoint
            ).where(
                WebhookEndpoint.user_id == user_id,
                WebhookEvent.created_at >= start_date,
                WebhookEvent.processed == True
            )
            processed_events = (await self.db.execute(processed_stmt)).scalar()
            
            return {
                "period_days": days,
                "total_events": total_events,
                "processed_events": processed_events,
                "processing_rate": (processed_events / total_events * 100) if total_events > 0 else 0,
                "events_by_type": event_counts,
            }
            
        except Exception as e:
            logger.error(f"Event statistics retrieval failed: {e}")
            raise
    
    async def _process_event_for_matching_endpoints(self, event: WebhookEvent) -> None:
        """Process event for all matching endpoints."""
        try:
            # Get matching endpoints
            from .webhook_manager import WebhookManager
            webhook_manager = WebhookManager(self.db, await get_redis_client())
            
            matching_endpoints = await webhook_manager.get_endpoints_for_event(
                event.event_type,
                event.metadata
            )
            
            # Schedule deliveries for matching endpoints
            for endpoint_data in matching_endpoints:
                await self._schedule_delivery_for_endpoint_data(event, endpoint_data)
            
            logger.info(
                f"Event scheduled for {len(matching_endpoints)} endpoints",
                **add_event_context(event.id, event.event_type.value, event.source)
            )
            
        except Exception as e:
            logger.error(f"Event processing for matching endpoints failed: {e}")
            raise
    
    async def _schedule_delivery_for_endpoint(
        self,
        event: WebhookEvent,
        endpoint: WebhookEndpoint
    ) -> None:
        """Schedule delivery for a specific endpoint."""
        if endpoint.status != WebhookStatus.ACTIVE:
            logger.warning(
                f"Skipping delivery to inactive endpoint: {endpoint.id}"
            )
            return
        
        try:
            from .delivery_service import DeliveryService
            delivery_service = DeliveryService()
            
            await delivery_service.schedule_delivery(
                endpoint.id,
                event.id
            )
            
            logger.info(
                "Delivery scheduled",
                **add_webhook_context(endpoint.id, endpoint.url, event.event_type.value)
            )
            
        except Exception as e:
            logger.error(f"Delivery scheduling failed: {e}")
            raise
    
    async def _schedule_delivery_for_endpoint_data(
        self,
        event: WebhookEvent,
        endpoint_data: Dict[str, Any]
    ) -> None:
        """Schedule delivery for endpoint data."""
        try:
            from .delivery_service import DeliveryService
            delivery_service = DeliveryService()
            
            await delivery_service.schedule_delivery(
                endpoint_data["id"],
                event.id
            )
            
            logger.info(
                "Delivery scheduled",
                **add_webhook_context(
                    endpoint_data["id"],
                    endpoint_data["url"],
                    event.event_type.value
                )
            )
            
        except Exception as e:
            logger.error(f"Delivery scheduling failed: {e}")
            raise
    
    def _event_to_dict(self, event: WebhookEvent) -> Dict[str, Any]:
        """Convert event model to dictionary."""
        return {
            "id": event.id,
            "endpoint_id": event.endpoint_id,
            "event_type": event.event_type.value,
            "source": event.source,
            "payload": event.payload,
            "metadata": event.metadata,
            "processed": event.processed,
            "processed_at": event.processed_at,
            "created_at": event.created_at,
        }