"""
Subscription management service for report scheduling.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import ReportSubscription, DeliveryAttempt
from app.models.schedule_models import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    DeliveryMethod
)

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing report subscriptions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_subscription(
        self,
        request: CreateSubscriptionRequest,
        user_id: str
    ) -> SubscriptionResponse:
        """Create a new subscription."""
        try:
            # Check if subscription already exists
            existing = await self.db.execute(
                select(ReportSubscription).where(
                    and_(
                        ReportSubscription.user_id == user_id,
                        ReportSubscription.schedule_id == request.schedule_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError("Subscription already exists for this schedule and user")
            
            # Create new subscription
            subscription = ReportSubscription(
                user_id=user_id,
                schedule_id=request.schedule_id,
                delivery_method=request.delivery_method,
                delivery_config=request.delivery_config.model_dump() if request.delivery_config else {},
                active=request.active if request.active is not None else True,
                preferences=request.preferences.model_dump() if request.preferences else {}
            )
            
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            
            logger.info(f"Created subscription {subscription.subscription_id} for user {user_id}")
            
            return SubscriptionResponse(
                subscription_id=subscription.subscription_id,
                user_id=subscription.user_id,
                schedule_id=subscription.schedule_id,
                delivery_method=subscription.delivery_method,
                delivery_config=subscription.delivery_config,
                active=subscription.active,
                preferences=subscription.preferences,
                total_deliveries=subscription.total_deliveries,
                successful_deliveries=subscription.successful_deliveries,
                failed_deliveries=subscription.failed_deliveries,
                last_delivery_at=subscription.last_delivery_at,
                last_delivery_status=subscription.last_delivery_status,
                created_at=subscription.created_at,
                updated_at=subscription.updated_at
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating subscription: {e}")
            raise
    
    async def list_subscriptions(
        self,
        user_id: str,
        schedule_id: Optional[UUID] = None,
        delivery_method: Optional[DeliveryMethod] = None,
        active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> SubscriptionListResponse:
        """List subscriptions with filtering."""
        try:
            # Build query conditions
            conditions = [ReportSubscription.user_id == user_id]
            
            if schedule_id:
                conditions.append(ReportSubscription.schedule_id == schedule_id)
            if delivery_method:
                conditions.append(ReportSubscription.delivery_method == delivery_method)
            if active is not None:
                conditions.append(ReportSubscription.active == active)
            
            # Get subscriptions with pagination
            query = (
                select(ReportSubscription)
                .where(and_(*conditions))
                .order_by(ReportSubscription.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            
            result = await self.db.execute(query)
            subscriptions = result.scalars().all()
            
            # Get total count
            count_query = select(ReportSubscription).where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total = len(count_result.scalars().all())
            
            # Convert to response models
            items = [
                SubscriptionResponse(
                    subscription_id=sub.subscription_id,
                    user_id=sub.user_id,
                    schedule_id=sub.schedule_id,
                    delivery_method=sub.delivery_method,
                    delivery_config=sub.delivery_config,
                    active=sub.active,
                    preferences=sub.preferences,
                    total_deliveries=sub.total_deliveries,
                    successful_deliveries=sub.successful_deliveries,
                    failed_deliveries=sub.failed_deliveries,
                    last_delivery_at=sub.last_delivery_at,
                    last_delivery_status=sub.last_delivery_status,
                    created_at=sub.created_at,
                    updated_at=sub.updated_at
                )
                for sub in subscriptions
            ]
            
            return SubscriptionListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            raise
    
    async def get_subscription(
        self,
        subscription_id: UUID,
        user_id: str
    ) -> Optional[SubscriptionResponse]:
        """Get subscription by ID."""
        try:
            result = await self.db.execute(
                select(ReportSubscription).where(
                    and_(
                        ReportSubscription.subscription_id == subscription_id,
                        ReportSubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return None
            
            return SubscriptionResponse(
                subscription_id=subscription.subscription_id,
                user_id=subscription.user_id,
                schedule_id=subscription.schedule_id,
                delivery_method=subscription.delivery_method,
                delivery_config=subscription.delivery_config,
                active=subscription.active,
                preferences=subscription.preferences,
                total_deliveries=subscription.total_deliveries,
                successful_deliveries=subscription.successful_deliveries,
                failed_deliveries=subscription.failed_deliveries,
                last_delivery_at=subscription.last_delivery_at,
                last_delivery_status=subscription.last_delivery_status,
                created_at=subscription.created_at,
                updated_at=subscription.updated_at
            )
            
        except Exception as e:
            logger.error(f"Error getting subscription {subscription_id}: {e}")
            raise
    
    async def update_subscription(
        self,
        subscription_id: UUID,
        request: UpdateSubscriptionRequest,
        user_id: str
    ) -> Optional[SubscriptionResponse]:
        """Update subscription."""
        try:
            # Get existing subscription
            result = await self.db.execute(
                select(ReportSubscription).where(
                    and_(
                        ReportSubscription.subscription_id == subscription_id,
                        ReportSubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return None
            
            # Update fields
            update_data = {}
            if request.delivery_config is not None:
                update_data["delivery_config"] = request.delivery_config.model_dump()
            if request.active is not None:
                update_data["active"] = request.active
            if request.preferences is not None:
                update_data["preferences"] = request.preferences.model_dump()
            
            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                
                await self.db.execute(
                    update(ReportSubscription)
                    .where(ReportSubscription.subscription_id == subscription_id)
                    .values(**update_data)
                )
                
                await self.db.commit()
                
                # Refresh and return updated subscription
                await self.db.refresh(subscription)
            
            return SubscriptionResponse(
                subscription_id=subscription.subscription_id,
                user_id=subscription.user_id,
                schedule_id=subscription.schedule_id,
                delivery_method=subscription.delivery_method,
                delivery_config=subscription.delivery_config,
                active=subscription.active,
                preferences=subscription.preferences,
                total_deliveries=subscription.total_deliveries,
                successful_deliveries=subscription.successful_deliveries,
                failed_deliveries=subscription.failed_deliveries,
                last_delivery_at=subscription.last_delivery_at,
                last_delivery_status=subscription.last_delivery_status,
                created_at=subscription.created_at,
                updated_at=subscription.updated_at
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            raise
    
    async def delete_subscription(
        self,
        subscription_id: UUID,
        user_id: str
    ) -> bool:
        """Delete subscription."""
        try:
            # Check if subscription exists
            result = await self.db.execute(
                select(ReportSubscription).where(
                    and_(
                        ReportSubscription.subscription_id == subscription_id,
                        ReportSubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False
            
            # Delete subscription (cascade will handle delivery attempts)
            await self.db.execute(
                delete(ReportSubscription).where(
                    ReportSubscription.subscription_id == subscription_id
                )
            )
            
            await self.db.commit()
            logger.info(f"Deleted subscription {subscription_id}")
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            raise
    
    async def test_subscription(
        self,
        subscription_id: UUID,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Test subscription delivery."""
        try:
            # Get subscription
            subscription = await self.get_subscription(subscription_id, user_id)
            if not subscription:
                return None
            
            # Create test delivery attempt
            test_attempt = DeliveryAttempt(
                execution_id=subscription_id,  # Use subscription_id as placeholder
                subscription_id=subscription_id,
                delivery_method=subscription.delivery_method,
                attempt_number=1,
                status="testing",
                attempted_at=datetime.now(timezone.utc)
            )
            
            self.db.add(test_attempt)
            await self.db.commit()
            
            # Return test result
            return {
                "success": True,
                "subscription_id": subscription_id,
                "delivery_method": subscription.delivery_method.value,
                "test_time": datetime.now(timezone.utc).isoformat(),
                "message": f"Test delivery initiated for {subscription.delivery_method.value}"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error testing subscription {subscription_id}: {e}")
            raise
    
    async def activate_subscription(
        self,
        subscription_id: UUID,
        user_id: str
    ) -> Optional[SubscriptionResponse]:
        """Activate subscription."""
        request = UpdateSubscriptionRequest(active=True)
        return await self.update_subscription(subscription_id, request, user_id)
    
    async def deactivate_subscription(
        self,
        subscription_id: UUID,
        user_id: str
    ) -> Optional[SubscriptionResponse]:
        """Deactivate subscription."""
        request = UpdateSubscriptionRequest(active=False)
        return await self.update_subscription(subscription_id, request, user_id)
    
    async def get_subscriptions_for_schedule(
        self,
        schedule_id: UUID,
        active_only: bool = True
    ) -> List[SubscriptionResponse]:
        """Get all subscriptions for a schedule."""
        try:
            conditions = [ReportSubscription.schedule_id == schedule_id]
            if active_only:
                conditions.append(ReportSubscription.active == True)
            
            result = await self.db.execute(
                select(ReportSubscription).where(and_(*conditions))
            )
            subscriptions = result.scalars().all()
            
            return [
                SubscriptionResponse(
                    subscription_id=sub.subscription_id,
                    user_id=sub.user_id,
                    schedule_id=sub.schedule_id,
                    delivery_method=sub.delivery_method,
                    delivery_config=sub.delivery_config,
                    active=sub.active,
                    preferences=sub.preferences,
                    total_deliveries=sub.total_deliveries,
                    successful_deliveries=sub.successful_deliveries,
                    failed_deliveries=sub.failed_deliveries,
                    last_delivery_at=sub.last_delivery_at,
                    last_delivery_status=sub.last_delivery_status,
                    created_at=sub.created_at,
                    updated_at=sub.updated_at
                )
                for sub in subscriptions
            ]
            
        except Exception as e:
            logger.error(f"Error getting subscriptions for schedule {schedule_id}: {e}")
            raise