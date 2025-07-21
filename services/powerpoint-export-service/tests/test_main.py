#!/usr/bin/env python3
"""
Comprehensive main application tests for PowerPoint Export Service.

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
        with patch('main.lifespan') as mock_lifespan:
            from main import app
            
            # Application should start without errors
            assert app is not None
            assert app.title == "PowerPoint Export Service"
    
    def test_application_routes_registration(self):
        """Test that all routes are properly registered."""
        from main import app
        
        # Get all registered routes
        routes = [route.path for route in app.routes]
        
        expected_routes = [
            "/",
            "/health",
            "/api/v1/health/",
            "/api/v1/powerpoint-exports/generate",
            "/api/v1/powerpoint-exports/bulk-generate",
            "/api/v1/powerpoint-exports/jobs",
            "/api/v1/powerpoint-exports/capabilities",
            "/api/v1/templates/"
        ]
        
        for expected_route in expected_routes:
            route_found = any(expected_route in route or route.startswith(expected_route.replace("{", "").replace("}", "")) for route in routes)
            assert route_found, f"Route {expected_route} not found"


class TestMiddleware:
    """Test application middleware."""
    
    def test_cors_middleware(self, test_client):
        """Test CORS middleware configuration."""
        # Make a preflight request
        response = test_client.options(
            "/api/v1/powerpoint-exports/generate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
    
    def test_security_headers_middleware(self, test_client):
        """Test security headers middleware."""
        response = test_client.get("/health")
        
        # Check for security headers
        headers = response.headers
        security_header_found = any(h in headers for h in [
            "x-content-type-options", 
            "x-frame-options",
            "strict-transport-security"
        ])
        assert security_header_found
    
    def test_request_id_middleware(self, test_client):
        """Test request ID middleware adds correlation ID."""
        response = test_client.get("/health")
        
        # Should have request ID in headers or response
        assert response.status_code == status.HTTP_200_OK
        # Request ID might be in headers or response data
        assert "x-request-id" in response.headers or "correlation_id" in str(response.content)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["service"] == "PowerPoint Export Service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_health_check_success(self, test_client):
        """Test successful health check."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "powerpoint-export-service"
        assert "timestamp" in data
        assert "version" in data
    
    def test_api_health_endpoint(self, test_client):
        """Test API health endpoint."""
        response = test_client.get("/api/v1/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "dependencies" in data
        assert "system_info" in data
    
    def test_readiness_probe(self, test_client):
        """Test Kubernetes readiness probe."""
        with patch('app.api.v1.endpoints.health.check_database_connection') as mock_db, \
             patch('app.api.v1.endpoints.health.check_redis_connection') as mock_redis:
            
            mock_db.return_value = True
            mock_redis.return_value = True
            
            response = test_client.get("/api/v1/health/ready")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["ready"] is True
            assert "dependencies" in data
    
    def test_liveness_probe(self, test_client):
        """Test Kubernetes liveness probe."""
        response = test_client.get("/api/v1/health/live")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["alive"] is True


class TestExceptionHandling:
    """Test global exception handling."""
    
    def test_validation_error_handling(self, test_client, auth_headers):
        """Test handling of validation errors."""
        # Send invalid request data
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json={"invalid": "data"}  # Missing required fields
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
    
    def test_authentication_error_handling(self, test_client):
        """Test handling of authentication errors."""
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            json={"title": "Test", "slides": []}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_not_found_error_handling(self, test_client, auth_headers):
        """Test handling of 404 errors."""
        response = test_client.get(
            "/api/v1/powerpoint-exports/jobs/non-existent-job",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_internal_server_error_handling(self, test_client, auth_headers):
        """Test handling of internal server errors."""
        with patch('app.services.powerpoint_generator.PowerPointGenerator.generate_presentation') as mock_gen:
            mock_gen.side_effect = Exception("Internal error")
            
            response = test_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json={
                    "title": "Test Presentation",
                    "slides": [{"title": "Slide 1", "content": []}]
                }
            )
        
        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]


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
        assert data["info"]["title"] == "PowerPoint Export Service"
        assert data["info"]["version"] == "1.0.0"
    
    def test_swagger_ui_available(self, test_client):
        """Test that Swagger UI is available."""
        response = test_client.get("/docs")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_available(self, test_client):
        """Test that ReDoc is available."""
        response = test_client.get("/redoc")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]


