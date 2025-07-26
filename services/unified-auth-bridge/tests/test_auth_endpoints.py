"""
Tests for authentication endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.endpoints.auth import router as auth_router
from app.models.auth import AuthRequest, ValidateTokenRequest, LogoutRequest, RefreshTokenRequest
from app.services.auth_bridge_service import AuthBridgeService


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1/auth")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth_bridge():
    """Mock AuthBridgeService"""
    return AsyncMock(spec=AuthBridgeService)


@pytest.fixture
def mock_app_state(app, mock_auth_bridge):
    """Mock app state with auth bridge service"""
    app.state.auth_bridge_service = mock_auth_bridge
    return app


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_authenticate_success(self, client, mock_app_state, mock_auth_bridge):
        """Test successful authentication"""
        # Mock successful authentication response
        mock_auth_bridge.authenticate.return_value = AsyncMock(
            success=True,
            user_profile=AsyncMock(
                username="testuser",
                email="test@example.com",
                roles=["user"]
            ),
            access_token="test_token",
            refresh_token="refresh_token",
            expires_in=3600,
            provider="cloud"
        )
        
        response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["access_token"] == "test_token"
    
    def test_authenticate_failure(self, client, mock_app_state, mock_auth_bridge):
        """Test authentication failure"""
        # Mock failed authentication response
        mock_auth_bridge.authenticate.return_value = AsyncMock(
            success=False,
            error_message="Invalid credentials",
            error_code="AUTH_FAILED"
        )
        
        response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is False
        assert "Invalid credentials" in data["data"]["error_message"]
    
    def test_authenticate_invalid_request(self, client, mock_app_state):
        """Test authentication with invalid request data"""
        response = client.post("/api/v1/auth/authenticate", json={
            "username": "",  # Empty username
            "password": "password123"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_validate_token_success(self, client, mock_app_state, mock_auth_bridge):
        """Test successful token validation"""
        # Mock successful validation response
        mock_auth_bridge.validate_token.return_value = AsyncMock(
            valid=True,
            user_profile=AsyncMock(
                username="testuser",
                email="test@example.com",
                roles=["user"]
            ),
            expires_at="2024-01-01T12:00:00Z"
        )
        
        response = client.post("/api/v1/auth/validate", json={
            "token": "test_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True
    
    def test_validate_token_invalid(self, client, mock_app_state, mock_auth_bridge):
        """Test token validation with invalid token"""
        # Mock invalid token response
        mock_auth_bridge.validate_token.return_value = AsyncMock(
            valid=False,
            error_message="Token expired",
            error_code="TOKEN_EXPIRED"
        )
        
        response = client.post("/api/v1/auth/validate", json={
            "token": "invalid_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is False
    
    def test_logout_success(self, client, mock_app_state, mock_auth_bridge):
        """Test successful logout"""
        # Mock successful logout response
        mock_auth_bridge.logout.return_value = AsyncMock(
            success=True,
            message="Logged out successfully"
        )
        
        response = client.post("/api/v1/auth/logout", json={
            "token": "test_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
    
    def test_logout_failure(self, client, mock_app_state, mock_auth_bridge):
        """Test logout failure"""
        # Mock failed logout response
        mock_auth_bridge.logout.return_value = AsyncMock(
            success=False,
            error_message="Token not found",
            error_code="TOKEN_NOT_FOUND"
        )
        
        response = client.post("/api/v1/auth/logout", json={
            "token": "invalid_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is False
    
    def test_refresh_token_success(self, client, mock_app_state, mock_auth_bridge):
        """Test successful token refresh"""
        # Mock successful refresh response
        mock_auth_bridge.refresh_token.return_value = AsyncMock(
            success=True,
            access_token="new_token",
            refresh_token="new_refresh_token",
            expires_in=3600
        )
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "refresh_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["access_token"] == "new_token"
    
    def test_refresh_token_invalid(self, client, mock_app_state, mock_auth_bridge):
        """Test token refresh with invalid refresh token"""
        # Mock invalid refresh token response
        mock_auth_bridge.refresh_token.return_value = AsyncMock(
            success=False,
            error_message="Invalid refresh token",
            error_code="INVALID_REFRESH_TOKEN"
        )
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_refresh_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is False
    
    def test_get_metrics_success(self, client, mock_app_state, mock_auth_bridge):
        """Test getting authentication metrics"""
        # Mock metrics response
        mock_auth_bridge.get_auth_metrics.return_value = {
            "total_attempts": 1000,
            "total_successes": 950,
            "success_rate": 0.95,
            "providers": {
                "cloud": {
                    "attempts": 600,
                    "successes": 580,
                    "success_rate": 0.967
                },
                "enterprise": {
                    "attempts": 400,
                    "successes": 370,
                    "success_rate": 0.925
                }
            }
        }
        
        response = client.get("/api/v1/auth/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_attempts"] == 1000
        assert data["data"]["success_rate"] == 0.95
    
    def test_service_error_handling(self, client, mock_app_state, mock_auth_bridge):
        """Test handling of service errors"""
        # Mock service exception
        mock_auth_bridge.authenticate.side_effect = Exception("Service error")
        
        response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "Authentication service error" in data["detail"]


class TestAuthEndpointsValidation:
    """Test request validation for auth endpoints"""
    
    def test_authenticate_missing_username(self, client, mock_app_state):
        """Test authentication with missing username"""
        response = client.post("/api/v1/auth/authenticate", json={
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_authenticate_missing_password(self, client, mock_app_state):
        """Test authentication with missing password"""
        response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser"
        })
        
        assert response.status_code == 422
    
    def test_validate_token_missing_token(self, client, mock_app_state):
        """Test token validation with missing token"""
        response = client.post("/api/v1/auth/validate", json={})
        
        assert response.status_code == 422
    
    def test_logout_missing_token(self, client, mock_app_state):
        """Test logout with missing token"""
        response = client.post("/api/v1/auth/logout", json={})
        
        assert response.status_code == 422
    
    def test_refresh_token_missing_refresh_token(self, client, mock_app_state):
        """Test token refresh with missing refresh token"""
        response = client.post("/api/v1/auth/refresh", json={})
        
        assert response.status_code == 422
    
    def test_authenticate_invalid_json(self, client, mock_app_state):
        """Test authentication with invalid JSON"""
        response = client.post("/api/v1/auth/authenticate", 
                              data="invalid json",
                              headers={"Content-Type": "application/json"})
        
        assert response.status_code == 422


class TestAuthEndpointsIntegration:
    """Test integration scenarios for auth endpoints"""
    
    def test_authenticate_and_validate_flow(self, client, mock_app_state, mock_auth_bridge):
        """Test complete authentication and validation flow"""
        # Mock authentication
        mock_auth_bridge.authenticate.return_value = AsyncMock(
            success=True,
            access_token="test_token",
            refresh_token="refresh_token",
            expires_in=3600
        )
        
        # Mock validation
        mock_auth_bridge.validate_token.return_value = AsyncMock(
            valid=True,
            user_profile=AsyncMock(username="testuser")
        )
        
        # Authenticate
        auth_response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert auth_response.status_code == 200
        auth_data = auth_response.json()
        token = auth_data["data"]["access_token"]
        
        # Validate token
        validate_response = client.post("/api/v1/auth/validate", json={
            "token": token
        })
        
        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["data"]["valid"] is True
    
    def test_authenticate_refresh_logout_flow(self, client, mock_app_state, mock_auth_bridge):
        """Test complete authentication, refresh, and logout flow"""
        # Mock authentication
        mock_auth_bridge.authenticate.return_value = AsyncMock(
            success=True,
            access_token="test_token",
            refresh_token="refresh_token",
            expires_in=3600
        )
        
        # Mock refresh
        mock_auth_bridge.refresh_token.return_value = AsyncMock(
            success=True,
            access_token="new_token",
            refresh_token="new_refresh_token",
            expires_in=3600
        )
        
        # Mock logout
        mock_auth_bridge.logout.return_value = AsyncMock(
            success=True,
            message="Logged out successfully"
        )
        
        # Authenticate
        auth_response = client.post("/api/v1/auth/authenticate", json={
            "username": "testuser",
            "password": "password123"
        })
        auth_data = auth_response.json()
        refresh_token = auth_data["data"]["refresh_token"]
        
        # Refresh token
        refresh_response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        refresh_data = refresh_response.json()
        new_token = refresh_data["data"]["access_token"]
        
        # Logout
        logout_response = client.post("/api/v1/auth/logout", json={
            "token": new_token
        })
        
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data["data"]["success"] is True