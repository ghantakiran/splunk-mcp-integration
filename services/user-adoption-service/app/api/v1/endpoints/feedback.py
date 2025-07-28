#!/usr/bin/env python3
"""
Feedback Collection API Endpoints
=================================
API endpoints for collecting, managing, and analyzing user feedback
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.adoption_models import (
    UserProfile, FeedbackSubmission, FeedbackFollowUp, SurveyTemplate, SurveyResponse,
    FeedbackType, FeedbackPriority,
    FeedbackSubmissionCreate, FeedbackSubmissionResponse,
    SurveyTemplateCreate, SurveyResponseCreate
)
from app.services.feedback_service import FeedbackService
from app.services.notification_service import NotificationService
from app.utils.auth import get_current_user, User

router = APIRouter()

@router.post("/submit", response_model=FeedbackSubmissionResponse)
async def submit_feedback(
    feedback_data: FeedbackSubmissionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit user feedback"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Create feedback submission
    feedback = FeedbackSubmission(
        user_profile_id=user_profile.id,
        feedback_type=feedback_data.feedback_type,
        category=feedback_data.category,
        priority=feedback_data.priority,
        title=feedback_data.title,
        description=feedback_data.description,
        rating=feedback_data.rating,
        tags=feedback_data.tags,
        page_url=feedback_data.page_url,
        feature_context=feedback_data.feature_context,
        is_anonymous=feedback_data.is_anonymous,
        contact_requested=feedback_data.contact_requested
    )
    
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    # Send notifications in background
    notification_service = NotificationService()
    background_tasks.add_task(
        notification_service.send_feedback_notification,
        feedback.id,
        user_profile.full_name
    )
    
    # Auto-categorize feedback based on content
    feedback_service = FeedbackService(db)
    background_tasks.add_task(
        feedback_service.auto_categorize_feedback,
        feedback.id
    )
    
    return feedback

@router.get("/submissions", response_model=List[FeedbackSubmissionResponse])
async def get_user_feedback(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    feedback_type: Optional[FeedbackType] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's feedback submissions"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Build query
    query = select(FeedbackSubmission).where(
        FeedbackSubmission.user_profile_id == user_profile.id
    )
    
    if status:
        query = query.where(FeedbackSubmission.status == status)
    
    if feedback_type:
        query = query.where(FeedbackSubmission.feedback_type == feedback_type)
    
    query = query.order_by(desc(FeedbackSubmission.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    return submissions

@router.get("/submissions/{feedback_id}")
async def get_feedback_details(
    feedback_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed feedback submission with follow-ups"""
    
    # Get feedback submission
    result = await db.execute(
        select(FeedbackSubmission)
        .where(FeedbackSubmission.id == feedback_id)
        .options(
            selectinload(FeedbackSubmission.user_profile),
            selectinload(FeedbackSubmission.follow_ups)
        )
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=404,
            detail="Feedback submission not found"
        )
    
    # Check access permissions (user can see their own feedback or admin can see all)
    if (feedback.user_profile.user_id != current_user.user_id and 
        not current_user.is_admin):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    return {
        "id": feedback.id,
        "feedback_type": feedback.feedback_type,
        "category": feedback.category,
        "priority": feedback.priority,
        "title": feedback.title,
        "description": feedback.description,
        "rating": feedback.rating,
        "tags": feedback.tags,
        "page_url": feedback.page_url,
        "feature_context": feedback.feature_context,
        "status": feedback.status,
        "is_anonymous": feedback.is_anonymous,
        "contact_requested": feedback.contact_requested,
        "assigned_to": feedback.assigned_to,
        "resolution_notes": feedback.resolution_notes,
        "resolved_at": feedback.resolved_at,
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
        "user": {
            "full_name": feedback.user_profile.full_name if not feedback.is_anonymous else "Anonymous",
            "email": feedback.user_profile.email if not feedback.is_anonymous else None,
            "department": feedback.user_profile.department
        },
        "follow_ups": [
            {
                "id": follow_up.id,
                "response_type": follow_up.response_type,
                "message": follow_up.message,
                "responder_type": follow_up.responder_type,
                "is_public": follow_up.is_public,
                "created_at": follow_up.created_at
            }
            for follow_up in feedback.follow_ups
        ]
    }

