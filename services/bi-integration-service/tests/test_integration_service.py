"""
Tests for Integration Service functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.integration_service import IntegrationService
from app.models.bi_models import BIIntegration, BIProvider, IntegrationStatus, DataSourceType, RefreshStatus


class TestIntegrationService:
    """Test suite for IntegrationService class."""

    @pytest.fixture
    def integration_service(self, db_session):
        """Create an IntegrationService instance."""
        return IntegrationService(db_session)

    @pytest.fixture
    def sample_integration_data(self):
        """Sample integration data for testing."""
        return {
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "site_id": "test-site",
            "credentials": {
                "token_name": "test-token",
                "token_value": "test-token-value"
            },
            "configuration": {
                "auto_refresh": True,
                "refresh_interval": 3600,
                "timeout": 300
            }
        }

    @pytest.fixture
    def mock_tableau_manager(self):
        """Mock Tableau manager."""
        with patch('app.services.integration_service.TableauManager') as mock_class:
            mock_manager = MagicMock()
            mock_class.return_value = mock_manager
            
            # Mock manager methods
            mock_manager.authenticate.return_value = AsyncMock(return_value=True)
            mock_manager.test_connection.return_value = AsyncMock(return_value={"success": True})
            mock_manager.list_workbooks.return_value = AsyncMock(return_value=[])
            mock_manager.list_data_sources.return_value = AsyncMock(return_value=[])
            
            yield mock_manager

    @pytest.fixture
    def mock_powerbi_manager(self):
        """Mock Power BI manager."""
        with patch('app.services.integration_service.PowerBIManager') as mock_class:
            mock_manager = MagicMock()
            mock_class.return_value = mock_manager
            
            # Mock manager methods
            mock_manager.authenticate.return_value = AsyncMock(return_value=True)
            mock_manager.test_connection.return_value = AsyncMock(return_value={"success": True})
            mock_manager.list_workspaces.return_value = AsyncMock(return_value=[])
            mock_manager.list_reports.return_value = AsyncMock(return_value=[])
            
            yield mock_manager

    @pytest.mark.asyncio
    async def test_create_integration_tableau(self, integration_service, sample_integration_data, mock_tableau_manager):
        """Test creating a Tableau integration."""
        integration_data = sample_integration_data.copy()
        integration_data["provider"] = "tableau"
        
        # Mock database operations
        with patch.object(integration_service.db, 'add') as mock_add:
            with patch.object(integration_service.db, 'commit') as mock_commit:
                with patch.object(integration_service.db, 'refresh') as mock_refresh:
                    mock_commit.return_value = AsyncMock()
                    mock_refresh.return_value = AsyncMock()
                    
                    result = await integration_service.create_integration(integration_data, "test-user@example.com")
                    
                    assert result is not None
                    assert result.name == "Test Integration"
                    assert result.provider == BIProvider.TABLEAU
                    assert result.status == IntegrationStatus.ACTIVE
                    mock_add.assert_called_once()
                    mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_integration_powerbi(self, integration_service, sample_integration_data, mock_powerbi_manager):
        """Test creating a Power BI integration."""
        integration_data = sample_integration_data.copy()
        integration_data["provider"] = "powerbi"
        integration_data["credentials"] = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "tenant_id": "test-tenant-id"
        }
        
        # Mock database operations
        with patch.object(integration_service.db, 'add') as mock_add:
            with patch.object(integration_service.db, 'commit') as mock_commit:
                with patch.object(integration_service.db, 'refresh') as mock_refresh:
                    mock_commit.return_value = AsyncMock()
                    mock_refresh.return_value = AsyncMock()
                    
                    result = await integration_service.create_integration(integration_data, "test-user@example.com")
                    
                    assert result is not None
                    assert result.name == "Test Integration"
                    assert result.provider == BIProvider.POWERBI
                    assert result.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_integration_invalid_provider(self, integration_service, sample_integration_data):
        """Test creating an integration with invalid provider."""
        integration_data = sample_integration_data.copy()
        integration_data["provider"] = "invalid_provider"
        
        with pytest.raises(ValueError, match="Unsupported BI provider"):
            await integration_service.create_integration(integration_data, "test-user@example.com")

    @pytest.mark.asyncio
    async def test_get_integration(self, integration_service):
        """Test getting an integration by ID."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock database query
        mock_result = AsyncMock()
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.name = "Test Integration"
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.get_integration(integration_id)
            
            assert result is not None
            assert result.id == integration_id
            assert result.name == "Test Integration"

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self, integration_service):
        """Test getting a non-existent integration."""
        integration_id = "nonexistent-id"
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.get_integration(integration_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_list_integrations(self, integration_service):
        """Test listing integrations with pagination."""
        # Mock integrations
        mock_integration1 = Mock(spec=BIIntegration)
        mock_integration1.id = "integration-1"
        mock_integration1.name = "Integration 1"
        mock_integration1.provider = BIProvider.TABLEAU
        
        mock_integration2 = Mock(spec=BIIntegration)
        mock_integration2.id = "integration-2"
        mock_integration2.name = "Integration 2"
        mock_integration2.provider = BIProvider.POWERBI
        
        # Mock database queries
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_integration1, mock_integration2]
        
        with patch.object(integration_service.db, 'execute') as mock_execute:
            mock_execute.side_effect = [mock_count_result, mock_result]
            
            result = await integration_service.list_integrations(limit=10, offset=0)
            
            assert result["total"] == 2
            assert len(result["items"]) == 2
            assert result["items"][0].name == "Integration 1"
            assert result["items"][1].name == "Integration 2"

    @pytest.mark.asyncio
    async def test_list_integrations_with_filters(self, integration_service):
        """Test listing integrations with filters."""
        # Mock integrations
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = "integration-1"
        mock_integration.name = "Tableau Integration"
        mock_integration.provider = BIProvider.TABLEAU
        
        # Mock database queries
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_integration]
        
        with patch.object(integration_service.db, 'execute') as mock_execute:
            mock_execute.side_effect = [mock_count_result, mock_result]
            
            result = await integration_service.list_integrations(
                limit=10, 
                offset=0, 
                provider="tableau",
                status="active"
            )
            
            assert result["total"] == 1
            assert len(result["items"]) == 1
            assert result["items"][0].provider == BIProvider.TABLEAU

    @pytest.mark.asyncio
    async def test_update_integration(self, integration_service):
        """Test updating an integration."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {
            "name": "Updated Integration",
            "configuration": {
                "auto_refresh": False,
                "refresh_interval": 7200
            }
        }
        
        # Mock existing integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.name = "Test Integration"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            with patch.object(integration_service.db, 'commit') as mock_commit:
                mock_commit.return_value = AsyncMock()
                
                result = await integration_service.update_integration(integration_id, update_data)
                
                assert result is not None
                assert mock_integration.name == "Updated Integration"
                mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_integration_not_found(self, integration_service):
        """Test updating a non-existent integration."""
        integration_id = "nonexistent-id"
        update_data = {"name": "Updated Integration"}
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.update_integration(integration_id, update_data)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_integration(self, integration_service):
        """Test deleting an integration."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock existing integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            with patch.object(integration_service.db, 'delete') as mock_delete:
                with patch.object(integration_service.db, 'commit') as mock_commit:
                    mock_commit.return_value = AsyncMock()
                    
                    result = await integration_service.delete_integration(integration_id)
                    
                    assert result is True
                    mock_delete.assert_called_once_with(mock_integration)
                    mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(self, integration_service):
        """Test deleting a non-existent integration."""
        integration_id = "nonexistent-id"
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.delete_integration(integration_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_test_integration_connection_tableau(self, integration_service, mock_tableau_manager):
        """Test testing Tableau integration connection."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.provider = BIProvider.TABLEAU
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock successful connection test
        mock_tableau_manager.test_connection.return_value = {"success": True, "server_info": {}}
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.test_integration_connection(integration_id)
            
            assert result["success"] is True
            assert "server_info" in result

    @pytest.mark.asyncio
    async def test_test_integration_connection_powerbi(self, integration_service, mock_powerbi_manager):
        """Test testing Power BI integration connection."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.provider = BIProvider.POWERBI
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock successful connection test
        mock_powerbi_manager.test_connection.return_value = {"success": True, "workspaces_count": 5}
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.test_integration_connection(integration_id)
            
            assert result["success"] is True
            assert "workspaces_count" in result

    @pytest.mark.asyncio
    async def test_test_integration_connection_not_found(self, integration_service):
        """Test testing connection for non-existent integration."""
        integration_id = "nonexistent-id"
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            with pytest.raises(ValueError, match="Integration not found"):
                await integration_service.test_integration_connection(integration_id)

    @pytest.mark.asyncio
    async def test_get_integration_workbooks_tableau(self, integration_service, mock_tableau_manager):
        """Test getting workbooks for Tableau integration."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.provider = BIProvider.TABLEAU
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock workbooks
        mock_workbooks = [
            {"id": "wb1", "name": "Workbook 1"},
            {"id": "wb2", "name": "Workbook 2"}
        ]
        mock_tableau_manager.list_workbooks.return_value = mock_workbooks
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.get_integration_workbooks(integration_id)
            
            assert len(result) == 2
            assert result[0]["id"] == "wb1"
            assert result[1]["id"] == "wb2"

    @pytest.mark.asyncio
    async def test_get_integration_workbooks_powerbi(self, integration_service, mock_powerbi_manager):
        """Test getting reports for Power BI integration."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.provider = BIProvider.POWERBI
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock workspaces and reports
        mock_workspaces = [{"id": "ws1", "name": "Workspace 1"}]
        mock_reports = [
            {"id": "rpt1", "name": "Report 1"},
            {"id": "rpt2", "name": "Report 2"}
        ]
        
        mock_powerbi_manager.list_workspaces.return_value = mock_workspaces
        mock_powerbi_manager.list_reports.return_value = mock_reports
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.get_integration_workbooks(integration_id)
            
            assert len(result) == 2
            assert result[0]["id"] == "rpt1"
            assert result[1]["id"] == "rpt2"

    @pytest.mark.asyncio
    async def test_refresh_integration_data_sources(self, integration_service, mock_tableau_manager):
        """Test refreshing integration data sources."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.provider = BIProvider.TABLEAU
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock data sources and refresh results
        mock_data_sources = [
            {"id": "ds1", "name": "Data Source 1"},
            {"id": "ds2", "name": "Data Source 2"}
        ]
        mock_refresh_result = {"job_id": "job1", "status": "InProgress"}
        
        mock_tableau_manager.list_data_sources.return_value = mock_data_sources
        mock_tableau_manager.refresh_data_source.return_value = mock_refresh_result
        
        with patch.object(integration_service.db, 'execute', return_value=mock_result):
            result = await integration_service.refresh_integration_data_sources(integration_id)
            
            assert "refresh_jobs" in result
            assert len(result["refresh_jobs"]) == 2

    @pytest.mark.asyncio
    async def test_get_integration_analytics(self, integration_service):
        """Test getting integration analytics."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock integration
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.id = integration_id
        mock_integration.name = "Test Integration"
        mock_integration.provider = BIProvider.TABLEAU
        mock_integration.status = IntegrationStatus.ACTIVE
        mock_integration.created_at = "2025-01-01T00:00:00Z"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        
        # Mock database queries for analytics
        mock_workbook_count = AsyncMock()
        mock_workbook_count.scalar.return_value = 5
        
        mock_datasource_count = AsyncMock()
        mock_datasource_count.scalar.return_value = 3
        
        with patch.object(integration_service.db, 'execute') as mock_execute:
            mock_execute.side_effect = [mock_result, mock_workbook_count, mock_datasource_count]
            
            result = await integration_service.get_integration_analytics(integration_id)
            
            assert result["integration"]["id"] == integration_id
            assert result["integration"]["name"] == "Test Integration"
            assert result["workbooks"]["total"] == 5
            assert result["data_sources"]["total"] == 3

    @pytest.mark.asyncio
    async def test_validate_integration_credentials(self, integration_service):
        """Test validating integration credentials."""
        # Test Tableau credentials
        tableau_creds = {
            "token_name": "test-token",
            "token_value": "test-token-value"
        }
        
        result = integration_service._validate_credentials("tableau", tableau_creds)
        assert result is True
        
        # Test Power BI credentials
        powerbi_creds = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "tenant_id": "test-tenant-id"
        }
        
        result = integration_service._validate_credentials("powerbi", powerbi_creds)
        assert result is True
        
        # Test invalid credentials
        invalid_creds = {"invalid": "credentials"}
        
        with pytest.raises(ValueError):
            integration_service._validate_credentials("tableau", invalid_creds)

    def test_get_manager_for_integration_tableau(self, integration_service, mock_tableau_manager):
        """Test getting manager for Tableau integration."""
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.provider = BIProvider.TABLEAU
        
        manager = integration_service._get_manager_for_integration(mock_integration)
        
        assert manager is not None

    def test_get_manager_for_integration_powerbi(self, integration_service, mock_powerbi_manager):
        """Test getting manager for Power BI integration."""
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.provider = BIProvider.POWERBI
        
        manager = integration_service._get_manager_for_integration(mock_integration)
        
        assert manager is not None

    def test_get_manager_for_integration_unsupported(self, integration_service):
        """Test getting manager for unsupported integration."""
        mock_integration = Mock(spec=BIIntegration)
        mock_integration.provider = BIProvider.LOOKER  # Unsupported for now
        
        with pytest.raises(ValueError, match="Unsupported BI provider"):
            integration_service._get_manager_for_integration(mock_integration)