class TestConfiguration:
    """Test application configuration."""
    
    def test_settings_loading(self, mock_settings):
        """Test settings are properly loaded."""
        from app.core.config import settings
        
        assert settings.API_PORT == 8011
        assert settings.PPT_MAX_SLIDES == 100
        assert settings.DEFAULT_THEME == "office"
    
    def test_environment_specific_settings(self, mock_settings):
        """Test environment-specific settings."""
        from app.core.config import settings
        
        # Test development settings
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
    
    def test_database_configuration(self, mock_settings):
        """Test database configuration."""
        from app.core.config import settings
        
        assert settings.DATABASE_URL is not None
        assert "postgresql://" in settings.DATABASE_URL
    
    def test_redis_configuration(self, mock_settings):
        """Test Redis configuration."""
        from app.core.config import settings
        
        assert settings.REDIS_URL is not None
        assert "redis://" in settings.REDIS_URL


class TestSecurity:
    """Test security configurations."""
    
    def test_cors_configuration(self, test_client):
        """Test CORS configuration."""
        # Test allowed origins
        response = test_client.options(
            "/api/v1/powerpoint-exports/capabilities",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
    
    def test_security_headers(self, test_client):
        """Test security headers are set."""
        response = test_client.get("/health")
        
        headers = response.headers
        # Check for common security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options", 
            "x-xss-protection"
        ]
        
        # At least one security header should be present
        found_headers = [h for h in security_headers if h in headers]
        assert len(found_headers) > 0
    
    def test_jwt_configuration(self, mock_settings):
        """Test JWT configuration."""
        from app.core.config import settings
        
        assert settings.JWT_SECRET_KEY is not None
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


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
    
    def test_capabilities_response_time(self, test_client):
        """Test capabilities endpoint response time."""
        import time
        
        start_time = time.time()
        response = test_client.get("/api/v1/powerpoint-exports/capabilities")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 0.5, f"Capabilities check took {response_time:.3f}s"
    
    def test_concurrent_health_checks(self, test_client):
        """Test handling of concurrent health check requests."""
        import concurrent.futures
        
        def make_health_request():
            return test_client.get("/health")
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK


class TestDatabaseConnections:
    """Test database connection handling."""
    
    def test_database_health_check(self, test_client, mock_database):
        """Test database health check."""
        with patch('app.core.database.check_database_connection') as mock_check:
            mock_check.return_value = True
            
            response = test_client.get("/api/v1/health/")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["dependencies"]["database"] is True
    
    def test_redis_health_check(self, test_client, mock_redis):
        """Test Redis health check."""
        with patch('app.core.redis_client.check_redis_connection') as mock_check:
            mock_check.return_value = True
            
            response = test_client.get("/api/v1/health/")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["dependencies"]["redis"] is True
    
    def test_database_connection_failure(self, test_client):
        """Test handling of database connection failures."""
        with patch('app.core.database.check_database_connection') as mock_check:
            mock_check.return_value = False
            
            response = test_client.get("/api/v1/health/ready")
            
            # Should indicate not ready
            assert response.status_code in [status.HTTP_503_SERVICE_UNAVAILABLE, status.HTTP_200_OK]
            # If 200, check ready status is False
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert data.get("ready") is False


class TestLogging:
    """Test logging configuration."""
    
    def test_logging_configuration(self, mock_settings):
        """Test logging is properly configured."""
        import logging
        
        # Check that logger exists
        logger = logging.getLogger("app")
        assert logger is not None
        
        # Log level should be set
        assert logger.level <= logging.DEBUG
    
    def test_request_logging(self, test_client):
        """Test that requests are logged."""
        with patch('app.core.logging.logger') as mock_logger:
            response = test_client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            # Logger should have been called (info, debug, etc.)
            assert mock_logger.info.called or mock_logger.debug.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])