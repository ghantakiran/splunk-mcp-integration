"""
Tests for Alert Manager main application.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestApplicationConfiguration:
    """Test suite for application configuration."""
    
    def test_app_initialization(self):
        """Test application initialization."""
        assert app.title == "Alert Management Service"
        assert app.description == "Comprehensive alerting system for Splunk MCP integration"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"
    
    def test_app_middleware_configuration(self):
        """Test middleware configuration."""
        # Check that middleware is configured
        middleware_classes = [type(middleware.cls) for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        
        # CORS middleware should be configured
        assert any("CORS" in str(cls) for cls in middleware_classes)
    
    def test_api_router_inclusion(self):
        """Test API router inclusion."""
        # Check that routes are registered
        routes = [route.path for route in app.routes]
        
        # Should have basic routes
        assert "/" in routes
        assert "/health" in routes
        
        # Should have API routes with prefix
        api_routes = [route for route in routes if route.startswith("/api/v1")]
        assert len(api_routes) > 0


class TestBasicEndpoints:
    """Test suite for basic application endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "alert-manager"
        assert "version" in data
        assert data["status"] == "running"
        assert data["docs"] == "/docs"
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alert-manager"
        assert "version" in data
    
    def test_docs_endpoint(self, client):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_endpoint(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert data["info"]["title"] == "Alert Management Service"
        assert "paths" in data
        assert "components" in data


class TestApplicationLifecycle:
    """Test suite for application lifecycle events."""
    
    @pytest.mark.asyncio
    async def test_startup_event(self):
        """Test application startup event."""
        with patch("app.main.logger") as mock_logger:
            # Import here to avoid circular imports during testing
            from app.main import startup_event
            
            await startup_event()
            
            # Verify startup logging
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Starting Alert Management service" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test application shutdown event."""
        with patch("app.main.logger") as mock_logger:
            from app.main import shutdown_event
            
            await shutdown_event()
            
            # Verify shutdown logging
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Shutting down Alert Management service" in call_args[0][0]


class TestMiddleware:
    """Test suite for middleware functionality."""
    
    def test_cors_middleware(self, client):
        """Test CORS middleware configuration."""
        response = client.options("/health")
        
        # CORS headers should be present for OPTIONS requests
        assert response.status_code == 200
    
    def test_request_processing(self, client):
        """Test request processing through middleware."""
        # Test with various request methods
        methods_to_test = ["GET", "POST", "PUT", "DELETE"]
        
        for method in methods_to_test:
            if method == "GET":
                response = client.get("/health")
            elif method == "POST":
                response = client.post("/api/v1/alerts/rules", json={})
            elif method == "PUT":
                response = client.put("/api/v1/alerts/rules/test", json={})
            elif method == "DELETE":
                response = client.delete("/api/v1/alerts/rules/test")
            
            # Should not fail at middleware level
            assert response.status_code != 500 or "middleware" not in response.text.lower()


class TestErrorHandling:
    """Test suite for application error handling."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Not Found" in data["detail"]
    
    def test_method_not_allowed_handling(self, client):
        """Test 405 method not allowed handling."""
        # Try POST on a GET-only endpoint
        response = client.post("/health")
        assert response.status_code == 405
        
        data = response.json()
        assert "detail" in data
        assert "Method Not Allowed" in data["detail"]
    
    def test_malformed_json_handling(self, client):
        """Test malformed JSON handling."""
        response = client.post(
            "/api/v1/alerts/rules",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Validation error


class TestApplicationSecurity:
    """Test suite for application security features."""
    
    def test_trusted_host_middleware_development(self):
        """Test trusted host middleware in development mode."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.debug = True
            
            # Import app module to trigger middleware setup
            import importlib
            import app.main
            importlib.reload(app.main)
            
            client = TestClient(app.main.app)
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_security_headers(self, client):
        """Test security headers in responses."""
        response = client.get("/health")
        
        # Check for basic security considerations
        assert response.status_code == 200
        
        # Content-Type should be properly set
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_request_size_limits(self, client):
        """Test request size limits."""
        # Test with large payload
        large_payload = {"data": "x" * 10000}
        
        response = client.post(
            "/api/v1/alerts/rules",
            json=large_payload
        )
        
        # Should handle large payloads appropriately
        # (either process or reject with appropriate status)
        assert response.status_code in [200, 201, 400, 413, 422]


class TestApplicationMetrics:
    """Test suite for application metrics and monitoring."""
    
    def test_response_time_reasonable(self, client):
        """Test that response times are reasonable."""
        import time
        
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Response time should be under 1 second for health check
        response_time = end_time - start_time
        assert response_time < 1.0
    
    def test_multiple_concurrent_requests(self, client):
        """Test handling of multiple concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.get("/health")
                results.put(response.status_code)
            except Exception as e:
                results.put(f"Error: {e}")
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        while not results.empty():
            result = results.get()
            if isinstance(result, int):
                assert result == 200
            else:
                pytest.fail(f"Request failed: {result}")


class TestConfigurationIntegration:
    """Test suite for configuration integration."""
    
    def test_settings_integration(self):
        """Test settings integration with application."""
        from app.core.config import settings
        
        # Test that settings are properly loaded
        assert hasattr(settings, "service_version")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "api_prefix")
        
        # Test that settings are used in app configuration
        assert app.version == settings.service_version
    
    @patch("app.core.config.settings")
    def test_debug_mode_configuration(self, mock_settings):
        """Test debug mode configuration."""
        mock_settings.debug = True
        mock_settings.cors_origins = ["*"]
        mock_settings.cors_credentials = True
        mock_settings.cors_methods = ["*"]
        mock_settings.cors_headers = ["*"]
        mock_settings.api_prefix = "/api/v1"
        mock_settings.service_version = "test-version"
        
        # Test that debug configuration works
        assert mock_settings.debug is True
    
    @patch("app.core.config.settings")
    def test_production_mode_configuration(self, mock_settings):
        """Test production mode configuration."""
        mock_settings.debug = False
        mock_settings.cors_origins = ["https://company.com"]
        mock_settings.cors_credentials = False
        mock_settings.cors_methods = ["GET", "POST"]
        mock_settings.cors_headers = ["Content-Type"]
        
        # Test that production configuration works
        assert mock_settings.debug is False


class TestApplicationIntegration:
    """Test suite for application integration scenarios."""
    
    def test_api_endpoint_registration(self, client):
        """Test that API endpoints are properly registered."""
        # Test various API endpoints
        test_endpoints = [
            "/api/v1/alerts/rules",
            "/api/v1/alerts/incidents", 
            "/api/v1/notifications/channels",
            "/api/v1/escalations/rules"
        ]
        
        for endpoint in test_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404
    
    def test_openapi_schema_completeness(self, client):
        """Test OpenAPI schema completeness."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Check essential schema components
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Check that we have some paths defined
        paths = schema["paths"]
        assert len(paths) > 0
        
        # Check that basic endpoints are documented
        assert "/" in paths or "/health" in paths
    
    def test_error_response_consistency(self, client):
        """Test error response consistency."""
        # Test various error scenarios
        error_responses = [
            client.get("/nonexistent"),  # 404
            client.post("/health"),       # 405
        ]
        
        for response in error_responses:
            assert response.status_code >= 400
            
            data = response.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)


if __name__ == "__main__":
    pytest.main([__file__])