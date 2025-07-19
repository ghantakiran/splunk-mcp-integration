"""
Unit tests for version management functionality.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.versioning_service import VersioningService
from app.models.versioning_models import (
    CreateVersionRequest, RestoreVersionRequest, CompareVersionsRequest,
    HistoryFilterRequest, VersionAction, ChangeType, HistoryEventType
)
from app.core.database import ScheduleVersion, ScheduleHistory


class TestVersioningAPI:
    """Test cases for versioning API endpoints."""
    
    def test_create_version_success(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test successful version creation."""
        version_data = {
            "schedule_id": str(created_schedule.schedule_id),
            "version_name": "Test Version",
            "description": "A test version",
            "changes": ["schedule_config", "query"],
            "change_notes": "Updated query and configuration",
            "tags": ["test", "update"]
        }
        
        response = client.post(
            "/api/v1/versions/",
            json=version_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "version_id" in data
        assert data["schedule_id"] == str(created_schedule.schedule_id)
        assert data["version_name"] == version_data["version_name"]
        assert data["description"] == version_data["description"]
        assert data["changes"] == version_data["changes"]
        assert data["change_notes"] == version_data["change_notes"]
        assert data["tags"] == version_data["tags"]
        assert data["is_current"] is True
        assert data["version_number"] >= 1
    
    def test_create_version_invalid_schedule(self, client: TestClient, auth_headers: dict):
        """Test version creation with invalid schedule ID."""
        version_data = {
            "schedule_id": str(uuid4()),
            "version_name": "Test Version",
            "description": "A test version",
            "changes": ["schedule_config"]
        }
        
        response = client.post(
            "/api/v1/versions/",
            json=version_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
    
    def test_create_version_unauthorized(self, client: TestClient, created_schedule):
        """Test version creation without authentication."""
        version_data = {
            "schedule_id": str(created_schedule.schedule_id),
            "changes": ["schedule_config"]
        }
        
        response = client.post(
            "/api/v1/versions/",
            json=version_data
        )
        
        assert response.status_code == 401
    
    def test_get_schedule_versions(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting versions for a schedule."""
        response = client.get(
            f"/api/v1/versions/schedule/{created_schedule.schedule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert isinstance(data["items"], list)
    
    def test_get_schedule_versions_with_pagination(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting versions with pagination."""
        response = client.get(
            f"/api/v1/versions/schedule/{created_schedule.schedule_id}?limit=10&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    def test_get_version_by_id(self, client: TestClient, auth_headers: dict, created_version):
        """Test getting a specific version by ID."""
        response = client.get(
            f"/api/v1/versions/{created_version.version_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["version_id"] == str(created_version.version_id)
        assert data["schedule_id"] == str(created_version.schedule_id)
        assert "schedule_config" in data
    
    def test_get_nonexistent_version(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent version."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/versions/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_compare_versions(self, client: TestClient, auth_headers: dict, created_version, another_version):
        """Test comparing two versions."""
        comparison_data = {
            "version_id_1": str(created_version.version_id),
            "version_id_2": str(another_version.version_id),
            "include_metadata": True
        }
        
        response = client.post(
            "/api/v1/versions/compare",
            json=comparison_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "version_1" in data
        assert "version_2" in data
        assert "differences" in data
        assert "summary" in data
        assert "is_identical" in data
    
    def test_restore_version(self, client: TestClient, auth_headers: dict, created_version):
        """Test restoring a version."""
        restore_data = {
            "version_id": str(created_version.version_id),
            "restore_notes": "Restoring to previous version"
        }
        
        response = client.post(
            "/api/v1/versions/restore",
            json=restore_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["restored_version_id"] == str(created_version.version_id)
        assert "new_version_id" in data
        assert "changes_applied" in data
    
    def test_get_version_stats(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting version statistics."""
        response = client.get(
            f"/api/v1/versions/schedule/{created_schedule.schedule_id}/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schedule_id" in data
        assert "total_versions" in data
        assert "current_version_number" in data
        assert "versions_by_action" in data
        assert "versions_by_change_type" in data
        assert "first_version_created" in data
        assert "last_version_created" in data
    
    def test_get_history(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting history events."""
        response = client.get(
            f"/api/v1/versions/history?schedule_id={created_schedule.schedule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["items"], list)
    
    def test_get_history_with_filters(self, client: TestClient, auth_headers: dict, created_schedule):
        """Test getting history with filters."""
        response = client.get(
            f"/api/v1/versions/history?schedule_id={created_schedule.schedule_id}&limit=5&event_types=version_change",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["limit"] == 5
        for item in data["items"]:
            if "event_type" in item:
                assert item["event_type"] == "version_change"


class TestVersioningService:
    """Test cases for versioning service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_version(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test creating a version via service."""
        service = VersioningService(db_session)
        
        request = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            version_name="Test Version",
            description="A test version",
            changes=[ChangeType.SCHEDULE_CONFIG, ChangeType.QUERY],
            change_notes="Updated configuration and query",
            tags=["test"]
        )
        
        result = await service.create_version(request, mock_user["user_id"])
        
        assert result.schedule_id == created_schedule.schedule_id
        assert result.version_name == "Test Version"
        assert result.description == "A test version"
        assert ChangeType.SCHEDULE_CONFIG in result.changes
        assert ChangeType.QUERY in result.changes
        assert result.change_notes == "Updated configuration and query"
        assert result.tags == ["test"]
        assert result.is_current is True
        assert result.created_by == mock_user["user_id"]
        assert result.version_number >= 1
    
    @pytest.mark.asyncio
    async def test_get_versions(self, db_session: AsyncSession, created_schedule, created_version):
        """Test getting versions via service."""
        service = VersioningService(db_session)
        
        result = await service.get_versions(
            schedule_id=created_schedule.schedule_id,
            limit=10,
            offset=0
        )
        
        assert result.total >= 1
        assert len(result.items) >= 1
        assert result.limit == 10
        assert result.offset == 0
        assert any(item.version_id == created_version.version_id for item in result.items)
    
    @pytest.mark.asyncio
    async def test_get_version(self, db_session: AsyncSession, created_version):
        """Test getting specific version via service."""
        service = VersioningService(db_session)
        
        result = await service.get_version(created_version.version_id)
        
        assert result is not None
        assert result.version_id == created_version.version_id
        assert result.schedule_id == created_version.schedule_id
    
    @pytest.mark.asyncio
    async def test_compare_versions(self, db_session: AsyncSession, created_version, another_version):
        """Test comparing versions via service."""
        service = VersioningService(db_session)
        
        request = CompareVersionsRequest(
            version_id_1=created_version.version_id,
            version_id_2=another_version.version_id,
            include_metadata=True
        )
        
        result = await service.compare_versions(request)
        
        assert result.version_1.version_id == created_version.version_id
        assert result.version_2.version_id == another_version.version_id
        assert "differences" in result.dict()
        assert "summary" in result.dict()
        assert isinstance(result.is_identical, bool)
    
    @pytest.mark.asyncio
    async def test_restore_version(self, db_session: AsyncSession, mock_user: dict, created_version):
        """Test restoring version via service."""
        service = VersioningService(db_session)
        
        request = RestoreVersionRequest(
            version_id=created_version.version_id,
            restore_notes="Test restore operation"
        )
        
        result = await service.restore_version(request, mock_user["user_id"])
        
        assert result.success is True
        assert result.restored_version_id == created_version.version_id
        assert result.new_version_id is not None
        assert isinstance(result.changes_applied, list)
    
    @pytest.mark.asyncio
    async def test_get_history(self, db_session: AsyncSession, created_schedule):
        """Test getting history via service."""
        service = VersioningService(db_session)
        
        request = HistoryFilterRequest(
            schedule_id=created_schedule.schedule_id,
            limit=10,
            offset=0
        )
        
        result = await service.get_history(request)
        
        assert result.total >= 0
        assert len(result.items) >= 0
        assert result.limit == 10
        assert result.offset == 0
    
    @pytest.mark.asyncio
    async def test_get_version_stats(self, db_session: AsyncSession, created_schedule, created_version):
        """Test getting version statistics via service."""
        service = VersioningService(db_session)
        
        result = await service.get_version_stats(created_schedule.schedule_id)
        
        assert result.schedule_id == created_schedule.schedule_id
        assert result.total_versions >= 1
        assert result.current_version_number >= 1
        assert isinstance(result.versions_by_action, dict)
        assert isinstance(result.versions_by_change_type, dict)
        assert result.first_version_created is not None
        assert result.last_version_created is not None
    
    @pytest.mark.asyncio
    async def test_version_numbering(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test that version numbers increment correctly."""
        service = VersioningService(db_session)
        
        # Create first version
        request1 = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            changes=[ChangeType.SCHEDULE_CONFIG]
        )
        version1 = await service.create_version(request1, mock_user["user_id"])
        
        # Create second version
        request2 = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            changes=[ChangeType.QUERY]
        )
        version2 = await service.create_version(request2, mock_user["user_id"])
        
        assert version2.version_number > version1.version_number
        assert version2.is_current is True
        
        # Verify first version is no longer current
        updated_version1 = await service.get_version(version1.version_id)
        assert updated_version1.is_current is False
    
    @pytest.mark.asyncio
    async def test_configuration_snapshot(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test that configuration snapshots are created correctly."""
        service = VersioningService(db_session)
        
        request = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            changes=[ChangeType.SCHEDULE_CONFIG]
        )
        
        version = await service.create_version(request, mock_user["user_id"])
        
        # Verify configuration snapshot contains expected fields
        config = version.schedule_config
        assert "name" in config
        assert "description" in config
        assert "cron_expression" in config
        assert "query" in config
        assert "report_format" in config
        assert config["name"] == created_schedule.name
    
    @pytest.mark.asyncio
    async def test_checksum_generation(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test that checksums are generated for versions."""
        service = VersioningService(db_session)
        
        request = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            changes=[ChangeType.SCHEDULE_CONFIG]
        )
        
        version = await service.create_version(request, mock_user["user_id"])
        
        assert version.checksum is not None
        assert len(version.checksum) == 64  # SHA-256 hex string length
        assert version.size_bytes > 0
    
    @pytest.mark.asyncio
    async def test_history_event_creation(self, db_session: AsyncSession, mock_user: dict, created_schedule):
        """Test that history events are created for version operations."""
        service = VersioningService(db_session)
        
        request = CreateVersionRequest(
            schedule_id=created_schedule.schedule_id,
            version_name="History Test Version",
            changes=[ChangeType.SCHEDULE_CONFIG]
        )
        
        await service.create_version(request, mock_user["user_id"])
        
        # Get history events
        history_request = HistoryFilterRequest(
            schedule_id=created_schedule.schedule_id,
            event_types=[HistoryEventType.VERSION_CHANGE]
        )
        
        history = await service.get_history(history_request)
        
        assert history.total > 0
        # Check that at least one event is for version creation
        version_events = [
            event for event in history.items 
            if event.event_type == HistoryEventType.VERSION_CHANGE and "created" in event.event_title.lower()
        ]
        assert len(version_events) > 0