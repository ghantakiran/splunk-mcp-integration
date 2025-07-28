#!/usr/bin/env python3
"""
Adoption Service
================
Service for calculating and managing user adoption metrics
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.adoption_models import (
    UserProfile, AdoptionMetric, AdoptionMetricType
)

class AdoptionService:
    """Service for managing user adoption metrics and analytics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_user_adoption_score(self, user_profile_id: uuid.UUID) -> Dict[str, Any]:
        """Calculate comprehensive adoption score for a user"""
        
        # Get user profile
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.id == user_profile_id)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            return {"adoption_score": 0.0, "engagement_level": "new", "feature_adoption_rate": 0.0}
        
        # Get adoption metrics for the user (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        metrics_result = await self.db.execute(
            select(AdoptionMetric)
            .where(
                and_(
                    AdoptionMetric.user_profile_id == user_profile_id,
                    AdoptionMetric.recorded_at >= thirty_days_ago
                )
            )
        )
        metrics = metrics_result.scalars().all()
        
        # Calculate adoption score components
        score_components = {
            "login_frequency": self._calculate_login_score(user_profile),
            "feature_usage": self._calculate_feature_usage_score(metrics),
            "engagement_depth": self._calculate_engagement_score(metrics),
            "onboarding_completion": self._calculate_onboarding_score(user_profile),
            "content_creation": self._calculate_content_creation_score(user_profile),
            "activity_recency": self._calculate_recency_score(user_profile)
        }
        
        # Weighted adoption score calculation
        weights = {
            "login_frequency": 0.15,
            "feature_usage": 0.25,
            "engagement_depth": 0.20,
            "onboarding_completion": 0.15,
            "content_creation": 0.15,
            "activity_recency": 0.10
        }
        
        adoption_score = sum(score_components[component] * weights[component] for component in weights)
        
        # Determine engagement level
        engagement_level = self._determine_engagement_level(adoption_score, user_profile)
        
        # Calculate feature adoption rate
        feature_adoption_rate = self._calculate_feature_adoption_rate(metrics)
        
        return {
            "adoption_score": round(adoption_score, 3),
            "engagement_level": engagement_level,
            "feature_adoption_rate": round(feature_adoption_rate, 3),
            "score_components": score_components
        }
    
    def _calculate_login_score(self, user_profile: UserProfile) -> float:
        """Calculate score based on login frequency"""
        if user_profile.total_logins == 0:
            return 0.0
        
        # Score based on login frequency
        if user_profile.total_logins >= 30:
            return 1.0
        elif user_profile.total_logins >= 15:
            return 0.8
        elif user_profile.total_logins >= 5:
            return 0.6
        elif user_profile.total_logins >= 1:
            return 0.3
        
        return 0.0
    
    def _calculate_feature_usage_score(self, metrics: List[AdoptionMetric]) -> float:
        """Calculate score based on feature usage diversity"""
        if not metrics:
            return 0.0
        
        # Count unique features used
        unique_features = set(metric.feature_name for metric in metrics if metric.feature_name)
        feature_count = len(unique_features)
        
        # Score based on feature diversity
        if feature_count >= 8:
            return 1.0
        elif feature_count >= 5:
            return 0.8
        elif feature_count >= 3:
            return 0.6
        elif feature_count >= 1:
            return 0.3
        
        return 0.0
    
    def _calculate_engagement_score(self, metrics: List[AdoptionMetric]) -> float:
        """Calculate score based on engagement depth"""
        if not metrics:
            return 0.0
        
        # Calculate engagement metrics
        session_metrics = [m for m in metrics if m.metric_type == AdoptionMetricType.SESSION_DURATION]
        query_metrics = [m for m in metrics if m.metric_type == AdoptionMetricType.QUERY_EXECUTION]
        
        avg_session_time = sum(m.metric_value for m in session_metrics) / len(session_metrics) if session_metrics else 0
        total_queries = len(query_metrics)
        
        # Score based on engagement depth
        engagement_score = 0.0
        
        # Session time component (0-0.5)
        if avg_session_time >= 1800:  # 30 minutes
            engagement_score += 0.5
        elif avg_session_time >= 900:  # 15 minutes
            engagement_score += 0.3
        elif avg_session_time >= 300:  # 5 minutes
            engagement_score += 0.2
        
        # Query activity component (0-0.5)
        if total_queries >= 50:
            engagement_score += 0.5
        elif total_queries >= 20:
            engagement_score += 0.3
        elif total_queries >= 5:
            engagement_score += 0.2
        
        return min(engagement_score, 1.0)
    
    def _calculate_onboarding_score(self, user_profile: UserProfile) -> float:
        """Calculate score based on onboarding completion"""
        if user_profile.onboarding_progress is None:
            return 0.0
        
        return user_profile.onboarding_progress
    
    def _calculate_content_creation_score(self, user_profile: UserProfile) -> float:
        """Calculate score based on content creation"""
        creation_score = 0.0
        
        # Dashboard creation (0-0.4)
        if user_profile.total_dashboards >= 5:
            creation_score += 0.4
        elif user_profile.total_dashboards >= 2:
            creation_score += 0.3
        elif user_profile.total_dashboards >= 1:
            creation_score += 0.2
        
        # Alert creation (0-0.3)
        if user_profile.total_alerts >= 3:
            creation_score += 0.3
        elif user_profile.total_alerts >= 1:
            creation_score += 0.2
        
        # Export activity (0-0.3)
        if user_profile.total_exports >= 5:
            creation_score += 0.3
        elif user_profile.total_exports >= 1:
            creation_score += 0.1
        
        return min(creation_score, 1.0)
    
    def _calculate_recency_score(self, user_profile: UserProfile) -> float:
        """Calculate score based on activity recency"""
        if not user_profile.last_activity_at:
            return 0.0
        
        days_since_activity = (datetime.utcnow() - user_profile.last_activity_at).days
        
        if days_since_activity <= 1:
            return 1.0
        elif days_since_activity <= 7:
            return 0.8
        elif days_since_activity <= 30:
            return 0.5
        elif days_since_activity <= 90:
            return 0.2
        
        return 0.0
    
    def _determine_engagement_level(self, adoption_score: float, user_profile: UserProfile) -> str:
        """Determine engagement level based on adoption score and profile"""
        if adoption_score >= 0.8:
            return "expert"
        elif adoption_score >= 0.6:
            return "advanced"
        elif adoption_score >= 0.4:
            return "intermediate"
        elif adoption_score >= 0.2:
            return "beginner"
        else:
            return "new"
    
    def _calculate_feature_adoption_rate(self, metrics: List[AdoptionMetric]) -> float:
        """Calculate the rate of feature adoption"""
        if not metrics:
            return 0.0
        
        # Total available features (based on platform capabilities)
        total_features = 12  # Adjust based on your platform
        
        # Unique features used
        unique_features = set(metric.feature_name for metric in metrics if metric.feature_name)
        
        return len(unique_features) / total_features
    
    async def calculate_and_update_adoption_score(self, user_profile_id: uuid.UUID):
        """Calculate and update adoption score for a user"""
        score_data = await self.calculate_user_adoption_score(user_profile_id)
        
        # Update user profile
        await self.db.execute(
            update(UserProfile)
            .where(UserProfile.id == user_profile_id)
            .values(
                adoption_score=score_data["adoption_score"],
                engagement_level=score_data["engagement_level"]
            )
        )
        
        await self.db.commit()
        
        return score_data
    
    async def update_user_metrics(self, user_profile_id: uuid.UUID, metric_type: AdoptionMetricType):
        """Update user profile metrics based on new activity"""
        
        user_result = await self.db.execute(
            select(UserProfile).where(UserProfile.id == user_profile_id)
        )
        user_profile = user_result.scalar_one_or_none()
        
        if not user_profile:
            return
        
        # Update specific metrics based on type
        if metric_type == AdoptionMetricType.LOGIN:
            user_profile.total_logins += 1
        elif metric_type == AdoptionMetricType.QUERY_EXECUTION:
            user_profile.total_queries += 1
        elif metric_type == AdoptionMetricType.DASHBOARD_CREATE:
            user_profile.total_dashboards += 1
        elif metric_type == AdoptionMetricType.ALERT_CREATE:
            user_profile.total_alerts += 1
        elif metric_type in [AdoptionMetricType.EXPORT_PDF, AdoptionMetricType.EXPORT_CSV]:
            user_profile.total_exports += 1
        
        # Update last activity
        user_profile.last_activity_at = datetime.utcnow()
        
        await self.db.commit()
    
    async def calculate_cohort_analysis(self, period_months: int = 12) -> Dict[str, Any]:
        """Calculate cohort analysis for user retention"""
        
        # Get cohorts based on registration month
        cohorts = {}
        end_date = datetime.utcnow()
        
        for month_offset in range(period_months):
            cohort_start = end_date - timedelta(days=30 * (month_offset + 1))
            cohort_end = end_date - timedelta(days=30 * month_offset)
            
            # Get users registered in this cohort
            cohort_users_result = await self.db.execute(
                select(UserProfile)
                .where(
                    and_(
                        UserProfile.created_at >= cohort_start,
                        UserProfile.created_at < cohort_end
                    )
                )
            )
            cohort_users = cohort_users_result.scalars().all()
            
            if not cohort_users:
                continue
            
            cohort_key = cohort_start.strftime("%Y-%m")
            cohorts[cohort_key] = {
                "cohort_size": len(cohort_users),
                "retention_rates": []
            }
            
            # Calculate retention for each month after registration
            for retention_month in range(month_offset + 1):
                retention_start = cohort_end + timedelta(days=30 * retention_month)
                retention_end = cohort_end + timedelta(days=30 * (retention_month + 1))
                
                # Count active users in retention period
                active_users_result = await self.db.execute(
                    select(func.count(func.distinct(AdoptionMetric.user_profile_id)))
                    .where(
                        and_(
                            AdoptionMetric.user_profile_id.in_([u.id for u in cohort_users]),
                            AdoptionMetric.recorded_at >= retention_start,
                            AdoptionMetric.recorded_at < retention_end
                        )
                    )
                )
                active_count = active_users_result.scalar() or 0
                
                retention_rate = (active_count / len(cohort_users) * 100) if cohort_users else 0
                cohorts[cohort_key]["retention_rates"].append({
                    "month": retention_month,
                    "retention_rate": round(retention_rate, 2),
                    "active_users": active_count
                })
        
        return {
            "period_months": period_months,
            "cohorts": cohorts,
            "generated_at": datetime.utcnow()
        }