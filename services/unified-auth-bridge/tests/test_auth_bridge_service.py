"""
Tests for Unified Authentication Bridge Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import aiohttp
import redis.asyncio as redis

from app.services.auth_bridge_service import AuthBridgeService
from app.models.auth import (
    AuthRequest, AuthResponse, AuthMode, ProviderType,
    ValidateTokenRequest, LogoutRequest, RefreshTokenRequest
)
from app.core.config import settings


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = None
    mock_redis.delete.return_value = None
    return mock_redis


@pytest.fixture
def mock_session():
    """Mock aiohttp session"""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "success": True,
        "user_profile": {
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"]
        },
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    return mock_session


@pytest.fixture
async def auth_bridge_service(mock_redis):
    """Create AuthBridgeService instance with mocked dependencies"""
    with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
        service = AuthBridgeService()
        await service.initialize()
        return service


class TestAuthBridgeService:
    """Test cases for AuthBridgeService"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_redis):
        """Test service initialization"""
        with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
            service = AuthBridgeService()
            await service.initialize()
            
            assert service.redis_client is not None
            assert service.session is not None
            assert len(service.providers) > 0
    
    @pytest.mark.asyncio
    async def test_authenticate_cloud_success(self, auth_bridge_service, mock_session):
        """Test successful cloud authentication"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123",
            preferred_provider="cloud"
        )
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is True
            assert response.user_profile.username == "testuser"
            assert response.access_token == "test_token"
            assert response.provider == ProviderType.CLOUD
    
    @pytest.mark.asyncio
    async def test_authenticate_enterprise_success(self, auth_bridge_service, mock_session):
        """Test successful enterprise authentication"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123",
            preferred_provider="enterprise"
        )
        
        # Mock enterprise API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "sessionKey": "enterprise_session_key",
            "user": "testuser"
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is True
            assert response.user_profile.username == "testuser"
            assert response.provider == ProviderType.ENTERPRISE
    
    @pytest.mark.asyncio
    async def test_authenticate_with_fallback(self, auth_bridge_service, mock_session):
        """Test authentication with fallback when primary provider fails"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123",
            preferred_provider="cloud"
        )
        
        # Mock cloud failure and enterprise success
        mock_cloud_response = AsyncMock()
        mock_cloud_response.status = 401
        mock_cloud_response.json.return_value = {"error": "Invalid credentials"}
        
        mock_enterprise_response = AsyncMock()
        mock_enterprise_response.status = 200
        mock_enterprise_response.json.return_value = {
            "sessionKey": "enterprise_session_key",
            "user": "testuser"
        }
        
        mock_session.post.side_effect = [
            mock_cloud_response,  # Cloud fails
            mock_enterprise_response  # Enterprise succeeds
        ]
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is True
            assert response.provider == ProviderType.ENTERPRISE
    
    @pytest.mark.asyncio
    async def test_authenticate_cached_result(self, auth_bridge_service, mock_redis):
        """Test authentication with cached result"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123"
        )
        
        # Mock cached authentication result
        cached_data = {
            "success": True,
            "user_profile": {
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"]
            },
            "access_token": "cached_token",
            "provider": "cloud",
            "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        }
        
        mock_redis.get.return_value = str(cached_data).encode()
        
        with patch('json.loads', return_value=cached_data):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is True
            assert response.access_token == "cached_token"
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_bridge_service, mock_session):
        """Test successful token validation"""
        validate_request = ValidateTokenRequest(
            token="test_token",
            provider="cloud"
        )
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.validate_token(validate_request)
            
            assert response.valid is True
            assert response.user_profile.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, auth_bridge_service, mock_session):
        """Test token validation with invalid token"""
        validate_request = ValidateTokenRequest(
            token="invalid_token",
            provider="cloud"
        )
        
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.json.return_value = {"error": "Invalid token"}
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.validate_token(validate_request)
            
            assert response.valid is False
    
    @pytest.mark.asyncio
    async def test_logout_success(self, auth_bridge_service, mock_session):
        """Test successful logout"""
        logout_request = LogoutRequest(
            token="test_token",
            provider="cloud"
        )
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.logout(logout_request)
            
            assert response.success is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_bridge_service, mock_session):
        """Test successful token refresh"""
        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_token",
            provider="cloud"
        )
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.refresh_token(refresh_request)
            
            assert response.success is True
            assert response.access_token == "test_token"
    
    @pytest.mark.asyncio
    async def test_get_provider_status(self, auth_bridge_service):
        """Test getting provider status"""
        status = await auth_bridge_service.get_provider_status()
        
        assert "mode" in status
        assert "providers" in status
        assert "priority_order" in status
        assert "fallback_enabled" in status
    
    @pytest.mark.asyncio
    async def test_check_health(self, auth_bridge_service, mock_session):
        """Test health check"""
        with patch.object(auth_bridge_service, 'session', mock_session):
            health = await auth_bridge_service.check_health()
            
            assert isinstance(health, dict)
            assert len(health) > 0
    
    @pytest.mark.asyncio
    async def test_get_auth_metrics(self, auth_bridge_service, mock_redis):
        """Test getting authentication metrics"""
        # Mock metrics data
        mock_redis.hgetall.return_value = {
            b"cloud_auth_attempts": b"100",
            b"cloud_auth_successes": b"95",
            b"enterprise_auth_attempts": b"50",
            b"enterprise_auth_successes": b"48"
        }
        
        metrics = await auth_bridge_service.get_auth_metrics()
        
        assert isinstance(metrics, dict)
        assert "total_attempts" in metrics
        assert "success_rate" in metrics
    
    @pytest.mark.asyncio
    async def test_cleanup(self, auth_bridge_service):
        """Test service cleanup"""
        await auth_bridge_service.cleanup()
        # Should not raise any exceptions


