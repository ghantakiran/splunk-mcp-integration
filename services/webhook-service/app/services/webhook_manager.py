"""
Webhook management service for the Webhook Service.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from ..core.logging import get_logger, add_webhook_context, add_user_context
from ..core.database import get_db_session
from ..core.redis_client import RedisCache
from ..models.webhook_models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookDelivery,
    WebhookLog,
    WebhookStatus,
    EventType,
    DeliveryStatus,
    WebhookEndpointCreate,
    WebhookEndpointUpdate,
    WebhookEndpointResponse,
    WebhookAnalytics,
)
from ..models.user_models import WebhookUser
from ..utils.validation import validate_webhook_url, validate_webhook_headers
from ..utils.security import generate_webhook_secret, validate_webhook_secret

logger = get_logger(__name__)


class WebhookManager:
    """Manages webhook endpoints and related operations."""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.cache = RedisCache(redis_client)
    
    async def create_endpoint(
        self,
        endpoint_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        """Create a new webhook endpoint."""
        logger = get_logger(__name__).bind(**add_user_context(user_id, ""))
        
        try:
            # Validate endpoint data
            create_data = WebhookEndpointCreate(**endpoint_data)
            
            # Additional validation
            await self._validate_endpoint_creation(create_data, user_id)
            
            # Generate secret if not provided
            secret = create_data.secret
            if not secret:
                secret = generate_webhook_secret()
            
            # Create webhook endpoint
            endpoint = WebhookEndpoint(
                user_id=user_id,
                name=create_data.name,
                description=create_data.description,
                url=str(create_data.url),
                method=create_data.method,
                headers=create_data.headers,
                secret=secret,
                event_types=[et.value for et in create_data.event_types],
                event_filters=create_data.event_filters,
                timeout=create_data.timeout,
                retry_attempts=create_data.retry_attempts,
                retry_delay=create_data.retry_delay,
            )
            
            self.db.add(endpoint)
            await self.db.commit()
            await self.db.refresh(endpoint)
            
            # Log activity
            await self._log_activity(
                endpoint_id=endpoint.id,
                user_id=user_id,
                action="created",
                details={"name": endpoint.name, "url": endpoint.url}
            )
            
            # Clear cache
            await self._invalidate_user_cache(user_id)
            
            logger.info(
                "Webhook endpoint created",
                **add_webhook_context(endpoint.id, endpoint.url, "", "")
            )
            
            return self._endpoint_to_dict(endpoint)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Webhook endpoint creation failed: {e}")
            raise
    
    async def get_endpoint(
        self,
        endpoint_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get webhook endpoint by ID."""
        try:
            # Check cache first
            cache_key = f"webhook_endpoint:{endpoint_id}:{user_id}"
            cached = await self.cache.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
            
            # Query database
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
            result = await self.db.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if endpoint:
                endpoint_dict = self._endpoint_to_dict(endpoint)
                # Cache result
                import json
                await self.cache.set(
                    cache_key,
                    json.dumps(endpoint_dict, default=str),
                    ttl=300  # 5 minutes
                )
                return endpoint_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Webhook endpoint retrieval failed: {e}")
            raise
    
    async def list_endpoints(
        self,
        user_id: str,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List webhook endpoints for a user."""
        try:
            # Build query
            stmt = select(WebhookEndpoint).where(WebhookEndpoint.user_id == user_id)
            
            if active_only:
                stmt = stmt.where(WebhookEndpoint.status == WebhookStatus.ACTIVE)
            
            stmt = stmt.offset(offset).limit(limit).order_by(WebhookEndpoint.created_at.desc())
            
            result = await self.db.execute(stmt)
            endpoints = result.scalars().all()
            
            return [self._endpoint_to_dict(endpoint) for endpoint in endpoints]
            
        except Exception as e:
            logger.error(f"Webhook endpoint listing failed: {e}")
            raise
    
    async def update_endpoint(
        self,
        endpoint_id: str,
        endpoint_data: Dict[str, Any],
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Update webhook endpoint."""
        logger = get_logger(__name__).bind(**add_user_context(user_id, ""))
        
        try:
            # Validate update data
            update_data = WebhookEndpointUpdate(**endpoint_data)
            
            # Get existing endpoint
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
            result = await self.db.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                return None
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            
            if update_dict:
                for field, value in update_dict.items():
                    if field == "url" and value:
                        value = str(value)
                    elif field == "event_types" and value:
                        value = [et.value for et in value]
                    setattr(endpoint, field, value)
                
                endpoint.updated_at = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(endpoint)
                
                # Log activity
                await self._log_activity(
                    endpoint_id=endpoint.id,
                    user_id=user_id,
                    action="updated",
                    details=update_dict
                )
                
                # Clear cache
                await self._invalidate_endpoint_cache(endpoint_id, user_id)
                
                logger.info(
                    "Webhook endpoint updated",
                    **add_webhook_context(endpoint.id, endpoint.url, "", "")
                )
            
            return self._endpoint_to_dict(endpoint)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Webhook endpoint update failed: {e}")
            raise
    
    async def delete_endpoint(
        self,
        endpoint_id: str,
        user_id: str,
    ) -> bool:
        """Delete webhook endpoint."""
        logger = get_logger(__name__).bind(**add_user_context(user_id, ""))
        
        try:
            # Get existing endpoint
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
            result = await self.db.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                return False
            
            # Soft delete by setting status to inactive
            endpoint.status = WebhookStatus.INACTIVE
            endpoint.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Log activity
            await self._log_activity(
                endpoint_id=endpoint.id,
                user_id=user_id,
                action="deleted",
                details={"name": endpoint.name}
            )
            
            # Clear cache
            await self._invalidate_endpoint_cache(endpoint_id, user_id)
            await self._invalidate_user_cache(user_id)
            
            logger.info(
                "Webhook endpoint deleted",
                **add_webhook_context(endpoint.id, endpoint.url, "", "")
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Webhook endpoint deletion failed: {e}")
            raise
    
    async def get_endpoints_for_event(
        self,
        event_type: EventType,
        filters: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Get webhook endpoints that should receive a specific event."""
        try:
            # Query active endpoints that subscribe to this event type
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.status == WebhookStatus.ACTIVE,
                WebhookEndpoint.event_types.contains([event_type.value])
            )
            
            result = await self.db.execute(stmt)
            endpoints = result.scalars().all()
            
            # Apply additional filtering if needed
            filtered_endpoints = []
            for endpoint in endpoints:
                if self._matches_event_filters(endpoint.event_filters, filters or {}):
                    filtered_endpoints.append(self._endpoint_to_dict(endpoint))
            
            return filtered_endpoints
            
        except Exception as e:
            logger.error(f"Event endpoint lookup failed: {e}")
            raise
    
    async def update_delivery_stats(
        self,
        endpoint_id: str,
        success: bool,
        response_time: float = None,
    ) -> None:
        """Update delivery statistics for an endpoint."""
        try:
            # Update endpoint statistics
            if success:
                stmt = update(WebhookEndpoint).where(
                    WebhookEndpoint.id == endpoint_id
                ).values(
                    total_deliveries=WebhookEndpoint.total_deliveries + 1,
                    successful_deliveries=WebhookEndpoint.successful_deliveries + 1,
                    last_delivery_at=datetime.utcnow(),
                    last_success_at=datetime.utcnow(),
                )
            else:
                stmt = update(WebhookEndpoint).where(
                    WebhookEndpoint.id == endpoint_id
                ).values(
                    total_deliveries=WebhookEndpoint.total_deliveries + 1,
                    failed_deliveries=WebhookEndpoint.failed_deliveries + 1,
                    last_delivery_at=datetime.utcnow(),
                    last_failure_at=datetime.utcnow(),
                )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Clear cache
            cache_key_pattern = f"webhook_endpoint:{endpoint_id}:*"
            # Note: In a real implementation, you'd need to iterate and delete matching keys
            
        except Exception as e:
            logger.error(f"Delivery stats update failed: {e}")
    
    async def get_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get webhook analytics for a user."""
        try:
            # Get endpoint counts
            endpoint_stmt = select(func.count(WebhookEndpoint.id)).where(
                WebhookEndpoint.user_id == user_id
            )
            total_endpoints = (await self.db.execute(endpoint_stmt)).scalar()
            
            active_endpoint_stmt = select(func.count(WebhookEndpoint.id)).where(
                WebhookEndpoint.user_id == user_id,
                WebhookEndpoint.status == WebhookStatus.ACTIVE
            )
            active_endpoints = (await self.db.execute(active_endpoint_stmt)).scalar()
            
            # Get event and delivery counts
            event_stmt = select(func.count(WebhookEvent.id)).join(
                WebhookEndpoint
            ).where(WebhookEndpoint.user_id == user_id)
            total_events = (await self.db.execute(event_stmt)).scalar()
            
            delivery_stmt = select(func.count(WebhookDelivery.id)).join(
                WebhookEndpoint
            ).where(WebhookEndpoint.user_id == user_id)
            total_deliveries = (await self.db.execute(delivery_stmt)).scalar()
            
            success_delivery_stmt = select(func.count(WebhookDelivery.id)).join(
                WebhookEndpoint
            ).where(
                WebhookEndpoint.user_id == user_id,
                WebhookDelivery.status == DeliveryStatus.DELIVERED
            )
            successful_deliveries = (await self.db.execute(success_delivery_stmt)).scalar()
            
            failed_deliveries = total_deliveries - successful_deliveries
            success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
            
            # Get average response time
            avg_response_stmt = select(func.avg(WebhookDelivery.response_time)).join(
                WebhookEndpoint
            ).where(
                WebhookEndpoint.user_id == user_id,
                WebhookDelivery.status == DeliveryStatus.DELIVERED
            )
            avg_response_time = (await self.db.execute(avg_response_stmt)).scalar() or 0
            
            return {
                "total_endpoints": total_endpoints,
                "active_endpoints": active_endpoints,
                "total_events": total_events,
                "total_deliveries": total_deliveries,
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": failed_deliveries,
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "events_by_type": {},  # Would implement detailed breakdown
                "deliveries_by_status": {},  # Would implement detailed breakdown
                "recent_activity": [],  # Would implement recent activity
            }
            
        except Exception as e:
            logger.error(f"Analytics retrieval failed: {e}")
            raise
    
    async def check_database_health(self) -> bool:
        """Check database health."""
        try:
            await self.db.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    async def check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            await self.cache.client.ping()
            return True
        except Exception:
            return False
    
    def _endpoint_to_dict(self, endpoint: WebhookEndpoint) -> Dict[str, Any]:
        """Convert endpoint model to dictionary."""
        return {
            "id": endpoint.id,
            "user_id": endpoint.user_id,
            "name": endpoint.name,
            "description": endpoint.description,
            "url": endpoint.url,
            "method": endpoint.method.value,
            "headers": endpoint.headers,
            "status": endpoint.status.value,
            "event_types": endpoint.event_types,
            "event_filters": endpoint.event_filters,
            "timeout": endpoint.timeout,
            "retry_attempts": endpoint.retry_attempts,
            "retry_delay": endpoint.retry_delay,
            "total_deliveries": endpoint.total_deliveries,
            "successful_deliveries": endpoint.successful_deliveries,
            "failed_deliveries": endpoint.failed_deliveries,
            "last_delivery_at": endpoint.last_delivery_at,
            "last_success_at": endpoint.last_success_at,
            "last_failure_at": endpoint.last_failure_at,
            "created_at": endpoint.created_at,
            "updated_at": endpoint.updated_at,
        }
    
    def _matches_event_filters(
        self,
        endpoint_filters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if event data matches endpoint filters."""
        if not endpoint_filters:
            return True
        
        for filter_key, filter_value in endpoint_filters.items():
            if filter_key not in event_data:
                return False
            
            if isinstance(filter_value, list):
                if event_data[filter_key] not in filter_value:
                    return False
            else:
                if event_data[filter_key] != filter_value:
                    return False
        
        return True
    
    async def _validate_endpoint_creation(
        self,
        data: WebhookEndpointCreate,
        user_id: str
    ) -> None:
        """Validate webhook endpoint creation."""
        # Validate URL
        await validate_webhook_url(str(data.url))
        
        # Validate headers
        validate_webhook_headers(data.headers)
        
        # Check user quota
        from .quota_manager import QuotaManager
        quota_manager = QuotaManager(self.db)
        await quota_manager.check_endpoint_quota(user_id)
    
    async def _log_activity(
        self,
        endpoint_id: str,
        user_id: str,
        action: str,
        details: Dict[str, Any],
    ) -> None:
        """Log webhook activity."""
        try:
            log_entry = WebhookLog(
                endpoint_id=endpoint_id,
                user_id=user_id,
                action=action,
                details=details,
            )
            
            self.db.add(log_entry)
            # Note: Don't commit here, let the caller handle it
            
        except Exception as e:
            logger.error(f"Activity logging failed: {e}")
    
    async def _invalidate_endpoint_cache(self, endpoint_id: str, user_id: str) -> None:
        """Invalidate endpoint cache."""
        cache_key = f"webhook_endpoint:{endpoint_id}:{user_id}"
        await self.cache.delete(cache_key)
    
    async def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate user-related cache."""
        # Would implement pattern-based cache invalidation
        pass