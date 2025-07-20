"""
Tests for ITSM Sync Manager functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.sync_manager import SyncManager, SyncConflictResolution
from app.models.itsm_models import ITSMIntegration, ITSMProvider, SyncRecord


@pytest.fixture
def servicenow_integration():
    """Create a test ServiceNow integration."""
    return ITSMIntegration(
        id="servicenow-integration-id",
        user_id="test-user-id",
        name="Test ServiceNow",
        provider=ITSMProvider.SERVICENOW,
        endpoint_url="https://test.service-now.com",
        credentials={"instance": "test", "username": "testuser", "password": "testpass"},
        field_mappings={"incident": {"title": "short_description", "description": "description"}}
    )


@pytest.fixture
def jira_integration():
    """Create a test Jira integration."""
    return ITSMIntegration(
        id="jira-integration-id",
        user_id="test-user-id",
        name="Test Jira",
        provider=ITSMProvider.JIRA,
        endpoint_url="https://test.atlassian.net",
        credentials={"server": "https://test.atlassian.net", "username": "testuser", "api_token": "token"},
        field_mappings={"issue": {"title": "summary", "description": "description"}}
    )


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return AsyncMock()


class TestSyncManager:
    """Test sync manager functionality."""
    
    @pytest.fixture
    def sync_manager(self, mock_db, mock_redis):
        """Create a sync manager instance."""
        return SyncManager(mock_db, mock_redis)
    
    @pytest.mark.asyncio
    async def test_sync_between_systems_basic(self, sync_manager, servicenow_integration, jira_integration):
        """Test basic synchronization between two systems."""
        # Mock source system tickets
        source_tickets = [
            {
                "external_id": "INC0001234",
                "title": "Test Incident",
                "description": "Test description",
                "status": "new",
                "priority": "medium",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Mock destination system response
        created_ticket = {
            "external_id": "TEST-123",
            "title": "Test Incident",
            "description": "Test description",
            "status": "to_do",
            "priority": "medium"
        }
        
        with patch.object(sync_manager, '_get_tickets_for_sync') as mock_get_tickets, \
             patch.object(sync_manager, '_sync_individual_ticket') as mock_sync_ticket, \
             patch.object(sync_manager, '_create_sync_record') as mock_create_record:
            
            mock_get_tickets.return_value = source_tickets
            mock_sync_ticket.return_value = created_ticket
            mock_create_record.return_value = None
            
            result = await sync_manager.sync_between_systems(
                servicenow_integration,
                jira_integration,
                "incident"
            )
            
            assert result["synced_count"] == 1
            assert result["failed_count"] == 0
            assert len(result["conflicts"]) == 0
            
            mock_get_tickets.assert_called_once()
            mock_sync_ticket.assert_called_once()
            mock_create_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_with_conflicts(self, sync_manager, servicenow_integration, jira_integration):
        """Test synchronization with conflicts."""
        # Mock source ticket that was modified in both systems
        source_ticket = {
            "external_id": "INC0001234",
            "title": "Updated Incident",
            "description": "Updated description",
            "status": "in_progress",
            "priority": "high",
            "updated_at": datetime.utcnow()
        }
        
        # Mock existing sync record
        existing_sync = SyncRecord(
            id="sync-record-123",
            source_integration_id=servicenow_integration.id,
            destination_integration_id=jira_integration.id,
            source_ticket_id="INC0001234",
            destination_ticket_id="TEST-123",
            last_synced_at=datetime.utcnow() - timedelta(hours=1),
            source_last_modified=datetime.utcnow() - timedelta(hours=2),
            destination_last_modified=datetime.utcnow() - timedelta(minutes=30)
        )
        
        # Mock destination ticket that was also modified
        destination_ticket = {
            "external_id": "TEST-123",
            "title": "Different Title",
            "description": "Different description",
            "status": "in_progress",
            "priority": "medium",
            "updated_at": datetime.utcnow() - timedelta(minutes=30)
        }
        
        with patch.object(sync_manager, '_get_tickets_for_sync') as mock_get_tickets, \
             patch.object(sync_manager, '_get_sync_record') as mock_get_sync, \
             patch.object(sync_manager, '_get_destination_ticket') as mock_get_dest, \
             patch.object(sync_manager, '_detect_conflict') as mock_detect_conflict, \
             patch.object(sync_manager, '_resolve_conflict') as mock_resolve_conflict:
            
            mock_get_tickets.return_value = [source_ticket]
            mock_get_sync.return_value = existing_sync
            mock_get_dest.return_value = destination_ticket
            mock_detect_conflict.return_value = True
            mock_resolve_conflict.return_value = {
                "resolution": "source_wins",
                "resolved_ticket": source_ticket
            }
            
            result = await sync_manager.sync_between_systems(
                servicenow_integration,
                jira_integration,
                "incident",
                conflict_resolution=SyncConflictResolution.SOURCE_WINS
            )
            
            assert result["synced_count"] == 1
            assert result["failed_count"] == 0
            assert len(result["conflicts"]) == 1
            
            mock_detect_conflict.assert_called_once()
            mock_resolve_conflict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_incremental_sync(self, sync_manager, servicenow_integration, jira_integration):
        """Test incremental synchronization."""
        last_sync_time = datetime.utcnow() - timedelta(hours=1)
        
        # Mock tickets modified since last sync
        modified_tickets = [
            {
                "external_id": "INC0001234",
                "title": "Updated Incident",
                "description": "Updated description",
                "status": "in_progress",
                "updated_at": datetime.utcnow() - timedelta(minutes=30)
            }
        ]
        
        with patch.object(sync_manager, '_get_modified_tickets_since') as mock_get_modified, \
             patch.object(sync_manager, '_sync_individual_ticket') as mock_sync_ticket, \
             patch.object(sync_manager, '_update_sync_record') as mock_update_record:
            
            mock_get_modified.return_value = modified_tickets
            mock_sync_ticket.return_value = modified_tickets[0]
            mock_update_record.return_value = None
            
            result = await sync_manager.incremental_sync(
                servicenow_integration,
                jira_integration,
                "incident",
                last_sync_time
            )
            
            assert result["synced_count"] == 1
            assert result["failed_count"] == 0
            
            mock_get_modified.assert_called_once_with(
                servicenow_integration, "incident", last_sync_time
            )
    
    @pytest.mark.asyncio
    async def test_bidirectional_sync(self, sync_manager, servicenow_integration, jira_integration):
        """Test bidirectional synchronization."""
        # Mock changes in both directions
        servicenow_changes = [
            {
                "external_id": "INC0001234",
                "title": "ServiceNow Update",
                "updated_at": datetime.utcnow() - timedelta(minutes=10)
            }
        ]
        
        jira_changes = [
            {
                "external_id": "TEST-456",
                "title": "Jira Update",
                "updated_at": datetime.utcnow() - timedelta(minutes=5)
            }
        ]
        
        with patch.object(sync_manager, 'incremental_sync') as mock_incremental_sync:
            mock_incremental_sync.side_effect = [
                {"synced_count": 1, "failed_count": 0, "conflicts": []},
                {"synced_count": 1, "failed_count": 0, "conflicts": []}
            ]
            
            result = await sync_manager.bidirectional_sync(
                servicenow_integration,
                jira_integration,
                "incident"
            )
            
            assert result["servicenow_to_jira"]["synced_count"] == 1
            assert result["jira_to_servicenow"]["synced_count"] == 1
            assert mock_incremental_sync.call_count == 2
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_source_wins(self, sync_manager):
        """Test conflict resolution with source wins strategy."""
        source_ticket = {
            "external_id": "INC0001234",
            "title": "Source Title",
            "description": "Source description",
            "priority": "high"
        }
        
        destination_ticket = {
            "external_id": "TEST-123",
            "title": "Destination Title",
            "description": "Destination description",
            "priority": "medium"
        }
        
        result = await sync_manager._resolve_conflict(
            source_ticket,
            destination_ticket,
            SyncConflictResolution.SOURCE_WINS
        )
        
        assert result["resolution"] == "source_wins"
        assert result["resolved_ticket"]["title"] == "Source Title"
        assert result["resolved_ticket"]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_destination_wins(self, sync_manager):
        """Test conflict resolution with destination wins strategy."""
        source_ticket = {
            "external_id": "INC0001234",
            "title": "Source Title",
            "priority": "high"
        }
        
        destination_ticket = {
            "external_id": "TEST-123",
            "title": "Destination Title",
            "priority": "medium"
        }
        
        result = await sync_manager._resolve_conflict(
            source_ticket,
            destination_ticket,
            SyncConflictResolution.DESTINATION_WINS
        )
        
        assert result["resolution"] == "destination_wins"
        assert result["resolved_ticket"]["title"] == "Destination Title"
        assert result["resolved_ticket"]["priority"] == "medium"
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_latest_wins(self, sync_manager):
        """Test conflict resolution with latest timestamp wins strategy."""
        older_time = datetime.utcnow() - timedelta(hours=1)
        newer_time = datetime.utcnow() - timedelta(minutes=30)
        
        source_ticket = {
            "external_id": "INC0001234",
            "title": "Source Title",
            "updated_at": older_time
        }
        
        destination_ticket = {
            "external_id": "TEST-123",
            "title": "Destination Title",
            "updated_at": newer_time
        }
        
        result = await sync_manager._resolve_conflict(
            source_ticket,
            destination_ticket,
            SyncConflictResolution.LATEST_WINS
        )
        
        assert result["resolution"] == "latest_wins"
        assert result["resolved_ticket"]["title"] == "Destination Title"  # Newer ticket wins
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self, sync_manager):
        """Test conflict detection logic."""
        sync_record = SyncRecord(
            last_synced_at=datetime.utcnow() - timedelta(hours=2),
            source_last_modified=datetime.utcnow() - timedelta(hours=3),
            destination_last_modified=datetime.utcnow() - timedelta(hours=3)
        )
        
        # Both tickets modified after last sync - conflict
        source_ticket = {"updated_at": datetime.utcnow() - timedelta(hours=1)}
        destination_ticket = {"updated_at": datetime.utcnow() - timedelta(minutes=30)}
        
        conflict = sync_manager._detect_conflict(source_ticket, destination_ticket, sync_record)
        assert conflict is True
        
        # Only source modified - no conflict
        source_ticket = {"updated_at": datetime.utcnow() - timedelta(hours=1)}
        destination_ticket = {"updated_at": datetime.utcnow() - timedelta(hours=4)}
        
        conflict = sync_manager._detect_conflict(source_ticket, destination_ticket, sync_record)
        assert conflict is False
    
    @pytest.mark.asyncio
    async def test_field_mapping_during_sync(self, sync_manager):
        """Test field mapping during synchronization."""
        source_ticket = {
            "external_id": "INC0001234",
            "title": "Test Incident",
            "description": "Test description",
            "priority": "medium",
            "status": "new"
        }
        
        field_mappings = {
            "title": "summary",
            "description": "description",
            "priority": "priority.name",
            "status": "status.name"
        }
        
        result = sync_manager._apply_field_mappings(source_ticket, field_mappings)
        
        assert result["summary"] == "Test Incident"
        assert result["description"] == "Test description"
        assert result["priority.name"] == "medium"
        assert result["status.name"] == "new"
    
    @pytest.mark.asyncio
    async def test_sync_performance_monitoring(self, sync_manager, servicenow_integration, jira_integration):
        """Test sync performance monitoring."""
        tickets = [{"external_id": f"INC000{i}", "title": f"Incident {i}"} for i in range(10)]
        
        with patch.object(sync_manager, '_get_tickets_for_sync') as mock_get_tickets, \
             patch.object(sync_manager, '_sync_individual_ticket') as mock_sync_ticket, \
             patch.object(sync_manager, '_record_sync_metrics') as mock_record_metrics:
            
            mock_get_tickets.return_value = tickets
            mock_sync_ticket.return_value = tickets[0]  # Simplified
            mock_record_metrics.return_value = None
            
            start_time = datetime.utcnow()
            result = await sync_manager.sync_between_systems(
                servicenow_integration,
                jira_integration,
                "incident"
            )
            end_time = datetime.utcnow()
            
            assert "sync_duration" in result
            assert "throughput" in result
            assert result["synced_count"] == 10
            
            mock_record_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_during_sync(self, sync_manager, servicenow_integration, jira_integration):
        """Test error handling during synchronization."""
        tickets = [
            {"external_id": "INC0001234", "title": "Good Ticket"},
            {"external_id": "INC0001235", "title": "Bad Ticket"}
        ]
        
        with patch.object(sync_manager, '_get_tickets_for_sync') as mock_get_tickets, \
             patch.object(sync_manager, '_sync_individual_ticket') as mock_sync_ticket:
            
            mock_get_tickets.return_value = tickets
            # First ticket succeeds, second fails
            mock_sync_ticket.side_effect = [
                tickets[0],
                Exception("Sync failed for bad ticket")
            ]
            
            result = await sync_manager.sync_between_systems(
                servicenow_integration,
                jira_integration,
                "incident"
            )
            
            assert result["synced_count"] == 1
            assert result["failed_count"] == 1
            assert len(result["errors"]) == 1
            assert "Sync failed for bad ticket" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_sync_status_tracking(self, sync_manager):
        """Test sync status tracking."""
        sync_job_id = "sync-job-123"
        
        await sync_manager.update_sync_status(sync_job_id, "running", {"progress": 50})
        
        # Verify Redis was called to store status
        sync_manager.redis.set.assert_called()
        call_args = sync_manager.redis.set.call_args
        assert sync_job_id in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_get_sync_history(self, sync_manager):
        """Test getting sync history."""
        # Mock database response
        sync_manager.db.fetch.return_value = [
            {
                "id": "sync-1",
                "source_integration_id": "source-id",
                "destination_integration_id": "dest-id",
                "sync_type": "full",
                "status": "completed",
                "synced_count": 100,
                "failed_count": 2,
                "started_at": datetime.utcnow() - timedelta(hours=1),
                "completed_at": datetime.utcnow() - timedelta(minutes=30)
            }
        ]
        
        history = await sync_manager.get_sync_history("source-id", "dest-id")
        
        assert len(history) == 1
        assert history[0]["synced_count"] == 100
        assert history[0]["status"] == "completed"
        
        sync_manager.db.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_sync_records(self, sync_manager):
        """Test cleanup of old sync records."""
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Mock database deletion
        sync_manager.db.execute.return_value = None
        
        await sync_manager.cleanup_old_sync_records(cutoff_date)
        
        sync_manager.db.execute.assert_called_once()
        call_args = sync_manager.db.execute.call_args[0][0]
        assert "DELETE" in call_args
        assert "last_synced_at" in call_args


if __name__ == "__main__":
    pytest.main([__file__])