"""
Test configuration and fixtures for Webhook Service tests.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.models.webhook_models import (
    WebhookStatus, EventType, DeliveryStatus, WebhookMethod,
    WebhookEndpoint, WebhookEvent, WebhookDelivery
)
from app.models.user_models import WebhookUser


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client():
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_database():
    """Mock database session."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.scalar = AsyncMock()
    mock_db.scalars = AsyncMock()
    return mock_db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.exists = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.info = AsyncMock()
    return mock_redis


@pytest.fixture
def mock_webhook_manager(mock_database, mock_redis):
    """Mock webhook manager service."""
    with patch('app.services.webhook_manager.WebhookManager') as MockManager:
        manager_instance = AsyncMock()
        
        # Mock basic CRUD operations
        manager_instance.create_endpoint = AsyncMock()
        manager_instance.list_endpoints = AsyncMock()
        manager_instance.get_endpoint = AsyncMock()
        manager_instance.update_endpoint = AsyncMock()
        manager_instance.delete_endpoint = AsyncMock()
        
        # Mock health and analytics
        manager_instance.check_database_health = AsyncMock(return_value=True)
        manager_instance.check_redis_health = AsyncMock(return_value=True)
        manager_instance.get_analytics = AsyncMock()
        
        MockManager.return_value = manager_instance
        yield manager_instance


@pytest.fixture
def mock_event_processor(mock_database, mock_redis):
    """Mock event processor service."""
    with patch('app.services.event_processor.EventProcessor') as MockProcessor:
        processor_instance = AsyncMock()
        
        # Mock event operations
        processor_instance.create_event = AsyncMock()
        processor_instance.list_events = AsyncMock()
        processor_instance.get_event = AsyncMock()
        processor_instance.process_event = AsyncMock()
        
        MockProcessor.return_value = processor_instance
        yield processor_instance


@pytest.fixture
def mock_delivery_service():
    """Mock delivery service."""
    with patch('app.services.delivery_service.DeliveryService') as MockService:
        service_instance = AsyncMock()
        
        # Mock delivery operations
        service_instance.list_deliveries = AsyncMock()
        service_instance.get_delivery = AsyncMock()
        service_instance.retry_delivery = AsyncMock()
        service_instance.start_processor = AsyncMock()
        
        MockService.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_user():
    """Mock user for authentication."""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.roles = ["basic"]
    user.permissions = ["webhook:create", "webhook:read", "webhook:update", "webhook:delete", "webhook:trigger", "webhook:retry", "webhook:analytics"]
    user.has_permission = Mock(return_value=True)
    return user


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


@pytest.fixture
def sample_webhook_endpoint_data():
    """Sample webhook endpoint data for testing."""
    return {
        "name": "Test Webhook",
        "description": "A test webhook endpoint",
        "url": "https://example.com/webhook",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "secret": "test-secret-123",
        "event_types": ["query.completed", "alert.triggered"],
        "event_filters": {"source": "test"},
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 300
    }


@pytest.fixture
def sample_webhook_endpoint():
    """Sample webhook endpoint model."""
    endpoint = Mock(spec=WebhookEndpoint)
    endpoint.id = str(uuid4())
    endpoint.user_id = "test-user-123"
    endpoint.name = "Test Webhook"
    endpoint.description = "A test webhook endpoint"
    endpoint.url = "https://example.com/webhook"
    endpoint.method = WebhookMethod.POST
    endpoint.headers = {"Content-Type": "application/json"}
    endpoint.secret = "test-secret-123"
    endpoint.status = WebhookStatus.ACTIVE
    endpoint.event_types = ["query.completed", "alert.triggered"]
    endpoint.event_filters = {"source": "test"}
    endpoint.timeout = 30
    endpoint.retry_attempts = 3
    endpoint.retry_delay = 300
    endpoint.total_deliveries = 10
    endpoint.successful_deliveries = 8
    endpoint.failed_deliveries = 2
    endpoint.last_delivery_at = datetime.utcnow()
    endpoint.last_success_at = datetime.utcnow()
    endpoint.last_failure_at = None
    endpoint.created_at = datetime.utcnow()
    endpoint.updated_at = datetime.utcnow()
    return endpoint


