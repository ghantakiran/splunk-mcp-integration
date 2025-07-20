"""
Tests for Delivery Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, call, MagicMock
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
import httpx

from app.services.delivery_service import DeliveryService
from app.models.webhook_models import (
    WebhookStatus, EventType, DeliveryStatus, WebhookMethod,
    WebhookEndpoint, WebhookEvent, WebhookDelivery
)


class TestDeliveryService:
    """Test suite for DeliveryService class."""

    @pytest.fixture
    def delivery_service(self):
        """Create a DeliveryService instance."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_delivery_service_initialization(self, delivery_service):
        """Test DeliveryService initialization."""
        assert delivery_service is not None
        assert hasattr(delivery_service, 'db')
        assert hasattr(delivery_service, 'cache')

    @pytest.mark.asyncio
    async def test_list_deliveries_success(self, delivery_service):
        """Test successful delivery listing."""
        user_id = "test-user-123"
        
        # Mock database operations
        with patch.object(delivery_service, 'db') as mock_db:
            mock_deliveries = [
                Mock(id="delivery-1", status=DeliveryStatus.DELIVERED),
                Mock(id="delivery-2", status=DeliveryStatus.FAILED)
            ]
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_deliveries
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with patch.object(delivery_service, '_delivery_to_dict') as mock_to_dict:
                mock_to_dict.side_effect = [
                    {"id": "delivery-1", "status": "delivered"},
                    {"id": "delivery-2", "status": "failed"}
                ]
                
                result = await delivery_service.list_deliveries(user_id)
                
                assert len(result) == 2
                assert result[0]["id"] == "delivery-1"
                assert result[1]["id"] == "delivery-2"

    @pytest.mark.asyncio
    async def test_list_deliveries_with_filters(self, delivery_service):
        """Test delivery listing with filters."""
        user_id = "test-user-123"
        endpoint_id = "test-endpoint-123"
        event_id = "test-event-123"
        status = "delivered"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_deliveries = [
                Mock(id="delivery-1", endpoint_id=endpoint_id, event_id=event_id, status=DeliveryStatus.DELIVERED)
            ]
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_deliveries
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with patch.object(delivery_service, '_delivery_to_dict') as mock_to_dict:
                mock_to_dict.return_value = {
                    "id": "delivery-1",
                    "endpoint_id": endpoint_id,
                    "event_id": event_id,
                    "status": "delivered"
                }
                
                result = await delivery_service.list_deliveries(
                    user_id=user_id,
                    endpoint_id=endpoint_id,
                    event_id=event_id,
                    status=status,
                    limit=50,
                    offset=0
                )
                
                assert len(result) == 1
                assert result[0]["endpoint_id"] == endpoint_id
                assert result[0]["event_id"] == event_id
                assert result[0]["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_get_delivery_success(self, delivery_service):
        """Test successful delivery retrieval."""
        delivery_id = "test-delivery-123"
        user_id = "test-user-123"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_delivery = Mock(id=delivery_id, status=DeliveryStatus.DELIVERED)
            mock_result = Mock()
            mock_result.scalar.return_value = mock_delivery
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with patch.object(delivery_service, '_delivery_to_dict') as mock_to_dict:
                mock_to_dict.return_value = {"id": delivery_id, "status": "delivered"}
                
                result = await delivery_service.get_delivery(delivery_id, user_id)
                
                assert result["id"] == delivery_id
                assert result["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_get_delivery_not_found(self, delivery_service):
        """Test delivery retrieval when not found."""
        delivery_id = "nonexistent-delivery"
        user_id = "test-user-123"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_result = Mock()
            mock_result.scalar.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await delivery_service.get_delivery(delivery_id, user_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_retry_delivery_success(self, delivery_service):
        """Test successful delivery retry."""
        delivery_id = "test-delivery-123"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_delivery = Mock(
                id=delivery_id,
                status=DeliveryStatus.FAILED,
                retry_count=1,
                max_attempts=3
            )
            mock_result = Mock()
            mock_result.scalar.return_value = mock_delivery
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            
            with patch.object(delivery_service, '_schedule_delivery') as mock_schedule:
                mock_schedule.return_value = None
                
                result = await delivery_service.retry_delivery(delivery_id)
                
                assert result is True
                assert mock_delivery.status == DeliveryStatus.PENDING
                assert mock_delivery.retry_count == 2
                mock_schedule.assert_called_once_with(delivery_id)

    @pytest.mark.asyncio
    async def test_retry_delivery_max_attempts_exceeded(self, delivery_service):
        """Test delivery retry when max attempts exceeded."""
        delivery_id = "test-delivery-123"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_delivery = Mock(
                id=delivery_id,
                status=DeliveryStatus.FAILED,
                retry_count=3,
                max_attempts=3
            )
            mock_result = Mock()
            mock_result.scalar.return_value = mock_delivery
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await delivery_service.retry_delivery(delivery_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_retry_delivery_not_failed(self, delivery_service):
        """Test delivery retry when delivery is not in failed state."""
        delivery_id = "test-delivery-123"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_delivery = Mock(
                id=delivery_id,
                status=DeliveryStatus.DELIVERED,  # Not failed
                retry_count=0,
                max_attempts=3
            )
            mock_result = Mock()
            mock_result.scalar.return_value = mock_delivery
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await delivery_service.retry_delivery(delivery_id)
            
            assert result is False


class TestDeliveryServiceProcessor:
    """Test suite for DeliveryService background processor."""

    @pytest.fixture
    def delivery_service(self):
        """Create a DeliveryService instance."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_start_processor(self, delivery_service):
        """Test background processor startup."""
        with patch.object(delivery_service, '_process_delivery_queue') as mock_process:
            # Mock the processor to run briefly and then stop
            mock_process.side_effect = asyncio.CancelledError()
            
            with pytest.raises(asyncio.CancelledError):
                await delivery_service.start_processor()
            
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_delivery_queue_success(self, delivery_service):
        """Test successful delivery queue processing."""
        with patch.object(delivery_service, 'cache') as mock_cache, \
             patch.object(delivery_service, '_deliver_webhook') as mock_deliver:
            
            # Mock Redis operations
            mock_cache.redis_client.brpop = AsyncMock(return_value=("webhook_deliveries", "delivery-123"))
            mock_deliver.return_value = None
            
            # Run one iteration of the processor
            with patch.object(delivery_service, '_should_continue_processing', side_effect=[True, False]):
                await delivery_service._process_delivery_queue()
            
            mock_deliver.assert_called_once_with("delivery-123")

    @pytest.mark.asyncio
    async def test_process_delivery_queue_empty(self, delivery_service):
        """Test delivery queue processing when queue is empty."""
        with patch.object(delivery_service, 'cache') as mock_cache:
            # Mock Redis to return None (empty queue)
            mock_cache.redis_client.brpop = AsyncMock(return_value=None)
            
            # Run one iteration of the processor
            with patch.object(delivery_service, '_should_continue_processing', side_effect=[True, False]):
                await delivery_service._process_delivery_queue()
            
            # Should handle empty queue gracefully


class TestDeliveryServiceWebhookDelivery:
    """Test suite for DeliveryService webhook delivery functionality."""

    @pytest.fixture
    def delivery_service(self):
        """Create a DeliveryService instance."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self, delivery_service):
        """Test successful webhook delivery."""
        delivery_id = "test-delivery-123"
        
        # Mock delivery and endpoint data
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3
        )
        
        mock_endpoint = Mock(
            url="https://example.com/webhook",
            method=WebhookMethod.POST,
            headers={"Content-Type": "application/json"},
            secret="test-secret",
            timeout=30
        )
        
        mock_event = Mock(
            event_type=EventType.QUERY_COMPLETED,
            payload={"test": "data"},
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, '_get_delivery_data') as mock_get_data, \
             patch.object(delivery_service, '_make_http_request') as mock_request, \
             patch.object(delivery_service, '_update_delivery_status') as mock_update:
            
            mock_get_data.return_value = (mock_delivery, mock_endpoint, mock_event)
            mock_request.return_value = {
                "status_code": 200,
                "response_body": '{"success": true}',
                "response_headers": {"Content-Type": "application/json"},
                "response_time": 150.5
            }
            mock_update.return_value = None
            
            await delivery_service._deliver_webhook(delivery_id)
            
            mock_update.assert_called_once()
            args = mock_update.call_args[0]
            assert args[0] == mock_delivery
            assert args[1] == DeliveryStatus.DELIVERED
            assert args[2]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_deliver_webhook_http_error(self, delivery_service):
        """Test webhook delivery with HTTP error."""
        delivery_id = "test-delivery-123"
        
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3
        )
        
        mock_endpoint = Mock(
            url="https://example.com/webhook",
            method=WebhookMethod.POST,
            headers={},
            secret="test-secret",
            timeout=30
        )
        
        mock_event = Mock(
            event_type=EventType.QUERY_COMPLETED,
            payload={"test": "data"}
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, '_get_delivery_data') as mock_get_data, \
             patch.object(delivery_service, '_make_http_request') as mock_request, \
             patch.object(delivery_service, '_update_delivery_status') as mock_update, \
             patch.object(delivery_service, '_schedule_retry') as mock_retry:
            
            mock_get_data.return_value = (mock_delivery, mock_endpoint, mock_event)
            mock_request.return_value = {
                "status_code": 500,
                "response_body": "Internal Server Error",
                "response_headers": {},
                "response_time": 100.0,
                "error": "HTTP 500 error"
            }
            mock_update.return_value = None
            mock_retry.return_value = None
            
            await delivery_service._deliver_webhook(delivery_id)
            
            mock_update.assert_called_once()
            args = mock_update.call_args[0]
            assert args[1] == DeliveryStatus.FAILED
            mock_retry.assert_called_once_with(mock_delivery)

    @pytest.mark.asyncio
    async def test_deliver_webhook_connection_error(self, delivery_service):
        """Test webhook delivery with connection error."""
        delivery_id = "test-delivery-123"
        
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3
        )
        
        mock_endpoint = Mock(
            url="https://unreachable.example.com/webhook",
            method=WebhookMethod.POST,
            headers={},
            secret="test-secret",
            timeout=30
        )
        
        mock_event = Mock(
            event_type=EventType.QUERY_COMPLETED,
            payload={"test": "data"}
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, '_get_delivery_data') as mock_get_data, \
             patch.object(delivery_service, '_make_http_request') as mock_request, \
             patch.object(delivery_service, '_update_delivery_status') as mock_update, \
             patch.object(delivery_service, '_schedule_retry') as mock_retry:
            
            mock_get_data.return_value = (mock_delivery, mock_endpoint, mock_event)
            mock_request.side_effect = Exception("Connection failed")
            mock_update.return_value = None
            mock_retry.return_value = None
            
            await delivery_service._deliver_webhook(delivery_id)
            
            mock_update.assert_called_once()
            args = mock_update.call_args[0]
            assert args[1] == DeliveryStatus.FAILED
            assert "Connection failed" in str(args[2])
            mock_retry.assert_called_once_with(mock_delivery)

    @pytest.mark.asyncio
    async def test_deliver_webhook_max_attempts_reached(self, delivery_service):
        """Test webhook delivery when max attempts reached."""
        delivery_id = "test-delivery-123"
        
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=3,
            max_attempts=3
        )
        
        mock_endpoint = Mock(
            url="https://example.com/webhook",
            timeout=30
        )
        
        mock_event = Mock(payload={"test": "data"})
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, '_get_delivery_data') as mock_get_data, \
             patch.object(delivery_service, '_make_http_request') as mock_request, \
             patch.object(delivery_service, '_update_delivery_status') as mock_update:
            
            mock_get_data.return_value = (mock_delivery, mock_endpoint, mock_event)
            mock_request.return_value = {
                "status_code": 500,
                "response_body": "Error",
                "response_headers": {},
                "response_time": 100.0,
                "error": "HTTP 500 error"
            }
            mock_update.return_value = None
            
            await delivery_service._deliver_webhook(delivery_id)
            
            # Should mark as failed without scheduling retry
            mock_update.assert_called_once()
            args = mock_update.call_args[0]
            assert args[1] == DeliveryStatus.FAILED


