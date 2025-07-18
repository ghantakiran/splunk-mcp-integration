"""
Webhook delivery service for the Webhook Service.
"""

import asyncio
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis

from ..core.config import settings, get_webhook_delivery_config, get_http_client_config
from ..core.logging import get_logger, add_delivery_context, add_webhook_context
from ..core.database import get_db_session
from ..core.redis_client import RedisQueue
from ..models.webhook_models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookDelivery,
    DeliveryStatus,
    WebhookStatus,
)

logger = get_logger(__name__)


class DeliveryService:
    """Handles webhook delivery and retry logic."""
    
    def __init__(self):
        self.config = get_webhook_delivery_config()
        self.http_config = get_http_client_config()
        self.queue = None
        self.http_client = None
        self._running = False
        self._delivery_tasks = set()
    
    async def start_processor(self) -> None:
        """Start the delivery processor."""
        if self._running:
            return
        
        self._running = True
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=self.http_config["timeout"],
            limits=httpx.Limits(**self.http_config["limits"]),
            headers=self.http_config["headers"],
        )
        
        # Initialize queue
        from ..core.redis_client import get_redis_client
        redis_client = await get_redis_client()
        self.queue = RedisQueue(redis_client, "webhook_delivery_queue")
        
        logger.info("Webhook delivery processor started")
        
        # Start processing loop
        asyncio.create_task(self._process_deliveries())
    
    async def stop_processor(self) -> None:
        """Stop the delivery processor."""
        self._running = False
        
        # Cancel running delivery tasks
        for task in self._delivery_tasks:
            task.cancel()
        
        await asyncio.gather(*self._delivery_tasks, return_exceptions=True)
        self._delivery_tasks.clear()
        
        # Close HTTP client
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        logger.info("Webhook delivery processor stopped")
    
    async def schedule_delivery(
        self,
        endpoint_id: str,
        event_id: str,
        delay: int = 0
    ) -> str:
        """Schedule a webhook delivery."""
        try:
            async with get_db_session() as db:
                # Create delivery record
                delivery = WebhookDelivery(
                    endpoint_id=endpoint_id,
                    event_id=event_id,
                    status=DeliveryStatus.PENDING,
                    scheduled_at=datetime.utcnow() + timedelta(seconds=delay),
                )
                
                db.add(delivery)
                await db.commit()
                await db.refresh(delivery)
                
                # Add to queue
                delivery_data = {
                    "delivery_id": delivery.id,
                    "endpoint_id": endpoint_id,
                    "event_id": event_id,
                    "scheduled_at": delivery.scheduled_at.isoformat(),
                }
                
                await self.queue.push(json.dumps(delivery_data))
                
                logger.info(
                    "Webhook delivery scheduled",
                    **add_delivery_context(delivery.id, endpoint_id, 1, "pending")
                )
                
                return delivery.id
                
        except Exception as e:
            logger.error(f"Delivery scheduling failed: {e}")
            raise
    
    async def deliver_webhook(
        self,
        delivery_id: str,
        attempt_number: int = 1
    ) -> bool:
        """Deliver a webhook."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with get_db_session() as db:
                # Get delivery with related data
                stmt = select(WebhookDelivery).where(
                    WebhookDelivery.id == delivery_id
                ).options(
                    selectinload(WebhookDelivery.endpoint),
                    selectinload(WebhookDelivery.event)
                )
                result = await db.execute(stmt)
                delivery = result.scalar_one_or_none()
                
                if not delivery:
                    logger.error(f"Delivery not found: {delivery_id}")
                    return False
                
                endpoint = delivery.endpoint
                event = delivery.event
                
                if endpoint.status != WebhookStatus.ACTIVE:
                    logger.warning(
                        "Skipping delivery to inactive endpoint",
                        **add_delivery_context(delivery_id, endpoint.id, attempt_number, "skipped")
                    )
                    return False
                
                # Update delivery attempt
                delivery.status = DeliveryStatus.PENDING
                delivery.attempt_number = attempt_number
                delivery.attempted_at = datetime.utcnow()
                await db.commit()
                
                # Prepare webhook payload
                payload = self._prepare_payload(event)
                headers = self._prepare_headers(endpoint, payload)
                
                logger.info(
                    "Attempting webhook delivery",
                    **add_delivery_context(delivery_id, endpoint.id, attempt_number, "attempting")
                )
                
                # Make HTTP request
                response = await self._make_request(
                    endpoint.url,
                    endpoint.method.value,
                    payload,
                    headers,
                    endpoint.timeout
                )
                
                # Calculate response time
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                # Update delivery record
                success = 200 <= response.status_code < 300
                
                delivery.status = DeliveryStatus.DELIVERED if success else DeliveryStatus.FAILED
                delivery.http_status = response.status_code
                delivery.response_body = response.text[:1000]  # Limit response body size
                delivery.response_headers = dict(response.headers)
                delivery.response_time = response_time
                delivery.completed_at = datetime.utcnow()
                
                if not success:
                    delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                
                await db.commit()
                
                # Update endpoint statistics
                from .webhook_manager import WebhookManager
                webhook_manager = WebhookManager(db, await get_redis_client())
                await webhook_manager.update_delivery_stats(
                    endpoint.id,
                    success,
                    response_time
                )
                
                if success:
                    logger.info(
                        "Webhook delivery successful",
                        **add_delivery_context(delivery_id, endpoint.id, attempt_number, "delivered", response_time)
                    )
                else:
                    logger.warning(
                        "Webhook delivery failed",
                        **add_delivery_context(delivery_id, endpoint.id, attempt_number, "failed", response_time),
                        http_status=response.status_code,
                        error=delivery.error_message
                    )
                
                # Schedule retry if needed
                if not success and attempt_number < endpoint.retry_attempts:
                    await self._schedule_retry(delivery_id, attempt_number + 1)
                
                return success
                
        except Exception as e:
            # Update delivery record with error
            try:
                async with get_db_session() as db:
                    stmt = update(WebhookDelivery).where(
                        WebhookDelivery.id == delivery_id
                    ).values(
                        status=DeliveryStatus.FAILED,
                        error_message=str(e),
                        completed_at=datetime.utcnow(),
                        response_time=(asyncio.get_event_loop().time() - start_time) * 1000
                    )
                    await db.execute(stmt)
                    await db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update delivery record: {update_error}")
            
            logger.error(
                f"Webhook delivery error: {e}",
                **add_delivery_context(delivery_id, "", attempt_number, "error")
            )
            return False
    
    async def retry_delivery(self, delivery_id: str) -> bool:
        """Retry a failed delivery."""
        try:
            async with get_db_session() as db:
                stmt = select(WebhookDelivery).where(
                    WebhookDelivery.id == delivery_id
                )
                result = await db.execute(stmt)
                delivery = result.scalar_one_or_none()
                
                if not delivery:
                    return False
                
                if delivery.status != DeliveryStatus.FAILED:
                    return False
                
                # Reset status and schedule new attempt
                next_attempt = delivery.attempt_number + 1
                delivery.status = DeliveryStatus.RETRYING
                delivery.retry_count += 1
                await db.commit()
                
                # Schedule delivery
                await self.schedule_delivery(
                    delivery.endpoint_id,
                    delivery.event_id,
                    delay=self._calculate_retry_delay(next_attempt)
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Delivery retry failed: {e}")
            return False
    
    async def list_deliveries(
        self,
        user_id: str,
        endpoint_id: str = None,
        event_id: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List webhook deliveries."""
        try:
            async with get_db_session() as db:
                # Build query
                stmt = select(WebhookDelivery).join(WebhookEndpoint).where(
                    WebhookEndpoint.user_id == user_id
                )
                
                if endpoint_id:
                    stmt = stmt.where(WebhookDelivery.endpoint_id == endpoint_id)
                
                if event_id:
                    stmt = stmt.where(WebhookDelivery.event_id == event_id)
                
                if status:
                    stmt = stmt.where(WebhookDelivery.status == DeliveryStatus(status))
                
                stmt = stmt.offset(offset).limit(limit).order_by(
                    WebhookDelivery.created_at.desc()
                )
                
                result = await db.execute(stmt)
                deliveries = result.scalars().all()
                
                return [self._delivery_to_dict(delivery) for delivery in deliveries]
                
        except Exception as e:
            logger.error(f"Delivery listing failed: {e}")
            raise
    
    async def get_delivery(
        self,
        delivery_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get delivery details."""
        try:
            async with get_db_session() as db:
                stmt = select(WebhookDelivery).join(WebhookEndpoint).where(
                    WebhookDelivery.id == delivery_id,
                    WebhookEndpoint.user_id == user_id
                )
                result = await db.execute(stmt)
                delivery = result.scalar_one_or_none()
                
                if delivery:
                    return self._delivery_to_dict(delivery)
                return None
                
        except Exception as e:
            logger.error(f"Delivery retrieval failed: {e}")
            raise
    
    async def _process_deliveries(self) -> None:
        """Main delivery processing loop."""
        while self._running:
            try:
                # Pop delivery from queue
                delivery_data = await self.queue.pop(timeout=10)
                
                if delivery_data:
                    data = json.loads(delivery_data)
                    
                    # Check if delivery should be processed now
                    scheduled_at = datetime.fromisoformat(data["scheduled_at"])
                    if scheduled_at <= datetime.utcnow():
                        # Create delivery task
                        task = asyncio.create_task(
                            self.deliver_webhook(data["delivery_id"])
                        )
                        self._delivery_tasks.add(task)
                        
                        # Clean up completed tasks
                        task.add_done_callback(self._delivery_tasks.discard)
                    else:
                        # Put back in queue for later
                        await self.queue.push(delivery_data)
                        await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delivery processing error: {e}")
                await asyncio.sleep(5)
    
    def _prepare_payload(self, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare webhook payload."""
        return {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "source": event.source,
            "timestamp": event.created_at.isoformat(),
            "data": event.payload,
            "metadata": event.metadata,
        }
    
    def _prepare_headers(
        self,
        endpoint: WebhookEndpoint,
        payload: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare webhook headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"Splunk-MCP-Webhook/{settings.version}",
            **endpoint.headers
        }
        
        # Add signature if secret is configured
        if endpoint.secret:
            payload_str = json.dumps(payload, separators=(',', ':'))
            signature = hmac.new(
                endpoint.secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        return headers
    
    async def _make_request(
        self,
        url: str,
        method: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int
    ) -> httpx.Response:
        """Make HTTP request to webhook endpoint."""
        response = await self.http_client.request(
            method=method,
            url=url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        return response
    
    async def _schedule_retry(self, delivery_id: str, attempt_number: int) -> None:
        """Schedule delivery retry."""
        delay = self._calculate_retry_delay(attempt_number)
        
        # Update delivery record
        async with get_db_session() as db:
            next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            
            stmt = update(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id
            ).values(
                status=DeliveryStatus.RETRYING,
                next_retry_at=next_retry_at
            )
            await db.execute(stmt)
            await db.commit()
        
        # Add to queue
        delivery_data = {
            "delivery_id": delivery_id,
            "scheduled_at": next_retry_at.isoformat(),
        }
        await self.queue.push(json.dumps(delivery_data))
        
        logger.info(
            f"Webhook delivery retry scheduled in {delay} seconds",
            **add_delivery_context(delivery_id, "", attempt_number, "retry_scheduled")
        )
    
    def _calculate_retry_delay(self, attempt_number: int) -> int:
        """Calculate retry delay using exponential backoff."""
        delay = self.config["retry_delay"] * (
            self.config["retry_exponential_base"] ** (attempt_number - 1)
        )
        return min(delay, self.config["retry_max_delay"])
    
    def _delivery_to_dict(self, delivery: WebhookDelivery) -> Dict[str, Any]:
        """Convert delivery model to dictionary."""
        return {
            "id": delivery.id,
            "endpoint_id": delivery.endpoint_id,
            "event_id": delivery.event_id,
            "status": delivery.status.value,
            "attempt_number": delivery.attempt_number,
            "max_attempts": delivery.max_attempts,
            "http_status": delivery.http_status,
            "response_body": delivery.response_body,
            "response_headers": delivery.response_headers,
            "error_message": delivery.error_message,
            "scheduled_at": delivery.scheduled_at,
            "attempted_at": delivery.attempted_at,
            "completed_at": delivery.completed_at,
            "response_time": delivery.response_time,
            "next_retry_at": delivery.next_retry_at,
            "retry_count": delivery.retry_count,
            "created_at": delivery.created_at,
            "updated_at": delivery.updated_at,
        }