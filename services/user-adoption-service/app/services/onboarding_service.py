#!/usr/bin/env python3
"""
Onboarding Service
==================
Service for managing user onboarding process and progress tracking
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import selectinload

from app.models.adoption_models import (
    UserProfile, OnboardingStep, OnboardingStatus
)

class OnboardingService:
    """Service for managing user onboarding"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Define standard onboarding steps
        self.standard_steps = [
            {
                "step_id": "welcome_tour",
                "step_name": "Welcome Tour",
                "step_order": 1,
                "description": "Complete the platform welcome tour"
            },
            {
                "step_id": "first_query",
                "step_name": "First Query",
                "step_order": 2,
                "description": "Execute your first natural language query"
            },
            {
                "step_id": "create_dashboard",
                "step_name": "Create Dashboard",
                "step_order": 3,
                "description": "Create your first dashboard"
            },
            {
                "step_id": "explore_visualizations",
                "step_name": "Explore Visualizations", 
                "step_order": 4,
                "description": "Explore different visualization types"
            },
            {
                "step_id": "setup_alert",
                "step_name": "Setup Alert",
                "step_order": 5,
                "description": "Create your first alert"
            },
            {
                "step_id": "export_report",
                "step_name": "Export Report",
                "step_order": 6,
                "description": "Export data in different formats"
            },
            {
                "step_id": "share_content",
                "step_name": "Share Content",
                "step_order": 7,
                "description": "Share a dashboard or report with colleagues"
            },
            {
                "step_id": "complete_profile",
                "step_name": "Complete Profile",
                "step_order": 8,
                "description": "Complete your user profile and preferences"
            }
        ]
    
    async def initialize_onboarding_steps(self, user_profile_id: uuid.UUID) -> List[OnboardingStep]:
        """Initialize onboarding steps for a new user"""
        
        steps = []
        for step_config in self.standard_steps:
            step = OnboardingStep(
                user_profile_id=user_profile_id,
                step_id=step_config["step_id"],
                step_name=step_config["step_name"],
                step_order=step_config["step_order"],
                status=OnboardingStatus.NOT_STARTED
            )
            steps.append(step)
            self.db.add(step)
        
        await self.db.commit()
        
        return steps
    
    async def update_onboarding_progress(self, user_profile_id: uuid.UUID) -> float:
        """Update overall onboarding progress for a user"""
        
        # Get all onboarding steps for the user
        result = await self.db.execute(
            select(OnboardingStep)
            .where(OnboardingStep.user_profile_id == user_profile_id)
        )
        steps = result.scalars().all()
        
        if not steps:
            return 0.0
        
        # Calculate progress
        total_steps = len(steps)
        completed_steps = len([s for s in steps if s.status == OnboardingStatus.COMPLETED])
        skipped_steps = len([s for s in steps if s.status == OnboardingStatus.SKIPPED])
        
        # Count skipped steps as partially completed for progress calculation
        progress = (completed_steps + (skipped_steps * 0.5)) / total_steps
        
        # Update user profile
        await self.db.execute(
            update(UserProfile)
            .where(UserProfile.id == user_profile_id)
            .values(
                onboarding_progress=progress,
                onboarding_status=self._determine_onboarding_status(steps),
                onboarding_completed_at=datetime.utcnow() if progress >= 0.8 else None
            )
        )
        
        await self.db.commit()
        
        return progress
    
    def _determine_onboarding_status(self, steps: List[OnboardingStep]) -> OnboardingStatus:
        """Determine overall onboarding status based on individual steps"""
        
        if not steps:
            return OnboardingStatus.NOT_STARTED
        
        completed_steps = len([s for s in steps if s.status == OnboardingStatus.COMPLETED])
        skipped_steps = len([s for s in steps if s.status == OnboardingStatus.SKIPPED])
        in_progress_steps = len([s for s in steps if s.status == OnboardingStatus.IN_PROGRESS])
        total_steps = len(steps)
        
        # Check for completion (80% threshold)
        completion_rate = (completed_steps + skipped_steps) / total_steps
        if completion_rate >= 0.8:
            return OnboardingStatus.COMPLETED
        
        # Check for abandonment (no activity in last 30 days)
        if in_progress_steps == 0 and completed_steps < total_steps * 0.3:
            # Check if any step was started more than 30 days ago
            for step in steps:
                if (step.started_at and 
                    datetime.utcnow() - step.started_at > timedelta(days=30)):
                    return OnboardingStatus.ABANDONED
        
        # Check if any step is in progress
        if in_progress_steps > 0 or completed_steps > 0:
            return OnboardingStatus.IN_PROGRESS
        
        return OnboardingStatus.NOT_STARTED
    
    async def get_user_onboarding_summary(self, user_profile_id: uuid.UUID) -> Dict[str, Any]:
        """Get comprehensive onboarding summary for a user"""
        
        # Get user profile with steps
        result = await self.db.execute(
            select(UserProfile)
            .where(UserProfile.id == user_profile_id)
            .options(selectinload(UserProfile.onboarding_steps))
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            return {}
        
        steps = user_profile.onboarding_steps
        
        # Calculate metrics
        total_steps = len(steps)
        completed_steps = len([s for s in steps if s.status == OnboardingStatus.COMPLETED])
        in_progress_steps = len([s for s in steps if s.status == OnboardingStatus.IN_PROGRESS])
        skipped_steps = len([s for s in steps if s.status == OnboardingStatus.SKIPPED])
        
        # Calculate completion times
        completion_times = [s.completion_time_seconds for s in steps if s.completion_time_seconds]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Find next recommended step
        next_step = None
        for step in sorted(steps, key=lambda x: x.step_order):
            if step.status == OnboardingStatus.NOT_STARTED:
                next_step = {
                    "step_id": step.step_id,
                    "step_name": step.step_name,
                    "step_order": step.step_order
                }
                break
        
        return {
            "user_profile_id": user_profile_id,
            "onboarding_status": user_profile.onboarding_status,
            "progress_percentage": round(user_profile.onboarding_progress * 100, 1),
            "started_at": user_profile.onboarding_started_at,
            "completed_at": user_profile.onboarding_completed_at,
            "steps_summary": {
                "total": total_steps,
                "completed": completed_steps,
                "in_progress": in_progress_steps,
                "skipped": skipped_steps,
                "remaining": total_steps - completed_steps - skipped_steps
            },
            "time_metrics": {
                "average_step_completion_time": avg_completion_time,
                "total_completion_times": completion_times
            },
            "next_recommended_step": next_step,
            "engagement_indicators": {
                "help_accessed_count": len([s for s in steps if s.help_accessed]),
                "total_attempts": sum(s.attempts for s in steps),
                "steps_with_multiple_attempts": len([s for s in steps if s.attempts > 1])
            }
        }
    
    async def get_onboarding_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get onboarding analytics across all users"""
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get user profiles in date range
        profiles_result = await self.db.execute(
            select(UserProfile)
            .where(UserProfile.created_at >= start_date)
            .options(selectinload(UserProfile.onboarding_steps))
        )
        profiles = profiles_result.scalars().all()
        
        if not profiles:
            return {
                "period": {"start_date": start_date, "end_date": end_date, "days": days},
                "total_users": 0,
                "metrics": {}
            }
        
        # Calculate overall metrics
        total_users = len(profiles)
        completed_count = len([p for p in profiles if p.onboarding_status == OnboardingStatus.COMPLETED])
        in_progress_count = len([p for p in profiles if p.onboarding_status == OnboardingStatus.IN_PROGRESS])
        skipped_count = len([p for p in profiles if p.onboarding_status == OnboardingStatus.SKIPPED])
        abandoned_count = len([p for p in profiles if p.onboarding_status == OnboardingStatus.ABANDONED])
        
        # Calculate average progress
        avg_progress = sum(p.onboarding_progress for p in profiles) / total_users
        
        # Calculate completion times for completed users
        completion_times = []
        for profile in profiles:
            if profile.onboarding_completed_at and profile.onboarding_started_at:
                completion_time = (profile.onboarding_completed_at - profile.onboarding_started_at).total_seconds()
                completion_times.append(completion_time)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Analyze step-by-step performance
        step_analytics = {}
        for profile in profiles:
            for step in profile.onboarding_steps:
                if step.step_id not in step_analytics:
                    step_analytics[step.step_id] = {
                        "step_name": step.step_name,
                        "step_order": step.step_order,
                        "total_users": 0,
                        "completed": 0,
                        "in_progress": 0,
                        "skipped": 0,
                        "not_started": 0,
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
                else:
                    analytics["not_started"] += 1
                
                if step.help_accessed:
                    analytics["help_accessed"] += 1
        
        # Calculate derived metrics for each step
        for step_id, analytics in step_analytics.items():
            total = analytics["total_users"]
            analytics["completion_rate"] = (analytics["completed"] / total * 100) if total > 0 else 0
            analytics["dropout_rate"] = ((analytics["not_started"] + analytics["skipped"]) / total * 100) if total > 0 else 0
            analytics["avg_completion_time"] = (sum(analytics["completion_times"]) / len(analytics["completion_times"])) if analytics["completion_times"] else 0
            analytics["help_usage_rate"] = (analytics["help_accessed"] / total * 100) if total > 0 else 0
            analytics["avg_attempts"] = analytics["total_attempts"] / total if total > 0 else 0
            
            # Remove raw data
            del analytics["completion_times"]
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "overview": {
                "total_users": total_users,
                "completion_rate": round(completed_count / total_users * 100, 2),
                "average_progress": round(avg_progress * 100, 2),
                "average_completion_time_hours": round(avg_completion_time / 3600, 2)
            },
            "status_distribution": {
                "completed": completed_count,
                "in_progress": in_progress_count,
                "skipped": skipped_count,
                "abandoned": abandoned_count,
                "not_started": total_users - completed_count - in_progress_count - skipped_count - abandoned_count
            },
            "step_analytics": step_analytics
        }
    
    async def identify_onboarding_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify steps where users commonly get stuck"""
        
        # Get all onboarding steps
        result = await self.db.execute(
            select(OnboardingStep)
            .options(selectinload(OnboardingStep.user_profile))
        )
        all_steps = result.scalars().all()
        
        # Group by step_id
        step_groups = {}
        for step in all_steps:
            if step.step_id not in step_groups:
                step_groups[step.step_id] = []
            step_groups[step.step_id].append(step)
        
        bottlenecks = []
        for step_id, steps in step_groups.items():
            total_users = len(steps)
            completed = len([s for s in steps if s.status == OnboardingStatus.COMPLETED])
            in_progress = len([s for s in steps if s.status == OnboardingStatus.IN_PROGRESS])
            abandoned = len([s for s in steps if s.status == OnboardingStatus.ABANDONED])
            
            # Calculate metrics that indicate bottlenecks
            completion_rate = completed / total_users if total_users > 0 else 0
            abandonment_rate = abandoned / total_users if total_users > 0 else 0
            avg_attempts = sum(s.attempts for s in steps) / total_users if total_users > 0 else 0
            help_usage_rate = len([s for s in steps if s.help_accessed]) / total_users if total_users > 0 else 0
            
            # Identify as bottleneck if:
            # - Low completion rate (< 70%)
            # - High abandonment rate (> 20%)
            # - High average attempts (> 2)
            # - High help usage (> 50%)
            bottleneck_score = 0
            bottleneck_indicators = []
            
            if completion_rate < 0.7:
                bottleneck_score += 30
                bottleneck_indicators.append("Low completion rate")
            
            if abandonment_rate > 0.2:
                bottleneck_score += 25
                bottleneck_indicators.append("High abandonment rate")
            
            if avg_attempts > 2:
                bottleneck_score += 20
                bottleneck_indicators.append("Multiple attempts required")
            
            if help_usage_rate > 0.5:
                bottleneck_score += 15
                bottleneck_indicators.append("High help usage")
            
            if in_progress / total_users > 0.3:
                bottleneck_score += 10
                bottleneck_indicators.append("Many users stuck in progress")
            
            if bottleneck_score >= 25:  # Threshold for identifying bottlenecks
                bottlenecks.append({
                    "step_id": step_id,
                    "step_name": steps[0].step_name if steps else step_id,
                    "step_order": steps[0].step_order if steps else 0,
                    "bottleneck_score": bottleneck_score,
                    "indicators": bottleneck_indicators,
                    "metrics": {
                        "total_users": total_users,
                        "completion_rate": round(completion_rate * 100, 2),
                        "abandonment_rate": round(abandonment_rate * 100, 2),
                        "avg_attempts": round(avg_attempts, 2),
                        "help_usage_rate": round(help_usage_rate * 100, 2),
                        "users_in_progress": in_progress
                    }
                })
        
        # Sort by bottleneck score (highest first)
        bottlenecks.sort(key=lambda x: x["bottleneck_score"], reverse=True)
        
        return bottlenecks
    
    async def get_personalized_onboarding_recommendations(self, user_profile_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get personalized recommendations for improving onboarding experience"""
        
        summary = await self.get_user_onboarding_summary(user_profile_id)
        
        if not summary:
            return []
        
        recommendations = []
        
        # Check for stalled progress
        if (summary["onboarding_status"] == OnboardingStatus.IN_PROGRESS and
            summary["steps_summary"]["in_progress"] > 0):
            recommendations.append({
                "type": "resume_progress",
                "priority": "high",
                "title": "Resume Your Onboarding",
                "description": "You have onboarding steps in progress. Complete them to unlock more features.",
                "action": "Continue onboarding",
                "next_step": summary["next_recommended_step"]
            })
        
        # Check for high help usage
        if summary["engagement_indicators"]["help_accessed_count"] > 3:
            recommendations.append({
                "type": "additional_training",
                "priority": "medium",
                "title": "Consider Additional Training",
                "description": "You've accessed help frequently. Additional training might be beneficial.",
                "action": "View training resources",
                "resources": ["video_tutorials", "documentation", "live_training"]
            })
        
        # Check for multiple attempts on steps
        if summary["engagement_indicators"]["steps_with_multiple_attempts"] > 2:
            recommendations.append({
                "type": "simplify_approach",
                "priority": "medium",
                "title": "Try a Simpler Approach",
                "description": "Some steps seem challenging. Consider starting with basic features.",
                "action": "Access beginner tutorials",
                "suggested_path": "basic_features_first"
            })
        
        # Check for low progress after significant time
        if (summary["started_at"] and
            datetime.utcnow() - summary["started_at"] > timedelta(days=7) and
            summary["progress_percentage"] < 50):
            recommendations.append({
                "type": "guided_session",
                "priority": "high",
                "title": "Schedule Guided Session",
                "description": "Your progress has slowed. A guided session might help.",
                "action": "Book session with expert",
                "contact_info": "training@company.com"
            })
        
        return recommendations