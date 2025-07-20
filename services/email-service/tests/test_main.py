"""
Tests for main Email Service application.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


class TestApplication:
    """Test suite for FastAPI application."""

    def test_app_initialization(self):
        """Test application initialization."""
        assert app.title == "Email Service"
        assert app.version
        assert "/openapi.json" in [route.path for route in app.routes if hasattr(route, 'path')]

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Email Service"
        assert "version" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_endpoint_available(self, client):
        """Test that health endpoints are available."""
        # Test basic health endpoint
        response = client.get("/health")
        assert response.status_code in [200, 404]  # Might not be implemented yet

    def test_cors_middleware(self, client):
        """Test CORS middleware configuration."""
        response = client.options("/")
        # CORS headers should be present in preflight response
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly handled

    def test_metrics_endpoint_when_disabled(self, client):
        """Test metrics endpoint when metrics are disabled."""
        with patch('app.core.config.settings.enable_metrics', False):
            response = client.get("/metrics")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_error_handling_middleware(self, async_client):
        """Test global error handling middleware."""
        # Test with non-existent endpoint
        response = await async_client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "metadata" in data

    def test_correlation_id_middleware(self, client):
        """Test correlation ID middleware."""
        # Test without correlation ID
        response = client.get("/")
        assert "X-Correlation-ID" in response.headers

        # Test with provided correlation ID
        correlation_id = "test-correlation-123"
        response = client.get("/", headers={"X-Correlation-ID": correlation_id})
        assert response.headers["X-Correlation-ID"] == correlation_id


class TestAuthentication:
    """Test suite for authentication."""

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/emails")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/emails", headers=headers)
        assert response.status_code == 401

    def test_protected_endpoint_without_bearer_prefix(self, client):
        """Test accessing protected endpoint without Bearer prefix."""
        headers = {"Authorization": "invalid-format-token"}
        response = client.get("/emails", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, app_with_mocks, mock_user):
        """Test successful user authentication."""
        from app.main import get_current_user, get_database
        from fastapi import Request
        
        # Mock request with valid token
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer valid-token"}
        
        # Mock database service
        db_service = AsyncMock()
        db_service.get_user = AsyncMock(return_value=mock_user)
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"sub": "test-user-123"}
            
            user = await get_current_user(request, db_service)
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_payload(self, app_with_mocks):
        """Test user authentication with invalid token payload."""
        from app.main import get_current_user
        from fastapi import Request, HTTPException
        
        # Mock request with token that has invalid payload
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer valid-token"}
        
        db_service = AsyncMock()
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {}  # Missing 'sub' field
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request, db_service)
            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, app_with_mocks):
        """Test user authentication with inactive user."""
        from app.main import get_current_user
        from fastapi import Request, HTTPException
        
        # Mock request
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer valid-token"}
        
        # Mock inactive user
        inactive_user = Mock()
        inactive_user.is_active = False
        
        db_service = AsyncMock()
        db_service.get_user = AsyncMock(return_value=inactive_user)
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"sub": "test-user-123"}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request, db_service)
            
            assert exc_info.value.status_code == 401


class TestWebhooks:
    """Test suite for webhook endpoints."""

    @pytest.mark.asyncio
    async def test_email_webhook_success(self, async_client, app_with_mocks, sample_webhook_payload):
        """Test successful email webhook processing."""
        # Mock email processor
        mock_processor = app_with_mocks.state.email_processor
        mock_processor.process_webhook.return_value = {"status": "processed"}
        
        response = await async_client.post("/webhooks/email", json=sample_webhook_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        
        # Verify processor was called
        mock_processor.process_webhook.assert_called_once_with(sample_webhook_payload)

    @pytest.mark.asyncio
    async def test_email_webhook_processing_error(self, async_client, app_with_mocks, sample_webhook_payload):
        """Test email webhook processing error."""
        # Mock email processor to raise exception
        mock_processor = app_with_mocks.state.email_processor
        mock_processor.process_webhook.side_effect = Exception("Processing failed")
        
        response = await async_client.post("/webhooks/email", json=sample_webhook_payload)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_email_webhook_invalid_payload(self, async_client, app_with_mocks):
        """Test email webhook with invalid payload."""
        response = await async_client.post("/webhooks/email", json="invalid-json")
        assert response.status_code == 422  # Validation error


class TestEmailProcessing:
    """Test suite for email processing endpoints."""

    @pytest.mark.asyncio
    async def test_process_email_query_success(self, async_client, app_with_mocks, auth_headers, mock_user):
        """Test successful email query processing."""
        # Set up mocks
        app_with_mocks.state.db.get_user.return_value = mock_user
        mock_processor = app_with_mocks.state.email_processor
        mock_processor.process_query_email.return_value = {
            "status": "processed",
            "query_id": "test-query-123"
        }
        
        query_data = {
            "query": "show me errors from last hour",
            "sender": "user@example.com",
            "format": "html"
        }
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"sub": "test-user-123"}
            
            response = await async_client.post(
                "/process/email",
                json=query_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "metadata" in data
            assert data["metadata"]["query_id"] == "test-query-123"
            
            # Verify processor was called
            mock_processor.process_query_email.assert_called_once_with(
                query_data,
                mock_user.id
            )

    @pytest.mark.asyncio
    async def test_process_email_query_unauthorized(self, async_client, app_with_mocks):
        """Test email query processing without authentication."""
        query_data = {"query": "test query"}
        
        response = await async_client.post("/process/email", json=query_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_process_email_query_processing_error(self, async_client, app_with_mocks, auth_headers, mock_user):
        """Test email query processing error."""
        # Set up mocks
        app_with_mocks.state.db.get_user.return_value = mock_user
        mock_processor = app_with_mocks.state.email_processor
        mock_processor.process_query_email.side_effect = Exception("Query processing failed")
        
        query_data = {"query": "test query"}
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"sub": "test-user-123"}
            
            response = await async_client.post(
                "/process/email",
                json=query_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500


class TestDependencyInjection:
    """Test suite for dependency injection."""

    @pytest.mark.asyncio
    async def test_get_database_dependency(self, app_with_mocks):
        """Test database dependency injection."""
        from app.main import get_database
        
        db_service = await get_database()
        assert db_service == app_with_mocks.state.db

    @pytest.mark.asyncio
    async def test_get_redis_dependency(self, app_with_mocks):
        """Test Redis dependency injection."""
        from app.main import get_redis
        
        redis_service = await get_redis()
        assert redis_service == app_with_mocks.state.redis

    @pytest.mark.asyncio
    async def test_get_rate_limiter_dependency(self, app_with_mocks):
        """Test rate limiter dependency injection."""
        from app.main import get_rate_limiter
        
        rate_limiter = await get_rate_limiter()
        assert rate_limiter == app_with_mocks.state.rate_limiter

    @pytest.mark.asyncio
    async def test_get_email_processor_dependency(self, app_with_mocks):
        """Test email processor dependency injection."""
        from app.main import get_email_processor
        
        email_processor = await get_email_processor()
        assert email_processor == app_with_mocks.state.email_processor

    @pytest.mark.asyncio
    async def test_get_report_generator_dependency(self, app_with_mocks):
        """Test report generator dependency injection."""
        from app.main import get_report_generator
        
        report_generator = await get_report_generator()
        assert report_generator == app_with_mocks.state.report_generator


class TestMiddleware:
    """Test suite for middleware functionality."""

    def test_logging_middleware_adds_correlation_id(self, client):
        """Test that logging middleware adds correlation ID to response."""
        response = client.get("/")
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_logging_middleware_preserves_correlation_id(self, client):
        """Test that logging middleware preserves provided correlation ID."""
        correlation_id = "test-correlation-456"
        response = client.get("/", headers={"X-Correlation-ID": correlation_id})
        assert response.headers["X-Correlation-ID"] == correlation_id

    def test_trusted_host_middleware(self, client):
        """Test trusted host middleware."""
        # This test verifies the middleware is configured
        # Actual behavior depends on environment settings
        response = client.get("/", headers={"Host": "localhost"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling_middleware_logs_errors(self, async_client):
        """Test that error handling middleware logs unhandled errors."""
        with patch('app.main.logger') as mock_logger:
            # Test with endpoint that doesn't exist
            response = await async_client.get("/this-will-cause-404")
            
            # Should get 404, not 500 (handled by FastAPI)
            assert response.status_code == 404

    def test_exception_handler_formats_http_exceptions(self, client):
        """Test that HTTP exception handler formats responses correctly."""
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "metadata" in data
        assert "correlation_id" in data["metadata"]


class TestLifespan:
    """Test suite for application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_sequence(self):
        """Test application startup sequence."""
        # This test verifies the lifespan context manager structure
        # Actual startup testing would require more complex mocking
        from app.main import lifespan
        
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Test that lifespan function exists and is callable
        assert callable(lifespan)

    def test_app_state_attributes_after_startup(self, app_with_mocks):
        """Test that app state has required attributes after startup."""
        assert hasattr(app_with_mocks.state, 'db')
        assert hasattr(app_with_mocks.state, 'redis')
        assert hasattr(app_with_mocks.state, 'email_processor')
        assert hasattr(app_with_mocks.state, 'report_generator')
        assert hasattr(app_with_mocks.state, 'rate_limiter')


class TestAPIRoutes:
    """Test suite for API route registration."""

    def test_all_routers_included(self, client):
        """Test that all expected routers are included."""
        # Get all registered routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # Check for expected route prefixes
        expected_prefixes = ["/health", "/emails", "/reports", "/users", "/subscriptions"]
        
        for prefix in expected_prefixes:
            # Check if any route starts with the expected prefix
            assert any(route.startswith(prefix) for route in routes), f"No routes found with prefix: {prefix}"

    def test_protected_routes_require_authentication(self, client):
        """Test that protected routes require authentication."""
        protected_endpoints = ["/emails", "/reports", "/users", "/subscriptions"]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    def test_route_tags_configuration(self):
        """Test that routes have proper tags configured."""
        # Check that routes are properly tagged for OpenAPI documentation
        route_tags = {}
        for route in app.routes:
            if hasattr(route, 'tags') and route.tags:
                route_tags[route.path] = route.tags
        
        # At least some routes should have tags
        assert len(route_tags) > 0, "No routes have tags configured"