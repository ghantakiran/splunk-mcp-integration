"""
Test cases for cloud instance management endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime

from app.main import app
from app.models.user import User
from app.models.cloud import (
    CloudInstanceCreate,
    CloudInstanceUpdate,
    CloudInstanceResponse,
    CloudConnectionRequest,
    EndpointType,
    InstanceStatus,
    HealthStatus
)


class TestCloudEndpoints:
    """Test cloud instance management endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_admin = True
        user.has_permission = Mock(return_value=True)
        return user
    
    @pytest.fixture
    def sample_instance_data(self):
        """Sample cloud instance data"""
        return {
            "name": "Test Cloud Instance",
            "description": "Test instance for unit tests",
            "endpoint_type": "cloud",
            "host": "test.splunkcloud.com",
            "port": 443,
            "scheme": "https",
            "tenant_id": "test-tenant",
            "priority": 100,
            "weight": 100,
            "max_connections": 50,
            "timeout": 30,
            "auth_token": "test-token",
            "tags": {"environment": "test"}
        }
    
    @pytest.fixture
    def sample_instance_response(self):
        """Sample cloud instance response"""
        return {
            "id": 1,
            "name": "Test Cloud Instance",
            "description": "Test instance for unit tests",
            "endpoint_type": "cloud",
            "host": "test.splunkcloud.com",
            "port": 443,
            "scheme": "https",
            "tenant_id": "test-tenant",
            "priority": 100,
            "weight": 100,
            "max_connections": 50,
            "timeout": 30,
            "tags": {"environment": "test"},
            "status": "active",
            "created_at": "2025-01-24T10:00:00Z",
            "updated_at": "2025-01-24T10:00:00Z",
            "created_by": 1,
            "updated_by": None
        }
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.create_instance')
    async def test_create_cloud_instance_success(self, mock_create, mock_get_user, client, mock_user, sample_instance_data, sample_instance_response):
        """Test successful cloud instance creation"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_create.return_value = CloudInstanceResponse(**sample_instance_response)
        
        # Make request
        response = client.post("/api/v1/cloud/instances", json=sample_instance_data)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Cloud Instance"
        assert data["data"]["endpoint_type"] == "cloud"
        assert "message" in data
        
        # Verify service was called
        mock_create.assert_called_once()
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    async def test_create_cloud_instance_unauthorized(self, mock_get_user, client, sample_instance_data):
        """Test cloud instance creation with insufficient permissions"""
        # Setup mock user without permissions
        user = Mock(spec=User)
        user.id = 1
        user.is_admin = False
        user.has_permission = Mock(return_value=False)
        mock_get_user.return_value = user
        
        # Make request
        response = client.post("/api/v1/cloud/instances", json=sample_instance_data)
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient permissions" in data["detail"]
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.list_instances')
    async def test_list_cloud_instances_success(self, mock_list, mock_get_user, client, mock_user, sample_instance_response):
        """Test successful cloud instance listing"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_list.return_value = [CloudInstanceResponse(**sample_instance_response)]
        
        # Make request
        response = client.get("/api/v1/cloud/instances")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test Cloud Instance"
        
        # Verify service was called with defaults
        mock_list.assert_called_once_with(
            limit=100,
            offset=0,
            tenant_id=None,
            status=None,
            include_health=True,
            user_id=1
        )
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.list_instances')
    async def test_list_cloud_instances_with_filters(self, mock_list, mock_get_user, client, mock_user):
        """Test cloud instance listing with filters"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_list.return_value = []
        
        # Make request with filters
        response = client.get(
            "/api/v1/cloud/instances",
            params={
                "limit": 50,
                "offset": 10,
                "tenant_id": "test-tenant",
                "status": "active",
                "include_health": False
            }
        )
        
        # Assertions
        assert response.status_code == 200
        
        # Verify service was called with filters
        mock_list.assert_called_once_with(
            limit=50,
            offset=10,
            tenant_id="test-tenant",
            status="active",
            include_health=False,
            user_id=1
        )
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_instance')
    async def test_get_cloud_instance_success(self, mock_get, mock_get_user, client, mock_user, sample_instance_response):
        """Test successful cloud instance retrieval"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get.return_value = CloudInstanceResponse(**sample_instance_response)
        
        # Make request
        response = client.get("/api/v1/cloud/instances/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["name"] == "Test Cloud Instance"
        
        # Verify service was called
        mock_get.assert_called_once_with(
            instance_id=1,
            include_metrics=False,
            user_id=1
        )
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_instance')
    async def test_get_cloud_instance_not_found(self, mock_get, mock_get_user, client, mock_user):
        """Test cloud instance retrieval when instance not found"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get.return_value = None
        
        # Make request
        response = client.get("/api/v1/cloud/instances/999")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Cloud instance not found" in data["detail"]
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.update_instance')
    async def test_update_cloud_instance_success(self, mock_update, mock_get_user, client, mock_user, sample_instance_response):
        """Test successful cloud instance update"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        updated_response = {**sample_instance_response, "priority": 150}
        mock_update.return_value = CloudInstanceResponse(**updated_response)
        
        # Make request
        update_data = {"priority": 150, "status": "maintenance"}
        response = client.put("/api/v1/cloud/instances/1", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["priority"] == 150
        
        # Verify service was called
        mock_update.assert_called_once()
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    async def test_update_cloud_instance_unauthorized(self, mock_get_user, client):
        """Test cloud instance update with insufficient permissions"""
        # Setup mock user without permissions
        user = Mock(spec=User)
        user.id = 1
        user.is_admin = False
        user.has_permission = Mock(return_value=False)
        mock_get_user.return_value = user
        
        # Make request
        update_data = {"priority": 150}
        response = client.put("/api/v1/cloud/instances/1", json=update_data)
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient permissions" in data["detail"]
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.delete_instance')
    async def test_delete_cloud_instance_success(self, mock_delete, mock_get_user, client, mock_user):
        """Test successful cloud instance deletion"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_delete.return_value = True
        
        # Make request
        response = client.delete("/api/v1/cloud/instances/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True
        assert data["data"]["instance_id"] == 1
        
        # Verify service was called
        mock_delete.assert_called_once_with(
            instance_id=1,
            force=False,
            deleted_by=1
        )
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.delete_instance')
    async def test_delete_cloud_instance_not_found(self, mock_delete, mock_get_user, client, mock_user):
        """Test cloud instance deletion when instance not found"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_delete.return_value = False
        
        # Make request
        response = client.delete("/api/v1/cloud/instances/999")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Cloud instance not found" in data["detail"]
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_optimal_connection')
    async def test_get_optimal_connection_success(self, mock_get_connection, mock_get_user, client, mock_user):
        """Test successful optimal connection retrieval"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        connection_response = {
            "endpoint_id": 1,
            "host": "test.splunkcloud.com",
            "port": 443,
            "scheme": "https",
            "tenant_id": "test-tenant",
            "session_token": "session-123",
            "expires_at": "2025-01-24T11:00:00Z",
            "load_balancer_algorithm": "round_robin",
            "connection_metadata": {}
        }
        mock_get_connection.return_value = connection_response
        
        # Make request
        request_data = {
            "tenant_id": "test-tenant",
            "endpoint_type": "cloud",
            "lb_config_name": "default"
        }
        response = client.post("/api/v1/cloud/connection", json=request_data)
        
        # Assertions  
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["endpoint_id"] == 1
        assert data["data"]["host"] == "test.splunkcloud.com"
        
        # Verify service was called
        mock_get_connection.assert_called_once()
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_optimal_connection')
    async def test_get_optimal_connection_none_available(self, mock_get_connection, mock_get_user, client, mock_user):
        """Test optimal connection when none available"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_connection.return_value = None
        
        # Make request
        request_data = {"tenant_id": "test-tenant"}
        response = client.post("/api/v1/cloud/connection", json=request_data)
        
        # Assertions
        assert response.status_code == 503
        data = response.json()
        assert "No healthy cloud instances available" in data["detail"]
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_instance_health')
    async def test_get_instance_health_success(self, mock_get_health, mock_get_user, client, mock_user):
        """Test successful instance health retrieval"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        health_data = {
            "instance_id": 1,
            "status": "healthy",
            "response_time_ms": 150.5,
            "status_code": 200,
            "error_message": None,
            "checked_at": "2025-01-24T10:30:00Z"
        }
        mock_get_health.return_value = health_data
        
        # Make request
        response = client.get("/api/v1/cloud/instances/1/health")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["instance_id"] == 1
        assert data["data"]["status"] == "healthy"
        assert data["data"]["response_time_ms"] == 150.5
        
        # Verify service was called
        mock_get_health.assert_called_once_with(instance_id=1, hours=24)
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.trigger_health_check')
    async def test_trigger_health_check_success(self, mock_trigger, mock_get_user, client, mock_user):
        """Test successful health check trigger"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        health_data = {
            "instance_id": 1,
            "status": "healthy",
            "response_time_ms": 120.0,
            "status_code": 200,
            "error_message": None,
            "checked_at": "2025-01-24T10:35:00Z"
        }
        mock_trigger.return_value = health_data
        
        # Make request
        response = client.post("/api/v1/cloud/instances/1/health-check")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["instance_id"] == 1
        assert data["data"]["status"] == "healthy"
        
        # Verify service was called
        mock_trigger.assert_called_once_with(instance_id=1, triggered_by=1)
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_instance_metrics')
    async def test_get_instance_metrics_success(self, mock_get_metrics, mock_get_user, client, mock_user):
        """Test successful instance metrics retrieval"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        metrics_data = {
            "instance_id": 1,
            "time_range_hours": 24,
            "total_requests": 1000,
            "successful_requests": 950,
            "failed_requests": 50,
            "avg_response_time_ms": 200.5,
            "min_response_time_ms": 50.0,
            "max_response_time_ms": 1000.0,
            "uptime_percentage": 0.99,
            "performance_history": []
        }
        mock_get_metrics.return_value = metrics_data
        
        # Make request
        response = client.get("/api/v1/cloud/instances/1/metrics")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["instance_id"] == 1
        assert data["data"]["total_requests"] == 1000
        assert data["data"]["uptime_percentage"] == 0.99
        
        # Verify service was called
        mock_get_metrics.assert_called_once_with(instance_id=1, hours=24)
    
    @patch('app.api.v1.endpoints.cloud.get_current_user')
    @patch('app.services.cloud_service.CloudService.get_health_summary')
    async def test_get_health_summary_success(self, mock_get_summary, mock_get_user, client, mock_user):
        """Test successful health summary retrieval"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        summary_data = {
            "total_instances": 5,
            "healthy_instances": 4,
            "degraded_instances": 1,
            "unhealthy_instances": 0,
            "avg_response_time_ms": 180.5,
            "health_percentage": 0.8,
            "last_updated": "2025-01-24T10:40:00Z"
        }
        mock_get_summary.return_value = summary_data
        
        # Make request
        response = client.get("/api/v1/cloud/health-summary")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_instances"] == 5
        assert data["data"]["healthy_instances"] == 4
        assert data["data"]["health_percentage"] == 0.8
        
        # Verify service was called
        mock_get_summary.assert_called_once()


