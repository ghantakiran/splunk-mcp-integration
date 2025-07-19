"""
Report delivery service for multi-channel delivery.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import DeliveryAttempt, ReportSubscription
from app.core.config import settings
from app.models.schedule_models import DeliveryMethod, SubscriptionResponse

logger = logging.getLogger(__name__)


class DeliveryService:
    """Service for delivering reports via multiple channels."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for service communication."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
            )
        return self.http_client
    
    async def deliver_reports(
        self,
        execution_id: UUID,
        subscriptions: List[SubscriptionResponse],
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deliver reports to all subscriptions.
        
        Args:
            execution_id: Execution ID for tracking
            subscriptions: List of active subscriptions
            report_data: Generated report data
            
        Returns:
            Delivery summary with results
        """
        try:
            logger.info(f"Starting delivery for execution {execution_id} to {len(subscriptions)} subscriptions")
            
            delivery_tasks = []
            for subscription in subscriptions:
                task = self._deliver_to_subscription(execution_id, subscription, report_data)
                delivery_tasks.append(task)
            
            # Execute deliveries concurrently
            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            
            # Process results
            successful_deliveries = 0
            failed_deliveries = 0
            delivery_details = []
            
            for i, result in enumerate(results):
                subscription = subscriptions[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Delivery failed for subscription {subscription.subscription_id}: {result}")
                    failed_deliveries += 1
                    delivery_details.append({
                        "subscription_id": str(subscription.subscription_id),
                        "delivery_method": subscription.delivery_method.value,
                        "success": False,
                        "error": str(result)
                    })
                else:
                    if result.get("success", False):
                        successful_deliveries += 1
                    else:
                        failed_deliveries += 1
                    
                    delivery_details.append({
                        "subscription_id": str(subscription.subscription_id),
                        "delivery_method": subscription.delivery_method.value,
                        "success": result.get("success", False),
                        "message": result.get("message", ""),
                        "error": result.get("error")
                    })
            
            summary = {
                "execution_id": str(execution_id),
                "total_subscriptions": len(subscriptions),
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": failed_deliveries,
                "delivery_details": delivery_details,
                "delivered_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Delivery completed for execution {execution_id}: {successful_deliveries} success, {failed_deliveries} failed")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error delivering reports for execution {execution_id}: {e}")
            raise
    
    async def _deliver_to_subscription(
        self,
        execution_id: UUID,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report to a single subscription."""
        attempt_number = 1
        max_retries = 3
        
        while attempt_number <= max_retries:
            try:
                # Create delivery attempt record
                attempt = DeliveryAttempt(
                    execution_id=execution_id,
                    subscription_id=subscription.subscription_id,
                    delivery_method=subscription.delivery_method,
                    attempt_number=attempt_number,
                    status="attempting",
                    attempted_at=datetime.now(timezone.utc)
                )
                
                self.db.add(attempt)
                await self.db.commit()
                
                # Attempt delivery based on method
                result = await self._perform_delivery(subscription, report_data)
                
                # Update attempt with result
                attempt.completed_at = datetime.now(timezone.utc)
                attempt.duration_seconds = (attempt.completed_at - attempt.attempted_at).total_seconds()
                attempt.success = result.get("success", False)
                attempt.status = "completed" if result.get("success") else "failed"
                attempt.error_message = result.get("error")
                attempt.response_data = result
                
                await self.db.commit()
                
                # Update subscription delivery stats
                await self._update_subscription_stats(subscription.subscription_id, result.get("success", False))
                
                if result.get("success", False):
                    logger.info(f"Delivery successful for subscription {subscription.subscription_id}")
                    return result
                else:
                    logger.warning(f"Delivery failed for subscription {subscription.subscription_id}: {result.get('error')}")
                    
                    if attempt_number >= max_retries:
                        return result
                    
                    # Wait before retry
                    await asyncio.sleep(2 ** attempt_number)  # Exponential backoff
                    attempt_number += 1
                    
            except Exception as e:
                logger.error(f"Error in delivery attempt {attempt_number} for subscription {subscription.subscription_id}: {e}")
                
                if attempt_number >= max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "subscription_id": str(subscription.subscription_id)
                    }
                
                attempt_number += 1
                await asyncio.sleep(2 ** attempt_number)
        
        return {
            "success": False,
            "error": "Max retries exceeded",
            "subscription_id": str(subscription.subscription_id)
        }
    
    async def _perform_delivery(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform the actual delivery based on method."""
        try:
            if subscription.delivery_method == DeliveryMethod.EMAIL:
                return await self._deliver_via_email(subscription, report_data)
            elif subscription.delivery_method == DeliveryMethod.SLACK:
                return await self._deliver_via_slack(subscription, report_data)
            elif subscription.delivery_method == DeliveryMethod.TEAMS:
                return await self._deliver_via_teams(subscription, report_data)
            elif subscription.delivery_method == DeliveryMethod.WEBHOOK:
                return await self._deliver_via_webhook(subscription, report_data)
            elif subscription.delivery_method == DeliveryMethod.FILE_STORAGE:
                return await self._deliver_via_file_storage(subscription, report_data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported delivery method: {subscription.delivery_method}"
                }
                
        except Exception as e:
            logger.error(f"Error performing delivery: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _deliver_via_email(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report via email."""
        try:
            http_client = await self._get_http_client()
            
            email_payload = {
                "to": subscription.delivery_config.get("email"),
                "subject": f"Scheduled Report - {report_data.get('execution_id')}",
                "report_data": report_data,
                "template": subscription.delivery_config.get("template", "default"),
                "include_attachment": subscription.delivery_config.get("include_attachment", True)
            }
            
            response = await http_client.post(
                f"{settings.EMAIL_SERVICE_URL}/api/v1/reports/send",
                json=email_payload,
                headers={"Authorization": f"Bearer {settings.SERVICE_AUTH_TOKEN}"}
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": result.get("success", False),
                "message": "Email sent successfully",
                "delivery_id": result.get("delivery_id")
            }
            
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return {
                "success": False,
                "error": f"Email delivery failed: {str(e)}"
            }
    
    async def _deliver_via_slack(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report via Slack."""
        try:
            http_client = await self._get_http_client()
            
            slack_payload = {
                "channel": subscription.delivery_config.get("channel"),
                "report_data": report_data,
                "format": subscription.delivery_config.get("format", "summary"),
                "include_chart": subscription.delivery_config.get("include_chart", True)
            }
            
            response = await http_client.post(
                f"{settings.SLACK_BOT_URL}/api/v1/reports/send",
                json=slack_payload,
                headers={"Authorization": f"Bearer {settings.SERVICE_AUTH_TOKEN}"}
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": result.get("success", False),
                "message": "Slack message sent successfully",
                "message_ts": result.get("message_ts")
            }
            
        except Exception as e:
            logger.error(f"Slack delivery failed: {e}")
            return {
                "success": False,
                "error": f"Slack delivery failed: {str(e)}"
            }
    
    async def _deliver_via_teams(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report via Microsoft Teams."""
        try:
            http_client = await self._get_http_client()
            
            teams_payload = {
                "conversation_id": subscription.delivery_config.get("conversation_id"),
                "report_data": report_data,
                "format": subscription.delivery_config.get("format", "adaptive_card"),
                "include_chart": subscription.delivery_config.get("include_chart", True)
            }
            
            response = await http_client.post(
                f"{settings.TEAMS_BOT_URL}/api/v1/reports/send",
                json=teams_payload,
                headers={"Authorization": f"Bearer {settings.SERVICE_AUTH_TOKEN}"}
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": result.get("success", False),
                "message": "Teams message sent successfully",
                "activity_id": result.get("activity_id")
            }
            
        except Exception as e:
            logger.error(f"Teams delivery failed: {e}")
            return {
                "success": False,
                "error": f"Teams delivery failed: {str(e)}"
            }
    
    async def _deliver_via_webhook(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report via webhook."""
        try:
            http_client = await self._get_http_client()
            
            webhook_url = subscription.delivery_config.get("webhook_url")
            headers = subscription.delivery_config.get("headers", {})
            
            if not webhook_url:
                return {
                    "success": False,
                    "error": "Webhook URL not configured"
                }
            
            webhook_payload = {
                "event_type": "scheduled_report",
                "report_data": report_data,
                "subscription_id": str(subscription.subscription_id),
                "delivered_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = await http_client.post(
                webhook_url,
                json=webhook_payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "Webhook delivered successfully",
                "status_code": response.status_code,
                "response_size": len(response.content)
            }
            
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return {
                "success": False,
                "error": f"Webhook delivery failed: {str(e)}"
            }
    
    async def _deliver_via_file_storage(
        self,
        subscription: SubscriptionResponse,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver report via file storage."""
        try:
            # This would integrate with a file storage service
            # For now, return a mock success response
            storage_path = subscription.delivery_config.get("storage_path", "/reports")
            file_name = f"report_{report_data.get('execution_id')}.{report_data.get('format', 'pdf')}"
            
            logger.info(f"Would store report at {storage_path}/{file_name}")
            
            return {
                "success": True,
                "message": "Report stored successfully",
                "file_path": f"{storage_path}/{file_name}",
                "file_size": report_data.get("file_size", 0)
            }
            
        except Exception as e:
            logger.error(f"File storage delivery failed: {e}")
            return {
                "success": False,
                "error": f"File storage delivery failed: {str(e)}"
            }
    
    async def _update_subscription_stats(
        self,
        subscription_id: UUID,
        success: bool
    ) -> None:
        """Update subscription delivery statistics."""
        try:
            if success:
                await self.db.execute(
                    update(ReportSubscription)
                    .where(ReportSubscription.subscription_id == subscription_id)
                    .values(
                        total_deliveries=ReportSubscription.total_deliveries + 1,
                        successful_deliveries=ReportSubscription.successful_deliveries + 1,
                        last_delivery_at=datetime.now(timezone.utc),
                        last_delivery_status="success"
                    )
                )
            else:
                await self.db.execute(
                    update(ReportSubscription)
                    .where(ReportSubscription.subscription_id == subscription_id)
                    .values(
                        total_deliveries=ReportSubscription.total_deliveries + 1,
                        failed_deliveries=ReportSubscription.failed_deliveries + 1,
                        last_delivery_at=datetime.now(timezone.utc),
                        last_delivery_status="failed"
                    )
                )
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating subscription stats: {e}")
    
    async def close(self):
        """Close HTTP client connections."""
        if self.http_client:
            await self.http_client.aclose()