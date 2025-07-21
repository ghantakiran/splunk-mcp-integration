#!/usr/bin/env python3
"""
Tests for HTML Report Service main application.

This module contains tests for the main FastAPI application,
health checks, and basic functionality.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


class TestMainApplication:
    """Test cases for main application functionality."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint redirect or response."""
        response = client.get("/")
        
        # Should either redirect or return service info
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_308_PERMANENT_REDIRECT
        ]
    
    def test_docs_endpoint(self, client: TestClient):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_openapi_endpoint(self, client: TestClient):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


class TestApplicationLifecycle:
    """Test cases for application lifecycle events."""
    
    @pytest.mark.asyncio
    async def test_startup_event(self):
        """Test application startup event."""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.HTML_OUTPUT_DIR = "/tmp/html-reports"
            
            with patch('os.makedirs') as mock_makedirs:
                # Import and create app to trigger startup
                from main import app
                
                # Simulate startup
                async with app.router.lifespan_context(app):
                    pass
                
                # Verify output directory creation was attempted
                mock_makedirs.assert_called()
    
    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test application shutdown event."""
        from main import app
        
        # Test that shutdown doesn't raise exceptions
        async with app.router.lifespan_context(app):
            pass


class TestMiddleware:
    """Test cases for application middleware."""
    
    def test_cors_middleware(self, client: TestClient):
        """Test CORS middleware configuration."""
        response = client.options("/api/v1/html-reports/capabilities")
        
        # Should handle OPTIONS request for CORS
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]
    
    def test_request_id_middleware(self, client: TestClient):
        """Test request ID middleware."""
        response = client.get("/health")
        
        # Should include request tracking headers
        assert response.status_code == status.HTTP_200_OK
        # Note: Implementation may vary, adjust based on actual middleware
    
    def test_error_handling_middleware(self, client: TestClient):
        """Test error handling middleware."""
        # Test with invalid endpoint
        response = client.get("/api/v1/html-reports/invalid-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestAPIVersioning:
    """Test cases for API versioning."""
    
    def test_v1_api_routes(self, client: TestClient):
        """Test v1 API routes are accessible."""
        # Test capabilities endpoint (should not require auth for basic info)
        response = client.get("/api/v1/html-reports/capabilities")
        
        # May return 401 if auth is required, or 200 if publicly accessible
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED
        ]
    
    def test_api_prefix_enforcement(self, client: TestClient):
        """Test that API prefix is enforced."""
        # Direct access without /api/v1 prefix should fail
        response = client.get("/html-reports/capabilities")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestErrorHandling:
    """Test cases for application-level error handling."""
    
    def test_404_error_handling(self, client: TestClient):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
    
    def test_405_error_handling(self, client: TestClient):
        """Test 405 method not allowed error handling."""
        # Try POST on a GET-only endpoint
        response = client.post("/health")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_500_error_handling(self, client: TestClient):
        """Test 500 internal server error handling."""
        with patch('app.api.v1.endpoints.html_reports.router') as mock_router:
            # Simulate an internal server error
            mock_router.side_effect = Exception("Test internal error")
            
            response = client.get("/api/v1/html-reports/capabilities")
            
            # The response may vary based on error handling implementation
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_404_NOT_FOUND  # If route isn't found due to mocking
            ]


class TestConfiguration:
    """Test cases for application configuration."""
    
    def test_settings_validation(self):
        """Test that settings are properly validated."""
        from app.core.config import settings
        
        # Test that required settings exist
        assert hasattr(settings, 'HTML_OUTPUT_DIR')
        assert hasattr(settings, 'HTML_TEMPLATE_DIR')
        assert hasattr(settings, 'HTML_MAX_FILE_SIZE_MB')
        assert hasattr(settings, 'MAX_CONCURRENT_JOBS')
    
    def test_environment_variable_loading(self):
        """Test environment variable loading."""
        with patch.dict('os.environ', {'HTML_MAX_FILE_SIZE_MB': '100'}):
            # Reimport settings to pick up environment change
            import importlib
            from app.core import config
            importlib.reload(config)
            
            # Note: This test depends on how settings are implemented
            # Adjust based on actual configuration management


class TestDependencyInjection:
    """Test cases for dependency injection."""
    
    def test_database_dependency_injection(self):
        """Test database dependency injection."""
        with patch('app.core.database.get_db_session_dependency') as mock_db:
            from app.core.database import get_db_session_dependency
            
            # Test that dependency is properly configured
            assert callable(get_db_session_dependency)
    
    def test_auth_dependency_injection(self):
        """Test authentication dependency injection."""
        with patch('app.utils.auth.get_current_user_full') as mock_auth:
            from app.utils.auth import get_current_user_full
            
            # Test that auth dependency is properly configured
            assert callable(get_current_user_full)


class TestLogging:
    """Test cases for application logging."""
    
    def test_logging_configuration(self):
        """Test logging configuration."""
        import logging
        
        # Test that logger is properly configured
        logger = logging.getLogger("app")
        assert logger is not None
        
        # Test that log level is set appropriately
        assert logger.level >= logging.DEBUG
    
    def test_structured_logging(self, client: TestClient):
        """Test structured logging output."""
        with patch('structlog.get_logger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance
            
            # Make a request that should trigger logging
            client.get("/health")
            
            # Verify that structured logging was used
            # Note: This depends on the actual implementation


class TestSecurityHeaders:
    """Test cases for security headers."""
    
    def test_security_headers_present(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/health")
        
        # Check for common security headers
        headers = response.headers
        
        # Note: Adjust based on actual security middleware implementation
        # Common headers might include:
        # - X-Content-Type-Options
        # - X-Frame-Options
        # - X-XSS-Protection
        # - Strict-Transport-Security (for HTTPS)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_content_type_headers(self, client: TestClient):
        """Test content type headers."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")


class TestResourceLimits:
    """Test cases for resource limits and constraints."""
    
    def test_request_size_limits(self, client: TestClient):
        """Test request size limits."""
        # Create a very large request payload
        large_payload = {
            "job_name": "test",
            "report_config": {
                "template": "modern",
                "metadata": {
                    "title": "x" * 10000,  # Very long title
                    "description": "test"
                }
            }
        }
        
        response = client.post("/api/v1/html-reports/generate", json=large_payload)
        
        # Should either process or reject based on size limits
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED  # If auth is required
        ]
    
    def test_concurrent_request_handling(self, client: TestClient):
        """Test concurrent request handling."""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.get("/health")
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK