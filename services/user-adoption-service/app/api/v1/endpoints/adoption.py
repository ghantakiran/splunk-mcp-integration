#!/usr/bin/env python3
"""
User Adoption Metrics API Endpoints
===================================
API endpoints for tracking and analyzing user adoption metrics
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
    UserProfile, AdoptionMetric, AdoptionMetricType, AdoptionMetricCreate
)
from app.services.adoption_service import AdoptionService
from app.utils.auth import get_current_user, User

router = APIRouter()

@router.post("/metrics")
async def track_adoption_metric(
    metric_data: AdoptionMetricCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Track a user adoption metric"""
    
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
    
    # Create adoption metric
    now = datetime.utcnow()
    metric = AdoptionMetric(
        user_profile_id=user_profile.id,
        metric_type=metric_data.metric_type,
        metric_name=metric_data.metric_name,
        metric_value=metric_data.metric_value,
        metric_unit=metric_data.metric_unit,
        feature_name=metric_data.feature_name,
        page_context=metric_data.page_context,
        session_id=metric_data.session_id,
        metric_data=metric_data.metric_data,
        recorded_at=now,
        date_dimension=now.date(),
        hour_dimension=now.hour,
        day_of_week=now.weekday()
    )
    
    db.add(metric)
    
    # Update user profile metrics in background
    adoption_service = AdoptionService(db)
    background_tasks.add_task(
        adoption_service.update_user_metrics,
        user_profile.id,
        metric_data.metric_type
    )
    
    # Update last activity
    user_profile.last_activity_at = now
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Adoption metric tracked successfully",
        "metric_id": metric.id,
        "recorded_at": metric.recorded_at
    }

