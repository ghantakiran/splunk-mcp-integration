"""
User API endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.models.user_models import (
    EmailUserCreate, EmailUserResponse, UserEmailSettingsCreate,
    UserEmailSettingsResponse, UserStatsResponse
)
from app.services.database_service import DatabaseService

router = APIRouter()


@router.post("/", response_model=EmailUserResponse)
async def create_user(
    user_data: EmailUserCreate,
    db: DatabaseService = Depends(),
):
    """Create a new email user."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/me", response_model=EmailUserResponse)
async def get_current_user(
    db: DatabaseService = Depends(),
):
    """Get current user profile."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/me/settings", response_model=UserEmailSettingsResponse)
async def get_user_settings(
    db: DatabaseService = Depends(),
):
    """Get user email settings."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/me/settings", response_model=UserEmailSettingsResponse)
async def update_user_settings(
    settings_data: UserEmailSettingsCreate,
    db: DatabaseService = Depends(),
):
    """Update user email settings."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: DatabaseService = Depends(),
):
    """Get user statistics."""
    # Implementation would go here
    raise HTTPException(status_code=501, detail="Not implemented")