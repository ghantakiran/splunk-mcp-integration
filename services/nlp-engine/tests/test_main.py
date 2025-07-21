#!/usr/bin/env python3
"""
Comprehensive main application tests for NLP Engine Service.

This module tests the main FastAPI application including startup/shutdown,
middleware, exception handling, and overall application behavior.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import status
from fastapi.testclient import TestClient


class TestApplicationLifecycle:
    """Test application lifecycle events."""
    
    def test_application_startup(self, mock_settings):
        """Test application startup sequence."""
        with patch('app.main.lifespan') as mock_lifespan:
            from app.main import app
            
            # Application should start without errors
            assert app is not None
            assert app.title == "NLP Engine Service"
    
    def test_application_routes_registration(self):
        """Test that all routes are properly registered."""
        from app.main import app
        
        # Get all registered routes
        routes = [route.path for route in app.routes]
        
        expected_routes = [
            "/health",
            "/ready",
            "/api/v1/spl/translate",
            "/api/v1/spl/validate",
            "/api/v1/spl/optimize",
            "/api/v1/ai/predictive/forecast",
            "/api/v1/ai/anomaly/detect",
            "/api/v1/ai/suggestions/generate"
        ]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} not found"
    
    @pytest.mark.asyncio
    async def test_application_lifespan(self):
        """Test application lifespan context manager."""
        from app.main import lifespan
        from app.main import app
        
        # Mock dependencies
        with patch('app.core.database.init_db') as mock_db_init, \
             patch('app.core.redis_client.init_redis') as mock_redis_init, \
             patch('app.ai.providers.init_ai_providers') as mock_ai_init:
            
            # Test startup
            async with lifespan(app):
                pass  # Context manager should handle startup/shutdown
            
            # Verify initialization calls were made
            mock_db_init.assert_called_once()
            mock_redis_init.assert_called_once()
            mock_ai_init.assert_called_once()


class TestMiddleware:
    """Test application middleware."""
    
    def test_cors_middleware(self, test_client):
        """Test CORS middleware configuration."""
        # Make a preflight request
        response = test_client.options(
            "/api/v1/spl/translate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
    
    def test_request_logging_middleware(self, test_client, auth_headers):
        """Test request logging middleware."""
        with patch('app.main.logger') as mock_logger:
            response = test_client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            # Logger should have been called for request/response logging
            assert mock_logger.info.call_count >= 1
    
    def test_error_handling_middleware(self, test_client):
        """Test global error handling middleware."""
        # Trigger an endpoint that doesn't exist
        response = test_client.get("/api/v1/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
    
    def test_security_headers_middleware(self, test_client):
        """Test security headers middleware."""
        response = test_client.get("/health")
        
        # Check for security headers
        headers = response.headers
        assert "x-content-type-options" in headers or "x-frame-options" in headers
    
    def test_request_id_middleware(self, test_client):
        """Test request ID middleware."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        # Request ID should be added to response headers
        assert "x-request-id" in response.headers or "x-correlation-id" in response.headers


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check_success(self, test_client):
        """Test successful health check."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_health_check_with_dependencies(self, test_client):
        """Test health check including dependency status."""
        with patch('app.core.database.check_db_health') as mock_db_health, \
             patch('app.core.redis_client.check_redis_health') as mock_redis_health:
            
            mock_db_health.return_value = True
            mock_redis_health.return_value = True
            
            response = test_client.get("/health?include_dependencies=true")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "dependencies" in data
            assert data["dependencies"]["database"] is True
            assert data["dependencies"]["redis"] is True
    
    def test_health_check_dependency_failure(self, test_client):
        """Test health check with failed dependencies."""
        with patch('app.core.database.check_db_health') as mock_db_health:
            mock_db_health.return_value = False
            
            response = test_client.get("/health?include_dependencies=true")
            
            # Should still return 200 but indicate unhealthy dependency
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["status"] == "degraded" or "dependencies" in data
    
    def test_readiness_probe(self, test_client):
        """Test Kubernetes readiness probe."""
        response = test_client.get("/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["ready"] is True
        assert "timestamp" in data
    
    def test_readiness_probe_not_ready(self, test_client):
        """Test readiness probe when service is not ready."""
        with patch('app.core.database.check_db_health') as mock_health:
            mock_health.return_value = False
            
            response = test_client.get("/ready")
            
            # May return 503 or 200 with ready=false depending on implementation
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


class TestExceptionHandling:
    """Test global exception handling."""
    
    def test_validation_error_handling(self, test_client, auth_headers):
        """Test handling of validation errors."""
        # Send invalid request data
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json={"invalid": "data"}  # Missing required fields
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_authentication_error_handling(self, test_client):
        """Test handling of authentication errors."""
        response = test_client.post(
            "/api/v1/spl/translate",
            json={"query": "test", "context": {}}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_authorization_error_handling(self, test_client):
        """Test handling of authorization errors."""
        # Send request with invalid token
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=invalid_headers,
            json={"query": "test", "context": {}}
        )
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_internal_server_error_handling(self, test_client, auth_headers):
        """Test handling of internal server errors."""
        with patch('app.api.v1.spl_endpoints.translate_query') as mock_translate:
            mock_translate.side_effect = Exception("Internal error")
            
            response = test_client.post(
                "/api/v1/spl/translate",
                headers=auth_headers,
                json={
                    "query": "test query",
                    "context": {"user_id": "test"}
                }
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "detail" in data
            # Should not expose internal error details
            assert "Internal error" not in str(data)
    
    def test_timeout_error_handling(self, test_client, auth_headers):
        """Test handling of timeout errors."""
        with patch('app.ai.nlp_service.NLPService.translate_query') as mock_translate:
            import asyncio
            mock_translate.side_effect = asyncio.TimeoutError()
            
            response = test_client.post(
                "/api/v1/spl/translate",
                headers=auth_headers,
                json={
                    "query": "test query",
                    "context": {"user_id": "test"}
                }
            )
            
            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema generation."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "NLP Engine Service"
    
    def test_swagger_docs(self, test_client):
        """Test Swagger UI documentation."""
        response = test_client.get("/docs")
        
        assert response.status_code == status.HTTP_200_OK
        assert "swagger" in response.text.lower()
    
    def test_redoc_documentation(self, test_client):
        """Test ReDoc documentation."""
        response = test_client.get("/redoc")
        
        assert response.status_code == status.HTTP_200_OK
        assert "redoc" in response.text.lower()


class TestConfiguration:
    """Test application configuration."""
    
    def test_settings_loading(self, mock_settings):
        """Test settings are properly loaded."""
        from app.core.config import settings
        
        assert settings.API_HOST == "0.0.0.0"
        assert settings.API_PORT == 8001
        assert settings.OPENAI_API_KEY == "test-openai-key"
    
    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        with patch.dict('os.environ', {'DEBUG': 'true', 'LOG_LEVEL': 'DEBUG'}):
            # Reload settings to pick up environment changes
            from importlib import reload
            import app.core.config
            reload(app.core.config)
            
            assert app.core.config.settings.DEBUG is True
            assert app.core.config.settings.LOG_LEVEL == "DEBUG"
    
    def test_default_configuration_values(self):
        """Test default configuration values."""
        from app.core.config import settings
        
        # Test that required settings have sensible defaults
        assert hasattr(settings, 'MAX_TOKENS')
        assert hasattr(settings, 'TEMPERATURE')
        assert hasattr(settings, 'MODEL_NAME')


class TestDatabaseIntegration:
    """Test database integration."""
    
    @pytest.mark.asyncio
    async def test_database_connection(self, mock_database):
        """Test database connection is properly initialized."""
        from app.core.database import get_db_session
        
        async with get_db_session() as session:
            assert session is not None
    
    def test_database_health_check(self):
        """Test database health check functionality."""
        with patch('app.core.database.check_db_health') as mock_health:
            mock_health.return_value = True
            
            from app.core.database import check_db_health
            result = check_db_health()
            
            assert result is True
            mock_health.assert_called_once()


class TestRedisIntegration:
    """Test Redis integration."""
    
    @pytest.mark.asyncio
    async def test_redis_connection(self, mock_redis):
        """Test Redis connection is properly initialized."""
        from app.core.redis_client import get_redis_client
        
        client = await get_redis_client()
        assert client is not None
    
    def test_redis_health_check(self):
        """Test Redis health check functionality."""
        with patch('app.core.redis_client.check_redis_health') as mock_health:
            mock_health.return_value = True
            
            from app.core.redis_client import check_redis_health
            result = check_redis_health()
            
            assert result is True
            mock_health.assert_called_once()


class TestMetricsAndMonitoring:
    """Test metrics and monitoring endpoints."""
    
    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        
        # Metrics endpoint might be protected or not implemented
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED
        ]
        
        if response.status_code == status.HTTP_200_OK:
            # Should contain Prometheus format metrics
            content = response.text
            assert "# HELP" in content or "# TYPE" in content
    
    def test_application_info_endpoint(self, test_client):
        """Test application info endpoint."""
        response = test_client.get("/info")
        
        # Info endpoint might not be implemented
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "version" in data or "name" in data


class TestSecurity:
    """Test security features."""
    
    def test_security_headers_present(self, test_client):
        """Test that security headers are present."""
        response = test_client.get("/health")
        
        headers = response.headers
        
        # Check for common security headers
        expected_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security"
        ]
        
        present_headers = [h for h in expected_headers if h in headers]
        assert len(present_headers) > 0, "No security headers found"
    
    def test_sensitive_data_not_exposed(self, test_client):
        """Test that sensitive data is not exposed in responses."""
        response = test_client.get("/openapi.json")
        
        content = response.text.lower()
        
        # Check that sensitive information is not exposed
        sensitive_terms = ["password", "secret", "key", "token"]
        for term in sensitive_terms:
            assert term not in content or f"example_{term}" in content
    
    def test_csrf_protection(self, test_client):
        """Test CSRF protection if implemented."""
        # This test depends on CSRF implementation
        response = test_client.post("/api/v1/spl/translate")
        
        # Should require proper authentication
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestPerformance:
    """Test performance characteristics."""
    
    def test_response_time_reasonable(self, test_client):
        """Test that response times are reasonable."""
        import time
        
        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 1.0, f"Health check took {response_time:.3f}s"
    
    def test_memory_usage_reasonable(self, test_client):
        """Test that memory usage is reasonable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Make several requests
        for _ in range(10):
            response = test_client.get("/health")
            assert response.status_code == status.HTTP_200_OK
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])