@pytest.fixture
def sample_webhook_event_data():
    """Sample webhook event data for testing."""
    return {
        "event_type": "query.completed",
        "source": "test-service",
        "payload": {
            "query_id": "test-query-123",
            "status": "completed",
            "results": {"count": 100}
        },
        "metadata": {
            "user_id": "test-user-123",
            "timestamp": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_webhook_event():
    """Sample webhook event model."""
    event = Mock(spec=WebhookEvent)
    event.id = str(uuid4())
    event.endpoint_id = str(uuid4())
    event.event_type = EventType.QUERY_COMPLETED
    event.source = "test-service"
    event.payload = {
        "query_id": "test-query-123",
        "status": "completed",
        "results": {"count": 100}
    }
    event.metadata = {
        "user_id": "test-user-123",
        "timestamp": datetime.utcnow().isoformat()
    }
    event.processed = False
    event.processed_at = None
    event.created_at = datetime.utcnow()
    return event


@pytest.fixture
def sample_webhook_delivery():
    """Sample webhook delivery model."""
    delivery = Mock(spec=WebhookDelivery)
    delivery.id = str(uuid4())
    delivery.endpoint_id = str(uuid4())
    delivery.event_id = str(uuid4())
    delivery.status = DeliveryStatus.DELIVERED
    delivery.attempt_number = 1
    delivery.max_attempts = 3
    delivery.http_status = 200
    delivery.response_body = '{"success": true}'
    delivery.response_headers = {"Content-Type": "application/json"}
    delivery.error_message = None
    delivery.scheduled_at = datetime.utcnow()
    delivery.attempted_at = datetime.utcnow()
    delivery.completed_at = datetime.utcnow()
    delivery.response_time = 150.5
    delivery.next_retry_at = None
    delivery.retry_count = 0
    delivery.created_at = datetime.utcnow()
    delivery.updated_at = datetime.utcnow()
    return delivery


@pytest.fixture
def sample_webhook_analytics():
    """Sample webhook analytics data."""
    return {
        "total_endpoints": 5,
        "active_endpoints": 4,
        "total_events": 100,
        "total_deliveries": 95,
        "successful_deliveries": 85,
        "failed_deliveries": 10,
        "success_rate": 89.5,
        "average_response_time": 275.3,
        "events_by_type": {
            "query.completed": 50,
            "alert.triggered": 30,
            "report.generated": 20
        },
        "deliveries_by_status": {
            "delivered": 85,
            "failed": 10
        },
        "recent_activity": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "webhook.created",
                "endpoint_name": "Test Webhook"
            }
        ]
    }


@pytest.fixture
def app_with_mocks(mock_webhook_manager, mock_event_processor, mock_delivery_service):
    """FastAPI app with mocked services."""
    app.state.webhook_manager = mock_webhook_manager
    app.state.event_processor = mock_event_processor
    app.state.delivery_service = mock_delivery_service
    app.state.db = mock_database()
    app.state.redis = mock_redis()
    return app


