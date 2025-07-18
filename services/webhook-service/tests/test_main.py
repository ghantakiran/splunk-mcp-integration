"""
Tests for Webhook Service main application.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


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
def test_list_webhooks_authenticated(mock_manager, mock_auth, client):
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
def test_create_webhook_endpoint(mock_manager, mock_auth, client):
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
def test_trigger_webhook_event(mock_processor, mock_auth, client):
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


def test_invalid_webhook_data(mock_auth, client):
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
def test_list_deliveries(mock_service, mock_auth, client):
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


if __name__ == "__main__":
    pytest.main([__file__])