class TestCloudModels:
    """Test cloud data models"""
    
    def test_cloud_instance_create_validation(self):
        """Test CloudInstanceCreate model validation"""
        # Valid data
        valid_data = {
            "name": "Test Instance",
            "endpoint_type": "cloud",
            "host": "test.splunkcloud.com",
            "auth_token": "test-token"
        }
        instance = CloudInstanceCreate(**valid_data)
        assert instance.name == "Test Instance"
        assert instance.endpoint_type == EndpointType.CLOUD
        assert instance.port == 443  # Default
        
        # Test validation error for missing auth
        invalid_data = {
            "name": "Test Instance",
            "endpoint_type": "cloud",
            "host": "test.splunkcloud.com"
        }
        with pytest.raises(ValueError):
            CloudInstanceCreate(**invalid_data)
    
    def test_cloud_instance_update_partial(self):
        """Test CloudInstanceUpdate with partial data"""
        update_data = {
            "priority": 150,
            "status": "maintenance"
        }
        update = CloudInstanceUpdate(**update_data)
        assert update.priority == 150
        assert update.status == InstanceStatus.MAINTENANCE
        assert update.name is None  # Not provided
    
    def test_cloud_connection_request_defaults(self):
        """Test CloudConnectionRequest with defaults"""
        request = CloudConnectionRequest()
        assert request.lb_config_name == "default"
        assert request.tenant_id is None
        assert request.requirements == {}
    
    def test_endpoint_type_enum(self):
        """Test EndpointType enum values"""
        assert EndpointType.CLOUD.value == "cloud"
        assert EndpointType.ENTERPRISE.value == "enterprise"
    
    def test_instance_status_enum(self):
        """Test InstanceStatus enum values"""
        assert InstanceStatus.ACTIVE.value == "active"
        assert InstanceStatus.INACTIVE.value == "inactive"
        assert InstanceStatus.MAINTENANCE.value == "maintenance"
        assert InstanceStatus.UNHEALTHY.value == "unhealthy"
    
    def test_health_status_enum(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"  
        assert HealthStatus.UNKNOWN.value == "unknown"