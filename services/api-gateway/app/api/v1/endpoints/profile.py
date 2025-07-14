"""
User profile management endpoints
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query as QueryParam, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.logging import get_logger
from ....api.deps import get_async_session, get_current_user, require_permissions
from ....models.user import User
from ....models.profile import (
    UserProfileUpdate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    UserProfileExtended,
    UserSettings,
    UserOnboardingProgress,
    ActivitySummary
)
from ....models.responses import SuccessResponse, COMMON_RESPONSES
from ....services.profile_service import ProfileService
from ....core.exceptions import ValidationError, ResourceNotFoundError
from ....core.audit import audit_action, AuditAction, AuditResource

router = APIRouter()
logger = get_logger(__name__)
profile_service = ProfileService()


@router.get(
    "/me",
    response_model=UserProfileExtended,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieve the complete profile of the currently authenticated user including activity summary",
    responses=COMMON_RESPONSES
)
async def get_my_profile(
    include_activity: bool = QueryParam(default=True, description="Include activity summary"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserProfileExtended:
    """Get current user's complete profile"""
    
    profile = await profile_service.get_user_profile(
        db=db,
        user_id=current_user.id,
        include_activity=include_activity
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.READ,
        resource=AuditResource.USER_PROFILE,
        resource_id=str(current_user.id),
        details={"include_activity": include_activity}
    )
    
    return profile