class TestDeliveryServiceHTTPOperations:
    """Test suite for DeliveryService HTTP operations."""

    @pytest.fixture
    def delivery_service(self):
        """Create a DeliveryService instance."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_make_http_request_post_success(self, delivery_service):
        """Test successful HTTP POST request."""
        endpoint_data = {
            "url": "https://example.com/webhook",
            "method": WebhookMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "secret": "test-secret",
            "timeout": 30
        }
        
        payload = {"event": "test", "data": {"key": "value"}}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed.total_seconds.return_value = 0.15
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            result = await delivery_service._make_http_request(endpoint_data, payload)
            
            assert result["status_code"] == 200
            assert result["response_body"] == '{"success": true}'
            assert result["response_headers"] == {"Content-Type": "application/json"}
            assert result["response_time"] == 150.0  # milliseconds

    @pytest.mark.asyncio
    async def test_make_http_request_put_success(self, delivery_service):
        """Test successful HTTP PUT request."""
        endpoint_data = {
            "url": "https://example.com/webhook",
            "method": WebhookMethod.PUT,
            "headers": {"Authorization": "Bearer token"},
            "secret": "test-secret",
            "timeout": 30
        }
        
        payload = {"update": "data"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        mock_response.headers = {}
        mock_response.elapsed.total_seconds.return_value = 0.08
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.put.return_value = mock_response
            
            result = await delivery_service._make_http_request(endpoint_data, payload)
            
            assert result["status_code"] == 200
            assert result["response_time"] == 80.0  # milliseconds

    @pytest.mark.asyncio
    async def test_make_http_request_timeout(self, delivery_service):
        """Test HTTP request timeout."""
        endpoint_data = {
            "url": "https://slow.example.com/webhook",
            "method": WebhookMethod.POST,
            "headers": {},
            "secret": "test-secret",
            "timeout": 1  # 1 second timeout
        }
        
        payload = {"test": "data"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(Exception, match="Request timeout"):
                await delivery_service._make_http_request(endpoint_data, payload)

    @pytest.mark.asyncio
    async def test_make_http_request_connection_error(self, delivery_service):
        """Test HTTP request connection error."""
        endpoint_data = {
            "url": "https://nonexistent.example.com/webhook",
            "method": WebhookMethod.POST,
            "headers": {},
            "secret": "test-secret",
            "timeout": 30
        }
        
        payload = {"test": "data"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                await delivery_service._make_http_request(endpoint_data, payload)

    def test_generate_webhook_signature(self, delivery_service):
        """Test webhook signature generation."""
        payload = '{"event": "test", "data": {"key": "value"}}'
        secret = "my-webhook-secret"
        
        signature = delivery_service._generate_signature(payload, secret)
        
        assert signature.startswith("sha256=")
        assert len(signature) > 10

        # Test that same input produces same signature
        signature2 = delivery_service._generate_signature(payload, secret)
        assert signature == signature2

    def test_build_webhook_payload(self, delivery_service):
        """Test webhook payload building."""
        mock_event = Mock(
            id="event-123",
            event_type=EventType.QUERY_COMPLETED,
            source="test-service",
            payload={"query_id": "query-123", "status": "completed"},
            metadata={"user_id": "user-123"},
            created_at=datetime(2025, 1, 16, 10, 30, 0)
        )
        
        mock_delivery = Mock(
            id="delivery-123",
            attempt_number=1
        )
        
        payload = delivery_service._build_webhook_payload(mock_event, mock_delivery)
        
        assert payload["event"]["id"] == "event-123"
        assert payload["event"]["type"] == "query.completed"
        assert payload["event"]["source"] == "test-service"
        assert payload["event"]["data"] == {"query_id": "query-123", "status": "completed"}
        assert payload["delivery"]["id"] == "delivery-123"
        assert payload["delivery"]["attempt"] == 1
        assert "timestamp" in payload


class TestDeliveryServiceHelperMethods:
    """Test suite for DeliveryService helper methods."""

    @pytest.fixture
    def delivery_service(self):
        """Create a DeliveryService instance."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_get_delivery_data_success(self, delivery_service):
        """Test successful delivery data retrieval."""
        delivery_id = "test-delivery-123"
        
        mock_delivery = Mock(id=delivery_id, endpoint_id="endpoint-123", event_id="event-123")
        mock_endpoint = Mock(id="endpoint-123", url="https://example.com/webhook")
        mock_event = Mock(id="event-123", event_type=EventType.QUERY_COMPLETED)
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_results = [
                Mock(scalar=Mock(return_value=mock_delivery)),
                Mock(scalar=Mock(return_value=mock_endpoint)),
                Mock(scalar=Mock(return_value=mock_event))
            ]
            mock_db.execute = AsyncMock(side_effect=mock_results)
            
            delivery, endpoint, event = await delivery_service._get_delivery_data(delivery_id)
            
            assert delivery.id == delivery_id
            assert endpoint.id == "endpoint-123"
            assert event.id == "event-123"

    @pytest.mark.asyncio
    async def test_get_delivery_data_not_found(self, delivery_service):
        """Test delivery data retrieval when delivery not found."""
        delivery_id = "nonexistent-delivery"
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_result = Mock(scalar=Mock(return_value=None))
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with pytest.raises(ValueError, match="not found"):
                await delivery_service._get_delivery_data(delivery_id)

    @pytest.mark.asyncio
    async def test_update_delivery_status_success(self, delivery_service):
        """Test successful delivery status update."""
        mock_delivery = Mock(id="delivery-123", status=DeliveryStatus.PENDING)
        new_status = DeliveryStatus.DELIVERED
        response_data = {
            "status_code": 200,
            "response_body": '{"success": true}',
            "response_headers": {"Content-Type": "application/json"},
            "response_time": 150.5
        }
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_db.commit = AsyncMock()
            
            await delivery_service._update_delivery_status(mock_delivery, new_status, response_data)
            
            assert mock_delivery.status == new_status
            assert mock_delivery.http_status == 200
            assert mock_delivery.response_body == '{"success": true}'
            assert mock_delivery.response_time == 150.5
            assert mock_delivery.completed_at is not None
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_delivery_status_failed(self, delivery_service):
        """Test delivery status update for failed delivery."""
        mock_delivery = Mock(id="delivery-123", status=DeliveryStatus.PENDING)
        new_status = DeliveryStatus.FAILED
        response_data = {
            "status_code": 500,
            "response_body": "Internal Server Error",
            "error": "HTTP 500 error"
        }
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_db.commit = AsyncMock()
            
            await delivery_service._update_delivery_status(mock_delivery, new_status, response_data)
            
            assert mock_delivery.status == new_status
            assert mock_delivery.error_message == "HTTP 500 error"
            assert mock_delivery.completed_at is not None
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_retry_success(self, delivery_service):
        """Test successful delivery retry scheduling."""
        mock_delivery = Mock(
            id="delivery-123",
            retry_count=1,
            max_attempts=3,
            status=DeliveryStatus.FAILED
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, '_calculate_retry_delay') as mock_delay, \
             patch.object(delivery_service, '_schedule_delivery') as mock_schedule:
            
            mock_delay.return_value = 300  # 5 minutes
            mock_schedule.return_value = None
            mock_db.commit = AsyncMock()
            
            await delivery_service._schedule_retry(mock_delivery)
            
            assert mock_delivery.status == DeliveryStatus.RETRYING
            assert mock_delivery.retry_count == 2
            assert mock_delivery.next_retry_at is not None
            mock_schedule.assert_called_once_with("delivery-123", delay=300)

    @pytest.mark.asyncio
    async def test_schedule_retry_max_attempts_reached(self, delivery_service):
        """Test retry scheduling when max attempts reached."""
        mock_delivery = Mock(
            id="delivery-123",
            retry_count=3,
            max_attempts=3,
            status=DeliveryStatus.FAILED
        )
        
        with patch.object(delivery_service, 'db') as mock_db:
            mock_db.commit = AsyncMock()
            
            await delivery_service._schedule_retry(mock_delivery)
            
            # Should remain failed, no retry scheduled
            assert mock_delivery.status == DeliveryStatus.FAILED
            assert mock_delivery.next_retry_at is None

    def test_calculate_retry_delay(self, delivery_service):
        """Test retry delay calculation."""
        # Test exponential backoff
        delay1 = delivery_service._calculate_retry_delay(1)
        delay2 = delivery_service._calculate_retry_delay(2)
        delay3 = delivery_service._calculate_retry_delay(3)
        
        assert delay1 < delay2 < delay3
        assert delay1 >= 60  # At least 1 minute
        assert delay3 <= 3600  # At most 1 hour

    @pytest.mark.asyncio
    async def test_schedule_delivery_immediate(self, delivery_service):
        """Test immediate delivery scheduling."""
        delivery_id = "delivery-123"
        
        with patch.object(delivery_service, 'cache') as mock_cache:
            mock_cache.redis_client.lpush = AsyncMock()
            
            await delivery_service._schedule_delivery(delivery_id)
            
            mock_cache.redis_client.lpush.assert_called_once_with("webhook_deliveries", delivery_id)

    @pytest.mark.asyncio
    async def test_schedule_delivery_delayed(self, delivery_service):
        """Test delayed delivery scheduling."""
        delivery_id = "delivery-123"
        delay = 300  # 5 minutes
        
        with patch.object(delivery_service, 'cache') as mock_cache:
            mock_cache.redis_client.zadd = AsyncMock()
            
            await delivery_service._schedule_delivery(delivery_id, delay=delay)
            
            # Should add to delayed queue instead of immediate queue
            mock_cache.redis_client.zadd.assert_called_once()

    def test_delivery_to_dict_success(self, delivery_service, sample_webhook_delivery):
        """Test successful delivery conversion to dictionary."""
        result = delivery_service._delivery_to_dict(sample_webhook_delivery)
        
        assert result["id"] == sample_webhook_delivery.id
        assert result["endpoint_id"] == sample_webhook_delivery.endpoint_id
        assert result["event_id"] == sample_webhook_delivery.event_id
        assert result["status"] == sample_webhook_delivery.status.value
        assert result["attempt_number"] == sample_webhook_delivery.attempt_number
        assert result["http_status"] == sample_webhook_delivery.http_status
        assert result["response_time"] == sample_webhook_delivery.response_time
        assert result["retry_count"] == sample_webhook_delivery.retry_count


