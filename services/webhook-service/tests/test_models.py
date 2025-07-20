"""
Tests for Webhook Service data models.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.models.webhook_models import (
    WebhookStatus, EventType, DeliveryStatus, WebhookMethod,
    WebhookEndpoint, WebhookEvent, WebhookDelivery, WebhookSubscription,
    WebhookLog, WebhookMetric,
    WebhookEndpointCreate, WebhookEndpointUpdate, WebhookEndpointResponse,
    WebhookEventCreate, WebhookEventResponse,
    WebhookDeliveryResponse, WebhookAnalytics
)


class TestEnums:
    """Test suite for enum classes."""

    def test_webhook_status_enum(self):
        """Test WebhookStatus enum values."""
        assert WebhookStatus.ACTIVE == "active"
        assert WebhookStatus.INACTIVE == "inactive"
        assert WebhookStatus.SUSPENDED == "suspended"
        assert WebhookStatus.FAILED == "failed"
        
        # Test enum iteration
        statuses = list(WebhookStatus)
        assert len(statuses) == 4

    def test_event_type_enum(self):
        """Test EventType enum values."""
        assert EventType.QUERY_COMPLETED == "query.completed"
        assert EventType.ALERT_TRIGGERED == "alert.triggered"
        assert EventType.DASHBOARD_CREATED == "dashboard.created"
        assert EventType.REPORT_GENERATED == "report.generated"
        assert EventType.ERROR_OCCURRED == "error.occurred"
        assert EventType.SYSTEM_STATUS_CHANGED == "system.status_changed"
        assert EventType.USER_ACTION == "user.action"
        assert EventType.DATA_UPDATED == "data.updated"
        
        # Test enum iteration
        types = list(EventType)
        assert len(types) == 8

    def test_delivery_status_enum(self):
        """Test DeliveryStatus enum values."""
        assert DeliveryStatus.PENDING == "pending"
        assert DeliveryStatus.DELIVERED == "delivered"
        assert DeliveryStatus.FAILED == "failed"
        assert DeliveryStatus.RETRYING == "retrying"
        assert DeliveryStatus.CANCELLED == "cancelled"
        
        # Test enum iteration
        statuses = list(DeliveryStatus)
        assert len(statuses) == 5

    def test_webhook_method_enum(self):
        """Test WebhookMethod enum values."""
        assert WebhookMethod.POST == "POST"
        assert WebhookMethod.PUT == "PUT"
        assert WebhookMethod.PATCH == "PATCH"
        
        # Test enum iteration
        methods = list(WebhookMethod)
        assert len(methods) == 3


class TestWebhookEndpointCreate:
    """Test suite for WebhookEndpointCreate model."""

    def test_valid_webhook_endpoint_create(self):
        """Test valid webhook endpoint creation."""
        data = {
            "name": "Test Webhook",
            "description": "A test webhook endpoint",
            "url": "https://example.com/webhook",
            "method": WebhookMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "secret": "test-secret-123",
            "event_types": [EventType.QUERY_COMPLETED, EventType.ALERT_TRIGGERED],
            "event_filters": {"source": "test"},
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 300
        }
        
        endpoint = WebhookEndpointCreate(**data)
        
        assert endpoint.name == "Test Webhook"
        assert endpoint.description == "A test webhook endpoint"
        assert str(endpoint.url) == "https://example.com/webhook"
        assert endpoint.method == WebhookMethod.POST
        assert endpoint.headers == {"Content-Type": "application/json"}
        assert endpoint.secret == "test-secret-123"
        assert endpoint.event_types == [EventType.QUERY_COMPLETED, EventType.ALERT_TRIGGERED]
        assert endpoint.event_filters == {"source": "test"}
        assert endpoint.timeout == 30
        assert endpoint.retry_attempts == 3
        assert endpoint.retry_delay == 300

    def test_webhook_endpoint_create_minimal_data(self):
        """Test webhook endpoint creation with minimal required data."""
        data = {
            "name": "Minimal Webhook",
            "url": "https://example.com/minimal"
        }
        
        endpoint = WebhookEndpointCreate(**data)
        
        assert endpoint.name == "Minimal Webhook"
        assert str(endpoint.url) == "https://example.com/minimal"
        assert endpoint.description is None
        assert endpoint.method == WebhookMethod.POST  # Default
        assert endpoint.headers == {}  # Default
        assert endpoint.secret is None
        assert endpoint.event_types == []  # Default
        assert endpoint.event_filters == {}  # Default
        assert endpoint.timeout == 30  # Default
        assert endpoint.retry_attempts == 3  # Default
        assert endpoint.retry_delay == 300  # Default

    def test_invalid_webhook_name_empty(self):
        """Test validation failure for empty webhook name."""
        data = {
            "name": "",
            "url": "https://example.com/webhook"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_webhook_name_too_long(self):
        """Test validation failure for webhook name too long."""
        data = {
            "name": "x" * 256,  # Exceeds max length of 255
            "url": "https://example.com/webhook"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_webhook_url(self):
        """Test validation failure for invalid webhook URL."""
        data = {
            "name": "Test Webhook",
            "url": "not-a-valid-url"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        url_errors = [e for e in errors if e["loc"] == ("url",)]
        assert len(url_errors) > 0

    def test_invalid_headers_not_dict(self):
        """Test validation failure for invalid headers format."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "headers": "not-a-dict"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        header_errors = [e for e in errors if e["loc"] == ("headers",)]
        assert len(header_errors) > 0

    def test_invalid_headers_non_string_values(self):
        """Test validation failure for non-string header values."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "headers": {"Content-Type": 123}  # Non-string value
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        header_errors = [e for e in errors if "headers" in str(e["loc"])]
        assert len(header_errors) > 0

    def test_invalid_secret_too_short(self):
        """Test validation failure for secret too short."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "secret": "short"  # Less than 8 characters
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        secret_errors = [e for e in errors if e["loc"] == ("secret",)]
        assert len(secret_errors) > 0

    def test_invalid_timeout_range(self):
        """Test validation failure for timeout out of range."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "timeout": 500  # Exceeds max of 300
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        timeout_errors = [e for e in errors if e["loc"] == ("timeout",)]
        assert len(timeout_errors) > 0

    def test_invalid_retry_attempts_range(self):
        """Test validation failure for retry attempts out of range."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "retry_attempts": 15  # Exceeds max of 10
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        retry_errors = [e for e in errors if e["loc"] == ("retry_attempts",)]
        assert len(retry_errors) > 0

    def test_invalid_event_filters_not_dict(self):
        """Test validation failure for invalid event filters format."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "event_filters": "not-a-dict"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEndpointCreate(**data)
        
        errors = exc_info.value.errors()
        filter_errors = [e for e in errors if e["loc"] == ("event_filters",)]
        assert len(filter_errors) > 0


class TestWebhookEndpointUpdate:
    """Test suite for WebhookEndpointUpdate model."""

    def test_valid_webhook_endpoint_update(self):
        """Test valid webhook endpoint update."""
        data = {
            "name": "Updated Webhook",
            "description": "Updated description",
            "url": "https://example.com/updated-webhook",
            "status": WebhookStatus.INACTIVE,
            "timeout": 60
        }
        
        endpoint = WebhookEndpointUpdate(**data)
        
        assert endpoint.name == "Updated Webhook"
        assert endpoint.description == "Updated description"
        assert str(endpoint.url) == "https://example.com/updated-webhook"
        assert endpoint.status == WebhookStatus.INACTIVE
        assert endpoint.timeout == 60

    def test_webhook_endpoint_update_partial_data(self):
        """Test webhook endpoint update with partial data."""
        data = {
            "name": "Partially Updated Webhook"
        }
        
        endpoint = WebhookEndpointUpdate(**data)
        
        assert endpoint.name == "Partially Updated Webhook"
        assert endpoint.description is None
        assert endpoint.url is None
        assert endpoint.status is None
        assert endpoint.timeout is None

    def test_webhook_endpoint_update_empty_data(self):
        """Test webhook endpoint update with no data."""
        endpoint = WebhookEndpointUpdate()
        
        assert endpoint.name is None
        assert endpoint.description is None
        assert endpoint.url is None
        assert endpoint.status is None


class TestWebhookEndpointResponse:
    """Test suite for WebhookEndpointResponse model."""

    def test_valid_webhook_endpoint_response(self):
        """Test valid webhook endpoint response."""
        endpoint_id = str(uuid4())
        user_id = str(uuid4())
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()
        
        data = {
            "id": endpoint_id,
            "user_id": user_id,
            "name": "Test Webhook",
            "description": "A test webhook",
            "url": "https://example.com/webhook",
            "method": WebhookMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "status": WebhookStatus.ACTIVE,
            "event_types": [EventType.QUERY_COMPLETED],
            "event_filters": {"source": "test"},
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 300,
            "total_deliveries": 10,
            "successful_deliveries": 8,
            "failed_deliveries": 2,
            "last_delivery_at": created_at,
            "last_success_at": created_at,
            "last_failure_at": None,
            "created_at": created_at,
            "updated_at": updated_at
        }
        
        response = WebhookEndpointResponse(**data)
        
        assert response.id == endpoint_id
        assert response.user_id == user_id
        assert response.name == "Test Webhook"
        assert response.status == WebhookStatus.ACTIVE
        assert response.total_deliveries == 10
        assert response.successful_deliveries == 8
        assert response.failed_deliveries == 2


class TestWebhookEventCreate:
    """Test suite for WebhookEventCreate model."""

    def test_valid_webhook_event_create(self):
        """Test valid webhook event creation."""
        payload = {
            "query_id": "test-query-123",
            "status": "completed",
            "results": {"count": 100}
        }
        metadata = {
            "user_id": "test-user-123",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        data = {
            "event_type": EventType.QUERY_COMPLETED,
            "source": "test-service",
            "payload": payload,
            "metadata": metadata
        }
        
        event = WebhookEventCreate(**data)
        
        assert event.event_type == EventType.QUERY_COMPLETED
        assert event.source == "test-service"
        assert event.payload == payload
        assert event.metadata == metadata

    def test_webhook_event_create_minimal_data(self):
        """Test webhook event creation with minimal data."""
        data = {
            "event_type": EventType.ALERT_TRIGGERED,
            "source": "alert-service",
            "payload": {"alert_id": "alert-123"}
        }
        
        event = WebhookEventCreate(**data)
        
        assert event.event_type == EventType.ALERT_TRIGGERED
        assert event.source == "alert-service"
        assert event.payload == {"alert_id": "alert-123"}
        assert event.metadata == {}  # Default

    def test_invalid_event_source_empty(self):
        """Test validation failure for empty event source."""
        data = {
            "event_type": EventType.QUERY_COMPLETED,
            "source": "",
            "payload": {"test": "data"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEventCreate(**data)
        
        errors = exc_info.value.errors()
        source_errors = [e for e in errors if e["loc"] == ("source",)]
        assert len(source_errors) > 0

    def test_invalid_event_source_too_long(self):
        """Test validation failure for event source too long."""
        data = {
            "event_type": EventType.QUERY_COMPLETED,
            "source": "x" * 256,  # Exceeds max length of 255
            "payload": {"test": "data"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEventCreate(**data)
        
        errors = exc_info.value.errors()
        source_errors = [e for e in errors if e["loc"] == ("source",)]
        assert len(source_errors) > 0

    def test_invalid_payload_not_dict(self):
        """Test validation failure for non-dict payload."""
        data = {
            "event_type": EventType.QUERY_COMPLETED,
            "source": "test-service",
            "payload": "not-a-dict"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookEventCreate(**data)
        
        errors = exc_info.value.errors()
        payload_errors = [e for e in errors if e["loc"] == ("payload",)]
        assert len(payload_errors) > 0


class TestWebhookEventResponse:
    """Test suite for WebhookEventResponse model."""

    def test_valid_webhook_event_response(self):
        """Test valid webhook event response."""
        event_id = str(uuid4())
        endpoint_id = str(uuid4())
        created_at = datetime.utcnow()
        processed_at = datetime.utcnow()
        
        data = {
            "id": event_id,
            "endpoint_id": endpoint_id,
            "event_type": EventType.QUERY_COMPLETED,
            "source": "test-service",
            "payload": {"query_id": "123"},
            "metadata": {"user_id": "user-123"},
            "processed": True,
            "processed_at": processed_at,
            "created_at": created_at
        }
        
        response = WebhookEventResponse(**data)
        
        assert response.id == event_id
        assert response.endpoint_id == endpoint_id
        assert response.event_type == EventType.QUERY_COMPLETED
        assert response.source == "test-service"
        assert response.processed is True
        assert response.processed_at == processed_at
        assert response.created_at == created_at


class TestWebhookDeliveryResponse:
    """Test suite for WebhookDeliveryResponse model."""

    def test_valid_webhook_delivery_response(self):
        """Test valid webhook delivery response."""
        delivery_id = str(uuid4())
        endpoint_id = str(uuid4())
        event_id = str(uuid4())
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()
        scheduled_at = datetime.utcnow()
        attempted_at = datetime.utcnow()
        completed_at = datetime.utcnow()
        
        data = {
            "id": delivery_id,
            "endpoint_id": endpoint_id,
            "event_id": event_id,
            "status": DeliveryStatus.DELIVERED,
            "attempt_number": 1,
            "max_attempts": 3,
            "http_status": 200,
            "response_body": '{"success": true}',
            "response_headers": {"Content-Type": "application/json"},
            "error_message": None,
            "scheduled_at": scheduled_at,
            "attempted_at": attempted_at,
            "completed_at": completed_at,
            "response_time": 150.5,
            "next_retry_at": None,
            "retry_count": 0,
            "created_at": created_at,
            "updated_at": updated_at
        }
        
        response = WebhookDeliveryResponse(**data)
        
        assert response.id == delivery_id
        assert response.endpoint_id == endpoint_id
        assert response.event_id == event_id
        assert response.status == DeliveryStatus.DELIVERED
        assert response.attempt_number == 1
        assert response.http_status == 200
        assert response.response_time == 150.5
        assert response.retry_count == 0


class TestWebhookAnalytics:
    """Test suite for WebhookAnalytics model."""

    def test_valid_webhook_analytics(self):
        """Test valid webhook analytics."""
        data = {
            "total_endpoints": 10,
            "active_endpoints": 8,
            "total_events": 1000,
            "total_deliveries": 950,
            "successful_deliveries": 900,
            "failed_deliveries": 50,
            "success_rate": 94.7,
            "average_response_time": 275.3,
            "events_by_type": {
                "query.completed": 500,
                "alert.triggered": 300,
                "report.generated": 200
            },
            "deliveries_by_status": {
                "delivered": 900,
                "failed": 50
            },
            "recent_activity": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": "webhook.created",
                    "endpoint_name": "Test Webhook"
                }
            ]
        }
        
        analytics = WebhookAnalytics(**data)
        
        assert analytics.total_endpoints == 10
        assert analytics.active_endpoints == 8
        assert analytics.total_events == 1000
        assert analytics.success_rate == 94.7
        assert analytics.average_response_time == 275.3
        assert len(analytics.events_by_type) == 3
        assert len(analytics.deliveries_by_status) == 2
        assert len(analytics.recent_activity) == 1

    def test_webhook_analytics_zero_values(self):
        """Test webhook analytics with zero values."""
        data = {
            "total_endpoints": 0,
            "active_endpoints": 0,
            "total_events": 0,
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "success_rate": 0.0,
            "average_response_time": 0.0,
            "events_by_type": {},
            "deliveries_by_status": {},
            "recent_activity": []
        }
        
        analytics = WebhookAnalytics(**data)
        
        assert analytics.total_endpoints == 0
        assert analytics.success_rate == 0.0
        assert len(analytics.events_by_type) == 0
        assert len(analytics.recent_activity) == 0


class TestDatabaseModels:
    """Test suite for SQLAlchemy database models."""

    def test_webhook_endpoint_model_structure(self):
        """Test WebhookEndpoint model structure."""
        # Test that the model has expected columns
        assert hasattr(WebhookEndpoint, 'id')
        assert hasattr(WebhookEndpoint, 'user_id')
        assert hasattr(WebhookEndpoint, 'name')
        assert hasattr(WebhookEndpoint, 'description')
        assert hasattr(WebhookEndpoint, 'url')
        assert hasattr(WebhookEndpoint, 'method')
        assert hasattr(WebhookEndpoint, 'headers')
        assert hasattr(WebhookEndpoint, 'secret')
        assert hasattr(WebhookEndpoint, 'status')
        assert hasattr(WebhookEndpoint, 'event_types')
        assert hasattr(WebhookEndpoint, 'event_filters')
        assert hasattr(WebhookEndpoint, 'timeout')
        assert hasattr(WebhookEndpoint, 'retry_attempts')
        assert hasattr(WebhookEndpoint, 'retry_delay')
        assert hasattr(WebhookEndpoint, 'total_deliveries')
        assert hasattr(WebhookEndpoint, 'successful_deliveries')
        assert hasattr(WebhookEndpoint, 'failed_deliveries')
        assert hasattr(WebhookEndpoint, 'created_at')
        assert hasattr(WebhookEndpoint, 'updated_at')
        
        # Test table name
        assert WebhookEndpoint.__tablename__ == "webhook_endpoints"

    def test_webhook_event_model_structure(self):
        """Test WebhookEvent model structure."""
        assert hasattr(WebhookEvent, 'id')
        assert hasattr(WebhookEvent, 'endpoint_id')
        assert hasattr(WebhookEvent, 'event_type')
        assert hasattr(WebhookEvent, 'source')
        assert hasattr(WebhookEvent, 'payload')
        assert hasattr(WebhookEvent, 'metadata')
        assert hasattr(WebhookEvent, 'processed')
        assert hasattr(WebhookEvent, 'processed_at')
        assert hasattr(WebhookEvent, 'created_at')
        
        # Test table name
        assert WebhookEvent.__tablename__ == "webhook_events"

    def test_webhook_delivery_model_structure(self):
        """Test WebhookDelivery model structure."""
        assert hasattr(WebhookDelivery, 'id')
        assert hasattr(WebhookDelivery, 'endpoint_id')
        assert hasattr(WebhookDelivery, 'event_id')
        assert hasattr(WebhookDelivery, 'status')
        assert hasattr(WebhookDelivery, 'attempt_number')
        assert hasattr(WebhookDelivery, 'max_attempts')
        assert hasattr(WebhookDelivery, 'http_status')
        assert hasattr(WebhookDelivery, 'response_body')
        assert hasattr(WebhookDelivery, 'response_headers')
        assert hasattr(WebhookDelivery, 'error_message')
        assert hasattr(WebhookDelivery, 'scheduled_at')
        assert hasattr(WebhookDelivery, 'attempted_at')
        assert hasattr(WebhookDelivery, 'completed_at')
        assert hasattr(WebhookDelivery, 'response_time')
        assert hasattr(WebhookDelivery, 'next_retry_at')
        assert hasattr(WebhookDelivery, 'retry_count')
        assert hasattr(WebhookDelivery, 'created_at')
        assert hasattr(WebhookDelivery, 'updated_at')
        
        # Test table name
        assert WebhookDelivery.__tablename__ == "webhook_deliveries"

    def test_webhook_subscription_model_structure(self):
        """Test WebhookSubscription model structure."""
        assert hasattr(WebhookSubscription, 'id')
        assert hasattr(WebhookSubscription, 'endpoint_id')
        assert hasattr(WebhookSubscription, 'event_type')
        assert hasattr(WebhookSubscription, 'active')
        assert hasattr(WebhookSubscription, 'filters')
        assert hasattr(WebhookSubscription, 'created_at')
        assert hasattr(WebhookSubscription, 'updated_at')
        
        # Test table name
        assert WebhookSubscription.__tablename__ == "webhook_subscriptions"

    def test_webhook_log_model_structure(self):
        """Test WebhookLog model structure."""
        assert hasattr(WebhookLog, 'id')
        assert hasattr(WebhookLog, 'endpoint_id')
        assert hasattr(WebhookLog, 'user_id')
        assert hasattr(WebhookLog, 'action')
        assert hasattr(WebhookLog, 'details')
        assert hasattr(WebhookLog, 'ip_address')
        assert hasattr(WebhookLog, 'user_agent')
        assert hasattr(WebhookLog, 'created_at')
        
        # Test table name
        assert WebhookLog.__tablename__ == "webhook_logs"

    def test_webhook_metric_model_structure(self):
        """Test WebhookMetric model structure."""
        assert hasattr(WebhookMetric, 'id')
        assert hasattr(WebhookMetric, 'endpoint_id')
        assert hasattr(WebhookMetric, 'metric_name')
        assert hasattr(WebhookMetric, 'metric_value')
        assert hasattr(WebhookMetric, 'metric_type')
        assert hasattr(WebhookMetric, 'tags')
        assert hasattr(WebhookMetric, 'timestamp')
        assert hasattr(WebhookMetric, 'time_bucket')
        assert hasattr(WebhookMetric, 'created_at')
        
        # Test table name
        assert WebhookMetric.__tablename__ == "webhook_metrics"


class TestModelValidation:
    """Test suite for model validation and edge cases."""

    def test_webhook_endpoint_create_with_all_event_types(self):
        """Test webhook endpoint creation with all event types."""
        data = {
            "name": "All Events Webhook",
            "url": "https://example.com/all-events",
            "event_types": list(EventType)
        }
        
        endpoint = WebhookEndpointCreate(**data)
        
        assert len(endpoint.event_types) == len(list(EventType))
        assert EventType.QUERY_COMPLETED in endpoint.event_types
        assert EventType.ALERT_TRIGGERED in endpoint.event_types

    def test_webhook_endpoint_create_with_complex_headers(self):
        """Test webhook endpoint creation with complex headers."""
        data = {
            "name": "Complex Headers Webhook",
            "url": "https://example.com/complex",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer token-123",
                "X-Custom-Header": "custom-value",
                "User-Agent": "Splunk-MCP-Webhook/1.0"
            }
        }
        
        endpoint = WebhookEndpointCreate(**data)
        
        assert len(endpoint.headers) == 4
        assert endpoint.headers["Content-Type"] == "application/json"
        assert endpoint.headers["Authorization"] == "Bearer token-123"
        assert endpoint.headers["X-Custom-Header"] == "custom-value"

    def test_webhook_endpoint_create_with_complex_event_filters(self):
        """Test webhook endpoint creation with complex event filters."""
        data = {
            "name": "Filtered Webhook",
            "url": "https://example.com/filtered",
            "event_filters": {
                "source": ["nlp-engine", "visualization-service"],
                "severity": "high",
                "user_id": "specific-user-123",
                "tags": {
                    "environment": "production",
                    "region": "us-west-2"
                }
            }
        }
        
        endpoint = WebhookEndpointCreate(**data)
        
        assert endpoint.event_filters["source"] == ["nlp-engine", "visualization-service"]
        assert endpoint.event_filters["severity"] == "high"
        assert endpoint.event_filters["user_id"] == "specific-user-123"
        assert endpoint.event_filters["tags"]["environment"] == "production"

    def test_webhook_event_create_with_nested_payload(self):
        """Test webhook event creation with nested payload."""
        complex_payload = {
            "query": {
                "id": "query-123",
                "spl": "index=main | stats count by source",
                "time_range": {
                    "earliest": "-1h",
                    "latest": "now"
                }
            },
            "results": {
                "total_count": 5000,
                "data": [
                    {"source": "/var/log/app.log", "count": 3000},
                    {"source": "/var/log/error.log", "count": 2000}
                ]
            },
            "metadata": {
                "execution_time": 2.5,
                "user": {
                    "id": "user-123",
                    "email": "user@example.com"
                }
            }
        }
        
        data = {
            "event_type": EventType.QUERY_COMPLETED,
            "source": "nlp-engine",
            "payload": complex_payload
        }
        
        event = WebhookEventCreate(**data)
        
        assert event.payload["query"]["id"] == "query-123"
        assert event.payload["results"]["total_count"] == 5000
        assert len(event.payload["results"]["data"]) == 2
        assert event.payload["metadata"]["execution_time"] == 2.5
        assert event.payload["metadata"]["user"]["email"] == "user@example.com"