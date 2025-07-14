"""
Pytest configuration and shared fixtures for rate limiting tests

Provides common test fixtures, configuration, and utilities
for testing the rate limiting system.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import Base, get_async_session
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Provide a Redis client for testing with a separate test database."""
    client = redis.from_url(
        "redis://localhost:6379/15",  # Use database 15 for tests
        encoding="utf-8",
        decode_responses=True
    )
    
    # Ensure clean state
    await client.flushdb()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
async def redis_client(test_redis_client) -> AsyncGenerator[redis.Redis, None]:
    """Provide a fresh Redis client for each test."""
    # Clear any existing data
    await test_redis_client.flushdb()
    yield test_redis_client
    # Clean up after test
    await test_redis_client.flushdb()


@pytest.fixture(scope="session")
def temp_db_file():
    """Create a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        yield tmp.name
    # Clean up
    try:
        os.unlink(tmp.name)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session")
async def test_db_engine(temp_db_file):
    """Create a test database engine."""
    database_url = f"sqlite+aiosqlite:///{temp_db_file}"
    engine = create_async_engine(database_url, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for testing."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings configuration."""
    return Settings(
        database_url="sqlite+aiosqlite:///test.db",
        redis_url="redis://localhost:6379/15",
        rate_limiting_enabled=True,
        jwt_secret_key="test_secret_key_for_testing_only",
        jwt_expire_minutes=30,
        environment="testing"
    )


@pytest.fixture
def test_app(test_settings) -> FastAPI:
    """Create a test FastAPI application."""
    app = FastAPI(title="Test API", version="1.0.0")
    
    # Override settings
    app.state.settings = test_settings
    
    # Add test endpoints
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}
    
    @app.post("/api/v1/auth/login")
    async def login_endpoint():
        return {"access_token": "test_token", "token_type": "bearer"}
    
    @app.post("/api/v1/queries")
    async def query_endpoint():
        return {"query_id": "test_query", "status": "executing"}
    
    @app.get("/api/v1/export/report")
    async def export_endpoint():
        return {"export_id": "test_export", "status": "pending"}
    
    return app


@pytest.fixture
async def test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_user() -> User:
    """Provide a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test_user_123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.roles = ["user"]
    user.is_active = True
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin_user() -> User:
    """Provide a mock admin user for testing."""
    user = Mock(spec=User)
    user.id = "admin_user_456"
    user.username = "adminuser"
    user.email = "admin@example.com"
    user.roles = ["admin"]
    user.is_active = True
    user.is_admin = True
    return user


@pytest.fixture
def mock_request():
    """Provide a mock FastAPI request object."""
    from fastapi import Request
    
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.url = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.headers = {}
    request.state = Mock()
    request.state.user = None
    request.state.token_data = None
    
    return request


@pytest.fixture
def rate_limit_test_data():
    """Provide test data for rate limiting scenarios."""
    return {
        "policies": [
            {
                "name": "test_policy_1",
                "algorithm": "fixed_window",
                "scope": "per_ip",
                "limit": 10,
                "window_seconds": 60,
                "enabled": True,
                "priority": 1
            },
            {
                "name": "test_policy_2",
                "algorithm": "sliding_window",
                "scope": "per_user",
                "limit": 100,
                "window_seconds": 3600,
                "enabled": True,
                "priority": 2
            },
            {
                "name": "test_policy_3",
                "algorithm": "token_bucket",
                "scope": "global",
                "limit": 1000,
                "window_seconds": 3600,
                "burst_limit": 1500,
                "refill_rate": 0.5,
                "enabled": True,
                "priority": 3
            }
        ],
        "test_scenarios": [
            {
                "name": "normal_load",
                "requests_per_second": 5,
                "duration_seconds": 10,
                "expected_success_rate": 1.0
            },
            {
                "name": "burst_load",
                "requests_per_second": 50,
                "duration_seconds": 2,
                "expected_success_rate": 0.8
            },
            {
                "name": "sustained_load",
                "requests_per_second": 20,
                "duration_seconds": 60,
                "expected_success_rate": 0.9
            }
        ]
    }


@pytest.fixture
def mock_time():
    """Provide a controllable time mock for testing time-based functionality."""
    import time
    from unittest.mock import patch
    
    current_time = 1000000000.0  # Fixed timestamp
    
    def mock_time_func():
        return current_time
    
    def advance_time(seconds):
        nonlocal current_time
        current_time += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        yield advance_time


@pytest.fixture
async def populated_redis(redis_client, rate_limit_test_data):
    """Provide a Redis client with pre-populated test data."""
    # Add some test rate limit data
    for i in range(5):
        key = f"rate_limit:fixed:test_key_{i}:1000000000"
        await redis_client.set(key, str(i + 1))
        await redis_client.expire(key, 60)
    
    # Add sliding window test data
    import time
    now = time.time()
    for i in range(3):
        key = f"rate_limit:sliding:test_sliding_{i}"
        await redis_client.zadd(key, {f"req_{j}": now + j for j in range(i + 1)})
        await redis_client.expire(key, 60)
    
    # Add token bucket test data
    bucket_data = {
        "tokens": 50.0,
        "last_refill": now
    }
    await redis_client.set(
        "rate_limit:bucket:test_bucket",
        json.dumps(bucket_data)
    )
    
    yield redis_client


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.redis = pytest.mark.redis


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add redis marker to tests that use Redis
        if "redis" in item.name.lower() or any(
            "redis" in fixture for fixture in item.fixturenames
        ):
            item.add_marker(pytest.mark.redis)
        
        # Add performance marker to performance tests
        if "performance" in item.name.lower() or "load" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        # Add integration marker to integration tests
        if "integration" in item.name.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # Default to unit test if no other marker
        if not any(mark.name in ["integration", "performance"] for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Async test support
@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


# JSON import for fixtures
import json