class TestDeliveryServiceErrorHandling:
    """Test suite for DeliveryService error handling."""

    @pytest.fixture
    def delivery_service_with_errors(self):
        """Create DeliveryService with error-prone dependencies."""
        service = DeliveryService()
        
        # Mock error-prone database
        service.db = AsyncMock()
        service.db.execute.side_effect = Exception("Database error")
        
        # Mock error-prone cache
        service.cache = AsyncMock()
        service.cache.redis_client.lpush.side_effect = Exception("Redis error")
        
        return service

    @pytest.mark.asyncio
    async def test_list_deliveries_database_error(self, delivery_service_with_errors):
        """Test delivery listing with database error."""
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await delivery_service_with_errors.list_deliveries(user_id)

    @pytest.mark.asyncio
    async def test_get_delivery_database_error(self, delivery_service_with_errors):
        """Test delivery retrieval with database error."""
        delivery_id = "test-delivery-123"
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await delivery_service_with_errors.get_delivery(delivery_id, user_id)

    @pytest.mark.asyncio
    async def test_schedule_delivery_redis_error(self, delivery_service_with_errors):
        """Test delivery scheduling with Redis error."""
        delivery_id = "test-delivery-123"
        
        with pytest.raises(Exception, match="Redis error"):
            await delivery_service_with_errors._schedule_delivery(delivery_id)


