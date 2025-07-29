#!/usr/bin/env python3
"""
Onboarding API Endpoints
========================
API endpoints for user onboarding tracking and management
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.adoption_models import (
    UserProfile, OnboardingStep, OnboardingStatus,
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    OnboardingStepUpdate
)
from app.services.onboarding_service import OnboardingService
from app.utils.auth import get_current_user, User

router = APIRouter()

@router.post("/users", response_model=UserProfileResponse)
async def create_user_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user profile for adoption tracking"""
    
    # Check if user profile already exists
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == profile_data.user_id)
    )
    existing_profile = result.scalar_one_or_none()
    
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="User profile already exists"
        )
    
    # Create user profile
    user_profile = UserProfile(
        user_id=profile_data.user_id,
        email=profile_data.email,
        full_name=profile_data.full_name,
        department=profile_data.department,
        role=profile_data.role,
        user_type=profile_data.user_type,
        first_login_at=datetime.utcnow()
    )
    
    db.add(user_profile)
    await db.commit()
    await db.refresh(user_profile)
    
    # Initialize onboarding steps
    onboarding_service = OnboardingService(db)
    await onboarding_service.initialize_onboarding_steps(user_profile.id)
    
    return user_profile

@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user profile by user ID"""
    
    result = await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.onboarding_steps))
    )
    user_profile = result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    return user_profile

@router.put("/users/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(
    user_id: str,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile information"""
    
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Update profile fields
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_profile, field, value)
    
    user_profile.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user_profile)
    
    return user_profile

