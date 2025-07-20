"""
Tests for Jira manager functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.jira_manager import JiraManager
from app.models.itsm_models import ITSMIntegration, ITSMProvider


@pytest.fixture
def jira_integration():
    """Create a test Jira integration."""
    return ITSMIntegration(
        id="test-jira-integration-id",
        user_id="test-user-id",
        name="Test Jira",
        provider=ITSMProvider.JIRA,
        endpoint_url="https://test.atlassian.net",
        credentials={
            "server": "https://test.atlassian.net",
            "username": "testuser@test.com",
            "api_token": "test-api-token"
        },
        field_mappings={
            "issue": {
                "title": "summary",
                "description": "description",
                "priority": "priority.name"
            }
        },
        table_mappings={
            "issue": "Bug"
        }
    )


@pytest.fixture
def mock_jira_client():
    """Create a mock JIRA client."""
    mock_client = MagicMock()
    mock_issue = MagicMock()
    mock_client.issue.return_value = mock_issue
    mock_client.create_issue.return_value = mock_issue
    return mock_client


class TestJiraManager:
    """Test Jira manager functionality."""
    
    @patch('app.services.jira_manager.JIRA')
    def test_initialize_client(self, mock_jira_class, jira_integration):
        """Test Jira client initialization."""
        mock_client = MagicMock()
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        # Verify client was created with correct parameters
        mock_jira_class.assert_called_once_with(
            server="https://test.atlassian.net",
            basic_auth=("testuser@test.com", "test-api-token")
        )
        assert manager.client == mock_client
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_jira_class, jira_integration):
        """Test successful connection test."""
        mock_client = MagicMock()
        mock_client.myself.return_value = {"accountId": "test-account-id"}
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        success, message = await manager.test_connection()
        
        assert success is True
        assert message == "Connection successful"
        mock_client.myself.assert_called_once()
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_jira_class, jira_integration):
        """Test failed connection test."""
        mock_client = MagicMock()
        mock_client.myself.side_effect = Exception("Authentication failed")
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        success, message = await manager.test_connection()
        
        assert success is False
        assert "Authentication failed" in message
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_create_ticket(self, mock_jira_class, jira_integration):
        """Test ticket creation."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.id = "10001"
        mock_issue.fields.summary = "Test Issue"
        mock_issue.fields.description = "Test description"
        mock_issue.fields.status.name = "To Do"
        mock_issue.fields.priority.name = "Medium"
        mock_issue.fields.assignee.displayName = "Test User"
        mock_issue.fields.created = "2025-01-16T10:30:00.000+0000"
        mock_issue.fields.updated = "2025-01-16T10:30:00.000+0000"
        
        mock_client.create_issue.return_value = mock_issue
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        ticket_data = {
            "title": "Test Issue",
            "description": "Test description",
            "priority": "medium",
            "issue_type": "Bug",
            "assigned_to": "testuser",
            "project_key": "TEST"
        }
        
        result = await manager.create_ticket(ticket_data, "test-user-id")
        
        assert result["key"] == "TEST-123"
        assert result["id"] == "10001"
        assert result["summary"] == "Test Issue"
        
        # Verify create_issue was called with correct fields
        mock_client.create_issue.assert_called_once()
        call_args = mock_client.create_issue.call_args[1]["fields"]
        assert call_args["summary"] == "Test Issue"
        assert call_args["description"] == "Test description"
        assert call_args["project"]["key"] == "TEST"
        assert call_args["issuetype"]["name"] == "Bug"
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_update_ticket(self, mock_jira_class, jira_integration):
        """Test ticket update."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Updated Test Issue"
        mock_issue.fields.description = "Updated description"
        mock_issue.fields.status.name = "In Progress"
        mock_issue.fields.priority.name = "High"
        
        mock_client.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        ticket_data = {
            "title": "Updated Test Issue",
            "description": "Updated description",
            "priority": "high",
            "status": "in_progress"
        }
        
        result = await manager.update_ticket("TEST-123", ticket_data)
        
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Updated Test Issue"
        
        # Verify issue was retrieved and updated
        mock_client.issue.assert_called_once_with("TEST-123")
        mock_issue.update.assert_called_once()
        
        # Check update fields
        update_args = mock_issue.update.call_args[1]["fields"]
        assert update_args["summary"] == "Updated Test Issue"
        assert update_args["description"] == "Updated description"
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_get_ticket(self, mock_jira_class, jira_integration):
        """Test ticket retrieval."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.id = "10001"
        mock_issue.fields.summary = "Test Issue"
        mock_issue.fields.description = "Test description"
        mock_issue.fields.status.name = "To Do"
        mock_issue.fields.priority.name = "Medium"
        mock_issue.fields.assignee.displayName = "Test User"
        mock_issue.fields.created = "2025-01-16T10:30:00.000+0000"
        mock_issue.fields.updated = "2025-01-16T10:30:00.000+0000"
        
        mock_client.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        result = await manager.get_ticket("TEST-123")
        
        assert result is not None
        assert result["key"] == "TEST-123"
        assert result["id"] == "10001"
        assert result["summary"] == "Test Issue"
        
        # Verify issue was retrieved
        mock_client.issue.assert_called_once_with("TEST-123")
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, mock_jira_class, jira_integration):
        """Test ticket retrieval when ticket not found."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = Exception("Issue does not exist")
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        result = await manager.get_ticket("NONEXISTENT-123")
        
        assert result is None
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_search_tickets(self, mock_jira_class, jira_integration):
        """Test ticket search."""
        mock_client = MagicMock()
        mock_issue1 = MagicMock()
        mock_issue1.key = "TEST-123"
        mock_issue1.fields.summary = "Test Issue 1"
        mock_issue1.fields.status.name = "To Do"
        
        mock_issue2 = MagicMock()
        mock_issue2.key = "TEST-124"
        mock_issue2.fields.summary = "Test Issue 2"
        mock_issue2.fields.status.name = "In Progress"
        
        mock_search_result = MagicMock()
        mock_search_result.issues = [mock_issue1, mock_issue2]
        mock_search_result.total = 2
        
        mock_client.search_issues.return_value = mock_search_result
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        query = {
            "search": "Test Issue",
            "project": "TEST",
            "status": "To Do",
            "priority": "Medium"
        }
        
        results = await manager.search_tickets(query)
        
        assert len(results) == 2
        assert results[0]["key"] == "TEST-123"
        assert results[1]["key"] == "TEST-124"
        
        # Verify search was called with JQL query
        mock_client.search_issues.assert_called_once()
        call_args = mock_client.search_issues.call_args[0][0]
        assert "project = TEST" in call_args
        assert "summary ~ \"Test Issue\"" in call_args
    
    def test_map_to_jira(self, jira_integration):
        """Test mapping generic data to Jira format."""
        manager = JiraManager(jira_integration)
        
        ticket_data = {
            "title": "Test Issue",
            "description": "Test description",
            "priority": "high",
            "issue_type": "Bug",
            "project_key": "TEST",
            "assigned_to": "testuser",
            "labels": ["urgent", "customer"],
            "custom_fields": {
                "story_points": 8,
                "epic_link": "EPIC-123"
            }
        }
        
        result = manager._map_to_jira(ticket_data)
        
        assert result["summary"] == "Test Issue"
        assert result["description"] == "Test description"
        assert result["priority"]["name"] == "High"
        assert result["issuetype"]["name"] == "Bug"
        assert result["project"]["key"] == "TEST"
        assert result["assignee"]["name"] == "testuser"
        assert result["labels"] == ["urgent", "customer"]
        assert result["customfield_story_points"] == 8
        assert result["customfield_epic_link"] == "EPIC-123"
    
    def test_build_jql_query(self, jira_integration):
        """Test building JQL query from generic query."""
        manager = JiraManager(jira_integration)
        
        query = {
            "search": "test issue",
            "project": "TEST",
            "status": "To Do",
            "priority": "High",
            "assigned_to": "testuser",
            "issue_type": "Bug",
            "created_after": "2025-01-16",
            "created_before": "2025-01-17"
        }
        
        result = manager._build_jql_query(query)
        
        assert "project = TEST" in result
        assert "summary ~ \"test issue\"" in result
        assert "status = \"To Do\"" in result
        assert "priority = \"High\"" in result
        assert "assignee = testuser" in result
        assert "issuetype = Bug" in result
        assert "created >= \"2025-01-16\"" in result
        assert "created <= \"2025-01-17\"" in result
        assert " AND " in result  # Should combine with AND
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_get_projects(self, mock_jira_class, jira_integration):
        """Test getting available projects."""
        mock_client = MagicMock()
        mock_projects = [
            MagicMock(key="TEST", name="Test Project", id="10001"),
            MagicMock(key="DEMO", name="Demo Project", id="10002")
        ]
        mock_client.projects.return_value = mock_projects
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        projects = await manager.get_projects()
        
        assert len(projects) == 2
        assert projects[0]["key"] == "TEST"
        assert projects[0]["name"] == "Test Project"
        assert projects[1]["key"] == "DEMO"
        assert projects[1]["name"] == "Demo Project"
        
        mock_client.projects.assert_called_once()
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_get_issue_types(self, mock_jira_class, jira_integration):
        """Test getting available issue types."""
        mock_client = MagicMock()
        mock_issue_types = [
            MagicMock(name="Bug", id="1"),
            MagicMock(name="Story", id="2"),
            MagicMock(name="Epic", id="3")
        ]
        mock_client.issue_types.return_value = mock_issue_types
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        issue_types = await manager.get_issue_types()
        
        assert len(issue_types) == 3
        assert issue_types[0]["name"] == "Bug"
        assert issue_types[1]["name"] == "Story"
        assert issue_types[2]["name"] == "Epic"
        
        mock_client.issue_types.assert_called_once()
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_transition_ticket(self, mock_jira_class, jira_integration):
        """Test ticket status transition."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_transitions = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"}
        ]
        
        mock_client.issue.return_value = mock_issue
        mock_client.transitions.return_value = mock_transitions
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        result = await manager.transition_ticket("TEST-123", "In Progress")
        
        assert result is True
        
        # Verify transition was called
        mock_client.issue.assert_called_once_with("TEST-123")
        mock_client.transitions.assert_called_once_with(mock_issue)
        mock_client.transition_issue.assert_called_once_with(mock_issue, "21")
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_add_comment(self, mock_jira_class, jira_integration):
        """Test adding comment to ticket."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = "comment-123"
        mock_comment.body = "Test comment"
        
        mock_client.issue.return_value = mock_issue
        mock_client.add_comment.return_value = mock_comment
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        result = await manager.add_comment("TEST-123", "Test comment")
        
        assert result["id"] == "comment-123"
        assert result["body"] == "Test comment"
        
        # Verify comment was added
        mock_client.issue.assert_called_once_with("TEST-123")
        mock_client.add_comment.assert_called_once_with(mock_issue, "Test comment")
    
    @patch('app.services.jira_manager.JIRA')
    @pytest.mark.asyncio
    async def test_get_field_mappings(self, mock_jira_class, jira_integration):
        """Test getting field mappings for a project."""
        mock_client = MagicMock()
        mock_fields = [
            {"id": "summary", "name": "Summary", "custom": False},
            {"id": "description", "name": "Description", "custom": False},
            {"id": "customfield_10001", "name": "Story Points", "custom": True},
            {"id": "customfield_10002", "name": "Epic Link", "custom": True}
        ]
        mock_client.fields.return_value = mock_fields
        mock_jira_class.return_value = mock_client
        
        manager = JiraManager(jira_integration)
        
        fields = await manager.get_field_mappings("TEST")
        
        assert len(fields) == 4
        assert any(field["id"] == "summary" for field in fields)
        assert any(field["id"] == "customfield_10001" for field in fields)
        
        mock_client.fields.assert_called_once()
    
    def test_convert_jira_to_generic(self, jira_integration):
        """Test converting Jira issue to generic format."""
        manager = JiraManager(jira_integration)
        
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.id = "10001"
        mock_issue.fields.summary = "Test Issue"
        mock_issue.fields.description = "Test description"
        mock_issue.fields.status.name = "In Progress"
        mock_issue.fields.priority.name = "High"
        mock_issue.fields.assignee.displayName = "Test User"
        mock_issue.fields.created = "2025-01-16T10:30:00.000+0000"
        mock_issue.fields.updated = "2025-01-16T11:00:00.000+0000"
        mock_issue.fields.labels = ["urgent", "customer"]
        
        result = manager._convert_jira_to_generic(mock_issue)
        
        assert result["external_id"] == "TEST-123"
        assert result["title"] == "Test Issue"
        assert result["description"] == "Test description"
        assert result["status"] == "in_progress"
        assert result["priority"] == "high"
        assert result["assigned_to"] == "Test User"
        assert result["labels"] == ["urgent", "customer"]


if __name__ == "__main__":
    pytest.main([__file__])