class TestDeliveryServiceIntegration:
    """Test suite for DeliveryService integration scenarios."""

    @pytest.fixture
    def delivery_service(self):
        """Create DeliveryService for integration testing."""
        return DeliveryService()

    @pytest.mark.asyncio
    async def test_full_delivery_lifecycle(self, delivery_service):
        """Test complete delivery lifecycle: queue, process, deliver."""
        delivery_id = "test-delivery-123"
        
        # Mock delivery, endpoint, and event
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3,
            endpoint_id="endpoint-123",
            event_id="event-123"
        )
        
        mock_endpoint = Mock(
            id="endpoint-123",
            url="https://example.com/webhook",
            method=WebhookMethod.POST,
            headers={"Content-Type": "application/json"},
            secret="test-secret",
            timeout=30
        )
        
        mock_event = Mock(
            id="event-123",
            event_type=EventType.QUERY_COMPLETED,
            source="test-service",
            payload={"query_id": "query-123", "status": "completed"},
            metadata={"user_id": "user-123"},
            created_at=datetime.utcnow()
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, 'cache') as mock_cache, \
             patch.object(delivery_service, '_make_http_request') as mock_request:
            
            # Mock database operations
            mock_results = [
                Mock(scalar=Mock(return_value=mock_delivery)),
                Mock(scalar=Mock(return_value=mock_endpoint)),
                Mock(scalar=Mock(return_value=mock_event))
            ]
            mock_db.execute = AsyncMock(side_effect=mock_results)
            mock_db.commit = AsyncMock()
            
            # Mock successful HTTP request
            mock_request.return_value = {
                "status_code": 200,
                "response_body": '{"success": true}',
                "response_headers": {"Content-Type": "application/json"},
                "response_time": 150.5
            }
            
            # Mock Redis operations
            mock_cache.redis_client.lpush = AsyncMock()
            
            # 1. Schedule delivery
            await delivery_service._schedule_delivery(delivery_id)
            mock_cache.redis_client.lpush.assert_called_once_with("webhook_deliveries", delivery_id)
            
            # 2. Process delivery
            await delivery_service._deliver_webhook(delivery_id)
            
            # Verify delivery was marked as delivered
            assert mock_delivery.status == DeliveryStatus.DELIVERED
            assert mock_delivery.http_status == 200
            assert mock_delivery.response_body == '{"success": true}'
            assert mock_delivery.completed_at is not None
            
            # Verify database was updated
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delivery_with_retry_logic(self, delivery_service):
        """Test delivery with retry logic for failed requests."""
        delivery_id = "test-delivery-123"
        
        mock_delivery = Mock(
            id=delivery_id,
            status=DeliveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3,
            retry_count=0,
            endpoint_id="endpoint-123",
            event_id="event-123"
        )
        
        mock_endpoint = Mock(
            id="endpoint-123",
            url="https://failing.example.com/webhook",
            method=WebhookMethod.POST,
            headers={},
            secret="test-secret",
            timeout=30
        )
        
        mock_event = Mock(
            id="event-123",
            event_type=EventType.QUERY_COMPLETED,
            payload={"test": "data"},
            created_at=datetime.utcnow()
        )
        
        with patch.object(delivery_service, 'db') as mock_db, \
             patch.object(delivery_service, 'cache') as mock_cache, \
             patch.object(delivery_service, '_make_http_request') as mock_request:
            
            # Mock database operations
            mock_results = [
                Mock(scalar=Mock(return_value=mock_delivery)),
                Mock(scalar=Mock(return_value=mock_endpoint)),
                Mock(scalar=Mock(return_value=mock_event))
            ]
            mock_db.execute = AsyncMock(side_effect=mock_results)
            mock_db.commit = AsyncMock()
            
            # Mock failed HTTP request
            mock_request.return_value = {
                "status_code": 500,
                "response_body": "Internal Server Error",
                "response_headers": {},
                "response_time": 100.0,
                "error": "HTTP 500 error"
            }
            
            # Mock Redis operations for retry scheduling
            mock_cache.redis_client.zadd = AsyncMock()
            
            # Process delivery (should fail and schedule retry)
            await delivery_service._deliver_webhook(delivery_id)
            
            # Verify delivery was marked as retrying
            assert mock_delivery.status == DeliveryStatus.RETRYING
            assert mock_delivery.retry_count == 1
            assert mock_delivery.next_retry_at is not None
            
            # Verify retry was scheduled
            mock_cache.redis_client.zadd.assert_called_once()