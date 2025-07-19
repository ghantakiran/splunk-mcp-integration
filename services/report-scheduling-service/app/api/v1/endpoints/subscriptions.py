"""
Subscription management API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule_models import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    DeliveryMethod
)
from app.services.subscription_service import SubscriptionService
from app.utils.auth import get_current_user, check_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subscription",
    description="Create a new report subscription for automated delivery"
)
async def create_subscription(
    request: CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new subscription."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:create")
        
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.create_subscription(request, current_user["user_id"])
        
        logger.info(f"Subscription created: {subscription.subscription_id} by user {current_user['user_id']}")
        return subscription
        
    except ValueError as e:
        logger.error(f"Validation error creating subscription: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/",
    response_model=SubscriptionListResponse,
    summary="List subscriptions",
    description="Get a list of subscriptions with optional filtering"
)
async def list_subscriptions(
    schedule_id: Optional[UUID] = Query(None, description="Filter by schedule ID"),
    delivery_method: Optional[DeliveryMethod] = Query(None, description="Filter by delivery method"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List subscriptions with optional filtering."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:read")
        
        subscription_service = SubscriptionService(db)
        subscriptions = await subscription_service.list_subscriptions(
            user_id=current_user["user_id"],
            schedule_id=schedule_id,
            delivery_method=delivery_method,
            active=active,
            limit=limit,
            offset=offset
        )
        
        return subscriptions
        
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription by ID",
    description="Retrieve a specific subscription by its ID"
)
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get subscription by ID."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:read")
        
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_subscription(subscription_id, current_user["user_id"])
        
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription",
    description="Update an existing subscription"
)
async def update_subscription(
    subscription_id: UUID,
    request: UpdateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update subscription."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:update")
        
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.update_subscription(
            subscription_id, request, current_user["user_id"]
        )
        
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        logger.info(f"Subscription updated: {subscription_id} by user {current_user['user_id']}")
        return subscription
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating subscription: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete subscription",
    description="Delete an existing subscription"
)
async def delete_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete subscription."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:delete")
        
        subscription_service = SubscriptionService(db)
        success = await subscription_service.delete_subscription(subscription_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        logger.info(f"Subscription deleted: {subscription_id} by user {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/{subscription_id}/test",
    summary="Test subscription delivery",
    description="Test delivery for a specific subscription"
)
async def test_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Test subscription delivery."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:test")
        
        subscription_service = SubscriptionService(db)
        result = await subscription_service.test_subscription(subscription_id, current_user["user_id"])
        
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        logger.info(f"Subscription test initiated: {subscription_id} by user {current_user['user_id']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/{subscription_id}/activate",
    response_model=SubscriptionResponse,
    summary="Activate subscription",
    description="Activate a paused subscription"
)
async def activate_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate subscription."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:update")
        
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.activate_subscription(subscription_id, current_user["user_id"])
        
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        logger.info(f"Subscription activated: {subscription_id} by user {current_user['user_id']}")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/{subscription_id}/deactivate",
    response_model=SubscriptionResponse,
    summary="Deactivate subscription",
    description="Deactivate an active subscription"
)
async def deactivate_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deactivate subscription."""
    try:
        # Check permissions
        await check_permission(current_user, "subscription:update")
        
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.deactivate_subscription(subscription_id, current_user["user_id"])
        
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        logger.info(f"Subscription deactivated: {subscription_id} by user {current_user['user_id']}")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating subscription {subscription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
