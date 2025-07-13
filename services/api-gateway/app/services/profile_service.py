"""
User profile management service
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from ..models.user import User
from ..models.conversation import Conversation
from ..models.query import Query
from ..models.dashboard import Dashboard
from ..models.alert import AlertRule
from ..models.profile import (
    UserProfileUpdate,
    UserPreferencesUpdate, 
    UserPreferencesResponse,
    NotificationPreferences,
    UIPreferences,
    QueryPreferences,
    SecurityPreferences,
    IntegrationPreferences,
    ActivitySummary,
    UserProfileExtended,
    UserSettings,
    UserOnboardingProgress,
    PreferenceTemplate
)
from ..core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    AuthorizationError,
    BusinessLogicError
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProfileService:
    """Service for managing user profiles and preferences"""
    
    def __init__(self):
        self.logger = logger
    
    async def get_user_profile(
        self, 
        db: AsyncSession, 
        user_id: UUID,
        include_activity: bool = True
    ) -> UserProfileExtended:
        """Get comprehensive user profile"""
        
        # Get user with relationships
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Build extended profile
        profile_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "display_name": user.display_name,
            "phone_number": user.get_preference("phone_number"),
            "department": user.get_preference("department"),
            "job_title": user.get_preference("job_title"),
            "bio": user.get_preference("bio"),
            "avatar_url": user.get_preference("avatar_url"),
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "roles": user.roles or [],
            "permissions": user.permissions or {},
            "timezone": user.timezone,
            "language": user.language,
            "last_login": user.last_login,
            "login_count": user.login_count,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
        # Add activity summary if requested
        if include_activity:
            activity = await self._get_user_activity_summary(db, user_id)
            profile_data["activity"] = activity
        else:
            profile_data["activity"] = ActivitySummary(
                total_queries=0, queries_this_week=0, queries_this_month=0,
                dashboards_created=0, dashboards_shared=0, alerts_created=0
            )
        
        return UserProfileExtended(**profile_data)
    
    async def update_user_profile(
        self,
        db: AsyncSession,
        user_id: UUID,
        profile_update: UserProfileUpdate,
        updated_by: UUID
    ) -> UserProfileExtended:
        """Update user profile information"""
        
        # Get user
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Check authorization (users can update their own profile)
        if user_id != updated_by:
            # Check if updater has admin permissions
            admin_query = select(User).where(User.id == updated_by)
            admin_result = await db.execute(admin_query)
            admin_user = admin_result.scalar_one_or_none()
            
            if not admin_user or not admin_user.has_permission("users:update"):
                raise AuthorizationError("Insufficient permissions to update this profile")
        
        # Update basic profile fields
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
            else:
                # Store in preferences for extended fields
                user.set_preference(field, value)
        
        user.updated_at = datetime.utcnow()
        
        try:
            await db.commit()
            await db.refresh(user)
            
            self.logger.info(
                "User profile updated",
                user_id=str(user_id),
                updated_by=str(updated_by),
                fields=list(update_data.keys())
            )
            
            return await self.get_user_profile(db, user_id)
            
        except Exception as e:
            await db.rollback()
            self.logger.error(
                "Failed to update user profile",
                user_id=str(user_id),
                error=str(e)
            )
            raise BusinessLogicError(f"Failed to update profile: {str(e)}")
    
    async def get_user_preferences(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> UserPreferencesResponse:
        """Get user preferences with defaults"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Extract preferences with defaults
        prefs = user.preferences or {}
        
        # Build structured preferences
        notifications = NotificationPreferences(**prefs.get("notifications", {}))
        ui = UIPreferences(**prefs.get("ui", {}))
        query_prefs = QueryPreferences(**prefs.get("query", {}))
        security = SecurityPreferences(**prefs.get("security", {}))
        integrations = IntegrationPreferences(**prefs.get("integrations", {}))
        
        return UserPreferencesResponse(
            notifications=notifications,
            ui=ui,
            query=query_prefs,
            security=security,
            integrations=integrations,
            last_updated=user.updated_at
        )
    
    async def update_user_preferences(
        self,
        db: AsyncSession,
        user_id: UUID,
        preferences_update: UserPreferencesUpdate,
        updated_by: UUID
    ) -> UserPreferencesResponse:
        """Update user preferences"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Check authorization
        if user_id != updated_by:
            admin_query = select(User).where(User.id == updated_by)
            admin_result = await db.execute(admin_query)
            admin_user = admin_result.scalar_one_or_none()
            
            if not admin_user or not admin_user.has_permission("users:update"):
                raise AuthorizationError("Insufficient permissions to update preferences")
        
        # Get current preferences
        current_prefs = user.preferences or {}
        
        # Update preferences by category
        update_data = preferences_update.dict(exclude_unset=True)
        
        for category, updates in update_data.items():
            if updates is not None:
                current_category = current_prefs.get(category, {})
                current_category.update(updates)
                current_prefs[category] = current_category
        
        user.preferences = current_prefs
        user.updated_at = datetime.utcnow()
        
        try:
            await db.commit()
            await db.refresh(user)
            
            self.logger.info(
                "User preferences updated",
                user_id=str(user_id),
                updated_by=str(updated_by),
                categories=list(update_data.keys())
            )
            
            return await self.get_user_preferences(db, user_id)
            
        except Exception as e:
            await db.rollback()
            self.logger.error(
                "Failed to update user preferences",
                user_id=str(user_id),
                error=str(e)
            )
            raise BusinessLogicError(f"Failed to update preferences: {str(e)}")
    
    async def get_user_settings(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> UserSettings:
        """Get complete user settings (profile + preferences)"""
        
        profile = await self.get_user_profile(db, user_id, include_activity=True)
        preferences = await self.get_user_preferences(db, user_id)
        
        return UserSettings(profile=profile, preferences=preferences)
    
    async def reset_preferences_to_defaults(
        self,
        db: AsyncSession,
        user_id: UUID,
        categories: Optional[List[str]] = None,
        reset_by: Optional[UUID] = None
    ) -> UserPreferencesResponse:
        """Reset user preferences to defaults"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Check authorization
        if reset_by and user_id != reset_by:
            admin_query = select(User).where(User.id == reset_by)
            admin_result = await db.execute(admin_query)
            admin_user = admin_result.scalar_one_or_none()
            
            if not admin_user or not admin_user.has_permission("users:update"):
                raise AuthorizationError("Insufficient permissions to reset preferences")
        
        current_prefs = user.preferences or {}
        
        # Default preferences
        default_categories = {
            "notifications": NotificationPreferences().dict(),
            "ui": UIPreferences().dict(),
            "query": QueryPreferences().dict(),
            "security": SecurityPreferences().dict(),
            "integrations": IntegrationPreferences().dict()
        }
        
        # Reset specified categories or all
        if categories:
            for category in categories:
                if category in default_categories:
                    current_prefs[category] = default_categories[category]
        else:
            current_prefs = default_categories
        
        user.preferences = current_prefs
        user.updated_at = datetime.utcnow()
        
        try:
            await db.commit()
            await db.refresh(user)
            
            self.logger.info(
                "User preferences reset to defaults",
                user_id=str(user_id),
                reset_by=str(reset_by) if reset_by else "self",
                categories=categories or "all"
            )
            
            return await self.get_user_preferences(db, user_id)
            
        except Exception as e:
            await db.rollback()
            self.logger.error(
                "Failed to reset user preferences",
                user_id=str(user_id),
                error=str(e)
            )
            raise BusinessLogicError(f"Failed to reset preferences: {str(e)}")
    
    async def get_onboarding_progress(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> UserOnboardingProgress:
        """Get user onboarding progress"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Check completion status
        profile_completed = bool(user.first_name and user.last_name)
        preferences_set = bool(user.preferences and len(user.preferences) > 0)
        
        # Check activity-based completion
        query_count = await db.scalar(
            select(func.count(Query.id)).where(Query.user_id == user_id)
        )
        dashboard_count = await db.scalar(
            select(func.count(Dashboard.id)).where(Dashboard.user_id == user_id)
        )
        alert_count = await db.scalar(
            select(func.count(AlertRule.id)).where(AlertRule.user_id == user_id)
        )
        
        first_query_executed = query_count > 0
        first_dashboard_created = dashboard_count > 0
        first_alert_created = alert_count > 0
        
        # Get from preferences
        tour_completed = user.get_preference("onboarding.tour_completed", False)
        training_completed = user.get_preference("onboarding.training_completed", False)
        
        # Calculate completion percentage
        steps = [
            profile_completed,
            preferences_set,
            first_query_executed,
            first_dashboard_created,
            first_alert_created,
            tour_completed,
            training_completed
        ]
        
        completed_steps = sum(steps)
        completion_percentage = (completed_steps / len(steps)) * 100
        
        completed_at = None
        if completion_percentage == 100:
            completed_at = user.get_preference("onboarding.completed_at")
            if completed_at and isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)
        
        return UserOnboardingProgress(
            user_id=user_id,
            profile_completed=profile_completed,
            preferences_set=preferences_set,
            first_query_executed=first_query_executed,
            first_dashboard_created=first_dashboard_created,
            first_alert_created=first_alert_created,
            tour_completed=tour_completed,
            training_completed=training_completed,
            completion_percentage=completion_percentage,
            last_step_completed=user.get_preference("onboarding.last_step"),
            completed_at=completed_at
        )
    
    async def update_onboarding_progress(
        self,
        db: AsyncSession,
        user_id: UUID,
        step: str,
        completed: bool = True
    ) -> UserOnboardingProgress:
        """Update onboarding progress for a specific step"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Update onboarding preferences
        user.set_preference(f"onboarding.{step}", completed)
        if completed:
            user.set_preference("onboarding.last_step", step)
            user.set_preference("onboarding.last_updated", datetime.utcnow().isoformat())
        
        # Check if onboarding is complete
        progress = await self.get_onboarding_progress(db, user_id)
        if progress.completion_percentage == 100 and not progress.completed_at:
            user.set_preference("onboarding.completed_at", datetime.utcnow().isoformat())
        
        user.updated_at = datetime.utcnow()
        
        try:
            await db.commit()
            await db.refresh(user)
            
            self.logger.info(
                "Onboarding progress updated",
                user_id=str(user_id),
                step=step,
                completed=completed
            )
            
            return await self.get_onboarding_progress(db, user_id)
            
        except Exception as e:
            await db.rollback()
            self.logger.error(
                "Failed to update onboarding progress",
                user_id=str(user_id),
                error=str(e)
            )
            raise BusinessLogicError(f"Failed to update onboarding progress: {str(e)}")
    
    async def _get_user_activity_summary(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> ActivitySummary:
        """Get user activity summary"""
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Query counts
        total_queries = await db.scalar(
            select(func.count(Query.id)).where(Query.user_id == user_id)
        )
        
        queries_this_week = await db.scalar(
            select(func.count(Query.id)).where(
                and_(
                    Query.user_id == user_id,
                    Query.created_at >= week_ago
                )
            )
        )
        
        queries_this_month = await db.scalar(
            select(func.count(Query.id)).where(
                and_(
                    Query.user_id == user_id,
                    Query.created_at >= month_ago
                )
            )
        )
        
        dashboards_created = await db.scalar(
            select(func.count(Dashboard.id)).where(Dashboard.user_id == user_id)
        )
        
        alerts_created = await db.scalar(
            select(func.count(AlertRule.id)).where(AlertRule.user_id == user_id)
        )
        
        # Last query time
        last_query_result = await db.execute(
            select(Query.created_at)
            .where(Query.user_id == user_id)
            .order_by(desc(Query.created_at))
            .limit(1)
        )
        last_query_time = last_query_result.scalar_one_or_none()
        
        # Get dashboard shares (simplified - would need a shares table in real implementation)
        dashboards_shared = 0  # Placeholder
        
        # Get most used indexes and chart types (simplified)
        most_used_indexes = []  # Would aggregate from query metadata
        favorite_chart_types = []  # Would aggregate from dashboard metadata
        
        return ActivitySummary(
            total_queries=total_queries or 0,
            queries_this_week=queries_this_week or 0,
            queries_this_month=queries_this_month or 0,
            dashboards_created=dashboards_created or 0,
            dashboards_shared=dashboards_shared,
            alerts_created=alerts_created or 0,
            last_query_time=last_query_time,
            most_used_indexes=most_used_indexes,
            favorite_chart_types=favorite_chart_types
        )
    
    async def export_user_data(
        self,
        db: AsyncSession,
        user_id: UUID,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export all user data for privacy compliance"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError("user", str(user_id))
        
        # Get all user data
        profile = await self.get_user_profile(db, user_id)
        preferences = await self.get_user_preferences(db, user_id)
        onboarding = await self.get_onboarding_progress(db, user_id)
        
        # Get related data (simplified - would include all related records)
        queries = await db.execute(
            select(Query).where(Query.user_id == user_id).limit(1000)
        )
        dashboards = await db.execute(
            select(Dashboard).where(Dashboard.user_id == user_id).limit(100)
        )
        
        export_data = {
            "export_info": {
                "user_id": str(user_id),
                "export_date": datetime.utcnow().isoformat(),
                "format": format
            },
            "profile": profile.dict(),
            "preferences": preferences.dict(),
            "onboarding": onboarding.dict(),
            "queries": [query.to_dict() for query in queries.scalars()],
            "dashboards": [dashboard.to_dict() for dashboard in dashboards.scalars()]
        }
        
        self.logger.info(
            "User data exported",
            user_id=str(user_id),
            format=format
        )
        
        return export_data