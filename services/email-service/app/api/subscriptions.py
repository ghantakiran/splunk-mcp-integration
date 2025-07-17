"""
Subscription API endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user_models import (
    UserSubscriptionCreate, UserSubscriptionResponse
)
from app.services.database_service import DatabaseService

router = APIRouter()


@router.post("/", response_model=UserSubscriptionResponse)
async def create_subscription(
    subscription_data: UserSubscriptionCreate,
    db: DatabaseService = Depends(),
):
    """Create a new subscription."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/", response_model=List[UserSubscriptionResponse])
async def list_subscriptions(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: DatabaseService = Depends(),
):
    """List user's subscriptions."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{subscription_id}", response_model=UserSubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    db: DatabaseService = Depends(),
):
    """Get specific subscription."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{subscription_id}", response_model=UserSubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    subscription_data: UserSubscriptionCreate,
    db: DatabaseService = Depends(),
):
    """Update a subscription."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: UUID,
    db: DatabaseService = Depends(),
):
    """Delete a subscription."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")