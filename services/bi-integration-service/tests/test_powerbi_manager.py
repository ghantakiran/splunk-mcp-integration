"""
Tests for Power BI Manager functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.powerbi_manager import PowerBIManager
from app.models.bi_models import BIIntegration, BIProvider, IntegrationStatus


class TestPowerBIManager:
    """Test suite for PowerBIManager class."""

    @pytest.fixture
    def powerbi_integration(self):
        """Create a test Power BI integration."""
        integration = Mock(spec=BIIntegration)
        integration.id = "test-integration-id"
        integration.name = "Test Power BI Integration"
        integration.provider = BIProvider.POWERBI
        integration.server_url = "https://api.powerbi.com"
        integration.site_id = None  # Power BI uses tenant_id
        integration.credentials = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "tenant_id": "test-tenant-id"
        }
        integration.status = IntegrationStatus.ACTIVE
        integration.configuration = {
            "auto_refresh": True,
            "refresh_interval": 3600,
            "timeout": 300
        }
        return integration

    @pytest.fixture
    def powerbi_integration_username(self):
        """Create a test Power BI integration with username/password."""
        integration = Mock(spec=BIIntegration)
        integration.id = "test-integration-id"
        integration.name = "Test Power BI Integration"
        integration.provider = BIProvider.POWERBI
        integration.server_url = "https://api.powerbi.com"
        integration.site_id = None
        integration.credentials = {
            "username": "test-user@example.com",
            "password": "test-password",
            "tenant_id": "test-tenant-id"
        }
        integration.status = IntegrationStatus.ACTIVE
        integration.configuration = {
            "auto_refresh": True,
            "refresh_interval": 3600,
            "timeout": 300
        }
        return integration

    @pytest.fixture
    def mock_msal_app(self):
        """Mock MSAL application."""
        with patch('app.services.powerbi_manager.msal') as mock_msal:
            mock_app = MagicMock()
            mock_msal.ConfidentialClientApplication.return_value = mock_app
            mock_msal.PublicClientApplication.return_value = mock_app
            
            # Mock successful token acquisition
            mock_app.acquire_token_for_client.return_value = {
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            
            mock_app.acquire_token_by_username_password.return_value = {
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            
            yield mock_app, mock_msal

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for Power BI API calls."""
        with patch('app.services.powerbi_manager.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful responses
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"value": []}
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = mock_response
            mock_client.put.return_value = mock_response
            mock_client.delete.return_value = mock_response
            
            yield mock_client

    def test_powerbi_manager_initialization_with_client_credentials(self, powerbi_integration, mock_msal_app):
        """Test PowerBIManager initialization with client credentials."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        
        # Verify MSAL app initialization
        mock_msal.ConfidentialClientApplication.assert_called_once()
        assert manager.tenant_id == "test-tenant-id"
        assert manager.credentials == {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "tenant_id": "test-tenant-id"
        }

    def test_powerbi_manager_initialization_with_username(self, powerbi_integration_username, mock_msal_app):
        """Test PowerBIManager initialization with username/password."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration_username)
        
        # Verify MSAL app initialization
        mock_msal.PublicClientApplication.assert_called_once()

    def test_powerbi_manager_initialization_invalid_credentials(self):
        """Test PowerBIManager initialization with invalid credentials."""
        integration = Mock(spec=BIIntegration)
        integration.server_url = "https://api.powerbi.com"
        integration.credentials = {"invalid": "credentials"}
        
        with pytest.raises(ValueError, match="Invalid Power BI credentials provided"):
            PowerBIManager(integration)

    @pytest.mark.asyncio
    async def test_authenticate_with_client_credentials(self, powerbi_integration, mock_msal_app):
        """Test authentication with client credentials."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        
        result = await manager.authenticate()
        
        assert result is True
        assert manager._authenticated is True
        assert manager.access_token == "test-access-token"
        mock_app.acquire_token_for_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_with_username_password(self, powerbi_integration_username, mock_msal_app):
        """Test authentication with username/password."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration_username)
        
        result = await manager.authenticate()
        
        assert result is True
        assert manager._authenticated is True
        assert manager.access_token == "test-access-token"
        mock_app.acquire_token_by_username_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, powerbi_integration, mock_msal_app):
        """Test authentication failure."""
        mock_app, mock_msal = mock_msal_app
        
        # Mock authentication failure
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Authentication failed"
        }
        
        manager = PowerBIManager(powerbi_integration)
        
        result = await manager.authenticate()
        
        assert result is False
        assert manager._authenticated is False
        assert manager.access_token is None

    @pytest.mark.asyncio
    async def test_list_workspaces(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test listing workspaces."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock workspace response
        mock_client.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "workspace-1",
                    "name": "Sales Workspace",
                    "description": "Sales analytics workspace",
                    "type": "Workspace",
                    "state": "Active"
                },
                {
                    "id": "workspace-2",
                    "name": "Marketing Workspace",
                    "description": "Marketing analytics workspace",
                    "type": "Workspace",
                    "state": "Active"
                }
            ]
        }
        
        workspaces = await manager.list_workspaces()
        
        assert len(workspaces) == 2
        assert workspaces[0]["id"] == "workspace-1"
        assert workspaces[0]["name"] == "Sales Workspace"
        assert workspaces[1]["id"] == "workspace-2"
        assert workspaces[1]["name"] == "Marketing Workspace"

    @pytest.mark.asyncio
    async def test_list_workspaces_not_authenticated(self, powerbi_integration, mock_msal_app):
        """Test listing workspaces when not authenticated."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = False
        
        with pytest.raises(Exception, match="Not authenticated"):
            await manager.list_workspaces()

    @pytest.mark.asyncio
    async def test_get_workspace(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test getting a specific workspace."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock workspace response
        mock_client.get.return_value.json.return_value = {
            "id": "workspace-1",
            "name": "Sales Workspace",
            "description": "Sales analytics workspace",
            "type": "Workspace",
            "state": "Active"
        }
        
        workspace = await manager.get_workspace("workspace-1")
        
        assert workspace["id"] == "workspace-1"
        assert workspace["name"] == "Sales Workspace"

    @pytest.mark.asyncio
    async def test_list_reports(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test listing reports in a workspace."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock reports response
        mock_client.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "report-1",
                    "name": "Sales Report",
                    "description": "Monthly sales report",
                    "webUrl": "https://powerbi.example.com/reports/report-1",
                    "embedUrl": "https://embed.powerbi.com/reports/report-1",
                    "datasetId": "dataset-1"
                },
                {
                    "id": "report-2",
                    "name": "Marketing Report",
                    "description": "Marketing campaign report",
                    "webUrl": "https://powerbi.example.com/reports/report-2",
                    "embedUrl": "https://embed.powerbi.com/reports/report-2",
                    "datasetId": "dataset-2"
                }
            ]
        }
        
        reports = await manager.list_reports("workspace-1")
        
        assert len(reports) == 2
        assert reports[0]["id"] == "report-1"
        assert reports[0]["name"] == "Sales Report"
        assert reports[1]["id"] == "report-2"
        assert reports[1]["name"] == "Marketing Report"

    @pytest.mark.asyncio
    async def test_get_report(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test getting a specific report."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock report response
        mock_client.get.return_value.json.return_value = {
            "id": "report-1",
            "name": "Sales Report",
            "description": "Monthly sales report",
            "webUrl": "https://powerbi.example.com/reports/report-1",
            "embedUrl": "https://embed.powerbi.com/reports/report-1",
            "datasetId": "dataset-1"
        }
        
        report = await manager.get_report("workspace-1", "report-1")
        
        assert report["id"] == "report-1"
        assert report["name"] == "Sales Report"

    @pytest.mark.asyncio
    async def test_list_datasets(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test listing datasets in a workspace."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock datasets response
        mock_client.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "dataset-1",
                    "name": "Sales Dataset",
                    "description": "Sales data from Splunk",
                    "configuredBy": "test-user@example.com",
                    "refreshSchedule": {
                        "enabled": True,
                        "frequency": "Daily"
                    }
                },
                {
                    "id": "dataset-2",
                    "name": "Marketing Dataset",
                    "description": "Marketing campaign data",
                    "configuredBy": "test-user@example.com",
                    "refreshSchedule": {
                        "enabled": False
                    }
                }
            ]
        }
        
        datasets = await manager.list_datasets("workspace-1")
        
        assert len(datasets) == 2
        assert datasets[0]["id"] == "dataset-1"
        assert datasets[0]["name"] == "Sales Dataset"
        assert datasets[1]["id"] == "dataset-2"
        assert datasets[1]["name"] == "Marketing Dataset"

    @pytest.mark.asyncio
    async def test_refresh_dataset(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test refreshing a dataset."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock refresh response
        mock_client.post.return_value.status_code = 202
        mock_client.post.return_value.json.return_value = {}
        
        result = await manager.refresh_dataset("workspace-1", "dataset-1")
        
        assert result["success"] is True
        assert result["message"] == "Dataset refresh initiated"

    @pytest.mark.asyncio
    async def test_refresh_dataset_failure(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test dataset refresh failure."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock refresh failure
        mock_client.post.return_value.status_code = 400
        mock_client.post.return_value.json.return_value = {
            "error": {
                "code": "InvalidRequest",
                "message": "Dataset refresh failed"
            }
        }
        
        result = await manager.refresh_dataset("workspace-1", "dataset-1")
        
        assert result["success"] is False
        assert "Dataset refresh failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_refresh_history(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test getting dataset refresh history."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock refresh history response
        mock_client.get.return_value.json.return_value = {
            "value": [
                {
                    "refreshType": "Scheduled",
                    "startTime": "2025-01-18T10:00:00Z",
                    "endTime": "2025-01-18T10:05:00Z",
                    "status": "Completed"
                },
                {
                    "refreshType": "OnDemand",
                    "startTime": "2025-01-18T09:00:00Z",
                    "endTime": "2025-01-18T09:02:00Z",
                    "status": "Completed"
                }
            ]
        }
        
        history = await manager.get_refresh_history("workspace-1", "dataset-1")
        
        assert len(history) == 2
        assert history[0]["status"] == "Completed"
        assert history[0]["refreshType"] == "Scheduled"
        assert history[1]["refreshType"] == "OnDemand"

    @pytest.mark.asyncio
    async def test_test_connection(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test connection testing."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        
        # Mock successful authentication and API call
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        mock_client.get.return_value.json.return_value = {
            "value": []
        }
        
        result = await manager.test_connection()
        
        assert result["success"] is True
        assert "workspaces_count" in result

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, powerbi_integration, mock_msal_app):
        """Test connection testing failure."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        
        # Mock authentication failure
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Authentication failed"
        }
        
        result = await manager.test_connection()
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_publish_report(self, powerbi_integration, mock_msal_app, mock_httpx_client):
        """Test publishing a report."""
        mock_app, mock_msal = mock_msal_app
        mock_client = mock_httpx_client
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        # Mock publish response
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "id": "new-report-id",
            "name": "New Report",
            "webUrl": "https://powerbi.example.com/reports/new-report-id"
        }
        
        report_data = {
            "name": "New Report",
            "file_path": "/tmp/test.pbix"
        }
        
        with patch('builtins.open', mock_open(read_data=b"fake pbix content")):
            with patch('os.path.exists', return_value=True):
                result = await manager.publish_report("workspace-1", report_data)
                
                assert result["id"] == "new-report-id"
                assert result["name"] == "New Report"

    @pytest.mark.asyncio
    async def test_publish_report_file_not_found(self, powerbi_integration, mock_msal_app):
        """Test publishing a report with missing file."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        manager._authenticated = True
        manager.access_token = "test-access-token"
        
        report_data = {
            "name": "New Report",
            "file_path": "/tmp/nonexistent.pbix"
        }
        
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ValueError, match="Report file not found"):
                await manager.publish_report("workspace-1", report_data)

    def test_get_auth_headers(self, powerbi_integration, mock_msal_app):
        """Test authentication header generation."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        manager.access_token = "test-access-token"
        
        headers = manager._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-access-token"
        assert headers["Content-Type"] == "application/json"

    def test_get_auth_headers_not_authenticated(self, powerbi_integration, mock_msal_app):
        """Test authentication header generation when not authenticated."""
        mock_app, mock_msal = mock_msal_app
        
        manager = PowerBIManager(powerbi_integration)
        manager.access_token = None
        
        with pytest.raises(Exception, match="Not authenticated"):
            manager._get_auth_headers()


# Helper function for mocking file operations
def mock_open(read_data=b''):
    """Mock file open operation."""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)