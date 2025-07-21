#!/usr/bin/env python3
"""
Comprehensive main application tests for Visualization Service.

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
            assert app.title == "Visualization Service"
    
    def test_application_routes_registration(self):
        """Test that all routes are properly registered."""
        from app.main import app
        
        # Get all registered routes
        routes = [route.path for route in app.routes]
        
        expected_routes = [
            "/health",
            "/ready",
            "/api/v1/charts/generate",
            "/api/v1/charts/export/formats",
            "/api/v1/dashboards",
            "/api/v1/charts/{chart_id}/export",
            "/api/v1/charts/{chart_id}/customize"
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
            "/api/v1/charts/generate",
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


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check_success(self, test_client):
        """Test successful health check."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_readiness_probe(self, test_client):
        """Test Kubernetes readiness probe."""
        response = test_client.get("/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["ready"] is True


class TestExceptionHandling:
    """Test global exception handling."""
    
    def test_validation_error_handling(self, test_client, auth_headers):
        """Test handling of validation errors."""
        # Send invalid request data
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json={"invalid": "data"}  # Missing required fields
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_authentication_error_handling(self, test_client):
        """Test handling of authentication errors."""
        response = test_client.post(
            "/api/v1/charts/generate",
            json={"chart_type": "line", "data": []}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
        assert data["info"]["title"] == "Visualization Service"


class TestConfiguration:
    """Test application configuration."""
    
    def test_settings_loading(self, mock_settings):
        """Test settings are properly loaded."""
        from app.core.config import settings
        
        assert settings.API_HOST == "0.0.0.0"
        assert settings.API_PORT == 8002


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])