@router.post("/submissions/{feedback_id}/follow-up")
async def add_feedback_follow_up(
    feedback_id: uuid.UUID,
    message: str,
    response_type: str = "response",
    is_public: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add follow-up response to feedback submission"""
    
    # Get feedback submission
    result = await db.execute(
        select(FeedbackSubmission).where(FeedbackSubmission.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=404,
            detail="Feedback submission not found"
        )
    
    # Create follow-up
    follow_up = FeedbackFollowUp(
        feedback_submission_id=feedback_id,
        response_type=response_type,
        message=message,
        responder_id=current_user.user_id,
        responder_type="admin" if current_user.is_admin else "user",
        is_public=is_public
    )
    
    db.add(follow_up)
    
    # Update feedback status if needed
    if feedback.status == "submitted":
        feedback.status = "in_progress"
    
    await db.commit()
    await db.refresh(follow_up)
    
    return {
        "success": True,
        "message": "Follow-up added successfully",
        "follow_up_id": follow_up.id,
        "created_at": follow_up.created_at
    }

@router.put("/submissions/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: uuid.UUID,
    status: str,
    resolution_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update feedback submission status (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Get feedback submission
    result = await db.execute(
        select(FeedbackSubmission).where(FeedbackSubmission.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=404,
            detail="Feedback submission not found"
        )
    
    # Update status
    feedback.status = status
    feedback.assigned_to = current_user.user_id
    
    if resolution_notes:
        feedback.resolution_notes = resolution_notes
    
    if status in ["resolved", "closed"]:
        feedback.resolved_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Feedback status updated to {status}",
        "status": status,
        "resolved_at": feedback.resolved_at
    }

@router.get("/analytics/feedback")
async def get_feedback_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get feedback analytics (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get feedback submissions in date range
    result = await db.execute(
        select(FeedbackSubmission)
        .where(FeedbackSubmission.created_at >= start_date)
    )
    submissions = result.scalars().all()
    
    # Calculate metrics
    total_submissions = len(submissions)
    
    # Group by feedback type
    type_distribution = {}
    for submission in submissions:
        feedback_type = submission.feedback_type
        if feedback_type not in type_distribution:
            type_distribution[feedback_type] = 0
        type_distribution[feedback_type] += 1
    
    # Group by priority
    priority_distribution = {}
    for submission in submissions:
        priority = submission.priority
        if priority not in priority_distribution:
            priority_distribution[priority] = 0
        priority_distribution[priority] += 1
    
    # Group by status
    status_distribution = {}
    for submission in submissions:
        status = submission.status
        if status not in status_distribution:
            status_distribution[status] = 0
        status_distribution[status] += 1
    
    # Calculate ratings distribution
    ratings = [s.rating for s in submissions if s.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    rating_distribution = {}
    for rating in ratings:
        if rating not in rating_distribution:
            rating_distribution[rating] = 0
        rating_distribution[rating] += 1
    
    # Calculate resolution metrics
    resolved_submissions = [s for s in submissions if s.resolved_at]
    resolution_times = []
    for submission in resolved_submissions:
        if submission.resolved_at and submission.created_at:
            resolution_time = (submission.resolved_at - submission.created_at).total_seconds() / 3600  # hours
            resolution_times.append(resolution_time)
    
    avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Top categories
    categories = [s.category for s in submissions if s.category]
    category_counts = {}
    for category in categories:
        if category not in category_counts:
            category_counts[category] = 0
        category_counts[category] += 1
    
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Daily submission trends
    daily_trends = {}
    for submission in submissions:
        date_key = submission.created_at.date().isoformat()
        if date_key not in daily_trends:
            daily_trends[date_key] = 0
        daily_trends[date_key] += 1
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "overview": {
            "total_submissions": total_submissions,
            "average_rating": round(avg_rating, 2),
            "resolution_rate": len(resolved_submissions) / total_submissions * 100 if total_submissions > 0 else 0,
            "average_resolution_time_hours": round(avg_resolution_time, 2)
        },
        "distributions": {
            "feedback_types": type_distribution,
            "priorities": priority_distribution,
            "statuses": status_distribution,
            "ratings": rating_distribution
        },
        "top_categories": dict(top_categories),
        "daily_trends": daily_trends
    }

# Survey Management Endpoints

@router.post("/surveys/templates", response_model=dict)
async def create_survey_template(
    template_data: SurveyTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new survey template (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    survey_template = SurveyTemplate(
        name=template_data.name,
        description=template_data.description,
        survey_type=template_data.survey_type,
        questions=template_data.questions,
        targeting_rules=template_data.targeting_rules,
        trigger_conditions=template_data.trigger_conditions,
        max_responses=template_data.max_responses,
        expiration_date=template_data.expiration_date,
        frequency_limit=template_data.frequency_limit,
        created_by=current_user.user_id
    )
    
    db.add(survey_template)
    await db.commit()
    await db.refresh(survey_template)
    
    return {
        "success": True,
        "template_id": survey_template.id,
        "message": "Survey template created successfully"
    }

@router.get("/surveys/templates")
async def get_survey_templates(
    survey_type: Optional[str] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get survey templates"""
    
    query = select(SurveyTemplate).where(SurveyTemplate.is_active == is_active)
    
    if survey_type:
        query = query.where(SurveyTemplate.survey_type == survey_type)
    
    result = await db.execute(query.order_by(desc(SurveyTemplate.created_at)))
    templates = result.scalars().all()
    
    return [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "survey_type": template.survey_type,
            "questions": template.questions,
            "is_active": template.is_active,
            "created_at": template.created_at
        }
        for template in templates
    ]

