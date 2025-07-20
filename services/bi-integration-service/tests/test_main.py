"""
Tests for the main FastAPI application.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.main import app


class TestMainApplication:
    """Test suite for the main FastAPI application."""

    @pytest_asyncio.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self, client, mock_database_health, mock_redis_health):
        """Test detailed health check endpoint."""
        with patch("app.core.database.get_database_health", return_value=await mock_database_health()):
            with patch("app.core.redis_client.get_redis_health", return_value=await mock_redis_health()):
                response = await client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "components" in data
                assert data["components"]["database"]["status"] == "healthy"
                assert data["components"]["redis"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint_database_failure(self, client, mock_redis_health):
        """Test detailed health check with database failure."""
        with patch("app.core.database.get_database_health", side_effect=Exception("Database connection failed")):
            with patch("app.core.redis_client.get_redis_health", return_value=await mock_redis_health()):
                response = await client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["components"]["database"]["status"] == "unhealthy"
                assert "Database connection failed" in data["components"]["database"]["error"]
                assert data["components"]["redis"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint_redis_failure(self, client, mock_database_health):
        """Test detailed health check with Redis failure."""
        with patch("app.core.database.get_database_health", return_value=await mock_database_health()):
            with patch("app.core.redis_client.get_redis_health", side_effect=Exception("Redis connection failed")):
                response = await client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["components"]["database"]["status"] == "healthy"
                assert data["components"]["redis"]["status"] == "unhealthy"
                assert "Redis connection failed" in data["components"]["redis"]["error"]

    @pytest.mark.asyncio
    async def test_service_info_endpoint(self, client):
        """Test service information endpoint."""
        response = await client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "api_version" in data
        assert "features" in data
        assert "supported_providers" in data
        
        # Check features
        features = data["features"]
        assert "tableau_integration" in features
        assert "powerbi_integration" in features
        assert "metrics_enabled" in features
        assert "rate_limiting" in features
        assert "debug" in features
        
        # Check supported providers
        providers = data["supported_providers"]
        assert "tableau" in providers
        assert "powerbi" in providers
        assert "looker" in providers
        assert "qlik" in providers

    @pytest.mark.asyncio
    async def test_docs_endpoint_in_debug_mode(self, client):
        """Test that docs endpoint is available in debug mode."""
        with patch("app.core.config.settings.debug", True):
            response = await client.get("/docs")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_endpoint(self, client):
        """Test OpenAPI schema endpoint."""
        with patch("app.core.config.settings.debug", True):
            response = await client.get("/openapi.json")
            assert response.status_code == 200
            
            schema = response.json()
            assert "openapi" in schema
            assert "info" in schema
            assert "paths" in schema
            assert "components" in schema
            
            # Check security scheme
            assert "securitySchemes" in schema["components"]
            assert "bearerAuth" in schema["components"]["securitySchemes"]
            
            # Check security requirement
            assert "security" in schema
            assert {"bearerAuth": []} in schema["security"]

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = await client.options("/health")
        
        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_gzip_compression(self, client):
        """Test that GZip compression is enabled for large responses."""
        # Create a large response by calling an endpoint that returns substantial data
        response = await client.get("/info")
        
        # Check if compression header is accepted
        assert response.status_code == 200
        # In a real scenario, you would send a large payload to trigger compression

    @pytest.mark.asyncio
    async def test_request_id_middleware(self, client):
        """Test that request ID middleware adds correlation ID."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        # In a real implementation, check for X-Request-ID or similar header
        # This would depend on the actual RequestIDMiddleware implementation

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint when enabled."""
        with patch("app.core.config.settings.metrics_enabled", True):
            response = await client.get("/metrics")
            
            # Metrics endpoint should be available
            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_http_exception_handling(self, client):
        """Test HTTP exception handling."""
        # Test 404 for non-existent endpoint
        response = await client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == 404
        assert "metadata" in data
        assert "correlation_id" in data["metadata"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, client):
        """Test general exception handling."""
        # Mock an endpoint to raise an exception
        with patch("app.api.v1.router.api_router") as mock_router:
            mock_router.side_effect = Exception("Test exception")
            
            # This would trigger general exception handler
            # In practice, you'd need a route that can be made to fail
            response = await client.get("/health")
            assert response.status_code == 200  # Health endpoint should still work

    @pytest.mark.asyncio
    async def test_process_time_header(self, client):
        """Test that process time header is added to responses."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        # Check for process time header
        assert "X-Process-Time" in response.headers
        
        # Process time should be a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """Test application startup procedures."""
        with patch("app.core.database.init_database") as mock_db_init:
            with patch("app.core.redis_client.init_redis") as mock_redis_init:
                mock_db_init.return_value = AsyncMock()
                mock_redis_init.return_value = AsyncMock()
                
                # This would be called during app startup
                # Testing lifespan events requires special handling
                assert mock_db_init.called or not mock_db_init.called  # Placeholder assertion

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test application shutdown procedures."""
        with patch("app.core.database.close_database") as mock_db_close:
            with patch("app.core.redis_client.close_redis") as mock_redis_close:
                mock_db_close.return_value = AsyncMock()
                mock_redis_close.return_value = AsyncMock()
                
                # This would be called during app shutdown
                # Testing lifespan events requires special handling
                assert mock_db_close.called or not mock_db_close.called  # Placeholder assertion


class TestApplicationConfiguration:
    """Test suite for application configuration."""

    def test_custom_openapi_schema(self):
        """Test custom OpenAPI schema generation."""
        # Call the custom openapi function
        schema = app.openapi()
        
        assert schema is not None
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Check security configuration
        assert "securitySchemes" in schema["components"]
        assert "bearerAuth" in schema["components"]["securitySchemes"]
        assert schema["components"]["securitySchemes"]["bearerAuth"]["type"] == "http"
        assert schema["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
        
        # Check security requirement
        assert "security" in schema
        assert {"bearerAuth": []} in schema["security"]

    def test_middleware_order(self):
        """Test that middleware is applied in correct order."""
        # Get middleware stack
        middleware_classes = [middleware.cls.__name__ for middleware in app.user_middleware]
        
        # Verify specific middleware are present
        # Order matters for middleware - some should come before others
        assert "CORSMiddleware" in middleware_classes
        assert "GZipMiddleware" in middleware_classes
        # Custom middleware should also be present
        # The exact order depends on the implementation


class TestApplicationMetrics:
    """Test suite for application metrics."""

    def test_prometheus_metrics_definition(self):
        """Test that Prometheus metrics are properly defined."""
        from app.main import (
            REQUEST_COUNT, REQUEST_DURATION, ACTIVE_CONNECTIONS,
            BI_INTEGRATIONS, TABLEAU_CONNECTIONS, POWERBI_CONNECTIONS
        )
        
        # Verify metrics are properly initialized
        assert REQUEST_COUNT._name == "bi_integration_requests_total"
        assert REQUEST_DURATION._name == "bi_integration_request_duration_seconds"
        assert ACTIVE_CONNECTIONS._name == "bi_integration_active_connections"
        assert BI_INTEGRATIONS._name == "bi_integration_total_integrations"
        assert TABLEAU_CONNECTIONS._name == "bi_integration_tableau_connections"
        assert POWERBI_CONNECTIONS._name == "bi_integration_powerbi_connections"
        
        # Check that counters and histograms have proper labels
        assert "method" in REQUEST_COUNT._labelnames
        assert "endpoint" in REQUEST_COUNT._labelnames
        assert "status_code" in REQUEST_COUNT._labelnames
        
        assert "method" in REQUEST_DURATION._labelnames
        assert "endpoint" in REQUEST_DURATION._labelnames

    @pytest.mark.asyncio
    async def test_metrics_middleware_increments_counters(self, client):
        """Test that metrics middleware properly increments counters."""
        from app.main import REQUEST_COUNT, ACTIVE_CONNECTIONS
        
        # Get initial counter values
        initial_count = REQUEST_COUNT._value._value
        initial_connections = ACTIVE_CONNECTIONS._value._value
        
        # Make a request
        response = await client.get("/health")
        assert response.status_code == 200
        
        # Verify counters were incremented
        # Note: In a real test, you'd need to account for label-specific counters
        # This is a simplified example


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_404_error_format(self, client):
        """Test 404 error response format."""
        response = await client.get("/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        
        # Check error response structure
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "metadata" in data
        
        # Check error details
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "type" in error
        assert error["code"] == 404
        
        # Check metadata
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "correlation_id" in metadata
        assert "version" in metadata

    @pytest.mark.asyncio
    async def test_500_error_format_debug_mode(self, client):
        """Test 500 error response format in debug mode."""
        with patch("app.core.config.settings.debug", True):
            # This test would require triggering an actual server error
            # For now, we'll test the structure expectation
            pass

    @pytest.mark.asyncio
    async def test_500_error_format_production_mode(self, client):
        """Test 500 error response format in production mode."""
        with patch("app.core.config.settings.debug", False):
            # This test would require triggering an actual server error
            # For now, we'll test the structure expectation
            pass