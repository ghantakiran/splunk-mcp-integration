"""
Unit tests for schedule management functionality.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scheduler_service import SchedulerService
from app.models.schedule_models import CreateScheduleRequest, UpdateScheduleRequest


class TestScheduleAPI:
    """Test cases for schedule API endpoints."""
    
    def test_create_schedule_success(self, client: TestClient, auth_headers: dict, sample_schedule_data: dict):
        """Test successful schedule creation."""
        response = client.post(
            "/api/v1/schedules/",
            json=sample_schedule_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "schedule_id" in data
        assert data["name"] == sample_schedule_data["name"]
        assert data["status"] == "active"
        assert data["cron_expression"] == sample_schedule_data["cron_expression"]
    
    def test_create_schedule_invalid_cron(self, client: TestClient, auth_headers: dict, sample_schedule_data: dict):
        """Test schedule creation with invalid cron expression."""
        sample_schedule_data["cron_expression"] = "invalid cron"
        
        response = client.post(
            "/api/v1/schedules/",
            json=sample_schedule_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "detail" in response.json()
    
    def test_create_schedule_unauthorized(self, client: TestClient, sample_schedule_data: dict):
        """Test schedule creation without authentication."""
        response = client.post(
            "/api/v1/schedules/",
            json=sample_schedule_data
        )
        
        assert response.status_code == 401
    
    def test_list_schedules(self, client: TestClient, auth_headers: dict):
        """Test listing schedules."""
        response = client.get(
            "/api/v1/schedules/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["items"], list)
    
    def test_get_schedule_by_id(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting schedule by ID."""
        response = client.get(
            f"/api/v1/schedules/{created_schedule.schedule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["schedule_id"] == str(created_schedule.schedule_id)
        assert data["name"] == created_schedule.name
    
    def test_get_nonexistent_schedule(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent schedule."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/schedules/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_schedule(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test updating schedule."""
        update_data = {
            "name": "Updated Schedule Name",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/api/v1/schedules/{created_schedule.schedule_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_schedule(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test deleting schedule."""
        response = client.delete(
            f"/api/v1/schedules/{created_schedule.schedule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify schedule is deleted
        get_response = client.get(
            f"/api/v1/schedules/{created_schedule.schedule_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    def test_execute_schedule(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test manual schedule execution."""
        response = client.post(
            f"/api/v1/schedules/{created_schedule.schedule_id}/execute",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "execution_id" in data
        assert data["status"] == "pending"
    
    def test_pause_schedule(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test pausing schedule."""
        response = client.post(
            f"/api/v1/schedules/{created_schedule.schedule_id}/pause",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "paused"
    
    def test_resume_schedule(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test resuming schedule."""
        # First pause the schedule
        client.post(
            f"/api/v1/schedules/{created_schedule.schedule_id}/pause",
            headers=auth_headers
        )
        
        # Then resume it
        response = client.post(
            f"/api/v1/schedules/{created_schedule.schedule_id}/resume",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "active"


class TestSchedulerService:
    """Test cases for scheduler service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_schedule(self, db_session: AsyncSession, mock_user: dict, sample_schedule_data: dict):
        """Test creating a schedule via service."""
        service = SchedulerService(db_session)
        
        request = CreateScheduleRequest(**sample_schedule_data)
        result = await service.create_schedule(request, mock_user["user_id"])
        
        assert result.name == sample_schedule_data["name"]
        assert result.user_id == mock_user["user_id"]
        assert result.status.value == "active"
        assert result.cron_expression == sample_schedule_data["cron_expression"]
    
    @pytest.mark.asyncio
    async def test_list_schedules(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test listing schedules via service."""
        service = SchedulerService(db_session)
        
        result = await service.list_schedules(mock_user["user_id"])
        
        assert result.total >= 1
        assert len(result.items) >= 1
        assert any(item.schedule_id == created_schedule.schedule_id for item in result.items)
    
    @pytest.mark.asyncio
    async def test_get_schedule(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test getting schedule by ID via service."""
        service = SchedulerService(db_session)
        
        result = await service.get_schedule(created_schedule.schedule_id, mock_user["user_id"])
        
        assert result is not None
        assert result.schedule_id == created_schedule.schedule_id
        assert result.name == created_schedule.name
    
    @pytest.mark.asyncio
    async def test_update_schedule(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test updating schedule via service."""
        service = SchedulerService(db_session)
        
        update_request = UpdateScheduleRequest(
            name="Updated Name",
            description="Updated Description"
        )
        
        result = await service.update_schedule(
            created_schedule.schedule_id,
            update_request,
            mock_user["user_id"]
        )
        
        assert result is not None
        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
    
    @pytest.mark.asyncio
    async def test_delete_schedule(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test deleting schedule via service."""
        service = SchedulerService(db_session)
        
        success = await service.delete_schedule(created_schedule.schedule_id, mock_user["user_id"])
        assert success is True
        
        # Verify schedule is deleted
        result = await service.get_schedule(created_schedule.schedule_id, mock_user["user_id"])
        assert result is None
    
    @pytest.mark.asyncio
    async def test_execute_schedule(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test manual schedule execution via service."""
        service = SchedulerService(db_session)
        
        result = await service.execute_schedule(created_schedule.schedule_id, mock_user["user_id"])
        
        assert result is not None
        assert result.schedule_id == created_schedule.schedule_id
        assert result.status.value == "pending"
    
    @pytest.mark.asyncio
    async def test_calculate_next_execution(self, db_session: AsyncSession):
        """Test next execution time calculation."""
        service = SchedulerService(db_session)
        
        # Test daily at 9 AM
        next_time = service._calculate_next_execution("0 9 * * *", "UTC")
        assert next_time is not None
        assert next_time.hour == 9
        
        # Test every Monday at 9 AM
        next_time = service._calculate_next_execution("0 9 * * 1", "UTC")
        assert next_time is not None
        assert next_time.hour == 9
        assert next_time.weekday() == 0  # Monday
    
    @pytest.mark.asyncio
    async def test_validate_cron_expression(self, db_session: AsyncSession):
        """Test cron expression validation."""
        service = SchedulerService(db_session)
        
        # Valid expressions
        assert service._validate_cron_expression("0 9 * * *") is True
        assert service._validate_cron_expression("0 0 1 * *") is True
        assert service._validate_cron_expression("*/15 * * * *") is True
        
        # Invalid expressions
        assert service._validate_cron_expression("invalid") is False
        assert service._validate_cron_expression("0 25 * * *") is False  # Invalid hour
        assert service._validate_cron_expression("") is False
    
    @pytest.mark.asyncio
    async def test_get_schedule_summary(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test getting schedule summary via service."""
        service = SchedulerService(db_session)
        
        summary = await service.get_schedule_summary(mock_user["user_id"])
        
        assert "total_schedules" in summary
        assert "active_schedules" in summary
        assert "recent_executions" in summary
        assert summary["total_schedules"] >= 1
    
    @pytest.mark.asyncio
    async def test_pause_resume_schedule(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test pausing and resuming schedule via service."""
        service = SchedulerService(db_session)
        
        # Pause schedule
        paused = await service.pause_schedule(created_schedule.schedule_id, mock_user["user_id"])
        assert paused is not None
        assert paused.status.value == "paused"
        
        # Resume schedule
        resumed = await service.resume_schedule(created_schedule.schedule_id, mock_user["user_id"])
        assert resumed is not None
        assert resumed.status.value == "active"
    
    @pytest.mark.asyncio
    async def test_schedule_access_control(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test that users can only access their own schedules."""
        service = SchedulerService(db_session)
        
        # Different user should not be able to access the schedule
        other_user_id = "other-user-456"
        result = await service.get_schedule(created_schedule.schedule_id, other_user_id)
        assert result is None
        
        # Original user should be able to access
        result = await service.get_schedule(created_schedule.schedule_id, mock_user["user_id"])
        assert result is not None