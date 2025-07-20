"""
Tests for Webhook Manager Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, call
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.webhook_manager import WebhookManager
from app.models.webhook_models import (
    WebhookStatus, EventType, DeliveryStatus, WebhookMethod,
    WebhookEndpoint, WebhookEvent, WebhookDelivery, WebhookLog
)
from app.models.user_models import WebhookUser


class TestWebhookManager:
    """Test suite for WebhookManager class."""

    @pytest.fixture
    def webhook_manager(self, mock_database, mock_redis):
        """Create a WebhookManager instance."""
        return WebhookManager(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_webhook_manager_initialization(self, webhook_manager):
        """Test WebhookManager initialization."""
        assert webhook_manager.db is not None
        assert webhook_manager.cache is not None

    @pytest.mark.asyncio
    async def test_create_endpoint_success(self, webhook_manager, sample_webhook_endpoint_data):
        """Test successful webhook endpoint creation."""
        user_id = "test-user-123"
        endpoint_id = str(uuid4())
        
        # Mock database operations
        mock_endpoint = Mock()
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = sample_webhook_endpoint_data["name"]
        mock_endpoint.url = sample_webhook_endpoint_data["url"]
        mock_endpoint.status = WebhookStatus.ACTIVE
        
        webhook_manager.db.add = Mock()
        webhook_manager.db.commit = AsyncMock()
        webhook_manager.db.refresh = AsyncMock()
        
        # Mock validation and helper methods
        with patch.object(webhook_manager, '_validate_endpoint_creation') as mock_validate, \
             patch.object(webhook_manager, '_log_activity') as mock_log, \
             patch.object(webhook_manager, '_invalidate_user_cache') as mock_cache, \
             patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict, \
             patch('app.services.webhook_manager.generate_webhook_secret') as mock_secret:
            
            mock_validate.return_value = None
            mock_log.return_value = None
            mock_cache.return_value = None
            mock_secret.return_value = "generated-secret-123"
            mock_to_dict.return_value = {
                "id": endpoint_id,
                "name": sample_webhook_endpoint_data["name"],
                "url": sample_webhook_endpoint_data["url"],
                "status": "active"
            }
            
            # Mock WebhookEndpoint constructor
            with patch('app.services.webhook_manager.WebhookEndpoint', return_value=mock_endpoint):
                result = await webhook_manager.create_endpoint(sample_webhook_endpoint_data, user_id)
            
            assert result["id"] == endpoint_id
            assert result["name"] == sample_webhook_endpoint_data["name"]
            mock_validate.assert_called_once()
            mock_log.assert_called_once()
            webhook_manager.db.add.assert_called_once_with(mock_endpoint)
            webhook_manager.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_endpoint_with_provided_secret(self, webhook_manager, sample_webhook_endpoint_data):
        """Test webhook endpoint creation with provided secret."""
        user_id = "test-user-123"
        endpoint_data = sample_webhook_endpoint_data.copy()
        endpoint_data["secret"] = "provided-secret-123"
        
        mock_endpoint = Mock()
        mock_endpoint.id = str(uuid4())
        
        webhook_manager.db.add = Mock()
        webhook_manager.db.commit = AsyncMock()
        webhook_manager.db.refresh = AsyncMock()
        
        with patch.object(webhook_manager, '_validate_endpoint_creation') as mock_validate, \
             patch.object(webhook_manager, '_log_activity') as mock_log, \
             patch.object(webhook_manager, '_invalidate_user_cache') as mock_cache, \
             patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            
            mock_validate.return_value = None
            mock_log.return_value = None
            mock_cache.return_value = None
            mock_to_dict.return_value = {"id": mock_endpoint.id}
            
            with patch('app.services.webhook_manager.WebhookEndpoint', return_value=mock_endpoint) as mock_endpoint_class:
                await webhook_manager.create_endpoint(endpoint_data, user_id)
                
                # Verify the provided secret was used
                args, kwargs = mock_endpoint_class.call_args
                assert kwargs['secret'] == "provided-secret-123"

    @pytest.mark.asyncio
    async def test_create_endpoint_validation_error(self, webhook_manager, sample_webhook_endpoint_data):
        """Test webhook endpoint creation with validation error."""
        user_id = "test-user-123"
        
        # Mock validation failure
        with patch.object(webhook_manager, '_validate_endpoint_creation') as mock_validate:
            mock_validate.side_effect = ValueError("Validation failed")
            
            with pytest.raises(ValueError, match="Validation failed"):
                await webhook_manager.create_endpoint(sample_webhook_endpoint_data, user_id)

    @pytest.mark.asyncio
    async def test_list_endpoints_success(self, webhook_manager):
        """Test successful webhook endpoint listing."""
        user_id = "test-user-123"
        
        # Mock database query results
        mock_endpoints = [
            Mock(id="endpoint-1", name="Webhook 1", status=WebhookStatus.ACTIVE),
            Mock(id="endpoint-2", name="Webhook 2", status=WebhookStatus.INACTIVE)
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_endpoints
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            mock_to_dict.side_effect = [
                {"id": "endpoint-1", "name": "Webhook 1", "status": "active"},
                {"id": "endpoint-2", "name": "Webhook 2", "status": "inactive"}
            ]
            
            result = await webhook_manager.list_endpoints(user_id, active_only=False)
            
            assert len(result) == 2
            assert result[0]["id"] == "endpoint-1"
            assert result[1]["id"] == "endpoint-2"
            mock_to_dict.assert_has_calls([call(mock_endpoints[0]), call(mock_endpoints[1])])

    @pytest.mark.asyncio
    async def test_list_endpoints_active_only(self, webhook_manager):
        """Test webhook endpoint listing with active_only filter."""
        user_id = "test-user-123"
        
        # Mock database query results (only active endpoints)
        mock_endpoints = [
            Mock(id="endpoint-1", name="Webhook 1", status=WebhookStatus.ACTIVE)
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_endpoints
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": "endpoint-1", "name": "Webhook 1", "status": "active"}
            
            result = await webhook_manager.list_endpoints(user_id, active_only=True)
            
            assert len(result) == 1
            assert result[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_endpoint_success(self, webhook_manager):
        """Test successful webhook endpoint retrieval."""
        endpoint_id = "test-endpoint-123"
        user_id = "test-user-123"
        
        mock_endpoint = Mock(id=endpoint_id, name="Test Webhook", user_id=user_id)
        mock_result = Mock()
        mock_result.scalar.return_value = mock_endpoint
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": endpoint_id, "name": "Test Webhook"}
            
            result = await webhook_manager.get_endpoint(endpoint_id, user_id)
            
            assert result["id"] == endpoint_id
            assert result["name"] == "Test Webhook"
            mock_to_dict.assert_called_once_with(mock_endpoint)

    @pytest.mark.asyncio
    async def test_get_endpoint_not_found(self, webhook_manager):
        """Test webhook endpoint retrieval when not found."""
        endpoint_id = "nonexistent-endpoint"
        user_id = "test-user-123"
        
        mock_result = Mock()
        mock_result.scalar.return_value = None
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_manager.get_endpoint(endpoint_id, user_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_endpoint_success(self, webhook_manager):
        """Test successful webhook endpoint update."""
        endpoint_id = "test-endpoint-123"
        user_id = "test-user-123"
        update_data = {
            "name": "Updated Webhook",
            "url": "https://example.com/updated"
        }
        
        mock_endpoint = Mock(id=endpoint_id, name="Old Webhook", user_id=user_id)
        mock_result = Mock()
        mock_result.scalar.return_value = mock_endpoint
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        webhook_manager.db.commit = AsyncMock()
        webhook_manager.db.refresh = AsyncMock()
        
        with patch.object(webhook_manager, '_log_activity') as mock_log, \
             patch.object(webhook_manager, '_invalidate_user_cache') as mock_cache, \
             patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            
            mock_log.return_value = None
            mock_cache.return_value = None
            mock_to_dict.return_value = {
                "id": endpoint_id,
                "name": "Updated Webhook",
                "url": "https://example.com/updated"
            }
            
            result = await webhook_manager.update_endpoint(endpoint_id, update_data, user_id)
            
            assert result["name"] == "Updated Webhook"
            assert result["url"] == "https://example.com/updated"
            mock_log.assert_called_once()
            webhook_manager.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_endpoint_not_found(self, webhook_manager):
        """Test webhook endpoint update when not found."""
        endpoint_id = "nonexistent-endpoint"
        user_id = "test-user-123"
        update_data = {"name": "Updated Webhook"}
        
        mock_result = Mock()
        mock_result.scalar.return_value = None
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_manager.update_endpoint(endpoint_id, update_data, user_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_endpoint_success(self, webhook_manager):
        """Test successful webhook endpoint deletion."""
        endpoint_id = "test-endpoint-123"
        user_id = "test-user-123"
        
        mock_endpoint = Mock(id=endpoint_id, user_id=user_id)
        mock_result = Mock()
        mock_result.scalar.return_value = mock_endpoint
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        webhook_manager.db.delete = Mock()
        webhook_manager.db.commit = AsyncMock()
        
        with patch.object(webhook_manager, '_log_activity') as mock_log, \
             patch.object(webhook_manager, '_invalidate_user_cache') as mock_cache:
            
            mock_log.return_value = None
            mock_cache.return_value = None
            
            result = await webhook_manager.delete_endpoint(endpoint_id, user_id)
            
            assert result is True
            webhook_manager.db.delete.assert_called_once_with(mock_endpoint)
            webhook_manager.db.commit.assert_called_once()
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_endpoint_not_found(self, webhook_manager):
        """Test webhook endpoint deletion when not found."""
        endpoint_id = "nonexistent-endpoint"
        user_id = "test-user-123"
        
        mock_result = Mock()
        mock_result.scalar.return_value = None
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_manager.delete_endpoint(endpoint_id, user_id)
        
        assert result is False


class TestWebhookManagerHealthChecks:
    """Test suite for WebhookManager health check methods."""

    @pytest.fixture
    def webhook_manager(self, mock_database, mock_redis):
        """Create a WebhookManager instance."""
        return WebhookManager(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_check_database_health_success(self, webhook_manager):
        """Test successful database health check."""
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_manager.check_database_health()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, webhook_manager):
        """Test database health check failure."""
        webhook_manager.db.execute = AsyncMock(side_effect=Exception("Database error"))
        
        result = await webhook_manager.check_database_health()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, webhook_manager):
        """Test successful Redis health check."""
        webhook_manager.cache.redis_client.ping = AsyncMock(return_value=True)
        
        result = await webhook_manager.check_redis_health()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_redis_health_failure(self, webhook_manager):
        """Test Redis health check failure."""
        webhook_manager.cache.redis_client.ping = AsyncMock(side_effect=Exception("Redis error"))
        
        result = await webhook_manager.check_redis_health()
        
        assert result is False


class TestWebhookManagerAnalytics:
    """Test suite for WebhookManager analytics methods."""

    @pytest.fixture
    def webhook_manager(self, mock_database, mock_redis):
        """Create a WebhookManager instance."""
        return WebhookManager(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_get_analytics_success(self, webhook_manager, sample_webhook_analytics):
        """Test successful analytics retrieval."""
        user_id = "test-user-123"
        
        # Mock database queries for analytics
        webhook_manager.db.execute = AsyncMock()
        
        # Mock the result of multiple queries
        mock_results = [
            Mock(scalar=Mock(return_value=5)),     # total_endpoints
            Mock(scalar=Mock(return_value=4)),     # active_endpoints
            Mock(scalar=Mock(return_value=100)),   # total_events
            Mock(scalar=Mock(return_value=95)),    # total_deliveries
            Mock(scalar=Mock(return_value=85)),    # successful_deliveries
            Mock(scalar=Mock(return_value=10)),    # failed_deliveries
        ]
        webhook_manager.db.execute.side_effect = mock_results
        
        with patch.object(webhook_manager, '_get_events_by_type') as mock_events, \
             patch.object(webhook_manager, '_get_deliveries_by_status') as mock_deliveries, \
             patch.object(webhook_manager, '_get_recent_activity') as mock_activity:
            
            mock_events.return_value = {"query.completed": 50, "alert.triggered": 30}
            mock_deliveries.return_value = {"delivered": 85, "failed": 10}
            mock_activity.return_value = [{"event": "webhook.created", "timestamp": datetime.utcnow()}]
            
            result = await webhook_manager.get_analytics(user_id)
            
            assert result["total_endpoints"] == 5
            assert result["active_endpoints"] == 4
            assert result["total_events"] == 100
            assert "success_rate" in result
            assert "events_by_type" in result
            assert "deliveries_by_status" in result
            assert "recent_activity" in result

    @pytest.mark.asyncio
    async def test_get_analytics_empty_data(self, webhook_manager):
        """Test analytics retrieval with no data."""
        user_id = "test-user-123"
        
        # Mock empty results
        mock_results = [
            Mock(scalar=Mock(return_value=0)),  # total_endpoints
            Mock(scalar=Mock(return_value=0)),  # active_endpoints
            Mock(scalar=Mock(return_value=0)),  # total_events
            Mock(scalar=Mock(return_value=0)),  # total_deliveries
            Mock(scalar=Mock(return_value=0)),  # successful_deliveries
            Mock(scalar=Mock(return_value=0)),  # failed_deliveries
        ]
        webhook_manager.db.execute.side_effect = mock_results
        
        with patch.object(webhook_manager, '_get_events_by_type') as mock_events, \
             patch.object(webhook_manager, '_get_deliveries_by_status') as mock_deliveries, \
             patch.object(webhook_manager, '_get_recent_activity') as mock_activity:
            
            mock_events.return_value = {}
            mock_deliveries.return_value = {}
            mock_activity.return_value = []
            
            result = await webhook_manager.get_analytics(user_id)
            
            assert result["total_endpoints"] == 0
            assert result["success_rate"] == 0.0
            assert result["average_response_time"] == 0.0


class TestWebhookManagerHelperMethods:
    """Test suite for WebhookManager helper methods."""

    @pytest.fixture
    def webhook_manager(self, mock_database, mock_redis):
        """Create a WebhookManager instance."""
        return WebhookManager(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_validate_endpoint_creation_success(self, webhook_manager):
        """Test successful endpoint creation validation."""
        from app.models.webhook_models import WebhookEndpointCreate, EventType
        
        create_data = WebhookEndpointCreate(
            name="Test Webhook",
            url="https://example.com/webhook",
            event_types=[EventType.QUERY_COMPLETED]
        )
        user_id = "test-user-123"
        
        # Mock user quota check
        with patch.object(webhook_manager, '_check_user_endpoint_quota') as mock_quota, \
             patch('app.services.webhook_manager.validate_webhook_url') as mock_validate_url, \
             patch('app.services.webhook_manager.validate_webhook_headers') as mock_validate_headers:
            
            mock_quota.return_value = True
            mock_validate_url.return_value = None
            mock_validate_headers.return_value = None
            
            # Should not raise any exception
            await webhook_manager._validate_endpoint_creation(create_data, user_id)
            
            mock_quota.assert_called_once_with(user_id)
            mock_validate_url.assert_called_once()
            mock_validate_headers.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_endpoint_creation_quota_exceeded(self, webhook_manager):
        """Test endpoint creation validation when quota exceeded."""
        from app.models.webhook_models import WebhookEndpointCreate, EventType
        
        create_data = WebhookEndpointCreate(
            name="Test Webhook",
            url="https://example.com/webhook",
            event_types=[EventType.QUERY_COMPLETED]
        )
        user_id = "test-user-123"
        
        with patch.object(webhook_manager, '_check_user_endpoint_quota') as mock_quota:
            mock_quota.return_value = False
            
            with pytest.raises(ValueError, match="quota"):
                await webhook_manager._validate_endpoint_creation(create_data, user_id)

    @pytest.mark.asyncio
    async def test_log_activity_success(self, webhook_manager):
        """Test successful activity logging."""
        endpoint_id = "test-endpoint-123"
        user_id = "test-user-123"
        action = "created"
        details = {"name": "Test Webhook", "url": "https://example.com/webhook"}
        
        webhook_manager.db.add = Mock()
        webhook_manager.db.commit = AsyncMock()
        
        with patch('app.services.webhook_manager.WebhookLog') as mock_log_class:
            mock_log = Mock()
            mock_log_class.return_value = mock_log
            
            await webhook_manager._log_activity(endpoint_id, user_id, action, details)
            
            webhook_manager.db.add.assert_called_once_with(mock_log)
            webhook_manager.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_user_cache_success(self, webhook_manager):
        """Test successful user cache invalidation."""
        user_id = "test-user-123"
        
        webhook_manager.cache.delete = AsyncMock()
        
        await webhook_manager._invalidate_user_cache(user_id)
        
        webhook_manager.cache.delete.assert_called()

    def test_endpoint_to_dict_success(self, webhook_manager, sample_webhook_endpoint):
        """Test successful endpoint conversion to dictionary."""
        result = webhook_manager._endpoint_to_dict(sample_webhook_endpoint)
        
        assert result["id"] == sample_webhook_endpoint.id
        assert result["name"] == sample_webhook_endpoint.name
        assert result["url"] == sample_webhook_endpoint.url
        assert result["status"] == sample_webhook_endpoint.status.value
        assert result["method"] == sample_webhook_endpoint.method.value
        assert result["headers"] == sample_webhook_endpoint.headers
        assert result["timeout"] == sample_webhook_endpoint.timeout


class TestWebhookManagerErrorHandling:
    """Test suite for WebhookManager error handling."""

    @pytest.fixture
    def webhook_manager_with_errors(self):
        """Create WebhookManager with error-prone dependencies."""
        db = AsyncMock()
        redis = AsyncMock()
        
        # Make some operations fail
        db.execute.side_effect = Exception("Database error")
        redis.ping.side_effect = Exception("Redis error")
        
        return WebhookManager(db, redis)

    @pytest.mark.asyncio
    async def test_create_endpoint_database_error(self, webhook_manager_with_errors, sample_webhook_endpoint_data):
        """Test webhook endpoint creation with database error."""
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await webhook_manager_with_errors.create_endpoint(sample_webhook_endpoint_data, user_id)

    @pytest.mark.asyncio
    async def test_list_endpoints_database_error(self, webhook_manager_with_errors):
        """Test webhook endpoint listing with database error."""
        user_id = "test-user-123"
        
        with pytest.raises(Exception, match="Database error"):
            await webhook_manager_with_errors.list_endpoints(user_id)

    @pytest.mark.asyncio
    async def test_check_redis_health_with_error(self, webhook_manager_with_errors):
        """Test Redis health check with connection error."""
        result = await webhook_manager_with_errors.check_redis_health()
        
        assert result is False


class TestWebhookManagerCacheIntegration:
    """Test suite for WebhookManager cache integration."""

    @pytest.fixture
    def webhook_manager(self, mock_database, mock_redis):
        """Create a WebhookManager instance."""
        return WebhookManager(mock_database, mock_redis)

    @pytest.mark.asyncio
    async def test_list_endpoints_with_cache_hit(self, webhook_manager):
        """Test webhook endpoint listing with cache hit."""
        user_id = "test-user-123"
        cached_data = [
            {"id": "endpoint-1", "name": "Cached Webhook 1"},
            {"id": "endpoint-2", "name": "Cached Webhook 2"}
        ]
        
        webhook_manager.cache.get = AsyncMock(return_value=cached_data)
        
        result = await webhook_manager.list_endpoints(user_id)
        
        assert result == cached_data
        webhook_manager.cache.get.assert_called_once()
        # Database should not be queried when cache hits
        webhook_manager.db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_endpoints_with_cache_miss(self, webhook_manager):
        """Test webhook endpoint listing with cache miss."""
        user_id = "test-user-123"
        
        # Mock cache miss
        webhook_manager.cache.get = AsyncMock(return_value=None)
        webhook_manager.cache.set = AsyncMock()
        
        # Mock database query
        mock_endpoints = [
            Mock(id="endpoint-1", name="DB Webhook 1")
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_endpoints
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": "endpoint-1", "name": "DB Webhook 1"}
            
            result = await webhook_manager.list_endpoints(user_id)
            
            assert len(result) == 1
            assert result[0]["name"] == "DB Webhook 1"
            webhook_manager.cache.get.assert_called_once()
            webhook_manager.cache.set.assert_called_once()
            webhook_manager.db.execute.assert_called_once()


class TestWebhookManagerIntegration:
    """Test suite for WebhookManager integration scenarios."""

    @pytest.fixture
    def webhook_manager(self, db_session, redis_client):
        """Create WebhookManager with more realistic dependencies."""
        return WebhookManager(db_session, redis_client)

    @pytest.mark.asyncio
    async def test_full_endpoint_lifecycle(self, webhook_manager, sample_webhook_endpoint_data):
        """Test complete endpoint lifecycle: create, update, delete."""
        user_id = "test-user-123"
        
        # Mock database operations for full lifecycle
        endpoint_id = str(uuid4())
        mock_endpoint = Mock()
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = sample_webhook_endpoint_data["name"]
        mock_endpoint.user_id = user_id
        
        # Setup mocks for create operation
        webhook_manager.db.add = Mock()
        webhook_manager.db.commit = AsyncMock()
        webhook_manager.db.refresh = AsyncMock()
        webhook_manager.db.delete = Mock()
        
        # Mock query results for get/update/delete operations
        mock_result = Mock()
        mock_result.scalar.return_value = mock_endpoint
        webhook_manager.db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(webhook_manager, '_validate_endpoint_creation'), \
             patch.object(webhook_manager, '_log_activity'), \
             patch.object(webhook_manager, '_invalidate_user_cache'), \
             patch.object(webhook_manager, '_endpoint_to_dict') as mock_to_dict, \
             patch('app.services.webhook_manager.generate_webhook_secret', return_value="secret"), \
             patch('app.services.webhook_manager.WebhookEndpoint', return_value=mock_endpoint):
            
            mock_to_dict.return_value = {
                "id": endpoint_id,
                "name": sample_webhook_endpoint_data["name"],
                "status": "active"
            }
            
            # 1. Create endpoint
            create_result = await webhook_manager.create_endpoint(sample_webhook_endpoint_data, user_id)
            assert create_result["id"] == endpoint_id
            
            # 2. Update endpoint
            update_data = {"name": "Updated Webhook"}
            mock_to_dict.return_value["name"] = "Updated Webhook"
            update_result = await webhook_manager.update_endpoint(endpoint_id, update_data, user_id)
            assert update_result["name"] == "Updated Webhook"
            
            # 3. Delete endpoint
            delete_result = await webhook_manager.delete_endpoint(endpoint_id, user_id)
            assert delete_result is True
            
            # Verify all operations were logged
            assert webhook_manager.db.commit.call_count >= 3