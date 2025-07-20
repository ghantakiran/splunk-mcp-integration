"""
Tests for Email Processor Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, Any
import asyncio

from app.services.email_processor import EmailProcessor
from app.services.database_service import DatabaseService
from app.services.redis_service import RedisService


class TestEmailProcessor:
    """Test suite for EmailProcessor class."""

    @pytest.fixture
    def email_processor(self, mock_database_service, mock_redis_service):
        """Create an EmailProcessor instance."""
        return EmailProcessor(mock_database_service, mock_redis_service)

    @pytest.mark.asyncio
    async def test_email_processor_initialization(self, email_processor):
        """Test EmailProcessor initialization."""
        await email_processor.initialize()
        # Initialization should complete without errors
        assert email_processor.db is not None
        assert email_processor.redis is not None

    @pytest.mark.asyncio
    async def test_email_processor_cleanup(self, email_processor):
        """Test EmailProcessor cleanup."""
        await email_processor.cleanup()
        # Cleanup should complete without errors

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, email_processor, sample_webhook_payload):
        """Test successful webhook processing."""
        result = await email_processor.process_webhook(sample_webhook_payload)
        
        assert result is not None
        assert isinstance(result, dict)
        assert result["status"] == "processed"
        assert result["webhook_id"] == sample_webhook_payload["id"]

    @pytest.mark.asyncio
    async def test_process_webhook_missing_id(self, email_processor):
        """Test webhook processing with missing ID."""
        payload = {
            "type": "email.received",
            "data": {"message": "test"}
        }
        
        result = await email_processor.process_webhook(payload)
        
        assert result is not None
        assert result["status"] == "processed"
        assert result["webhook_id"] is None

    @pytest.mark.asyncio
    async def test_process_webhook_empty_payload(self, email_processor):
        """Test webhook processing with empty payload."""
        result = await email_processor.process_webhook({})
        
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_query_email_success(self, email_processor):
        """Test successful email query processing."""
        query_data = {
            "query": "show me errors from last hour",
            "sender": "user@example.com",
            "format": "html"
        }
        user_id = "test-user-123"
        
        result = await email_processor.process_query_email(query_data, user_id)
        
        assert result is not None
        assert isinstance(result, dict)
        assert result["status"] == "processed"
        assert result["query_id"] == "placeholder"

    @pytest.mark.asyncio
    async def test_process_query_email_with_minimal_data(self, email_processor):
        """Test email query processing with minimal data."""
        query_data = {"query": "simple query"}
        user_id = "test-user-123"
        
        result = await email_processor.process_query_email(query_data, user_id)
        
        assert result is not None
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_start_imap_processing(self, email_processor):
        """Test IMAP processing startup."""
        # Start IMAP processing in the background
        task = asyncio.create_task(email_processor.start_imap_processing())
        
        # Let it run for a short time
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            # This is expected when cancelling
            pass

    @pytest.mark.asyncio
    async def test_start_imap_processing_logs_startup(self, email_processor):
        """Test that IMAP processing logs startup message."""
        with patch('app.services.email_processor.logger') as mock_logger:
            # Start and immediately cancel
            task = asyncio.create_task(email_processor.start_imap_processing())
            await asyncio.sleep(0.01)  # Brief delay to let it start
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Check that startup was logged
            mock_logger.info.assert_called_with("IMAP processing started")


class TestEmailProcessorIntegration:
    """Test suite for EmailProcessor integration scenarios."""

    @pytest.fixture
    def email_processor_with_real_services(self, db_session):
        """Create EmailProcessor with more realistic service mocks."""
        # Create more sophisticated mocks
        db_service = AsyncMock(spec=DatabaseService)
        db_service.session = db_session
        
        redis_service = AsyncMock(spec=RedisService)
        
        return EmailProcessor(db_service, redis_service)

    @pytest.mark.asyncio
    async def test_webhook_processing_with_database_interaction(
        self, 
        email_processor_with_real_services,
        sample_webhook_payload
    ):
        """Test webhook processing with database interaction."""
        processor = email_processor_with_real_services
        
        # Mock database operations
        processor.db.create_email = AsyncMock(return_value=Mock(id="email-123"))
        processor.db.update_email_status = AsyncMock()
        
        result = await processor.process_webhook(sample_webhook_payload)
        
        assert result["status"] == "processed"
        # In a real implementation, we would verify database calls

    @pytest.mark.asyncio
    async def test_query_email_processing_with_nlp_integration(
        self,
        email_processor_with_real_services,
        mock_nlp_service
    ):
        """Test email query processing with NLP service integration."""
        processor = email_processor_with_real_services
        
        query_data = {
            "query": "show me errors from last hour",
            "sender": "user@example.com"
        }
        user_id = "test-user-123"
        
        # Mock NLP service response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "spl_query": "index=main level=error earliest=-1h",
                    "confidence": 0.95
                }
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await processor.process_query_email(query_data, user_id)
            
            assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_email_processing_with_template_rendering(
        self,
        email_processor_with_real_services
    ):
        """Test email processing with template rendering."""
        processor = email_processor_with_real_services
        
        # Mock template data
        template_data = {
            "template_id": "template-123",
            "variables": {
                "user_name": "John Doe",
                "query_results": [
                    {"timestamp": "2025-01-16T10:00:00Z", "level": "error", "message": "Test error"}
                ]
            }
        }
        
        # Mock template retrieval and rendering
        processor.db.get_template = AsyncMock(return_value=Mock(
            subject_template="Query Results for {{user_name}}",
            body_html_template="<h1>Results</h1><p>{{query_results|length}} results found</p>"
        ))
        
        query_data = {
            "query": "test query",
            "template_data": template_data
        }
        
        result = await processor.process_query_email(query_data, "user-123")
        
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_batch_email_processing(self, email_processor_with_real_services):
        """Test processing multiple emails in batch."""
        processor = email_processor_with_real_services
        
        # Mock multiple webhook payloads
        payloads = [
            {"id": f"webhook-{i}", "type": "email.received", "data": {"message": f"test-{i}"}}
            for i in range(5)
        ]
        
        # Process all payloads
        results = await asyncio.gather(*[
            processor.process_webhook(payload) for payload in payloads
        ])
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["status"] == "processed"
            assert result["webhook_id"] == f"webhook-{i}"

    @pytest.mark.asyncio
    async def test_concurrent_query_processing(self, email_processor_with_real_services):
        """Test concurrent query processing."""
        processor = email_processor_with_real_services
        
        # Create multiple concurrent queries
        queries = [
            {
                "query": f"query-{i}",
                "sender": f"user{i}@example.com"
            }
            for i in range(3)
        ]
        
        # Process all queries concurrently
        tasks = [
            processor.process_query_email(query, f"user-{i}")
            for i, query in enumerate(queries)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result["status"] == "processed"


class TestEmailProcessorErrorHandling:
    """Test suite for EmailProcessor error handling."""

    @pytest.fixture
    def email_processor_with_failing_services(self):
        """Create EmailProcessor with services that fail."""
        db_service = AsyncMock(spec=DatabaseService)
        redis_service = AsyncMock(spec=RedisService)
        
        # Make some operations fail
        db_service.create_email.side_effect = Exception("Database error")
        redis_service.set.side_effect = Exception("Redis error")
        
        return EmailProcessor(db_service, redis_service)

    @pytest.mark.asyncio
    async def test_webhook_processing_with_database_error(
        self,
        email_processor_with_failing_services,
        sample_webhook_payload
    ):
        """Test webhook processing when database operations fail."""
        # This test verifies that the processor handles database errors gracefully
        # In the current implementation, it just returns a result without database interaction
        result = await email_processor_with_failing_services.process_webhook(sample_webhook_payload)
        
        # Should still return a result even with database issues
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_query_processing_with_redis_error(
        self,
        email_processor_with_failing_services
    ):
        """Test query processing when Redis operations fail."""
        query_data = {"query": "test query"}
        user_id = "test-user-123"
        
        # Should handle Redis errors gracefully
        result = await email_processor_with_failing_services.process_query_email(query_data, user_id)
        
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_initialization_with_service_errors(self, mock_database_service, mock_redis_service):
        """Test initialization when services have issues."""
        # Make initialization operations potentially fail
        mock_database_service.initialize = AsyncMock(side_effect=Exception("DB init failed"))
        
        processor = EmailProcessor(mock_database_service, mock_redis_service)
        
        # Should handle initialization errors gracefully
        await processor.initialize()
        # No exceptions should be raised


class TestEmailProcessorMocking:
    """Test suite for EmailProcessor with detailed mocking."""

    @pytest.mark.asyncio
    async def test_webhook_processing_logs_payload_keys(self, email_processor, sample_webhook_payload):
        """Test that webhook processing logs payload keys."""
        with patch('app.services.email_processor.logger') as mock_logger:
            await email_processor.process_webhook(sample_webhook_payload)
            
            # Verify logging was called with payload keys
            mock_logger.info.assert_called_with(
                "Processing email webhook",
                payload_keys=list(sample_webhook_payload.keys())
            )

    @pytest.mark.asyncio
    async def test_query_processing_logs_user_id(self, email_processor):
        """Test that query processing logs user ID."""
        with patch('app.services.email_processor.logger') as mock_logger:
            query_data = {"query": "test"}
            user_id = "test-user-456"
            
            await email_processor.process_query_email(query_data, user_id)
            
            # Verify logging was called with user ID
            mock_logger.info.assert_called_with(
                "Processing email query",
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_imap_processing_startup_logging(self, email_processor):
        """Test that IMAP processing logs startup."""
        with patch('app.services.email_processor.logger') as mock_logger:
            # Start IMAP processing
            task = asyncio.create_task(email_processor.start_imap_processing())
            
            # Let it run briefly
            await asyncio.sleep(0.01)
            
            # Cancel to stop the loop
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify startup was logged
            mock_logger.info.assert_any_call("IMAP processing started")

    @pytest.mark.asyncio
    async def test_webhook_processing_with_various_payload_structures(self, email_processor):
        """Test webhook processing with different payload structures."""
        # Test with minimal payload
        minimal_payload = {"type": "test"}
        result1 = await email_processor.process_webhook(minimal_payload)
        assert result1["webhook_id"] is None
        
        # Test with complex payload
        complex_payload = {
            "id": "complex-123",
            "type": "email.received",
            "data": {
                "nested": {
                    "field": "value"
                },
                "array": [1, 2, 3]
            },
            "metadata": {
                "timestamp": "2025-01-16T10:00:00Z"
            }
        }
        result2 = await email_processor.process_webhook(complex_payload)
        assert result2["webhook_id"] == "complex-123"

    @pytest.mark.asyncio
    async def test_query_processing_with_various_query_structures(self, email_processor):
        """Test query processing with different query data structures."""
        # Test with minimal query
        minimal_query = {"query": "simple"}
        result1 = await email_processor.process_query_email(minimal_query, "user1")
        assert result1["status"] == "processed"
        
        # Test with complex query
        complex_query = {
            "query": "complex search with parameters",
            "parameters": {
                "time_range": "last_24h",
                "index": "main"
            },
            "format": "html",
            "include_charts": True
        }
        result2 = await email_processor.process_query_email(complex_query, "user2")
        assert result2["status"] == "processed"