@router.get("/users/{user_id}/steps")
async def get_onboarding_steps(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding steps for a user"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Get onboarding steps
    steps_result = await db.execute(
        select(OnboardingStep)
        .where(OnboardingStep.user_profile_id == user_profile.id)
        .order_by(OnboardingStep.step_order)
    )
    steps = steps_result.scalars().all()
    
    return {
        "user_id": user_id,
        "onboarding_status": user_profile.onboarding_status,
        "onboarding_progress": user_profile.onboarding_progress,
        "total_steps": len(steps),
        "completed_steps": len([s for s in steps if s.status == OnboardingStatus.COMPLETED]),
        "steps": [
            {
                "id": step.id,
                "step_id": step.step_id,
                "step_name": step.step_name,
                "step_order": step.step_order,
                "status": step.status,
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "attempts": step.attempts,
                "completion_time_seconds": step.completion_time_seconds,
                "help_accessed": step.help_accessed,
                "step_data": step.step_data
            }
            for step in steps
        ]
    }

@router.post("/users/{user_id}/steps/{step_id}/start")
async def start_onboarding_step(
    user_id: str,
    step_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start an onboarding step"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Get onboarding step
    step_result = await db.execute(
        select(OnboardingStep).where(
            and_(
                OnboardingStep.user_profile_id == user_profile.id,
                OnboardingStep.step_id == step_id
            )
        )
    )
    step = step_result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(
            status_code=404,
            detail="Onboarding step not found"
        )
    
    # Update step status
    step.status = OnboardingStatus.IN_PROGRESS
    step.started_at = datetime.utcnow()
    step.attempts += 1
    
    # Update user profile onboarding status
    if user_profile.onboarding_status == OnboardingStatus.NOT_STARTED:
        user_profile.onboarding_status = OnboardingStatus.IN_PROGRESS
        user_profile.onboarding_started_at = datetime.utcnow()
    
    user_profile.last_activity_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Started onboarding step: {step.step_name}",
        "step_id": step_id,
        "status": step.status,
        "started_at": step.started_at
    }

@router.post("/users/{user_id}/steps/{step_id}/complete")
async def complete_onboarding_step(
    user_id: str,
    step_id: str,
    step_update: OnboardingStepUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete an onboarding step"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Get onboarding step
    step_result = await db.execute(
        select(OnboardingStep).where(
            and_(
                OnboardingStep.user_profile_id == user_profile.id,
                OnboardingStep.step_id == step_id
            )
        )
    )
    step = step_result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(
            status_code=404,
            detail="Onboarding step not found"
        )
    
    # Update step
    now = datetime.utcnow()
    step.status = step_update.status
    step.completed_at = now if step_update.status == OnboardingStatus.COMPLETED else None
    step.help_accessed = step_update.help_accessed
    step.step_data = step_update.step_data
    
    # Calculate completion time
    if step.started_at and step.completed_at:
        step.completion_time_seconds = int((step.completed_at - step.started_at).total_seconds())
    
    # Update user profile progress
    onboarding_service = OnboardingService(db)
    await onboarding_service.update_onboarding_progress(user_profile.id)
    
    user_profile.last_activity_at = now
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Updated onboarding step: {step.step_name}",
        "step_id": step_id,
        "status": step.status,
        "completed_at": step.completed_at,
        "completion_time_seconds": step.completion_time_seconds
    }

@router.get("/users/{user_id}/progress")
async def get_onboarding_progress(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed onboarding progress for a user"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Get onboarding steps with progress
    steps_result = await db.execute(
        select(OnboardingStep)
        .where(OnboardingStep.user_profile_id == user_profile.id)
        .order_by(OnboardingStep.step_order)
    )
    steps = steps_result.scalars().all()
    
    # Calculate progress metrics
    total_steps = len(steps)
    completed_steps = len([s for s in steps if s.status == OnboardingStatus.COMPLETED])
    in_progress_steps = len([s for s in steps if s.status == OnboardingStatus.IN_PROGRESS])
    skipped_steps = len([s for s in steps if s.status == OnboardingStatus.SKIPPED])
    
    # Calculate time metrics
    completion_times = [s.completion_time_seconds for s in steps if s.completion_time_seconds]
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    # Calculate engagement metrics
    help_accessed_count = len([s for s in steps if s.help_accessed])
    total_attempts = sum(s.attempts for s in steps)
    
    # Determine next recommended step
    next_step = None
    for step in steps:
        if step.status == OnboardingStatus.NOT_STARTED:
            next_step = {
                "step_id": step.step_id,
                "step_name": step.step_name,
                "step_order": step.step_order
            }
            break
    
    return {
        "user_id": user_id,
        "onboarding_status": user_profile.onboarding_status,
        "overall_progress": {
            "percentage": user_profile.onboarding_progress,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "in_progress_steps": in_progress_steps,
            "skipped_steps": skipped_steps,
            "remaining_steps": total_steps - completed_steps - skipped_steps
        },
        "time_metrics": {
            "started_at": user_profile.onboarding_started_at,
            "completed_at": user_profile.onboarding_completed_at,
            "average_step_completion_time": avg_completion_time,
            "total_completion_times": completion_times
        },
        "engagement_metrics": {
            "help_accessed_count": help_accessed_count,
            "total_attempts": total_attempts,
            "engagement_level": user_profile.engagement_level
        },
        "next_recommended_step": next_step,
        "steps_summary": [
            {
                "step_id": step.step_id,
                "step_name": step.step_name,
                "status": step.status,
                "completion_time_seconds": step.completion_time_seconds,
                "attempts": step.attempts,
                "help_accessed": step.help_accessed
            }
            for step in steps
        ]
    }

@router.post("/users/{user_id}/skip-onboarding")
async def skip_onboarding(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Allow user to skip the onboarding process"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Update onboarding status
    user_profile.onboarding_status = OnboardingStatus.SKIPPED
    user_profile.onboarding_progress = 1.0  # Consider as completed for metrics
    user_profile.last_activity_at = datetime.utcnow()
    
    # Mark all remaining steps as skipped
    await db.execute(
        update(OnboardingStep)
        .where(
            and_(
                OnboardingStep.user_profile_id == user_profile.id,
                OnboardingStep.status == OnboardingStatus.NOT_STARTED
            )
        )
        .values(status=OnboardingStatus.SKIPPED)
    )
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Onboarding process skipped",
        "onboarding_status": user_profile.onboarding_status,
        "progress": user_profile.onboarding_progress
    }

@router.get("/analytics/onboarding")
async def get_onboarding_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding analytics for administrators"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get user profiles in date range
    profiles_result = await db.execute(
        select(UserProfile)
        .where(UserProfile.created_at >= start_date)
        .options(selectinload(UserProfile.onboarding_steps))
    )
    profiles = profiles_result.scalars().all()
    
    # Calculate analytics
    total_users = len(profiles)
    completed_onboarding = len([p for p in profiles if p.onboarding_status == OnboardingStatus.COMPLETED])
    in_progress_onboarding = len([p for p in profiles if p.onboarding_status == OnboardingStatus.IN_PROGRESS])
    skipped_onboarding = len([p for p in profiles if p.onboarding_status == OnboardingStatus.SKIPPED])
    abandoned_onboarding = len([p for p in profiles if p.onboarding_status == OnboardingStatus.ABANDONED])
    
    # Calculate completion rate
    completion_rate = (completed_onboarding / total_users * 100) if total_users > 0 else 0
    
    # Calculate average progress
    avg_progress = sum(p.onboarding_progress for p in profiles) / total_users if total_users > 0 else 0
    
    # Step-by-step analytics
    step_analytics = {}
    for profile in profiles:
        for step in profile.onboarding_steps:
            if step.step_id not in step_analytics:
                step_analytics[step.step_id] = {
                    "step_name": step.step_name,
                    "total_users": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "skipped": 0,
                    "completion_times": [],
                    "help_accessed": 0,
                    "total_attempts": 0
                }
            
            analytics = step_analytics[step.step_id]
            analytics["total_users"] += 1
            analytics["total_attempts"] += step.attempts
            
            if step.status == OnboardingStatus.COMPLETED:
                analytics["completed"] += 1
                if step.completion_time_seconds:
                    analytics["completion_times"].append(step.completion_time_seconds)
            elif step.status == OnboardingStatus.IN_PROGRESS:
                analytics["in_progress"] += 1
            elif step.status == OnboardingStatus.SKIPPED:
                analytics["skipped"] += 1
            
            if step.help_accessed:
                analytics["help_accessed"] += 1
    
    # Calculate step completion rates and average times
    for step_id, analytics in step_analytics.items():
        analytics["completion_rate"] = (analytics["completed"] / analytics["total_users"] * 100) if analytics["total_users"] > 0 else 0
        analytics["avg_completion_time"] = sum(analytics["completion_times"]) / len(analytics["completion_times"]) if analytics["completion_times"] else 0
        analytics["help_usage_rate"] = (analytics["help_accessed"] / analytics["total_users"] * 100) if analytics["total_users"] > 0 else 0
        analytics["avg_attempts"] = analytics["total_attempts"] / analytics["total_users"] if analytics["total_users"] > 0 else 0
        
        # Remove raw data from response
        del analytics["completion_times"]
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "overall_metrics": {
            "total_users": total_users,
            "completion_rate": round(completion_rate, 2),
            "average_progress": round(avg_progress * 100, 2),
            "status_distribution": {
                "completed": completed_onboarding,
                "in_progress": in_progress_onboarding,
                "skipped": skipped_onboarding,
                "abandoned": abandoned_onboarding,
                "not_started": total_users - completed_onboarding - in_progress_onboarding - skipped_onboarding - abandoned_onboarding
            }
        },
        "step_analytics": step_analytics
    }