@router.get("/metrics/user/{user_id}")
async def get_user_adoption_metrics(
    user_id: str,
    metric_type: Optional[AdoptionMetricType] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get adoption metrics for a specific user"""
    
    # Check if user can access these metrics
    if user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
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
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Build metrics query
    query = select(AdoptionMetric).where(
        and_(
            AdoptionMetric.user_profile_id == user_profile.id,
            AdoptionMetric.recorded_at >= start_date
        )
    )
    
    if metric_type:
        query = query.where(AdoptionMetric.metric_type == metric_type)
    
    result = await db.execute(query.order_by(desc(AdoptionMetric.recorded_at)))
    metrics = result.scalars().all()
    
    # Group metrics by type
    metrics_by_type = {}
    for metric in metrics:
        if metric.metric_type not in metrics_by_type:
            metrics_by_type[metric.metric_type] = []
        metrics_by_type[metric.metric_type].append({
            "metric_name": metric.metric_name,
            "metric_value": metric.metric_value,
            "metric_unit": metric.metric_unit,
            "feature_name": metric.feature_name,
            "recorded_at": metric.recorded_at,
            "metric_data": metric.metric_data
        })
    
    # Calculate summary statistics
    adoption_service = AdoptionService(db)
    user_stats = await adoption_service.calculate_user_adoption_score(user_profile.id)
    
    return {
        "user_id": user_id,
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "summary": {
            "total_metrics": len(metrics),
            "adoption_score": user_stats["adoption_score"],
            "engagement_level": user_stats["engagement_level"],
            "feature_adoption_rate": user_stats["feature_adoption_rate"],
            "last_activity": user_profile.last_activity_at
        },
        "metrics_by_type": metrics_by_type,
        "user_profile": {
            "total_logins": user_profile.total_logins,
            "total_queries": user_profile.total_queries,
            "total_dashboards": user_profile.total_dashboards,
            "total_alerts": user_profile.total_alerts,
            "total_exports": user_profile.total_exports
        }
    }

@router.get("/metrics/features")
async def get_feature_adoption_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get feature adoption metrics across all users"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get feature usage metrics
    result = await db.execute(
        select(
            AdoptionMetric.feature_name,
            func.count(AdoptionMetric.id).label("usage_count"),
            func.count(func.distinct(AdoptionMetric.user_profile_id)).label("unique_users"),
            func.avg(AdoptionMetric.metric_value).label("avg_value"),
            func.sum(AdoptionMetric.metric_value).label("total_value")
        )
        .where(
            and_(
                AdoptionMetric.recorded_at >= start_date,
                AdoptionMetric.feature_name.is_not(None)
            )
        )
        .group_by(AdoptionMetric.feature_name)
        .order_by(desc("usage_count"))
    )
    feature_stats = result.all()
    
    # Get total active users in period
    total_users_result = await db.execute(
        select(func.count(func.distinct(AdoptionMetric.user_profile_id)))
        .where(AdoptionMetric.recorded_at >= start_date)
    )
    total_active_users = total_users_result.scalar() or 0
    
    # Calculate feature adoption rates
    feature_metrics = []
    for stat in feature_stats:
        adoption_rate = (stat.unique_users / total_active_users * 100) if total_active_users > 0 else 0
        feature_metrics.append({
            "feature_name": stat.feature_name,
            "usage_count": stat.usage_count,
            "unique_users": stat.unique_users,
            "adoption_rate": round(adoption_rate, 2),
            "avg_value": round(float(stat.avg_value or 0), 2),
            "total_value": float(stat.total_value or 0)
        })
    
    # Get usage trends by day
    daily_usage_result = await db.execute(
        select(
            AdoptionMetric.date_dimension,
            func.count(AdoptionMetric.id).label("total_usage"),
            func.count(func.distinct(AdoptionMetric.user_profile_id)).label("active_users")
        )
        .where(AdoptionMetric.recorded_at >= start_date)
        .group_by(AdoptionMetric.date_dimension)
        .order_by(AdoptionMetric.date_dimension)
    )
    daily_trends = daily_usage_result.all()
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "overview": {
            "total_active_users": total_active_users,
            "total_features_used": len(feature_metrics),
            "total_usage_events": sum(f["usage_count"] for f in feature_metrics)
        },
        "feature_adoption": feature_metrics,
        "daily_trends": [
            {
                "date": trend.date_dimension.isoformat(),
                "total_usage": trend.total_usage,
                "active_users": trend.active_users
            }
            for trend in daily_trends
        ]
    }

@router.get("/metrics/engagement")
async def get_engagement_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user engagement metrics"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get user engagement levels
    engagement_result = await db.execute(
        select(
            UserProfile.engagement_level,
            func.count(UserProfile.id).label("user_count")
        )
        .group_by(UserProfile.engagement_level)
    )
    engagement_distribution = engagement_result.all()
    
    # Get activity patterns by hour
    hourly_activity_result = await db.execute(
        select(
            AdoptionMetric.hour_dimension,
            func.count(AdoptionMetric.id).label("activity_count")
        )
        .where(AdoptionMetric.recorded_at >= start_date)
        .group_by(AdoptionMetric.hour_dimension)
        .order_by(AdoptionMetric.hour_dimension)
    )
    hourly_activity = hourly_activity_result.all()
    
    # Get activity patterns by day of week
    daily_activity_result = await db.execute(
        select(
            AdoptionMetric.day_of_week,
            func.count(AdoptionMetric.id).label("activity_count")
        )
        .where(AdoptionMetric.recorded_at >= start_date)
        .group_by(AdoptionMetric.day_of_week)
        .order_by(AdoptionMetric.day_of_week)
    )
    daily_activity = daily_activity_result.all()
    
    # Get session duration metrics
    session_duration_result = await db.execute(
        select(
            func.avg(AdoptionMetric.metric_value).label("avg_duration"),
            func.min(AdoptionMetric.metric_value).label("min_duration"),
            func.max(AdoptionMetric.metric_value).label("max_duration")
        )
        .where(
            and_(
                AdoptionMetric.metric_type == AdoptionMetricType.SESSION_DURATION,
                AdoptionMetric.recorded_at >= start_date
            )
        )
    )
    session_stats = session_duration_result.first()
    
    # Get top active users
    top_users_result = await db.execute(
        select(
            UserProfile.full_name,
            UserProfile.department,
            UserProfile.adoption_score,
            UserProfile.total_logins,
            UserProfile.last_activity_at
        )
        .where(UserProfile.last_activity_at >= start_date)
        .order_by(desc(UserProfile.adoption_score))
        .limit(10)
    )
    top_users = top_users_result.all()
    
    # Calculate retention metrics
    retention_result = await db.execute(
        select(
            func.count(func.distinct(AdoptionMetric.user_profile_id)).label("active_users")
        )
        .where(AdoptionMetric.recorded_at >= start_date)
    )
    current_active_users = retention_result.scalar() or 0
    
    # Previous period for comparison
    previous_start = start_date - timedelta(days=days)
    previous_retention_result = await db.execute(
        select(
            func.count(func.distinct(AdoptionMetric.user_profile_id)).label("active_users")
        )
        .where(
            and_(
                AdoptionMetric.recorded_at >= previous_start,
                AdoptionMetric.recorded_at < start_date
            )
        )
    )
    previous_active_users = previous_retention_result.scalar() or 0
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "engagement_distribution": {
            level.engagement_level: level.user_count
            for level in engagement_distribution
        },
        "activity_patterns": {
            "hourly": {
                str(hour.hour_dimension): hour.activity_count
                for hour in hourly_activity
            },
            "daily": {
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day.day_of_week]: day.activity_count
                for day in daily_activity
            }
        },
        "session_metrics": {
            "avg_duration_minutes": round(float(session_stats.avg_duration or 0) / 60, 2),
            "min_duration_minutes": round(float(session_stats.min_duration or 0) / 60, 2),
            "max_duration_minutes": round(float(session_stats.max_duration or 0) / 60, 2)
        },
        "retention_metrics": {
            "current_active_users": current_active_users,
            "previous_active_users": previous_active_users,
            "growth_rate": ((current_active_users - previous_active_users) / previous_active_users * 100) if previous_active_users > 0 else 0
        },
        "top_active_users": [
            {
                "full_name": user.full_name,
                "department": user.department,
                "adoption_score": user.adoption_score,
                "total_logins": user.total_logins,
                "last_activity": user.last_activity_at
            }
            for user in top_users
        ]
    }

@router.get("/metrics/cohort-analysis")
async def get_cohort_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cohort analysis for user adoption"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    adoption_service = AdoptionService(db)
    cohort_data = await adoption_service.calculate_cohort_analysis()
    
    return cohort_data

@router.get("/metrics/funnel-analysis")
async def get_funnel_analysis(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get adoption funnel analysis"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Define adoption funnel steps
    funnel_steps = [
        ("registration", "User Registration"),
        ("first_login", "First Login"),
        ("first_query", "First Query"),
        ("dashboard_view", "Dashboard View"),
        ("dashboard_create", "Dashboard Creation"),
        ("alert_create", "Alert Creation"),
        ("report_export", "Report Export")
    ]
    
    # Get users in date range
    users_result = await db.execute(
        select(UserProfile)
        .where(UserProfile.created_at >= start_date)
    )
    users = users_result.scalars().all()
    total_users = len(users)
    
    # Calculate funnel metrics
    funnel_data = []
    remaining_users = total_users
    
    for step_id, step_name in funnel_steps:
        if step_id == "registration":
            step_users = total_users
        elif step_id == "first_login":
            step_users = len([u for u in users if u.first_login_at])
        elif step_id == "first_query":
            step_users = len([u for u in users if u.total_queries > 0])
        elif step_id == "dashboard_view":
            # Users who have viewed dashboards (tracked via metrics)
            dashboard_viewers_result = await db.execute(
                select(func.count(func.distinct(AdoptionMetric.user_profile_id)))
                .where(
                    and_(
                        AdoptionMetric.metric_type == AdoptionMetricType.DASHBOARD_VIEW,
                        AdoptionMetric.user_profile_id.in_([u.id for u in users])
                    )
                )
            )
            step_users = dashboard_viewers_result.scalar() or 0
        elif step_id == "dashboard_create":
            step_users = len([u for u in users if u.total_dashboards > 0])
        elif step_id == "alert_create":
            step_users = len([u for u in users if u.total_alerts > 0])
        elif step_id == "report_export":
            step_users = len([u for u in users if u.total_exports > 0])
        else:
            step_users = 0
        
        conversion_rate = (step_users / total_users * 100) if total_users > 0 else 0
        step_conversion_rate = (step_users / remaining_users * 100) if remaining_users > 0 else 0
        
        funnel_data.append({
            "step_id": step_id,
            "step_name": step_name,
            "users": step_users,
            "conversion_rate": round(conversion_rate, 2),
            "step_conversion_rate": round(step_conversion_rate, 2),
            "drop_off": remaining_users - step_users
        })
        
        remaining_users = step_users
    
    # Calculate overall funnel efficiency
    funnel_efficiency = (remaining_users / total_users * 100) if total_users > 0 else 0
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        },
        "overview": {
            "total_users": total_users,
            "funnel_efficiency": round(funnel_efficiency, 2),
            "final_step_users": remaining_users
        },
        "funnel_steps": funnel_data
    }

@router.post("/users/{user_id}/engagement-score")
async def update_user_engagement_score(
    user_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger engagement score calculation for a user"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
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
    
    # Update engagement score in background
    adoption_service = AdoptionService(db)
    background_tasks.add_task(
        adoption_service.calculate_and_update_adoption_score,
        user_profile.id
    )
    
    return {
        "success": True,
        "message": "Engagement score calculation triggered",
        "user_id": user_id
    }

@router.get("/users/low-engagement")
async def get_low_engagement_users(
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    days_inactive: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get users with low engagement scores for intervention"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Calculate cutoff date for inactive users
    cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
    
    # Get low engagement users
    result = await db.execute(
        select(UserProfile)
        .where(
            and_(
                UserProfile.adoption_score <= threshold,
                UserProfile.last_activity_at < cutoff_date
            )
        )
        .order_by(UserProfile.adoption_score)
    )
    low_engagement_users = result.scalars().all()
    
    return {
        "criteria": {
            "engagement_threshold": threshold,
            "days_inactive": days_inactive,
            "cutoff_date": cutoff_date
        },
        "users": [
            {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "department": user.department,
                "adoption_score": user.adoption_score,
                "engagement_level": user.engagement_level,
                "last_activity_at": user.last_activity_at,
                "onboarding_status": user.onboarding_status,
                "total_logins": user.total_logins,
                "total_queries": user.total_queries,
                "created_at": user.created_at
            }
            for user in low_engagement_users
        ],
        "total_users": len(low_engagement_users)
    }