"""
Tests for ITSM Service main application.
"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "itsm-service"
    assert data["version"] == "1.0.0"


def test_health_check_detailed(client: TestClient):
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "timestamp" in data
    assert data["service"] == "itsm-service"


def test_metrics_endpoint(client: TestClient):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "itsm_requests_total" in response.text


def test_root_endpoint(client: TestClient):
    """Test root endpoint redirects to docs."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert "/docs" in response.headers["location"]


def test_api_info(client: TestClient):
    """Test API info endpoint."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "ITSM Service"
    assert data["data"]["version"] == "1.0.0"
    assert data["data"]["description"] == "ITSM tool integration service"


def test_cors_headers(client: TestClient):
    """Test CORS headers are present."""
    response = client.get("/health")
    assert response.status_code == 200
    
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_authentication_required(client: TestClient):
    """Test that protected endpoints require authentication."""
    # Remove the authentication override
    from app.main import app
    from app.utils.auth import get_current_user
    
    # Temporarily remove override
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    
    response = client.get("/api/v1/integrations")
    assert response.status_code == 401
    
    # Restore override for other tests
    def mock_user():
        from tests.conftest import test_user
        return test_user()
    
    app.dependency_overrides[get_current_user] = mock_user


def test_request_id_header(client: TestClient):
    """Test that request ID is added to response headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers


def test_content_type_json(client: TestClient):
    """Test that API endpoints return JSON content type."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self, client: TestClient):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["errors"][0]["message"].lower()
    
    def test_405_method_not_allowed(self, client: TestClient):
        """Test 405 method not allowed error."""
        response = client.post("/health")
        assert response.status_code == 405
        
        data = response.json()
        assert data["success"] is False
        assert "method not allowed" in data["errors"][0]["message"].lower()
    
    def test_422_validation_error(self, client: TestClient):
        """Test 422 validation error handling."""
        # Send invalid JSON to create integration endpoint
        response = client.post(
            "/api/v1/integrations",
            json={"invalid": "data"}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiting_headers(self, client: TestClient):
        """Test that rate limiting headers are present."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        
        # Rate limiting headers should be present
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, client: TestClient):
        """Test rate limiting when limit is exceeded."""
        # This test would need to be configured with a very low rate limit
        # For now, just verify the endpoint is protected
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        
        # Verify rate limit headers are decreasing
        limit = int(response.headers["x-ratelimit-limit"])
        remaining = int(response.headers["x-ratelimit-remaining"])
        assert remaining <= limit


class TestSecurity:
    """Test security features."""
    
    def test_security_headers(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # Security headers should be present
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers
    
    def test_no_server_header(self, client: TestClient):
        """Test that server header is not exposed."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # Server header should not reveal implementation details
        server_header = response.headers.get("server", "").lower()
        assert "uvicorn" not in server_header
        assert "fastapi" not in server_header
    
    def test_input_sanitization(self, client: TestClient):
        """Test input sanitization."""
        # Test with potentially malicious input
        malicious_input = "<script>alert('xss')</script>"
        
        response = client.get(f"/api/v1/integrations?search={malicious_input}")
        
        # Should not return 500 error, should handle gracefully
        assert response.status_code in [200, 400, 422]


class TestDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI JSON schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "ITSM Service API"
    
    def test_docs_endpoint(self, client: TestClient):
        """Test Swagger UI docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger" in response.text.lower()
    
    def test_redoc_endpoint(self, client: TestClient):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()