"""
Tests for Event Processor Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, call
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.event_processor import EventProcessor
from app.models.webhook_models import (
    WebhookStatus, EventType, DeliveryStatus, WebhookMethod,
    WebhookEndpoint, WebhookEvent, WebhookDelivery
)


class TestEventProcessor:
    """Test suite for EventProcessor class."""

    @pytest.fixture
    def event_processor(self, mock_database, mock_redis):
        """Create an EventProcessor instance."""
        return EventProcessor(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_event_processor_initialization(self, event_processor):
        """Test EventProcessor initialization."""
        assert event_processor.db is not None
        assert event_processor.cache is not None

    @pytest.mark.asyncio
    async def test_create_event_success(self, event_processor, sample_webhook_event_data):
        """Test successful event creation."""
        user_id = "test-user-123"
        event_id = str(uuid4())
        
        # Mock database operations
        mock_event = Mock()
        mock_event.id = event_id
        mock_event.event_type = EventType.QUERY_COMPLETED
        mock_event.source = sample_webhook_event_data["source"]
        mock_event.processed = False
        
        event_processor.db.add = Mock()
        event_processor.db.commit = AsyncMock()
        event_processor.db.refresh = AsyncMock()
        
        # Mock helper methods
        with patch.object(event_processor, '_validate_event_data') as mock_validate, \
             patch.object(event_processor, '_event_to_dict') as mock_to_dict, \
             patch('app.services.event_processor.WebhookEvent', return_value=mock_event):
            
            mock_validate.return_value = None
            mock_to_dict.return_value = {
                "id": event_id,
                "event_type": "query.completed",
                "source": sample_webhook_event_data["source"],
                "processed": False
            }
            
            result = await event_processor.create_event(sample_webhook_event_data, user_id)
            
            assert result["id"] == event_id
            assert result["event_type"] == "query.completed"
            assert result["processed"] is False
            mock_validate.assert_called_once()
            event_processor.db.add.assert_called_once_with(mock_event)
            event_processor.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_event_validation_error(self, event_processor, sample_webhook_event_data):
        """Test event creation with validation error."""
        user_id = "test-user-123"
        
        # Mock validation failure
        with patch.object(event_processor, '_validate_event_data') as mock_validate:
            mock_validate.side_effect = ValueError("Invalid event data")
            
            with pytest.raises(ValueError, match="Invalid event data"):
                await event_processor.create_event(sample_webhook_event_data, user_id)

    @pytest.mark.asyncio
    async def test_list_events_success(self, event_processor):
        """Test successful event listing."""
        user_id = "test-user-123"
        
        # Mock database query results
        mock_events = [
            Mock(id="event-1", event_type=EventType.QUERY_COMPLETED, processed=True),
            Mock(id="event-2", event_type=EventType.ALERT_TRIGGERED, processed=False)
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_events
        event_processor.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(event_processor, '_event_to_dict') as mock_to_dict:
            mock_to_dict.side_effect = [
                {"id": "event-1", "event_type": "query.completed", "processed": True},
                {"id": "event-2", "event_type": "alert.triggered", "processed": False}
            ]
            
            result = await event_processor.list_events(user_id)
            
            assert len(result) == 2
            assert result[0]["id"] == "event-1"
            assert result[1]["id"] == "event-2"
            mock_to_dict.assert_has_calls([call(mock_events[0]), call(mock_events[1])])

    @pytest.mark.asyncio
    async def test_list_events_with_endpoint_filter(self, event_processor):
        """Test event listing with endpoint filter."""
        user_id = "test-user-123"
        endpoint_id = "test-endpoint-123"
        
        mock_events = [
            Mock(id="event-1", endpoint_id=endpoint_id, event_type=EventType.QUERY_COMPLETED)
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_events
        event_processor.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(event_processor, '_event_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": "event-1", "endpoint_id": endpoint_id}
            
            result = await event_processor.list_events(
                user_id=user_id,
                endpoint_id=endpoint_id,
                limit=50,
                offset=0
            )
            
            assert len(result) == 1
            assert result[0]["endpoint_id"] == endpoint_id

    @pytest.mark.asyncio
    async def test_get_event_success(self, event_processor):
        """Test successful event retrieval."""
        event_id = "test-event-123"
        user_id = "test-user-123"
        
        mock_event = Mock(id=event_id, event_type=EventType.QUERY_COMPLETED)
        mock_result = Mock()
        mock_result.scalar.return_value = mock_event
        event_processor.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(event_processor, '_event_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": event_id, "event_type": "query.completed"}
            
            result = await event_processor.get_event(event_id, user_id)
            
            assert result["id"] == event_id
            assert result["event_type"] == "query.completed"
            mock_to_dict.assert_called_once_with(mock_event)

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, event_processor):
        """Test event retrieval when not found."""
        event_id = "nonexistent-event"
        user_id = "test-user-123"
        
        mock_result = Mock()
        mock_result.scalar.return_value = None
        event_processor.db.execute = AsyncMock(return_value=mock_result)
        
        result = await event_processor.get_event(event_id, user_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_process_event_success(self, event_processor):
        """Test successful event processing."""
        event_id = "test-event-123"
        
        # Mock event and endpoints
        mock_event = Mock(
            id=event_id,
            event_type=EventType.QUERY_COMPLETED,
            payload={"test": "data"},
            processed=False
        )
        
        mock_endpoints = [
            Mock(id="endpoint-1", url="https://example.com/webhook1", status=WebhookStatus.ACTIVE),
            Mock(id="endpoint-2", url="https://example.com/webhook2", status=WebhookStatus.ACTIVE)
        ]
        
        # Mock database queries
        event_result = Mock()
        event_result.scalar.return_value = mock_event
        endpoints_result = Mock()
        endpoints_result.scalars.return_value.all.return_value = mock_endpoints
        
        event_processor.db.execute = AsyncMock(side_effect=[event_result, endpoints_result])
        event_processor.db.commit = AsyncMock()
        
        with patch.object(event_processor, '_create_deliveries') as mock_create_deliveries, \
             patch.object(event_processor, '_schedule_deliveries') as mock_schedule:
            
            mock_create_deliveries.return_value = ["delivery-1", "delivery-2"]
            mock_schedule.return_value = None
            
            result = await event_processor.process_event(event_id)
            
            assert result["event_id"] == event_id
            assert result["endpoints_matched"] == 2
            assert result["deliveries_created"] == 2
            assert mock_event.processed is True
            mock_create_deliveries.assert_called_once()
            mock_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_already_processed(self, event_processor):
        """Test processing an already processed event."""
        event_id = "test-event-123"
        
        # Mock already processed event
        mock_event = Mock(
            id=event_id,
            event_type=EventType.QUERY_COMPLETED,
            processed=True
        )
        
        event_result = Mock()
        event_result.scalar.return_value = mock_event
        event_processor.db.execute = AsyncMock(return_value=event_result)
        
        result = await event_processor.process_event(event_id)
        
        assert result["event_id"] == event_id
        assert result["status"] == "already_processed"

    @pytest.mark.asyncio
    async def test_process_event_not_found(self, event_processor):
        """Test processing a non-existent event."""
        event_id = "nonexistent-event"
        
        event_result = Mock()
        event_result.scalar.return_value = None
        event_processor.db.execute = AsyncMock(return_value=event_result)
        
        result = await event_processor.process_event(event_id)
        
        assert result["event_id"] == event_id
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_process_event_no_matching_endpoints(self, event_processor):
        """Test processing event with no matching endpoints."""
        event_id = "test-event-123"
        
        mock_event = Mock(
            id=event_id,
            event_type=EventType.QUERY_COMPLETED,
            processed=False
        )
        
        # Mock empty endpoints result
        event_result = Mock()
        event_result.scalar.return_value = mock_event
        endpoints_result = Mock()
        endpoints_result.scalars.return_value.all.return_value = []
        
        event_processor.db.execute = AsyncMock(side_effect=[event_result, endpoints_result])
        event_processor.db.commit = AsyncMock()
        
        result = await event_processor.process_event(event_id)
        
        assert result["event_id"] == event_id
        assert result["endpoints_matched"] == 0
        assert result["deliveries_created"] == 0
        assert mock_event.processed is True


class TestEventProcessorHelperMethods:
    """Test suite for EventProcessor helper methods."""

    @pytest.fixture
    def event_processor(self, mock_database, mock_redis):
        """Create an EventProcessor instance."""
        return EventProcessor(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_validate_event_data_success(self, event_processor):
        """Test successful event data validation."""
        from app.models.webhook_models import WebhookEventCreate, EventType
        
        event_data = WebhookEventCreate(
            event_type=EventType.QUERY_COMPLETED,
            source="test-service",
            payload={"test": "data"}
        )
        
        # Should not raise any exception
        await event_processor._validate_event_data(event_data)

    @pytest.mark.asyncio
    async def test_validate_event_data_invalid_source(self, event_processor):
        """Test event data validation with invalid source."""
        from app.models.webhook_models import WebhookEventCreate, EventType
        
        event_data = WebhookEventCreate(
            event_type=EventType.QUERY_COMPLETED,
            source="",  # Empty source
            payload={"test": "data"}
        )
        
        with pytest.raises(ValueError, match="source"):
            await event_processor._validate_event_data(event_data)

    @pytest.mark.asyncio
    async def test_validate_event_data_empty_payload(self, event_processor):
        """Test event data validation with empty payload."""
        from app.models.webhook_models import WebhookEventCreate, EventType
        
        event_data = WebhookEventCreate(
            event_type=EventType.QUERY_COMPLETED,
            source="test-service",
            payload={}  # Empty payload
        )
        
        with pytest.raises(ValueError, match="payload"):
            await event_processor._validate_event_data(event_data)

    @pytest.mark.asyncio
    async def test_find_matching_endpoints_success(self, event_processor):
        """Test finding matching endpoints for event."""
        mock_event = Mock(
            event_type=EventType.QUERY_COMPLETED,
            source="test-service",
            payload={"test": "data"}
        )
        
        mock_endpoints = [
            Mock(
                id="endpoint-1",
                event_types=["query.completed"],
                event_filters={},
                status=WebhookStatus.ACTIVE
            ),
            Mock(
                id="endpoint-2",
                event_types=["alert.triggered"],  # Different event type
                event_filters={},
                status=WebhookStatus.ACTIVE
            ),
            Mock(
                id="endpoint-3",
                event_types=["query.completed"],
                event_filters={"source": "test-service"},
                status=WebhookStatus.ACTIVE
            )
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_endpoints
        event_processor.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(event_processor, '_matches_event_filters') as mock_matches:
            mock_matches.side_effect = [True, False, True]  # endpoint-1 and endpoint-3 match
            
            result = await event_processor._find_matching_endpoints(mock_event)
            
            assert len(result) == 2
            assert result[0].id == "endpoint-1"
            assert result[1].id == "endpoint-3"

    def test_matches_event_filters_no_filters(self, event_processor):
        """Test event filter matching with no filters."""
        mock_event = Mock(source="test-service", payload={"test": "data"})
        filters = {}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is True

    def test_matches_event_filters_source_match(self, event_processor):
        """Test event filter matching with source filter."""
        mock_event = Mock(source="test-service", payload={"test": "data"})
        filters = {"source": "test-service"}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is True

    def test_matches_event_filters_source_no_match(self, event_processor):
        """Test event filter matching with non-matching source filter."""
        mock_event = Mock(source="test-service", payload={"test": "data"})
        filters = {"source": "other-service"}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is False

    def test_matches_event_filters_source_list_match(self, event_processor):
        """Test event filter matching with source list filter."""
        mock_event = Mock(source="test-service", payload={"test": "data"})
        filters = {"source": ["test-service", "other-service"]}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is True

    def test_matches_event_filters_payload_field_match(self, event_processor):
        """Test event filter matching with payload field filter."""
        mock_event = Mock(
            source="test-service",
            payload={"user_id": "user-123", "status": "completed"}
        )
        filters = {"payload.user_id": "user-123"}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is True

    def test_matches_event_filters_payload_field_no_match(self, event_processor):
        """Test event filter matching with non-matching payload field filter."""
        mock_event = Mock(
            source="test-service",
            payload={"user_id": "user-123", "status": "completed"}
        )
        filters = {"payload.user_id": "user-456"}
        
        result = event_processor._matches_event_filters(mock_event, filters)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_create_deliveries_success(self, event_processor):
        """Test successful delivery creation."""
        mock_event = Mock(id="event-123")
        mock_endpoints = [
            Mock(id="endpoint-1", retry_attempts=3),
            Mock(id="endpoint-2", retry_attempts=5)
        ]
        
        event_processor.db.add = Mock()
        event_processor.db.flush = AsyncMock()
        
        mock_deliveries = [
            Mock(id="delivery-1"),
            Mock(id="delivery-2")
        ]
        
        with patch('app.services.event_processor.WebhookDelivery') as mock_delivery_class:
            mock_delivery_class.side_effect = mock_deliveries
            
            result = await event_processor._create_deliveries(mock_event, mock_endpoints)
            
            assert len(result) == 2
            assert result == ["delivery-1", "delivery-2"]
            assert event_processor.db.add.call_count == 2
            event_processor.db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_deliveries_success(self, event_processor):
        """Test successful delivery scheduling."""
        delivery_ids = ["delivery-1", "delivery-2"]
        
        # Mock Redis queue operations
        event_processor.cache.redis_client.lpush = AsyncMock()
        
        await event_processor._schedule_deliveries(delivery_ids)
        
        # Should queue each delivery
        assert event_processor.cache.redis_client.lpush.call_count == 2

    def test_event_to_dict_success(self, event_processor, sample_webhook_event):
        """Test successful event conversion to dictionary."""
        result = event_processor._event_to_dict(sample_webhook_event)
        
        assert result["id"] == sample_webhook_event.id
        assert result["endpoint_id"] == sample_webhook_event.endpoint_id
        assert result["event_type"] == sample_webhook_event.event_type.value
        assert result["source"] == sample_webhook_event.source
        assert result["payload"] == sample_webhook_event.payload
        assert result["metadata"] == sample_webhook_event.metadata
        assert result["processed"] == sample_webhook_event.processed
        assert result["created_at"] == sample_webhook_event.created_at


class TestEventProcessorErrorHandling:
    """Test suite for EventProcessor error handling."""

    @pytest.fixture
    def event_processor_with_errors(self):
        """Create EventProcessor with error-prone dependencies."""
        db = AsyncMock()
        redis = AsyncMock()
        
        # Make some operations fail
        db.execute.side_effect = Exception("Database error")
        redis.lpush.side_effect = Exception("Redis error")
        
        return EventProcessor(db, redis)

    @pytest.mark.asyncio
    async def test_create_event_database_error(self, event_processor_with_errors, sample_webhook_event_data):
        """Test event creation with database error."""
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await event_processor_with_errors.create_event(sample_webhook_event_data, user_id)

    @pytest.mark.asyncio
    async def test_list_events_database_error(self, event_processor_with_errors):
        """Test event listing with database error."""
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await event_processor_with_errors.list_events(user_id)

    @pytest.mark.asyncio
    async def test_process_event_database_error(self, event_processor_with_errors):
        """Test event processing with database error."""
        event_id = "test-event-123"
        
        with pytest.raises(Exception, match="Database error"):
            await event_processor_with_errors.process_event(event_id)

    @pytest.mark.asyncio
    async def test_schedule_deliveries_redis_error(self, event_processor_with_errors):
        """Test delivery scheduling with Redis error."""
        delivery_ids = ["delivery-1", "delivery-2"]
        
        with pytest.raises(Exception, match="Redis error"):
            await event_processor_with_errors._schedule_deliveries(delivery_ids)


class TestEventProcessorConcurrency:
    """Test suite for EventProcessor concurrency scenarios."""

    @pytest.fixture
    def event_processor(self, mock_database, mock_redis):
        """Create an EventProcessor instance."""
        return EventProcessor(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_concurrent_event_creation(self, event_processor, sample_webhook_event_data):
        """Test concurrent event creation."""
        user_id = "test-user-123"
        
        # Mock database operations
        event_processor.db.add = Mock()
        event_processor.db.commit = AsyncMock()
        event_processor.db.refresh = AsyncMock()
        
        mock_events = [
            Mock(id=f"event-{i}", event_type=EventType.QUERY_COMPLETED)
            for i in range(3)
        ]
        
        with patch.object(event_processor, '_validate_event_data'), \
             patch.object(event_processor, '_event_to_dict') as mock_to_dict, \
             patch('app.services.event_processor.WebhookEvent') as mock_event_class:
            
            mock_event_class.side_effect = mock_events
            mock_to_dict.side_effect = [
                {"id": f"event-{i}", "event_type": "query.completed"}
                for i in range(3)
            ]
            
            # Create multiple events concurrently
            tasks = [
                event_processor.create_event(sample_webhook_event_data, user_id)
                for _ in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result["id"] == f"event-{i}"
            
            # Verify all events were created
            assert event_processor.db.add.call_count == 3
            assert event_processor.db.commit.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, event_processor):
        """Test concurrent event processing."""
        event_ids = ["event-1", "event-2", "event-3"]
        
        # Mock events and database operations
        mock_events = [
            Mock(id=event_id, event_type=EventType.QUERY_COMPLETED, processed=False)
            for event_id in event_ids
        ]
        
        mock_results = [
            Mock(scalar=Mock(return_value=event))
            for event in mock_events
        ]
        mock_results.extend([
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
            for _ in range(3)
        ])
        
        event_processor.db.execute = AsyncMock(side_effect=mock_results)
        event_processor.db.commit = AsyncMock()
        
        # Process multiple events concurrently
        tasks = [
            event_processor.process_event(event_id)
            for event_id in event_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["event_id"] == event_ids[i]
            assert result["endpoints_matched"] == 0  # No matching endpoints in mock


class TestEventProcessorIntegration:
    """Test suite for EventProcessor integration scenarios."""

    @pytest.fixture
    def event_processor(self, db_session, redis_client):
        """Create EventProcessor with more realistic dependencies."""
        return EventProcessor(db_session, redis_client)

    @pytest.mark.asyncio
    async def test_full_event_lifecycle(self, event_processor, sample_webhook_event_data):
        """Test complete event lifecycle: create, process, deliver."""
        user_id = "test-user-123"
        
        # Mock database operations
        event_id = str(uuid4())
        mock_event = Mock()
        mock_event.id = event_id
        mock_event.event_type = EventType.QUERY_COMPLETED
        mock_event.processed = False
        
        mock_endpoint = Mock(
            id="endpoint-123",
            event_types=["query.completed"],
            event_filters={},
            status=WebhookStatus.ACTIVE,
            retry_attempts=3
        )
        
        event_processor.db.add = Mock()
        event_processor.db.commit = AsyncMock()
        event_processor.db.refresh = AsyncMock()
        event_processor.db.flush = AsyncMock()
        
        # Mock database query results
        event_result = Mock(scalar=Mock(return_value=mock_event))
        endpoints_result = Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_endpoint]))))
        
        event_processor.db.execute = AsyncMock(side_effect=[event_result, endpoints_result])
        event_processor.cache.redis_client.lpush = AsyncMock()
        
        with patch.object(event_processor, '_validate_event_data'), \
             patch.object(event_processor, '_event_to_dict') as mock_to_dict, \
             patch.object(event_processor, '_matches_event_filters', return_value=True), \
             patch('app.services.event_processor.WebhookEvent', return_value=mock_event), \
             patch('app.services.event_processor.WebhookDelivery') as mock_delivery_class:
            
            mock_delivery = Mock(id="delivery-123")
            mock_delivery_class.return_value = mock_delivery
            
            mock_to_dict.return_value = {
                "id": event_id,
                "event_type": "query.completed",
                "processed": False
            }
            
            # 1. Create event
            create_result = await event_processor.create_event(sample_webhook_event_data, user_id)
            assert create_result["id"] == event_id
            
            # 2. Process event
            process_result = await event_processor.process_event(event_id)
            assert process_result["event_id"] == event_id
            assert process_result["endpoints_matched"] == 1
            assert process_result["deliveries_created"] == 1
            
            # Verify Redis queuing was called
            event_processor.cache.redis_client.lpush.assert_called_once()
            
            # Verify event was marked as processed
            assert mock_event.processed is True