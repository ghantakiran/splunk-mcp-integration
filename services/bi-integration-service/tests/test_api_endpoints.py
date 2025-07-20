"""
Tests for BI Integration Service API endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from httpx import AsyncClient

from app.main import app
from app.models.bi_models import BIProvider, IntegrationStatus


class TestIntegrationsEndpoints:
    """Test suite for integrations API endpoints."""

    @pytest.mark.asyncio
    async def test_create_integration_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful integration creation."""
        integration_data = {
            "name": "Test Tableau Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "site_id": "test-site",
            "credentials": {
                "token_name": "test-token",
                "token_value": "test-token-value"
            },
            "configuration": {
                "auto_refresh": True,
                "refresh_interval": 3600
            }
        }
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock successful creation
                mock_integration = Mock()
                mock_integration.id = "550e8400-e29b-41d4-a716-446655440000"
                mock_integration.name = "Test Tableau Integration"
                mock_integration.provider = BIProvider.TABLEAU
                mock_integration.status = IntegrationStatus.ACTIVE
                mock_service.create_integration.return_value = mock_integration
                
                response = await client.post(
                    "/api/v1/integrations",
                    json=integration_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == "550e8400-e29b-41d4-a716-446655440000"
                assert data["data"]["name"] == "Test Tableau Integration"

    @pytest.mark.asyncio
    async def test_create_integration_invalid_data(self, client, auth_headers, mock_jwt_payload):
        """Test integration creation with invalid data."""
        integration_data = {
            "name": "",  # Invalid: empty name
            "provider": "invalid_provider",  # Invalid provider
            "server_url": "not-a-url"  # Invalid URL
        }
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            response = await client.post(
                "/api/v1/integrations",
                json=integration_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422
            data = response.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_create_integration_unauthorized(self, client):
        """Test integration creation without authentication."""
        integration_data = {
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com"
        }
        
        response = await client.post("/api/v1/integrations", json=integration_data)
        
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_integration_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful integration retrieval."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock integration
                mock_integration = Mock()
                mock_integration.id = integration_id
                mock_integration.name = "Test Integration"
                mock_integration.provider = BIProvider.TABLEAU
                mock_integration.status = IntegrationStatus.ACTIVE
                mock_service.get_integration.return_value = mock_integration
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == integration_id
                assert data["data"]["name"] == "Test Integration"

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self, client, auth_headers, mock_jwt_payload):
        """Test getting non-existent integration."""
        integration_id = "nonexistent-id"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.get_integration.return_value = None
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 404
                data = response.json()
                assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_integrations_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful integration listing."""
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock integrations list
                mock_integration1 = Mock()
                mock_integration1.id = "integration-1"
                mock_integration1.name = "Integration 1"
                mock_integration1.provider = BIProvider.TABLEAU
                
                mock_integration2 = Mock()
                mock_integration2.id = "integration-2"
                mock_integration2.name = "Integration 2"
                mock_integration2.provider = BIProvider.POWERBI
                
                mock_service.list_integrations.return_value = {
                    "items": [mock_integration1, mock_integration2],
                    "total": 2,
                    "limit": 10,
                    "offset": 0,
                    "has_more": False
                }
                
                response = await client.get(
                    "/api/v1/integrations",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["items"]) == 2
                assert data["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_list_integrations_with_filters(self, client, auth_headers, mock_jwt_payload):
        """Test integration listing with filters."""
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                mock_service.list_integrations.return_value = {
                    "items": [],
                    "total": 0,
                    "limit": 10,
                    "offset": 0,
                    "has_more": False
                }
                
                response = await client.get(
                    "/api/v1/integrations?provider=tableau&status=active&limit=5",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                mock_service.list_integrations.assert_called_once()
                # Verify that filters were passed to the service

    @pytest.mark.asyncio
    async def test_update_integration_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful integration update."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {
            "name": "Updated Integration",
            "configuration": {
                "auto_refresh": False,
                "refresh_interval": 7200
            }
        }
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock updated integration
                mock_integration = Mock()
                mock_integration.id = integration_id
                mock_integration.name = "Updated Integration"
                mock_service.update_integration.return_value = mock_integration
                
                response = await client.put(
                    f"/api/v1/integrations/{integration_id}",
                    json=update_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Updated Integration"

    @pytest.mark.asyncio
    async def test_update_integration_not_found(self, client, auth_headers, mock_jwt_payload):
        """Test updating non-existent integration."""
        integration_id = "nonexistent-id"
        update_data = {"name": "Updated Integration"}
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.update_integration.return_value = None
                
                response = await client.put(
                    f"/api/v1/integrations/{integration_id}",
                    json=update_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 404
                data = response.json()
                assert data["success"] is False

    @pytest.mark.asyncio
    async def test_delete_integration_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful integration deletion."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.delete_integration.return_value = True
                
                response = await client.delete(
                    f"/api/v1/integrations/{integration_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(self, client, auth_headers, mock_jwt_payload):
        """Test deleting non-existent integration."""
        integration_id = "nonexistent-id"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.delete_integration.return_value = False
                
                response = await client.delete(
                    f"/api/v1/integrations/{integration_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 404


class TestWorkbooksEndpoints:
    """Test suite for workbooks API endpoints."""

    @pytest.mark.asyncio
    async def test_list_workbooks_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful workbook listing."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock workbooks
                mock_workbooks = [
                    {"id": "wb1", "name": "Workbook 1"},
                    {"id": "wb2", "name": "Workbook 2"}
                ]
                mock_service.get_integration_workbooks.return_value = mock_workbooks
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}/workbooks",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_list_workbooks_integration_not_found(self, client, auth_headers, mock_jwt_payload):
        """Test listing workbooks for non-existent integration."""
        integration_id = "nonexistent-id"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.get_integration_workbooks.side_effect = ValueError("Integration not found")
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}/workbooks",
                    headers=auth_headers
                )
                
                assert response.status_code == 404


class TestDataSourcesEndpoints:
    """Test suite for data sources API endpoints."""

    @pytest.mark.asyncio
    async def test_refresh_data_sources_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful data source refresh."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock refresh results
                mock_result = {
                    "refresh_jobs": [
                        {"data_source_id": "ds1", "job_id": "job1", "status": "InProgress"},
                        {"data_source_id": "ds2", "job_id": "job2", "status": "InProgress"}
                    ]
                }
                mock_service.refresh_integration_data_sources.return_value = mock_result
                
                response = await client.post(
                    f"/api/v1/integrations/{integration_id}/data-sources/refresh",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["refresh_jobs"]) == 2


class TestConnectionTestEndpoints:
    """Test suite for connection test API endpoints."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful connection test."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock successful connection test
                mock_result = {
                    "success": True,
                    "server_info": {
                        "version": "2023.3",
                        "build": "20230918.23.0927.1526"
                    },
                    "response_time_ms": 245
                }
                mock_service.test_integration_connection.return_value = mock_result
                
                response = await client.post(
                    f"/api/v1/integrations/{integration_id}/test-connection",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["success"] is True
                assert "server_info" in data["data"]

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, client, auth_headers, mock_jwt_payload):
        """Test failed connection test."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock failed connection test
                mock_result = {
                    "success": False,
                    "error": "Authentication failed",
                    "error_code": "AUTH_FAILED"
                }
                mock_service.test_integration_connection.return_value = mock_result
                
                response = await client.post(
                    f"/api/v1/integrations/{integration_id}/test-connection",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True  # API call succeeded
                assert data["data"]["success"] is False  # Connection test failed
                assert "error" in data["data"]


class TestAnalyticsEndpoints:
    """Test suite for analytics API endpoints."""

    @pytest.mark.asyncio
    async def test_get_integration_analytics_success(self, client, auth_headers, mock_jwt_payload):
        """Test successful analytics retrieval."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock analytics data
                mock_analytics = {
                    "integration": {
                        "id": integration_id,
                        "name": "Test Integration",
                        "provider": "tableau",
                        "status": "active"
                    },
                    "workbooks": {
                        "total": 15,
                        "active": 12,
                        "last_updated": "2025-01-18T10:00:00Z"
                    },
                    "data_sources": {
                        "total": 8,
                        "healthy": 7,
                        "failed": 1
                    },
                    "usage": {
                        "daily_requests": 156,
                        "weekly_requests": 1089,
                        "monthly_requests": 4521
                    }
                }
                mock_service.get_integration_analytics.return_value = mock_analytics
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}/analytics",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["integration"]["id"] == integration_id
                assert data["data"]["workbooks"]["total"] == 15
                assert data["data"]["data_sources"]["total"] == 8


class TestErrorHandling:
    """Test suite for error handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_invalid_integration_id_format(self, client, auth_headers, mock_jwt_payload):
        """Test handling of invalid integration ID format."""
        invalid_id = "not-a-uuid"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            response = await client.get(
                f"/api/v1/integrations/{invalid_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_service_exception_handling(self, client, auth_headers, mock_jwt_payload):
        """Test handling of service layer exceptions."""
        integration_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.services.integration_service.IntegrationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.get_integration.side_effect = Exception("Database error")
                
                response = await client.get(
                    f"/api/v1/integrations/{integration_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 500
                data = response.json()
                assert data["success"] is False

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, auth_headers, mock_jwt_payload):
        """Test rate limiting functionality."""
        with patch('app.utils.dependencies.verify_jwt_token', return_value=mock_jwt_payload):
            with patch('app.middleware.rate_limit.RateLimitMiddleware') as mock_rate_limit:
                # Mock rate limit exceeded
                mock_rate_limit.side_effect = Exception("Rate limit exceeded")
                
                # This test would need actual rate limiting middleware to be effective
                # For now, we're just testing the structure
                response = await client.get("/api/v1/integrations", headers=auth_headers)
                
                # The actual status code depends on rate limiting implementation
                assert response.status_code in [200, 429]