@pytest.fixture
def db_session():
    """Database session fixture."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


@pytest.fixture
def redis_client():
    """Redis client fixture."""
    redis = AsyncMock()
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock()
    redis.expire = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.info = AsyncMock()
    return redis


# Test data generators
@pytest.fixture
def webhook_endpoint_factory():
    """Factory for creating webhook endpoint test data."""
    def create_endpoint(
        user_id: str = "test-user-123",
        name: str = "Test Webhook",
        url: str = "https://example.com/webhook",
        status: WebhookStatus = WebhookStatus.ACTIVE,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": name,
            "description": kwargs.get("description", "A test webhook"),
            "url": url,
            "method": kwargs.get("method", "POST"),
            "headers": kwargs.get("headers", {}),
            "secret": kwargs.get("secret", "test-secret"),
            "status": status.value if isinstance(status, WebhookStatus) else status,
            "event_types": kwargs.get("event_types", ["query.completed"]),
            "event_filters": kwargs.get("event_filters", {}),
            "timeout": kwargs.get("timeout", 30),
            "retry_attempts": kwargs.get("retry_attempts", 3),
            "retry_delay": kwargs.get("retry_delay", 300),
            "total_deliveries": kwargs.get("total_deliveries", 0),
            "successful_deliveries": kwargs.get("successful_deliveries", 0),
            "failed_deliveries": kwargs.get("failed_deliveries", 0),
            "last_delivery_at": kwargs.get("last_delivery_at"),
            "last_success_at": kwargs.get("last_success_at"),
            "last_failure_at": kwargs.get("last_failure_at"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }
    return create_endpoint


@pytest.fixture
def webhook_event_factory():
    """Factory for creating webhook event test data."""
    def create_event(
        endpoint_id: str = None,
        event_type: EventType = EventType.QUERY_COMPLETED,
        source: str = "test-service",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "endpoint_id": endpoint_id or str(uuid4()),
            "event_type": event_type.value if isinstance(event_type, EventType) else event_type,
            "source": source,
            "payload": kwargs.get("payload", {"test": "data"}),
            "metadata": kwargs.get("metadata", {}),
            "processed": kwargs.get("processed", False),
            "processed_at": kwargs.get("processed_at"),
            "created_at": kwargs.get("created_at", datetime.utcnow())
        }
    return create_event


@pytest.fixture
def webhook_delivery_factory():
    """Factory for creating webhook delivery test data."""
    def create_delivery(
        endpoint_id: str = None,
        event_id: str = None,
        status: DeliveryStatus = DeliveryStatus.DELIVERED,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "endpoint_id": endpoint_id or str(uuid4()),
            "event_id": event_id or str(uuid4()),
            "status": status.value if isinstance(status, DeliveryStatus) else status,
            "attempt_number": kwargs.get("attempt_number", 1),
            "max_attempts": kwargs.get("max_attempts", 3),
            "http_status": kwargs.get("http_status", 200),
            "response_body": kwargs.get("response_body", '{"success": true}'),
            "response_headers": kwargs.get("response_headers", {}),
            "error_message": kwargs.get("error_message"),
            "scheduled_at": kwargs.get("scheduled_at", datetime.utcnow()),
            "attempted_at": kwargs.get("attempted_at", datetime.utcnow()),
            "completed_at": kwargs.get("completed_at", datetime.utcnow()),
            "response_time": kwargs.get("response_time", 100.0),
            "next_retry_at": kwargs.get("next_retry_at"),
            "retry_count": kwargs.get("retry_count", 0),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }
    return create_delivery


# Mock decorators for skipping tests when dependencies are not available
@pytest.fixture
def skip_if_no_redis():
    """Skip test if Redis is not available."""
    def decorator(func):
        return pytest.mark.skipif(
            True,  # Always skip for unit tests
            reason="Redis not available in unit tests"
        )(func)
    return decorator


@pytest.fixture
def skip_if_no_database():
    """Skip test if database is not available."""
    def decorator(func):
        return pytest.mark.skipif(
            True,  # Always skip for unit tests
            reason="Database not available in unit tests"
        )(func)
    return decorator


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_patches():
    """Automatically cleanup patches after each test."""
    yield
    # Any cleanup code here if needed


# Performance testing fixtures
@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "max_response_time": 1.0,  # seconds
        "max_memory_usage": 100,   # MB
        "concurrent_requests": 10
    }


# Integration test fixtures
@pytest.fixture
def integration_config():
    """Configuration for integration tests."""
    return {
        "test_webhook_url": "https://httpbin.org/post",
        "test_timeout": 10,
        "test_retry_attempts": 2
    }