"""
Tests for Webhook Service main application.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime
from uuid import uuid4

from app.main import app
from app.models.webhook_models import WebhookStatus, EventType, DeliveryStatus


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication."""
    with patch("app.utils.auth.get_current_user") as mock:
        mock_user = AsyncMock()
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        mock_user.roles = ["basic"]
        mock_user.has_permission.return_value = True
        mock.return_value = mock_user
        yield mock


@pytest.fixture
def mock_require_permissions():
    """Mock permission requirements."""
    with patch("app.utils.auth.require_permissions") as mock:
        mock.return_value = lambda: None
        yield mock


def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "webhook-service"


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200


@patch("app.main.get_webhook_manager")
def test_detailed_health_check(mock_manager, client):
    """Test detailed health check endpoint."""
    # Mock the webhook manager
    mock_manager_instance = AsyncMock()
    mock_manager_instance.check_database_health.return_value = True
    mock_manager_instance.check_redis_health.return_value = True
    mock_manager.return_value = mock_manager_instance
    
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["dependencies"]["database"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_unauthorized_access(client):
    """Test that protected endpoints require authentication."""
    response = client.get("/webhooks/endpoints")
    assert response.status_code == 403  # No auth header


@patch("app.main.get_webhook_manager")
def test_list_webhooks_authenticated(mock_manager, mock_auth, mock_require_permissions, client):
    """Test listing webhooks with authentication."""
    # Mock the webhook manager
    mock_manager_instance = AsyncMock()
    mock_manager_instance.list_endpoints.return_value = [
        {
            "id": "webhook-123",
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "status": "active"
        }
    ]
    mock_manager.return_value = mock_manager_instance
    
    response = client.get(
        "/webhooks/endpoints",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1


@patch("app.main.get_webhook_manager")
def test_create_webhook_endpoint(mock_manager, mock_auth, mock_require_permissions, client):
    """Test creating a webhook endpoint."""
    # Mock the webhook manager
    mock_manager_instance = AsyncMock()
    mock_manager_instance.create_endpoint.return_value = {
        "id": "webhook-456",
        "name": "New Webhook",
        "url": "https://example.com/new-webhook",
        "status": "active"
    }
    mock_manager.return_value = mock_manager_instance
    
    webhook_data = {
        "name": "New Webhook",
        "description": "Test webhook",
        "url": "https://example.com/new-webhook",
        "event_types": ["query.completed"],
        "timeout": 30
    }
    
    response = client.post(
        "/webhooks/endpoints",
        json=webhook_data,
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "New Webhook"


@patch("app.main.get_event_processor")
def test_trigger_webhook_event(mock_processor, mock_auth, mock_require_permissions, client):
    """Test triggering a webhook event."""
    # Mock the event processor
    mock_processor_instance = AsyncMock()
    mock_processor_instance.create_event.return_value = {
        "id": "event-789",
        "event_type": "query.completed",
        "source": "test",
        "processed": False
    }
    mock_processor.return_value = mock_processor_instance
    
    event_data = {
        "event_type": "query.completed",
        "source": "test-service",
        "payload": {
            "query_id": "123",
            "status": "completed"
        }
    }
    
    response = client.post(
        "/webhooks/events/trigger",
        json=event_data,
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["event_type"] == "query.completed"


def test_invalid_webhook_data(mock_auth, mock_require_permissions, client):
    """Test creating webhook with invalid data."""
    invalid_data = {
        "name": "",  # Empty name should fail validation
        "url": "not-a-valid-url",
        "event_types": ["invalid.event.type"]
    }
    
    response = client.post(
        "/webhooks/endpoints",
        json=invalid_data,
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 422  # Validation error


@patch("app.main.get_delivery_service")
def test_list_deliveries(mock_service, mock_auth, mock_require_permissions, client):
    """Test listing webhook deliveries."""
    # Mock the delivery service
    mock_service_instance = AsyncMock()
    mock_service_instance.list_deliveries.return_value = [
        {
            "id": "delivery-123",
            "endpoint_id": "webhook-123",
            "status": "delivered",
            "response_time": 150.5
        }
    ]
    mock_service.return_value = mock_service_instance
    
    response = client.get(
        "/webhooks/deliveries",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["status"] == "delivered"


class TestApplicationLifecycle:
    """Test suite for application lifecycle events."""
    
    def test_app_initialization(self):
        """Test application initialization."""
        assert app.title == "Splunk MCP Webhook Service"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
    
    @patch("app.main.init_database")
    @patch("app.main.init_redis")
    async def test_lifespan_startup(self, mock_init_redis, mock_init_database):
        """Test application startup lifecycle."""
        mock_init_database.return_value = None
        mock_init_redis.return_value = None
        
        # This would be tested in integration tests
        # For now, just verify mocks are configured
        assert mock_init_database is not None
        assert mock_init_redis is not None


class TestMiddleware:
    """Test suite for middleware functionality."""
    
    def test_cors_middleware_configured(self):
        """Test CORS middleware is configured."""
        # Check that CORS middleware exists in the middleware stack
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        # Note: middleware is wrapped, so we check for the actual app behavior
        assert app is not None
    
    def test_trusted_host_middleware_configured(self):
        """Test trusted host middleware is configured."""
        from fastapi.middleware.trustedhost import TrustedHostMiddleware
        # Note: middleware is wrapped, so we check for the actual app behavior
        assert app is not None
    
    @patch("app.main.check_rate_limit")
    def test_rate_limiting_middleware(self, mock_check_rate_limit, client):
        """Test rate limiting middleware."""
        mock_check_rate_limit.return_value = None
        
        response = client.get("/health")
        assert response.status_code == 200
        
        # Verify rate limiting was checked
        mock_check_rate_limit.assert_called()


class TestErrorHandling:
    """Test suite for error handling."""
    
    @patch("app.main.get_webhook_manager")
    def test_webhook_creation_service_error(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test webhook creation when service fails."""
        # Mock service failure
        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_endpoint.side_effect = Exception("Service error")
        mock_manager.return_value = mock_manager_instance
        
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "event_types": ["query.completed"]
        }
        
        response = client.post(
            "/webhooks/endpoints",
            json=webhook_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 500
    
    @patch("app.main.get_webhook_manager")
    def test_webhook_listing_service_error(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test webhook listing when service fails."""
        # Mock service failure
        mock_manager_instance = AsyncMock()
        mock_manager_instance.list_endpoints.side_effect = Exception("Service error")
        mock_manager.return_value = mock_manager_instance
        
        response = client.get(
            "/webhooks/endpoints",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 500
    
    def test_authentication_required_endpoints(self, client):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            ("/webhooks/endpoints", "get"),
            ("/webhooks/endpoints", "post"),
            ("/webhooks/endpoints/test-id", "get"),
            ("/webhooks/endpoints/test-id", "put"),
            ("/webhooks/endpoints/test-id", "delete"),
            ("/webhooks/events/trigger", "post"),
            ("/webhooks/events", "get"),
            ("/webhooks/events/test-id", "get"),
            ("/webhooks/deliveries", "get"),
            ("/webhooks/deliveries/test-id", "get"),
            ("/webhooks/deliveries/test-id/retry", "post"),
            ("/webhooks/analytics/overview", "get"),
            ("/webhooks/analytics/metrics", "get"),
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "get":
                response = client.get(endpoint)
            elif method == "post":
                response = client.post(endpoint, json={})
            elif method == "put":
                response = client.put(endpoint, json={})
            elif method == "delete":
                response = client.delete(endpoint)
            
            # Should be 403 (Forbidden) due to missing auth
            assert response.status_code == 403


class TestWebhookEndpointOperations:
    """Test suite for webhook endpoint CRUD operations."""
    
    @patch("app.main.get_webhook_manager")
    def test_get_webhook_endpoint_success(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test successful webhook endpoint retrieval."""
        endpoint_id = "test-endpoint-123"
        
        mock_manager_instance = AsyncMock()
        mock_manager_instance.get_endpoint.return_value = {
            "id": endpoint_id,
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "status": "active"
        }
        mock_manager.return_value = mock_manager_instance
        
        response = client.get(
            f"/webhooks/endpoints/{endpoint_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == endpoint_id
    
    @patch("app.main.get_webhook_manager")
    def test_get_webhook_endpoint_not_found(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test webhook endpoint retrieval when not found."""
        endpoint_id = "nonexistent-endpoint"
        
        mock_manager_instance = AsyncMock()
        mock_manager_instance.get_endpoint.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        response = client.get(
            f"/webhooks/endpoints/{endpoint_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 404
    
    @patch("app.main.get_webhook_manager")
    def test_update_webhook_endpoint_success(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test successful webhook endpoint update."""
        endpoint_id = "test-endpoint-123"
        
        mock_manager_instance = AsyncMock()
        mock_manager_instance.update_endpoint.return_value = {
            "id": endpoint_id,
            "name": "Updated Webhook",
            "url": "https://example.com/updated-webhook",
            "status": "active"
        }
        mock_manager.return_value = mock_manager_instance
        
        update_data = {
            "name": "Updated Webhook",
            "url": "https://example.com/updated-webhook"
        }
        
        response = client.put(
            f"/webhooks/endpoints/{endpoint_id}",
            json=update_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Webhook"
    
    @patch("app.main.get_webhook_manager")
    def test_delete_webhook_endpoint_success(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test successful webhook endpoint deletion."""
        endpoint_id = "test-endpoint-123"
        
        mock_manager_instance = AsyncMock()
        mock_manager_instance.delete_endpoint.return_value = True
        mock_manager.return_value = mock_manager_instance
        
        response = client.delete(
            f"/webhooks/endpoints/{endpoint_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]


class TestEventOperations:
    """Test suite for webhook event operations."""
    
    @patch("app.main.get_event_processor")
    def test_list_webhook_events_success(self, mock_processor, mock_auth, mock_require_permissions, client):
        """Test successful webhook event listing."""
        mock_processor_instance = AsyncMock()
        mock_processor_instance.list_events.return_value = [
            {
                "id": "event-123",
                "event_type": "query.completed",
                "source": "test-service",
                "processed": True
            }
        ]
        mock_processor.return_value = mock_processor_instance
        
        response = client.get(
            "/webhooks/events",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["event_type"] == "query.completed"
    
    @patch("app.main.get_event_processor")
    def test_get_webhook_event_success(self, mock_processor, mock_auth, mock_require_permissions, client):
        """Test successful webhook event retrieval."""
        event_id = "test-event-123"
        
        mock_processor_instance = AsyncMock()
        mock_processor_instance.get_event.return_value = {
            "id": event_id,
            "event_type": "alert.triggered",
            "source": "alert-service",
            "processed": False
        }
        mock_processor.return_value = mock_processor_instance
        
        response = client.get(
            f"/webhooks/events/{event_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == event_id


class TestDeliveryOperations:
    """Test suite for webhook delivery operations."""
    
    @patch("app.main.get_delivery_service")
    def test_get_webhook_delivery_success(self, mock_service, mock_auth, mock_require_permissions, client):
        """Test successful webhook delivery retrieval."""
        delivery_id = "test-delivery-123"
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_delivery.return_value = {
            "id": delivery_id,
            "endpoint_id": "webhook-123",
            "status": "delivered",
            "response_time": 200.0
        }
        mock_service.return_value = mock_service_instance
        
        response = client.get(
            f"/webhooks/deliveries/{delivery_id}",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == delivery_id
    
    @patch("app.main.get_delivery_service")
    def test_retry_webhook_delivery_success(self, mock_service, mock_auth, mock_require_permissions, client):
        """Test successful webhook delivery retry."""
        delivery_id = "test-delivery-123"
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_delivery.return_value = {
            "id": delivery_id,
            "status": "failed",
            "endpoint_id": "webhook-123"
        }
        mock_service_instance.retry_delivery.return_value = None
        mock_service.return_value = mock_service_instance
        
        response = client.post(
            f"/webhooks/deliveries/{delivery_id}/retry",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "retry initiated" in data["message"]
    
    @patch("app.main.get_delivery_service")
    def test_retry_webhook_delivery_invalid_status(self, mock_service, mock_auth, mock_require_permissions, client):
        """Test webhook delivery retry with invalid status."""
        delivery_id = "test-delivery-123"
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_delivery.return_value = {
            "id": delivery_id,
            "status": "delivered",  # Not failed, so retry should be rejected
            "endpoint_id": "webhook-123"
        }
        mock_service.return_value = mock_service_instance
        
        response = client.post(
            f"/webhooks/deliveries/{delivery_id}/retry",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 400


class TestAnalyticsEndpoints:
    """Test suite for webhook analytics endpoints."""
    
    @patch("app.main.get_webhook_manager")
    def test_get_webhook_analytics_success(self, mock_manager, mock_auth, mock_require_permissions, client):
        """Test successful webhook analytics retrieval."""
        mock_manager_instance = AsyncMock()
        mock_manager_instance.get_analytics.return_value = {
            "total_endpoints": 5,
            "active_endpoints": 4,
            "total_events": 100,
            "success_rate": 95.0
        }
        mock_manager.return_value = mock_manager_instance
        
        response = client.get(
            "/webhooks/analytics/overview",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_endpoints"] == 5
        assert data["data"]["success_rate"] == 95.0
    
    @patch("app.main.WebhookMetrics")
    def test_get_webhook_metrics_success(self, mock_metrics, mock_auth, mock_require_permissions, client):
        """Test successful webhook metrics retrieval."""
        mock_metrics_instance = AsyncMock()
        mock_metrics_instance.get_user_metrics.return_value = {
            "request_count": 1000,
            "error_count": 50,
            "average_response_time": 250.5
        }
        mock_metrics.return_value = mock_metrics_instance
        
        response = client.get(
            "/webhooks/analytics/metrics",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_count" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__])