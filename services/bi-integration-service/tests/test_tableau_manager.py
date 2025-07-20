"""
Tests for Tableau Manager functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.tableau_manager import TableauManager
from app.models.bi_models import BIIntegration, BIProvider, IntegrationStatus


class TestTableauManager:
    """Test suite for TableauManager class."""

    @pytest.fixture
    def tableau_integration(self):
        """Create a test Tableau integration."""
        integration = Mock(spec=BIIntegration)
        integration.id = "test-integration-id"
        integration.name = "Test Tableau Integration"
        integration.provider = BIProvider.TABLEAU
        integration.server_url = "https://tableau.example.com"
        integration.site_id = "test-site"
        integration.credentials = {
            "token_name": "test-token",
            "token_value": "test-token-value"
        }
        integration.status = IntegrationStatus.ACTIVE
        integration.configuration = {
            "auto_refresh": True,
            "refresh_interval": 3600,
            "timeout": 300
        }
        return integration

    @pytest.fixture
    def tableau_integration_username_auth(self):
        """Create a test Tableau integration with username/password auth."""
        integration = Mock(spec=BIIntegration)
        integration.id = "test-integration-id"
        integration.name = "Test Tableau Integration"
        integration.provider = BIProvider.TABLEAU
        integration.server_url = "https://tableau.example.com"
        integration.site_id = "test-site"
        integration.credentials = {
            "username": "test-user",
            "password": "test-password"
        }
        integration.status = IntegrationStatus.ACTIVE
        integration.configuration = {
            "auto_refresh": True,
            "refresh_interval": 3600,
            "timeout": 300
        }
        return integration

    @pytest.fixture
    def mock_tableau_server(self):
        """Mock Tableau Server client."""
        with patch('app.services.tableau_manager.TSC') as mock_tsc:
            mock_server = MagicMock()
            mock_tsc.Server.return_value = mock_server
            
            # Mock authentication classes
            mock_tsc.PersonalAccessTokenAuth = MagicMock()
            mock_tsc.TableauAuth = MagicMock()
            
            # Mock server methods
            mock_server.auth = MagicMock()
            mock_server.workbooks = MagicMock()
            mock_server.datasources = MagicMock()
            mock_server.projects = MagicMock()
            mock_server.users = MagicMock()
            mock_server.groups = MagicMock()
            
            yield mock_server, mock_tsc

    def test_tableau_manager_initialization_with_token(self, tableau_integration, mock_tableau_server):
        """Test TableauManager initialization with personal access token."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Verify server initialization
        mock_tsc.Server.assert_called_once_with("https://tableau.example.com")
        assert manager.server_url == "https://tableau.example.com"
        assert manager.site_id == "test-site"
        assert manager.credentials == {"token_name": "test-token", "token_value": "test-token-value"}
        
        # Verify authentication setup
        mock_tsc.PersonalAccessTokenAuth.assert_called_once_with(
            "test-token", "test-token-value", "test-site"
        )

    def test_tableau_manager_initialization_with_username(self, tableau_integration_username_auth, mock_tableau_server):
        """Test TableauManager initialization with username/password."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration_username_auth)
        
        # Verify server initialization
        mock_tsc.Server.assert_called_once_with("https://tableau.example.com")
        
        # Verify authentication setup
        mock_tsc.TableauAuth.assert_called_once_with(
            "test-user", "test-password", "test-site"
        )

    def test_tableau_manager_initialization_invalid_credentials(self):
        """Test TableauManager initialization with invalid credentials."""
        integration = Mock(spec=BIIntegration)
        integration.server_url = "https://tableau.example.com"
        integration.site_id = "test-site"
        integration.credentials = {"invalid": "credentials"}
        
        with patch('app.services.tableau_manager.TSC'):
            with pytest.raises(ValueError, match="Invalid Tableau credentials provided"):
                TableauManager(integration)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, tableau_integration, mock_tableau_server):
        """Test successful authentication."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock successful authentication
        mock_server.auth.sign_in.return_value = None
        
        with patch.object(manager, 'server', mock_server):
            result = await manager.authenticate()
            
            assert result is True
            assert manager._authenticated is True
            mock_server.auth.sign_in.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, tableau_integration, mock_tableau_server):
        """Test authentication failure."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock authentication failure
        mock_server.auth.sign_in.side_effect = Exception("Authentication failed")
        
        with patch.object(manager, 'server', mock_server):
            result = await manager.authenticate()
            
            assert result is False
            assert manager._authenticated is False

    @pytest.mark.asyncio
    async def test_disconnect(self, tableau_integration, mock_tableau_server):
        """Test disconnection from Tableau server."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        mock_server.auth.sign_out.return_value = None
        
        with patch.object(manager, 'server', mock_server):
            await manager.disconnect()
            
            assert manager._authenticated is False
            mock_server.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_workbooks(self, tableau_integration, mock_tableau_server):
        """Test listing workbooks."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock workbook objects
        mock_workbook1 = MagicMock()
        mock_workbook1.id = "wb1"
        mock_workbook1.name = "Workbook 1"
        mock_workbook1.project_name = "Project 1"
        mock_workbook1.size = 1024000
        mock_workbook1.created_at = "2025-01-01T00:00:00Z"
        mock_workbook1.updated_at = "2025-01-18T10:00:00Z"
        
        mock_workbook2 = MagicMock()
        mock_workbook2.id = "wb2"
        mock_workbook2.name = "Workbook 2"
        mock_workbook2.project_name = "Project 2"
        mock_workbook2.size = 2048000
        mock_workbook2.created_at = "2025-01-01T00:00:00Z"
        mock_workbook2.updated_at = "2025-01-18T10:00:00Z"
        
        # Mock server response
        mock_server.workbooks.get.return_value = ([mock_workbook1, mock_workbook2], None)
        
        with patch.object(manager, 'server', mock_server):
            workbooks = await manager.list_workbooks()
            
            assert len(workbooks) == 2
            assert workbooks[0]["id"] == "wb1"
            assert workbooks[0]["name"] == "Workbook 1"
            assert workbooks[1]["id"] == "wb2"
            assert workbooks[1]["name"] == "Workbook 2"

    @pytest.mark.asyncio
    async def test_list_workbooks_not_authenticated(self, tableau_integration, mock_tableau_server):
        """Test listing workbooks when not authenticated."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = False
        
        with patch.object(manager, 'server', mock_server):
            with pytest.raises(Exception, match="Not authenticated"):
                await manager.list_workbooks()

    @pytest.mark.asyncio
    async def test_get_workbook(self, tableau_integration, mock_tableau_server):
        """Test getting a specific workbook."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock workbook object
        mock_workbook = MagicMock()
        mock_workbook.id = "wb1"
        mock_workbook.name = "Test Workbook"
        mock_workbook.project_name = "Test Project"
        mock_workbook.description = "Test description"
        mock_workbook.size = 1024000
        mock_workbook.created_at = "2025-01-01T00:00:00Z"
        mock_workbook.updated_at = "2025-01-18T10:00:00Z"
        
        mock_server.workbooks.get_by_id.return_value = mock_workbook
        
        with patch.object(manager, 'server', mock_server):
            workbook = await manager.get_workbook("wb1")
            
            assert workbook["id"] == "wb1"
            assert workbook["name"] == "Test Workbook"
            assert workbook["project_name"] == "Test Project"
            mock_server.workbooks.get_by_id.assert_called_once_with("wb1")

    @pytest.mark.asyncio
    async def test_get_workbook_not_found(self, tableau_integration, mock_tableau_server):
        """Test getting a workbook that doesn't exist."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        mock_server.workbooks.get_by_id.side_effect = Exception("Workbook not found")
        
        with patch.object(manager, 'server', mock_server):
            with pytest.raises(Exception, match="Workbook not found"):
                await manager.get_workbook("nonexistent")

    @pytest.mark.asyncio
    async def test_publish_workbook(self, tableau_integration, mock_tableau_server):
        """Test publishing a workbook."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock workbook object and project
        mock_project = MagicMock()
        mock_project.id = "project1"
        mock_server.projects.get.return_value = ([mock_project], None)
        
        mock_workbook = MagicMock()
        mock_workbook.id = "new-wb-id"
        mock_workbook.name = "New Workbook"
        mock_server.workbooks.publish.return_value = mock_workbook
        
        workbook_data = {
            "name": "New Workbook",
            "project_name": "Test Project",
            "file_path": "/tmp/test.twbx",
            "description": "Test workbook"
        }
        
        with patch.object(manager, 'server', mock_server):
            with patch('os.path.exists', return_value=True):
                result = await manager.publish_workbook(workbook_data)
                
                assert result["id"] == "new-wb-id"
                assert result["name"] == "New Workbook"
                mock_server.workbooks.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_workbook_file_not_found(self, tableau_integration, mock_tableau_server):
        """Test publishing a workbook with missing file."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        workbook_data = {
            "name": "New Workbook",
            "project_name": "Test Project",
            "file_path": "/tmp/nonexistent.twbx"
        }
        
        with patch.object(manager, 'server', mock_server):
            with patch('os.path.exists', return_value=False):
                with pytest.raises(ValueError, match="Workbook file not found"):
                    await manager.publish_workbook(workbook_data)

    @pytest.mark.asyncio
    async def test_list_data_sources(self, tableau_integration, mock_tableau_server):
        """Test listing data sources."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock data source objects
        mock_ds1 = MagicMock()
        mock_ds1.id = "ds1"
        mock_ds1.name = "Data Source 1"
        mock_ds1.datasource_type = "splunk"
        mock_ds1.created_at = "2025-01-01T00:00:00Z"
        mock_ds1.updated_at = "2025-01-18T10:00:00Z"
        
        mock_ds2 = MagicMock()
        mock_ds2.id = "ds2"
        mock_ds2.name = "Data Source 2"
        mock_ds2.datasource_type = "postgresql"
        mock_ds2.created_at = "2025-01-01T00:00:00Z"
        mock_ds2.updated_at = "2025-01-18T10:00:00Z"
        
        mock_server.datasources.get.return_value = ([mock_ds1, mock_ds2], None)
        
        with patch.object(manager, 'server', mock_server):
            data_sources = await manager.list_data_sources()
            
            assert len(data_sources) == 2
            assert data_sources[0]["id"] == "ds1"
            assert data_sources[0]["name"] == "Data Source 1"
            assert data_sources[1]["id"] == "ds2"
            assert data_sources[1]["name"] == "Data Source 2"

    @pytest.mark.asyncio
    async def test_refresh_data_source(self, tableau_integration, mock_tableau_server):
        """Test refreshing a data source."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock data source and refresh job
        mock_ds = MagicMock()
        mock_ds.id = "ds1"
        mock_server.datasources.get_by_id.return_value = mock_ds
        
        mock_job = MagicMock()
        mock_job.id = "job1"
        mock_job.status = "InProgress"
        mock_server.datasources.refresh.return_value = mock_job
        
        with patch.object(manager, 'server', mock_server):
            result = await manager.refresh_data_source("ds1")
            
            assert result["job_id"] == "job1"
            assert result["status"] == "InProgress"
            mock_server.datasources.refresh.assert_called_once_with(mock_ds)

    @pytest.mark.asyncio
    async def test_get_refresh_status(self, tableau_integration, mock_tableau_server):
        """Test getting refresh job status."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        manager._authenticated = True
        
        # Mock job object
        mock_job = MagicMock()
        mock_job.id = "job1"
        mock_job.status = "Success"
        mock_job.created_at = "2025-01-18T10:00:00Z"
        mock_job.completed_at = "2025-01-18T10:05:00Z"
        
        mock_server.jobs.get_by_id.return_value = mock_job
        
        with patch.object(manager, 'server', mock_server):
            status = await manager.get_refresh_status("job1")
            
            assert status["job_id"] == "job1"
            assert status["status"] == "Success"
            assert status["created_at"] == "2025-01-18T10:00:00Z"
            assert status["completed_at"] == "2025-01-18T10:05:00Z"

    @pytest.mark.asyncio
    async def test_test_connection(self, tableau_integration, mock_tableau_server):
        """Test connection testing."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock successful authentication and server info
        mock_server.auth.sign_in.return_value = None
        mock_server.server_info.get.return_value = MagicMock()
        mock_server.auth.sign_out.return_value = None
        
        with patch.object(manager, 'server', mock_server):
            result = await manager.test_connection()
            
            assert result["success"] is True
            assert "server_info" in result
            mock_server.auth.sign_in.assert_called_once()
            mock_server.server_info.get.assert_called_once()
            mock_server.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, tableau_integration, mock_tableau_server):
        """Test connection testing failure."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock authentication failure
        mock_server.auth.sign_in.side_effect = Exception("Authentication failed")
        
        with patch.object(manager, 'server', mock_server):
            result = await manager.test_connection()
            
            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]

    def test_convert_workbook_to_dict(self, tableau_integration, mock_tableau_server):
        """Test workbook object to dictionary conversion."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock workbook object
        mock_workbook = MagicMock()
        mock_workbook.id = "wb1"
        mock_workbook.name = "Test Workbook"
        mock_workbook.project_name = "Test Project"
        mock_workbook.description = "Test description"
        mock_workbook.size = 1024000
        mock_workbook.created_at = "2025-01-01T00:00:00Z"
        mock_workbook.updated_at = "2025-01-18T10:00:00Z"
        mock_workbook.tags = ["tag1", "tag2"]
        
        result = manager._convert_workbook_to_dict(mock_workbook)
        
        assert result["id"] == "wb1"
        assert result["name"] == "Test Workbook"
        assert result["project_name"] == "Test Project"
        assert result["description"] == "Test description"
        assert result["size"] == 1024000
        assert result["tags"] == ["tag1", "tag2"]

    def test_convert_datasource_to_dict(self, tableau_integration, mock_tableau_server):
        """Test data source object to dictionary conversion."""
        mock_server, mock_tsc = mock_tableau_server
        
        manager = TableauManager(tableau_integration)
        
        # Mock data source object
        mock_ds = MagicMock()
        mock_ds.id = "ds1"
        mock_ds.name = "Test Data Source"
        mock_ds.datasource_type = "splunk"
        mock_ds.project_name = "Test Project"
        mock_ds.created_at = "2025-01-01T00:00:00Z"
        mock_ds.updated_at = "2025-01-18T10:00:00Z"
        
        result = manager._convert_datasource_to_dict(mock_ds)
        
        assert result["id"] == "ds1"
        assert result["name"] == "Test Data Source"
        assert result["type"] == "splunk"
        assert result["project_name"] == "Test Project"