"""
Tests for ServiceNow manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.servicenow_manager import ServiceNowManager
from app.models.itsm_models import ITSMIntegration, ITSMProvider


@pytest.fixture
def servicenow_integration():
    """Create a test ServiceNow integration."""
    return ITSMIntegration(
        id="test-integration-id",
        user_id="test-user-id",
        name="Test ServiceNow",
        provider=ITSMProvider.SERVICENOW,
        endpoint_url="https://test.service-now.com",
        credentials={
            "instance": "test",
            "username": "testuser",
            "password": "testpass"
        },
        field_mappings={
            "incident": {
                "title": "short_description",
                "description": "description"
            }
        }
    )


@pytest.fixture
def mock_pysnow_client():
    """Create a mock pysnow client."""
    mock_client = MagicMock()
    mock_resource = MagicMock()
    mock_client.resource.return_value = mock_resource
    return mock_client, mock_resource


class TestServiceNowManager:
    """Test ServiceNow manager functionality."""
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    def test_initialize_client(self, mock_pysnow_class, servicenow_integration):
        """Test ServiceNow client initialization."""
        mock_client = MagicMock()
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        # Verify client was created with correct parameters
        mock_pysnow_class.assert_called_once_with(
            instance="test",
            user="testuser",
            password="testpass"
        )
        assert manager.client == mock_client
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_pysnow_class, servicenow_integration):
        """Test successful connection test."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client.resource.return_value = mock_resource
        mock_resource.get.return_value = mock_response
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        success, message = await manager.test_connection()
        
        assert success is True
        assert message == "Connection successful"
        mock_resource.get.assert_called_once_with(query={'limit': 1})
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_pysnow_class, servicenow_integration):
        """Test failed connection test."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        mock_client.resource.return_value = mock_resource
        mock_resource.get.return_value = mock_response
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        success, message = await manager.test_connection()
        
        assert success is False
        assert message == "Connection failed"
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_create_ticket(self, mock_pysnow_class, servicenow_integration):
        """Test ticket creation."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_record = {
            "sys_id": "test-sys-id",
            "number": "INC0001234",
            "state": "1",
            "short_description": "Test Incident",
            "description": "Test description",
            "priority": "4",
            "assigned_to": "test.user",
            "assignment_group": "IT Support",
            "sys_created_on": "2025-01-16 10:30:00",
            "sys_updated_on": "2025-01-16 10:30:00"
        }
        
        mock_client.resource.return_value = mock_resource
        mock_resource.create.return_value.one.return_value = mock_record
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        ticket_data = {
            "title": "Test Incident",
            "description": "Test description",
            "priority": "medium",
            "assigned_to": "test.user",
            "assigned_group": "IT Support"
        }
        
        result = await manager.create_ticket(ticket_data, "test-user-id")
        
        assert result["sys_id"] == "test-sys-id"
        assert result["number"] == "INC0001234"
        assert result["short_description"] == "Test Incident"
        
        # Verify create was called with mapped data
        mock_resource.create.assert_called_once()
        call_args = mock_resource.create.call_args[1]["payload"]
        assert call_args["short_description"] == "Test Incident"
        assert call_args["description"] == "Test description"
        assert call_args["priority"] == "4"  # medium mapped to 4
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_update_ticket(self, mock_pysnow_class, servicenow_integration):
        """Test ticket update."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_record = {
            "sys_id": "test-sys-id",
            "number": "INC0001234",
            "state": "2",
            "short_description": "Updated Test Incident",
            "description": "Updated description",
            "priority": "3",
            "assigned_to": "test.user",
            "assignment_group": "IT Support",
            "sys_created_on": "2025-01-16 10:30:00",
            "sys_updated_on": "2025-01-16 11:00:00"
        }
        
        mock_client.resource.return_value = mock_resource
        mock_resource.update.return_value.one.return_value = mock_record
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        ticket_data = {
            "title": "Updated Test Incident",
            "description": "Updated description",
            "priority": "high",
            "status": "in_progress"
        }
        
        result = await manager.update_ticket("test-sys-id", ticket_data)
        
        assert result["sys_id"] == "test-sys-id"
        assert result["short_description"] == "Updated Test Incident"
        assert result["state"] == "2"
        
        # Verify update was called with correct parameters
        mock_resource.update.assert_called_once()
        call_args = mock_resource.update.call_args
        assert call_args[1]["query"]["sys_id"] == "test-sys-id"
        
        payload = call_args[1]["payload"]
        assert payload["short_description"] == "Updated Test Incident"
        assert payload["priority"] == "3"  # high mapped to 3
        assert payload["state"] == "2"  # in_progress mapped to 2
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_get_ticket(self, mock_pysnow_class, servicenow_integration):
        """Test ticket retrieval."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_record = {
            "sys_id": "test-sys-id",
            "number": "INC0001234",
            "state": "1",
            "short_description": "Test Incident",
            "description": "Test description",
            "priority": "4",
            "assigned_to": "test.user",
            "assignment_group": "IT Support",
            "sys_created_on": "2025-01-16 10:30:00",
            "sys_updated_on": "2025-01-16 10:30:00"
        }
        
        mock_client.resource.return_value = mock_resource
        mock_resource.get.return_value = [mock_record]
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        result = await manager.get_ticket("test-sys-id")
        
        assert result is not None
        assert result["sys_id"] == "test-sys-id"
        assert result["number"] == "INC0001234"
        assert result["short_description"] == "Test Incident"
        
        # Verify get was called with correct query
        mock_resource.get.assert_called_once_with(query={'sys_id': 'test-sys-id'})
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, mock_pysnow_class, servicenow_integration):
        """Test ticket retrieval when ticket not found."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        
        mock_client.resource.return_value = mock_resource
        mock_resource.get.return_value = []  # No records found
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        result = await manager.get_ticket("nonexistent-id")
        
        assert result is None
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_search_tickets(self, mock_pysnow_class, servicenow_integration):
        """Test ticket search."""
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_records = [
            {
                "sys_id": "test-sys-id-1",
                "number": "INC0001234",
                "state": "1",
                "short_description": "Test Incident 1",
                "description": "Test description 1",
                "priority": "4",
                "assigned_to": "test.user1",
                "assignment_group": "IT Support",
                "sys_created_on": "2025-01-16 10:30:00",
                "sys_updated_on": "2025-01-16 10:30:00"
            },
            {
                "sys_id": "test-sys-id-2",
                "number": "INC0001235",
                "state": "2",
                "short_description": "Test Incident 2",
                "description": "Test description 2",
                "priority": "3",
                "assigned_to": "test.user2",
                "assignment_group": "IT Support",
                "sys_created_on": "2025-01-16 10:35:00",
                "sys_updated_on": "2025-01-16 10:35:00"
            }
        ]
        
        mock_client.resource.return_value = mock_resource
        mock_resource.get.return_value = mock_records
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        query = {
            "search": "Test Incident",
            "status": "new",
            "priority": "medium"
        }
        
        results = await manager.search_tickets(query)
        
        assert len(results) == 2
        assert results[0]["sys_id"] == "test-sys-id-1"
        assert results[1]["sys_id"] == "test-sys-id-2"
        
        # Verify search was called with built query
        mock_resource.get.assert_called_once()
        call_args = mock_resource.get.call_args[1]["query"]
        assert "sysparm_query" in call_args
        assert "sysparm_limit" in call_args
        assert call_args["sysparm_limit"] == 100
    
    def test_map_to_servicenow(self, servicenow_integration):
        """Test mapping generic data to ServiceNow format."""
        manager = ServiceNowManager(servicenow_integration)
        
        ticket_data = {
            "title": "Test Incident",
            "description": "Test description",
            "priority": "high",
            "status": "in_progress",
            "assigned_to": "test.user",
            "assigned_group": "IT Support",
            "category": "Software",
            "subcategory": "Application",
            "custom_fields": {
                "business_impact": "low"
            }
        }
        
        result = manager._map_to_servicenow(ticket_data, "incident")
        
        assert result["short_description"] == "Test Incident"
        assert result["description"] == "Test description"
        assert result["priority"] == "3"  # high mapped to 3
        assert result["state"] == "2"  # in_progress mapped to 2
        assert result["assigned_to"] == "test.user"
        assert result["assignment_group"] == "IT Support"
        assert result["category"] == "Software"
        assert result["subcategory"] == "Application"
        assert result["business_impact"] == "low"
    
    def test_build_servicenow_query(self, servicenow_integration):
        """Test building ServiceNow query from generic query."""
        manager = ServiceNowManager(servicenow_integration)
        
        query = {
            "search": "test incident",
            "status": "new",
            "priority": "high",
            "assigned_to": "test.user",
            "created_after": "2025-01-16",
            "created_before": "2025-01-17"
        }
        
        result = manager._build_servicenow_query(query)
        
        assert "sysparm_query" in result
        query_str = result["sysparm_query"]
        
        assert "short_descriptionLIKEtest incident" in query_str
        assert "state=1" in query_str  # new status
        assert "priority=3" in query_str  # high priority
        assert "assigned_to=test.user" in query_str
        assert "sys_created_on>=2025-01-16" in query_str
        assert "sys_created_on<=2025-01-17" in query_str
    
    @patch('app.services.servicenow_manager.pysnow.Client')
    @pytest.mark.asyncio
    async def test_get_tables(self, mock_pysnow_class, servicenow_integration):
        """Test getting available tables."""
        mock_client = MagicMock()
        mock_pysnow_class.return_value = mock_client
        
        manager = ServiceNowManager(servicenow_integration)
        
        tables = await manager.get_tables()
        
        assert len(tables) == 5
        assert any(table["name"] == "incident" for table in tables)
        assert any(table["name"] == "problem" for table in tables)
        assert any(table["name"] == "change_request" for table in tables)