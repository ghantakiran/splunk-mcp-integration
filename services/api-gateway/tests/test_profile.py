"""
Comprehensive tests for user profile management system
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.profile import (
    UserProfileUpdate,
    UserPreferencesUpdate,
    NotificationPreferences,
    UIPreferences,
    QueryPreferences,
    SecurityPreferences,
    IntegrationPreferences,
    UserOnboardingProgress
)
from app.services.profile_service import ProfileService
from app.core.exceptions import ResourceNotFoundError, AuthorizationError, ValidationError


class TestProfileService:
    """Test ProfileService business logic"""
    
    @pytest.fixture
    def profile_service(self):
        return ProfileService()
    
    @pytest.fixture
    def mock_user(self):
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_verified=True,
            timezone="UTC",
            language="en",
            preferences={
                "notifications": {"email_notifications": True},
                "ui": {"theme": "dark"}
            },
            roles=["user"],
            permissions={}
        )
        return user
    
    @pytest.fixture
    def mock_admin_user(self):
        user = User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True,
            is_superuser=True,
            roles=["admin"],
            permissions={"users:update": True, "users:read": True}
        )
        return user
    
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, profile_service, mock_user):
        """Test successful user profile retrieval"""
        
        with patch('app.services.profile_service.select') as mock_select:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            # Mock activity summary
            mock_db.scalar.return_value = 5  # Mock query counts
            
            profile = await profile_service.get_user_profile(
                db=mock_db,
                user_id=mock_user.id,
                include_activity=True
            )
            
            assert profile.id == mock_user.id
            assert profile.username == mock_user.username
            assert profile.email == mock_user.email
            assert profile.full_name == "Test User"
            assert profile.activity is not None
    
    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, profile_service):
        """Test user profile retrieval with non-existent user"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            user_id = uuid4()
            
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await profile_service.get_user_profile(
                    db=mock_db,
                    user_id=user_id
                )
            
            assert "user" in str(exc_info.value)
            assert str(user_id) in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, profile_service, mock_user):
        """Test successful user profile update"""
        
        with patch('app.services.profile_service.select') as mock_select:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            profile_update = UserProfileUpdate(
                first_name="Updated",
                last_name="Name",
                timezone="US/Pacific",
                phone_number="+1234567890"
            )
            
            # Mock the get_user_profile call at the end
            with patch.object(profile_service, 'get_user_profile') as mock_get_profile:
                mock_get_profile.return_value = AsyncMock()
                
                result = await profile_service.update_user_profile(
                    db=mock_db,
                    user_id=mock_user.id,
                    profile_update=profile_update,
                    updated_by=mock_user.id
                )
                
                assert mock_db.commit.called
                assert mock_db.refresh.called
                mock_get_profile.assert_called_once_with(mock_db, mock_user.id)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_unauthorized(self, profile_service, mock_user):
        """Test unauthorized user profile update"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            other_user_id = uuid4()
            profile_update = UserProfileUpdate(first_name="Hacker")
            
            with pytest.raises(AuthorizationError):
                await profile_service.update_user_profile(
                    db=mock_db,
                    user_id=mock_user.id,
                    profile_update=profile_update,
                    updated_by=other_user_id
                )
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_success(self, profile_service, mock_user):
        """Test successful user preferences retrieval"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            preferences = await profile_service.get_user_preferences(
                db=mock_db,
                user_id=mock_user.id
            )
            
            assert preferences.notifications.email_notifications == True
            assert preferences.ui.theme == "dark"
            assert preferences.last_updated == mock_user.updated_at
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, profile_service, mock_user):
        """Test successful user preferences update"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            preferences_update = UserPreferencesUpdate(
                notifications=NotificationPreferences(
                    email_notifications=False,
                    slack_notifications=True
                ),
                ui=UIPreferences(
                    theme="light",
                    density="compact"
                )
            )
            
            with patch.object(profile_service, 'get_user_preferences') as mock_get_prefs:
                mock_get_prefs.return_value = AsyncMock()
                
                result = await profile_service.update_user_preferences(
                    db=mock_db,
                    user_id=mock_user.id,
                    preferences_update=preferences_update,
                    updated_by=mock_user.id
                )
                
                assert mock_db.commit.called
                assert mock_db.refresh.called
                mock_get_prefs.assert_called_once_with(mock_db, mock_user.id)
    
    @pytest.mark.asyncio
    async def test_reset_preferences_to_defaults(self, profile_service, mock_user):
        """Test resetting preferences to defaults"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            with patch.object(profile_service, 'get_user_preferences') as mock_get_prefs:
                mock_get_prefs.return_value = AsyncMock()
                
                result = await profile_service.reset_preferences_to_defaults(
                    db=mock_db,
                    user_id=mock_user.id,
                    categories=["ui", "notifications"],
                    reset_by=mock_user.id
                )
                
                assert mock_db.commit.called
                assert mock_db.refresh.called
    
    @pytest.mark.asyncio
    async def test_get_onboarding_progress(self, profile_service, mock_user):
        """Test getting onboarding progress"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            # Mock query counts
            mock_db.scalar.return_value = 2
            
            progress = await profile_service.get_onboarding_progress(
                db=mock_db,
                user_id=mock_user.id
            )
            
            assert isinstance(progress, UserOnboardingProgress)
            assert progress.user_id == mock_user.id
            assert progress.profile_completed == True  # has first and last name
            assert progress.completion_percentage >= 0
            assert progress.completion_percentage <= 100
    
    @pytest.mark.asyncio
    async def test_update_onboarding_progress(self, profile_service, mock_user):
        """Test updating onboarding progress"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            with patch.object(profile_service, 'get_onboarding_progress') as mock_get_progress:
                mock_progress = UserOnboardingProgress(
                    user_id=mock_user.id,
                    tour_completed=True,
                    completion_percentage=85.7
                )
                mock_get_progress.return_value = mock_progress
                
                result = await profile_service.update_onboarding_progress(
                    db=mock_db,
                    user_id=mock_user.id,
                    step="tour_completed",
                    completed=True
                )
                
                assert mock_db.commit.called
                assert result.tour_completed == True
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, profile_service, mock_user):
        """Test exporting user data"""
        
        with patch('app.services.profile_service.select'):
            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            # Mock related data queries
            mock_queries_result = AsyncMock()
            mock_queries_result.scalars.return_value = []
            mock_dashboards_result = AsyncMock()
            mock_dashboards_result.scalars.return_value = []
            
            mock_db.execute.side_effect = [
                mock_result,  # user query
                mock_queries_result,  # queries
                mock_dashboards_result  # dashboards
            ]
            
            with patch.object(profile_service, 'get_user_profile') as mock_get_profile, \
                 patch.object(profile_service, 'get_user_preferences') as mock_get_prefs, \
                 patch.object(profile_service, 'get_onboarding_progress') as mock_get_progress:
                
                mock_get_profile.return_value = AsyncMock()
                mock_get_prefs.return_value = AsyncMock()
                mock_get_progress.return_value = AsyncMock()
                
                export_data = await profile_service.export_user_data(
                    db=mock_db,
                    user_id=mock_user.id,
                    format="json"
                )
                
                assert "export_info" in export_data
                assert "profile" in export_data
                assert "preferences" in export_data
                assert "onboarding" in export_data
                assert export_data["export_info"]["user_id"] == str(mock_user.id)
                assert export_data["export_info"]["format"] == "json"


