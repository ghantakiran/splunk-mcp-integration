"""
Test configuration and fixtures for Unified Authentication Bridge Service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.models.auth import UserProfile, ProviderType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_user_profile():
    """Mock user profile for testing"""
    return UserProfile(
        username="testuser",
        email="test@example.com",
        display_name="Test User",
        roles=["user"],
        tenant_id="test_tenant",
        groups=["test_group"],
        last_login="2024-01-01T12:00:00Z"
    )


@pytest.fixture
def mock_auth_response_data():
    """Mock authentication response data"""
    return {
        "success": True,
        "user_profile": {
            "username": "testuser",
            "email": "test@example.com",
            "display_name": "Test User",
            "roles": ["user"],
            "tenant_id": "test_tenant",
            "groups": ["test_group"],
            "last_login": "2024-01-01T12:00:00Z"
        },
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "provider": "cloud"
    }


@pytest.fixture
def mock_cloud_auth_response():
    """Mock Splunk Cloud authentication response"""
    return {
        "access_token": "cloud_access_token",
        "refresh_token": "cloud_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "user": {
            "username": "testuser",
            "email": "test@example.com",
            "displayName": "Test User",
            "roles": ["user"],
            "tenantId": "test_tenant"
        }
    }


@pytest.fixture
def mock_enterprise_auth_response():
    """Mock Splunk Enterprise authentication response"""
    return {
        "sessionKey": "enterprise_session_key",
        "user": "testuser"
    }


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    mock_redis = AsyncMock()
    
    # Default return values
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.hget.return_value = None
    mock_redis.hset.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hincrby.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.ping.return_value = True
    
    return mock_redis


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    mock_session = AsyncMock()
    
    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "success": True,
        "data": "test response"
    }
    mock_response.text.return_value = "test response"
    
    # Mock context manager
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.put.return_value.__aenter__.return_value = mock_response
    mock_session.delete.return_value.__aenter__.return_value = mock_response
    
    return mock_session


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return {
        "APP_NAME": "Test Unified Auth Bridge",
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "SECRET_KEY": "test_secret_key",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": 30,
        "JWT_REFRESH_EXPIRE_DAYS": 7,
        "REDIS_URL": "redis://localhost:6379/9",
        "REDIS_DB": 9,
        "REDIS_POOL_SIZE": 10,
        "API_GATEWAY_URL": "http://localhost:8000",
        "CLOUD_AUTH_SERVICE_URL": "http://localhost:8017",
        "CLOUD_CONNECTION_MANAGER_URL": "http://localhost:8018",
        "SPLUNK_ENTERPRISE_HOST": "localhost",
        "SPLUNK_ENTERPRISE_PORT": 8089,
        "SPLUNK_ENTERPRISE_SCHEME": "https",
        "AUTH_BRIDGE_MODE": "hybrid",
        "AUTH_PRIORITY": "cloud,enterprise",
        "AUTH_FALLBACK_ENABLED": True,
        "AUTH_CACHE_TTL": 300,
        "SESSION_TIMEOUT_MINUTES": 60,
        "MAX_SESSIONS_PER_USER": 5,
        "RATE_LIMIT_REQUESTS_PER_MINUTE": 200,
        "HEALTH_CHECK_INTERVAL": 30,
        "HEALTH_CHECK_TIMEOUT": 10
    }


@pytest.fixture
def mock_provider_config():
    """Mock provider configuration"""
    return [
        {
            "type": "cloud",
            "name": "Splunk Cloud",
            "priority": 1,
            "url": "http://localhost:8017",
            "enabled": True
        },
        {
            "type": "enterprise",
            "name": "Splunk Enterprise",
            "priority": 2,
            "url": "https://localhost:8089",
            "enabled": True
        }
    ]


@pytest.fixture
def sample_auth_request():
    """Sample authentication request data"""
    return {
        "username": "testuser",
        "password": "password123",
        "tenant_id": "test_tenant",
        "preferred_provider": "cloud"
    }


@pytest.fixture
def sample_validate_request():
    """Sample token validation request data"""
    return {
        "token": "test_token",
        "provider": "cloud"
    }


@pytest.fixture
def sample_logout_request():
    """Sample logout request data"""
    return {
        "token": "test_token",
        "provider": "cloud",
        "logout_all": False
    }


@pytest.fixture
def sample_refresh_request():
    """Sample token refresh request data"""
    return {
        "refresh_token": "test_refresh_token",
        "provider": "cloud"
    }


@pytest.fixture
def mock_correlation_id():
    """Mock correlation ID for testing"""
    return "test-correlation-id-12345"


@pytest.fixture
def mock_request_state():
    """Mock request state with correlation ID"""
    mock_state = Mock()
    mock_state.correlation_id = "test-correlation-id-12345"
    return mock_state


@pytest.fixture
def mock_fastapi_request(mock_request_state):
    """Mock FastAPI request object"""
    mock_request = Mock()
    mock_request.state = mock_request_state
    return mock_request


class MockHealthCheck:
    """Mock health check utility"""
    
    @staticmethod
    def create_healthy_response():
        """Create a healthy service response"""
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T12:00:00Z",
            "response_time": 0.1,
            "details": {}
        }
    
    @staticmethod
    def create_unhealthy_response(error="Service unavailable"):
        """Create an unhealthy service response"""
        return {
            "status": "unhealthy",
            "timestamp": "2024-01-01T12:00:00Z",
            "response_time": 5.0,
            "error": error
        }


@pytest.fixture
def mock_health_check():
    """Mock health check utility"""
    return MockHealthCheck()


class MockMetrics:
    """Mock metrics utility"""
    
    @staticmethod
    def create_sample_metrics():
        """Create sample authentication metrics"""
        return {
            "total_attempts": 1000,
            "total_successes": 950,
            "success_rate": 0.95,
            "cache_hits": 500,
            "cache_misses": 500,
            "cache_hit_rate": 0.5,
            "providers": {
                "cloud": {
                    "attempts": 600,
                    "successes": 580,
                    "success_rate": 0.967,
                    "avg_response_time": 0.2
                },
                "enterprise": {
                    "attempts": 400,
                    "successes": 370,
                    "success_rate": 0.925,
                    "avg_response_time": 0.5
                }
            },
            "last_updated": "2024-01-01T12:00:00Z"
        }


@pytest.fixture
def mock_metrics():
    """Mock metrics utility"""
    return MockMetrics()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers"""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ["integration", "unit"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Async test utilities
@pytest.fixture
async def async_test_client():
    """Create async test client"""
    from httpx import AsyncClient
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client