@router.put(
    "/me",
    response_model=UserProfileExtended,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Update the profile information of the currently authenticated user",
    responses=COMMON_RESPONSES
)
async def update_my_profile(
    profile_update: UserProfileUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserProfileExtended:
    """Update current user's profile"""
    
    updated_profile = await profile_service.update_user_profile(
        db=db,
        user_id=current_user.id,
        profile_update=profile_update,
        updated_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PROFILE,
        resource_id=str(current_user.id),
        details=profile_update.dict(exclude_unset=True)
    )
    
    return updated_profile


@router.get(
    "/me/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user preferences",
    description="Retrieve all preference categories for the current user",
    responses=COMMON_RESPONSES
)
async def get_my_preferences(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Get current user's preferences"""
    
    preferences = await profile_service.get_user_preferences(
        db=db,
        user_id=current_user.id
    )
    
    return preferences


@router.put(
    "/me/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user preferences",
    description="Update one or more preference categories for the current user",
    responses=COMMON_RESPONSES
)
async def update_my_preferences(
    preferences_update: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Update current user's preferences"""
    
    updated_preferences = await profile_service.update_user_preferences(
        db=db,
        user_id=current_user.id,
        preferences_update=preferences_update,
        updated_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PREFERENCES,
        resource_id=str(current_user.id),
        details=preferences_update.dict(exclude_unset=True)
    )
    
    return updated_preferences


@router.post(
    "/me/preferences/reset",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset preferences to defaults",
    description="Reset specified preference categories to default values",
    responses=COMMON_RESPONSES
)
async def reset_my_preferences(
    categories: Optional[List[str]] = QueryParam(
        default=None,
        description="Preference categories to reset (all if not specified)"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Reset user preferences to defaults"""
    
    reset_preferences = await profile_service.reset_preferences_to_defaults(
        db=db,
        user_id=current_user.id,
        categories=categories,
        reset_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PREFERENCES,
        resource_id=str(current_user.id),
        details={"action": "reset", "categories": categories or "all"}
    )
    
    return reset_preferences


@router.get(
    "/me/settings",
    response_model=UserSettings,
    status_code=status.HTTP_200_OK,
    summary="Get complete user settings",
    description="Retrieve both profile and preferences in a single response",
    responses=COMMON_RESPONSES
)
async def get_my_settings(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserSettings:
    """Get complete user settings (profile + preferences)"""
    
    settings_data = await profile_service.get_user_settings(
        db=db,
        user_id=current_user.id
    )
    
    return settings_data


@router.get(
    "/me/activity",
    response_model=ActivitySummary,
    status_code=status.HTTP_200_OK,
    summary="Get user activity summary",
    description="Retrieve activity statistics and usage patterns for the current user",
    responses=COMMON_RESPONSES
)
async def get_my_activity(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> ActivitySummary:
    """Get current user's activity summary"""
    
    activity = await profile_service._get_user_activity_summary(
        db=db,
        user_id=current_user.id
    )
    
    return activity


@router.get(
    "/me/onboarding",
    response_model=UserOnboardingProgress,
    status_code=status.HTTP_200_OK,
    summary="Get onboarding progress",
    description="Retrieve the current user's onboarding completion status",
    responses=COMMON_RESPONSES
)
async def get_my_onboarding_progress(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserOnboardingProgress:
    """Get current user's onboarding progress"""
    
    progress = await profile_service.get_onboarding_progress(
        db=db,
        user_id=current_user.id
    )
    
    return progress


@router.post(
    "/me/onboarding/{step}",
    response_model=UserOnboardingProgress,
    status_code=status.HTTP_200_OK,
    summary="Update onboarding step",
    description="Mark an onboarding step as completed or update its status",
    responses=COMMON_RESPONSES
)
async def update_onboarding_step(
    step: str,
    completed: bool = QueryParam(default=True, description="Mark step as completed"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserOnboardingProgress:
    """Update onboarding progress for a specific step"""
    
    # Validate step name
    valid_steps = [
        "tour_completed", "training_completed", "profile_setup",
        "preferences_set", "first_query", "first_dashboard", "first_alert"
    ]
    
    if step not in valid_steps:
        raise ValidationError(
            f"Invalid onboarding step. Must be one of: {', '.join(valid_steps)}"
        )
    
    progress = await profile_service.update_onboarding_progress(
        db=db,
        user_id=current_user.id,
        step=step,
        completed=completed
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PROFILE,
        resource_id=str(current_user.id),
        details={"onboarding_step": step, "completed": completed}
    )
    
    return progress


@router.get(
    "/me/export",
    status_code=status.HTTP_200_OK,
    summary="Export user data",
    description="Export all user data for privacy compliance (GDPR, etc.)",
    responses=COMMON_RESPONSES
)
async def export_my_data(
    format: str = QueryParam(default="json", description="Export format (json, csv)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """Export all user data"""
    
    if format not in ["json", "csv"]:
        raise ValidationError("Export format must be 'json' or 'csv'")
    
    export_data = await profile_service.export_user_data(
        db=db,
        user_id=current_user.id,
        format=format
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.EXPORT,
        resource=AuditResource.USER_DATA,
        resource_id=str(current_user.id),
        details={"format": format}
    )
    
    # In production, this might trigger a background job and send download link via email
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=user_data_{current_user.id}.{format}",
            "Content-Type": f"application/{format}"
        }
    )


# Admin endpoints for managing other users' profiles
@router.get(
    "/{user_id}",
    response_model=UserProfileExtended,
    status_code=status.HTTP_200_OK,
    summary="Get user profile (Admin)",
    description="Retrieve profile of any user (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:read"]))]
)
async def get_user_profile(
    user_id: UUID,
    include_activity: bool = QueryParam(default=True, description="Include activity summary"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserProfileExtended:
    """Get any user's profile (admin only)"""
    
    profile = await profile_service.get_user_profile(
        db=db,
        user_id=user_id,
        include_activity=include_activity
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.READ,
        resource=AuditResource.USER_PROFILE,
        resource_id=str(user_id),
        details={"admin_access": True, "include_activity": include_activity}
    )
    
    return profile


@router.put(
    "/{user_id}",
    response_model=UserProfileExtended,
    status_code=status.HTTP_200_OK,
    summary="Update user profile (Admin)",
    description="Update any user's profile (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:update"]))]
)
async def update_user_profile(
    user_id: UUID,
    profile_update: UserProfileUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserProfileExtended:
    """Update any user's profile (admin only)"""
    
    updated_profile = await profile_service.update_user_profile(
        db=db,
        user_id=user_id,
        profile_update=profile_update,
        updated_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PROFILE,
        resource_id=str(user_id),
        details={
            "admin_update": True,
            "changes": profile_update.dict(exclude_unset=True)
        }
    )
    
    return updated_profile


@router.get(
    "/{user_id}/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user preferences (Admin)",
    description="Retrieve any user's preferences (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:read"]))]
)
async def get_user_preferences(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Get any user's preferences (admin only)"""
    
    preferences = await profile_service.get_user_preferences(
        db=db,
        user_id=user_id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.READ,
        resource=AuditResource.USER_PREFERENCES,
        resource_id=str(user_id),
        details={"admin_access": True}
    )
    
    return preferences


@router.put(
    "/{user_id}/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user preferences (Admin)",
    description="Update any user's preferences (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:update"]))]
)
async def update_user_preferences(
    user_id: UUID,
    preferences_update: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Update any user's preferences (admin only)"""
    
    updated_preferences = await profile_service.update_user_preferences(
        db=db,
        user_id=user_id,
        preferences_update=preferences_update,
        updated_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PREFERENCES,
        resource_id=str(user_id),
        details={
            "admin_update": True,
            "changes": preferences_update.dict(exclude_unset=True)
        }
    )
    
    return updated_preferences


@router.post(
    "/{user_id}/preferences/reset",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset user preferences (Admin)",
    description="Reset any user's preferences to defaults (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:update"]))]
)
async def reset_user_preferences(
    user_id: UUID,
    categories: Optional[List[str]] = QueryParam(
        default=None,
        description="Preference categories to reset (all if not specified)"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserPreferencesResponse:
    """Reset any user's preferences to defaults (admin only)"""
    
    reset_preferences = await profile_service.reset_preferences_to_defaults(
        db=db,
        user_id=user_id,
        categories=categories,
        reset_by=current_user.id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        resource=AuditResource.USER_PREFERENCES,
        resource_id=str(user_id),
        details={
            "admin_reset": True,
            "categories": categories or "all"
        }
    )
    
    return reset_preferences


@router.get(
    "/{user_id}/settings",
    response_model=UserSettings,
    status_code=status.HTTP_200_OK,
    summary="Get user settings (Admin)",
    description="Retrieve complete settings for any user (requires admin permissions)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["users:read"]))]
)
async def get_user_settings(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> UserSettings:
    """Get any user's complete settings (admin only)"""
    
    settings_data = await profile_service.get_user_settings(
        db=db,
        user_id=user_id
    )
    
    await audit_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.READ,
        resource=AuditResource.USER_SETTINGS,
        resource_id=str(user_id),
        details={"admin_access": True}
    )
    
    return settings_data