@router.get("/surveys/active")
async def get_active_surveys_for_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active surveys for the current user"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        return []
    
    # Get active survey templates
    templates_result = await db.execute(
        select(SurveyTemplate).where(
            and_(
                SurveyTemplate.is_active == True,
                or_(
                    SurveyTemplate.expiration_date.is_(None),
                    SurveyTemplate.expiration_date > datetime.utcnow()
                )
            )
        )
    )
    templates = templates_result.scalars().all()
    
    # Filter surveys based on targeting rules and frequency limits
    feedback_service = FeedbackService(db)
    eligible_surveys = []
    
    for template in templates:
        if await feedback_service.is_user_eligible_for_survey(user_profile.id, template.id):
            eligible_surveys.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "survey_type": template.survey_type,
                "questions": template.questions,
                "display_settings": template.display_settings
            })
    
    return eligible_surveys

@router.post("/surveys/responses")
async def submit_survey_response(
    response_data: SurveyResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit survey response"""
    
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    )
    user_profile = profile_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Check if survey template exists
    template_result = await db.execute(
        select(SurveyTemplate).where(SurveyTemplate.id == response_data.survey_template_id)
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Survey template not found"
        )
    
    # Create survey response
    survey_response = SurveyResponse(
        survey_template_id=response_data.survey_template_id,
        user_profile_id=user_profile.id,
        responses=response_data.responses,
        completion_status=response_data.completion_status,
        trigger_context=response_data.trigger_context,
        completed_at=datetime.utcnow() if response_data.completion_status == "completed" else None
    )
    
    # Calculate completion percentage
    total_questions = len(template.questions)
    answered_questions = len([r for r in response_data.responses.values() if r is not None and r != ""])
    survey_response.completion_percentage = answered_questions / total_questions if total_questions > 0 else 0
    
    db.add(survey_response)
    await db.commit()
    await db.refresh(survey_response)
    
    return {
        "success": True,
        "response_id": survey_response.id,
        "completion_percentage": survey_response.completion_percentage,
        "message": "Survey response submitted successfully"
    }