class TestProfileEndpoints:
    """Test profile API endpoints"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        # Mock JWT token for testing
        return {"Authorization": "Bearer test_token"}
    
    def test_get_my_profile_success(self, client, auth_headers):
        """Test GET /profile/me endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.get_user_profile') as mock_get_profile:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_profile = AsyncMock()
            mock_profile.dict.return_value = {
                "id": str(mock_user.id),
                "username": "testuser",
                "email": "test@example.com"
            }
            mock_get_profile.return_value = mock_profile
            
            response = client.get("/api/v1/profile/me", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            mock_get_profile.assert_called_once()
    
    def test_update_my_profile_success(self, client, auth_headers):
        """Test PUT /profile/me endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.update_user_profile') as mock_update_profile:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_updated_profile = AsyncMock()
            mock_updated_profile.dict.return_value = {
                "id": str(mock_user.id),
                "first_name": "Updated"
            }
            mock_update_profile.return_value = mock_updated_profile
            
            update_data = {
                "first_name": "Updated",
                "timezone": "US/Pacific"
            }
            
            response = client.put("/api/v1/profile/me", json=update_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            mock_update_profile.assert_called_once()
    
    def test_get_my_preferences_success(self, client, auth_headers):
        """Test GET /profile/me/preferences endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.get_user_preferences') as mock_get_prefs:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_preferences = AsyncMock()
            mock_preferences.dict.return_value = {
                "notifications": {"email_notifications": True},
                "ui": {"theme": "dark"}
            }
            mock_get_prefs.return_value = mock_preferences
            
            response = client.get("/api/v1/profile/me/preferences", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            mock_get_prefs.assert_called_once()
    
    def test_update_my_preferences_success(self, client, auth_headers):
        """Test PUT /profile/me/preferences endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.update_user_preferences') as mock_update_prefs:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_updated_prefs = AsyncMock()
            mock_updated_prefs.dict.return_value = {
                "notifications": {"email_notifications": False}
            }
            mock_update_prefs.return_value = mock_updated_prefs
            
            update_data = {
                "notifications": {
                    "email_notifications": False,
                    "slack_notifications": True
                }
            }
            
            response = client.put("/api/v1/profile/me/preferences", json=update_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            mock_update_prefs.assert_called_once()
    
    def test_reset_my_preferences_success(self, client, auth_headers):
        """Test POST /profile/me/preferences/reset endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.reset_preferences_to_defaults') as mock_reset:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_reset_prefs = AsyncMock()
            mock_reset_prefs.dict.return_value = {"notifications": {}, "ui": {}}
            mock_reset.return_value = mock_reset_prefs
            
            response = client.post(
                "/api/v1/profile/me/preferences/reset?categories=ui&categories=notifications",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_reset.assert_called_once()
    
    def test_get_my_onboarding_progress(self, client, auth_headers):
        """Test GET /profile/me/onboarding endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.get_onboarding_progress') as mock_get_progress:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_progress = AsyncMock()
            mock_progress.dict.return_value = {
                "user_id": str(mock_user.id),
                "completion_percentage": 75.0
            }
            mock_get_progress.return_value = mock_progress
            
            response = client.get("/api/v1/profile/me/onboarding", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            mock_get_progress.assert_called_once()
    
    def test_update_onboarding_step_success(self, client, auth_headers):
        """Test POST /profile/me/onboarding/{step} endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.update_onboarding_progress') as mock_update:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_updated_progress = AsyncMock()
            mock_updated_progress.dict.return_value = {
                "user_id": str(mock_user.id),
                "tour_completed": True
            }
            mock_update.return_value = mock_updated_progress
            
            response = client.post(
                "/api/v1/profile/me/onboarding/tour_completed?completed=true",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_update.assert_called_once()
    
    def test_update_onboarding_step_invalid_step(self, client, auth_headers):
        """Test POST /profile/me/onboarding/{step} with invalid step"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            response = client.post(
                "/api/v1/profile/me/onboarding/invalid_step",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_export_my_data_success(self, client, auth_headers):
        """Test GET /profile/me/export endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_async_session') as mock_get_db, \
             patch('app.services.profile_service.ProfileService.export_user_data') as mock_export:
            
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_get_user.return_value = mock_user
            
            mock_export_data = {
                "export_info": {"user_id": str(mock_user.id)},
                "profile": {},
                "preferences": {}
            }
            mock_export.return_value = mock_export_data
            
            response = client.get("/api/v1/profile/me/export?format=json", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert "Content-Disposition" in response.headers
            mock_export.assert_called_once()


class TestSettingsEndpoints:
    """Test settings API endpoints"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test_token"}
    
    def test_get_available_themes(self, client, auth_headers):
        """Test GET /settings/themes endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_user.get_preference.return_value = "dark"
            mock_get_user.return_value = mock_user
            
            response = client.get("/api/v1/settings/themes", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "themes" in data
            assert "light" in data["themes"]
            assert "dark" in data["themes"]
            assert "auto" in data["themes"]
            assert data["current_theme"] == "dark"
    
    def test_get_available_chart_types(self, client, auth_headers):
        """Test GET /settings/chart-types endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_user.get_preference.return_value = "line"
            mock_get_user.return_value = mock_user
            
            response = client.get("/api/v1/settings/chart-types", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "chart_types" in data
            assert "line" in data["chart_types"]
            assert "bar" in data["chart_types"]
            assert "recommendations" in data
    
    def test_get_default_settings(self, client, auth_headers):
        """Test GET /settings/defaults endpoint"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_user.has_role.return_value = False
            mock_user.roles = ["user"]
            mock_get_user.return_value = mock_user
            
            response = client.get("/api/v1/settings/defaults", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "defaults" in data
            assert "notifications" in data["defaults"]
            assert "ui" in data["defaults"]
            assert "query" in data["defaults"]
            assert "security" in data["defaults"]
            assert "integrations" in data["defaults"]
    
    def test_validate_settings_valid(self, client, auth_headers):
        """Test POST /settings/validate with valid settings"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_get_user.return_value = mock_user
            
            valid_settings = {
                "notifications": {
                    "email_notifications": True,
                    "slack_notifications": False
                },
                "ui": {
                    "theme": "dark",
                    "density": "compact"
                }
            }
            
            response = client.post(
                "/api/v1/settings/validate",
                json=valid_settings,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] == True
            assert len(data["errors"]) == 0
    
    def test_validate_settings_invalid(self, client, auth_headers):
        """Test POST /settings/validate with invalid settings"""
        
        with patch('app.api.deps.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_get_user.return_value = mock_user
            
            invalid_settings = {
                "ui": {
                    "theme": "invalid_theme",  # Invalid theme
                    "panels_per_row": 10  # Exceeds maximum
                }
            }
            
            response = client.post(
                "/api/v1/settings/validate",
                json=invalid_settings,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] == False
            assert len(data["errors"]) > 0


class TestProfileModels:
    """Test profile data models"""
    
    def test_notification_preferences_defaults(self):
        """Test NotificationPreferences with default values"""
        prefs = NotificationPreferences()
        
        assert prefs.email_notifications == True
        assert prefs.slack_notifications == False
        assert prefs.query_completion == True
        assert prefs.quiet_hours_enabled == False
    
    def test_ui_preferences_validation(self):
        """Test UIPreferences validation"""
        # Valid preferences
        prefs = UIPreferences(
            theme="dark",
            density="compact",
            panels_per_row=4
        )
        assert prefs.theme == "dark"
        assert prefs.panels_per_row == 4
        
        # Invalid panels_per_row
        with pytest.raises(ValidationError):
            UIPreferences(panels_per_row=10)  # Exceeds maximum
    
    def test_user_profile_update_validation(self):
        """Test UserProfileUpdate validation"""
        # Valid timezone
        update = UserProfileUpdate(
            first_name="Test",
            timezone="US/Pacific",
            language="en"
        )
        assert update.timezone == "US/Pacific"
        
        # Invalid timezone
        with pytest.raises(ValidationError):
            UserProfileUpdate(timezone="Invalid/Timezone")
        
        # Invalid language
        with pytest.raises(ValidationError):
            UserProfileUpdate(language="invalid")
    
    def test_query_preferences_validation(self):
        """Test QueryPreferences validation"""
        # Valid preferences
        prefs = QueryPreferences(
            max_results=5000,
            query_timeout=600
        )
        assert prefs.max_results == 5000
        
        # Invalid max_results (too high)
        with pytest.raises(ValidationError):
            QueryPreferences(max_results=20000)
        
        # Invalid query_timeout (too low)
        with pytest.raises(ValidationError):
            QueryPreferences(query_timeout=10)


# Integration test fixtures and utilities
@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "preferences": {
            "notifications": {
                "email_notifications": True,
                "slack_notifications": False
            },
            "ui": {
                "theme": "dark",
                "density": "compact"
            }
        }
    }


@pytest.fixture
def sample_preferences_update():
    """Sample preferences update data"""
    return {
        "notifications": {
            "email_notifications": False,
            "push_notifications": True,
            "weekly_summary": True
        },
        "ui": {
            "theme": "light",
            "sidebar_collapsed": True,
            "animations_enabled": False
        },
        "query": {
            "default_time_range": "7d",
            "max_results": 2000,
            "auto_complete_enabled": True
        }
    }