class TestAuthBridgeServiceErrorHandling:
    """Test error handling in AuthBridgeService"""
    
    @pytest.mark.asyncio
    async def test_authenticate_network_error(self, auth_bridge_service):
        """Test authentication with network error"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123"
        )
        
        mock_session = AsyncMock()
        mock_session.post.side_effect = aiohttp.ClientError("Network error")
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is False
            assert "error" in response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_authenticate_timeout_error(self, auth_bridge_service):
        """Test authentication with timeout error"""
        auth_request = AuthRequest(
            username="testuser",
            password="password123"
        )
        
        mock_session = AsyncMock()
        mock_session.post.side_effect = aiohttp.ServerTimeoutError("Timeout")
        
        with patch.object(auth_bridge_service, 'session', mock_session):
            response = await auth_bridge_service.authenticate(auth_request)
            
            assert response.success is False
            assert "timeout" in response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, mock_redis):
        """Test handling Redis connection errors"""
        mock_redis.get.side_effect = redis.ConnectionError("Redis connection failed")
        
        with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
            service = AuthBridgeService()
            await service.initialize()
            
            auth_request = AuthRequest(
                username="testuser",
                password="password123"
            )
            
            # Should handle Redis error gracefully and continue without caching
            response = await service.authenticate(auth_request)
            # The test should not fail due to Redis error


class TestAuthBridgeServiceConfiguration:
    """Test different configuration modes"""
    
    @pytest.mark.asyncio
    async def test_cloud_only_mode(self, mock_redis):
        """Test cloud-only authentication mode"""
        with patch('app.core.config.settings.AUTH_BRIDGE_MODE', 'cloud_only'):
            with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
                service = AuthBridgeService()
                await service.initialize()
                
                # Should only have cloud provider
                providers = service.providers
                cloud_providers = [p for p in providers if p["type"] == "cloud"]
                enterprise_providers = [p for p in providers if p["type"] == "enterprise"]
                
                assert len(cloud_providers) > 0
                assert len(enterprise_providers) == 0
    
    @pytest.mark.asyncio
    async def test_enterprise_only_mode(self, mock_redis):
        """Test enterprise-only authentication mode"""
        with patch('app.core.config.settings.AUTH_BRIDGE_MODE', 'enterprise_only'):
            with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
                service = AuthBridgeService()
                await service.initialize()
                
                # Should only have enterprise provider
                providers = service.providers
                cloud_providers = [p for p in providers if p["type"] == "cloud"]
                enterprise_providers = [p for p in providers if p["type"] == "enterprise"]
                
                assert len(cloud_providers) == 0
                assert len(enterprise_providers) > 0
    
    @pytest.mark.asyncio
    async def test_hybrid_mode(self, mock_redis):
        """Test hybrid authentication mode"""
        with patch('app.core.config.settings.AUTH_BRIDGE_MODE', 'hybrid'):
            with patch('app.services.auth_bridge_service.redis.from_url', return_value=mock_redis):
                service = AuthBridgeService()
                await service.initialize()
                
                # Should have both providers
                providers = service.providers
                cloud_providers = [p for p in providers if p["type"] == "cloud"]
                enterprise_providers = [p for p in providers if p["type"] == "enterprise"]
                
                assert len(cloud_providers) > 0
                assert len(enterprise_providers) > 0