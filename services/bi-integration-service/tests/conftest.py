"""
Shared test configuration and fixtures for BI Integration Service.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_database
from app.models.bi_models import BIProvider, IntegrationStatus, DataSourceType, RefreshStatus


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Create test database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    """Create test HTTP client."""
    # Override database dependency
    async def override_get_database():
        return db_session
    
    app.dependency_overrides[get_database] = override_get_database
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.incr.return_value = 1
    mock_redis.hget.return_value = None
    mock_redis.hset.return_value = True
    mock_redis.hgetall.return_value = {}
    return mock_redis


@pytest.fixture
def mock_tableau_server():
    """Mock Tableau Server client."""
    mock_server = MagicMock()
    mock_server.auth = MagicMock()
    mock_server.server_info = MagicMock()
    mock_server.workbooks = MagicMock()
    mock_server.datasources = MagicMock()
    mock_server.projects = MagicMock()
    mock_server.users = MagicMock()
    mock_server.groups = MagicMock()
    mock_server.sites = MagicMock()
    
    # Mock authentication
    mock_server.auth.sign_in.return_value = None
    mock_server.auth.sign_out.return_value = None
    
    return mock_server


@pytest.fixture
def mock_powerbi_client():
    """Mock Power BI client."""
    mock_client = MagicMock()
    mock_client.workspaces = MagicMock()
    mock_client.reports = MagicMock()
    mock_client.datasets = MagicMock()
    mock_client.dashboards = MagicMock()
    mock_client.users = MagicMock()
    mock_client.apps = MagicMock()
    
    return mock_client


@pytest.fixture
def sample_bi_integration():
    """Sample BI integration data."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Tableau Integration",
        "provider": BIProvider.TABLEAU,
        "server_url": "https://tableau.example.com",
        "site_id": "test-site",
        "credentials": {
            "token_name": "test-token",
            "token_value": "test-token-value"
        },
        "status": IntegrationStatus.ACTIVE,
        "configuration": {
            "auto_refresh": True,
            "refresh_interval": 3600,
            "timeout": 300
        },
        "created_by": "test-user@example.com",
        "created_at": "2025-01-18T10:00:00Z",
        "updated_at": "2025-01-18T10:00:00Z"
    }


@pytest.fixture
def sample_bi_workbook():
    """Sample BI workbook data."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "integration_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Workbook",
        "project_name": "Test Project",
        "description": "Test workbook description",
        "url": "https://tableau.example.com/workbooks/test",
        "size": 1024000,
        "created_at": "2025-01-18T10:00:00Z",
        "updated_at": "2025-01-18T10:00:00Z",
        "tags": ["test", "sample"],
        "metadata": {
            "view_count": 10,
            "last_accessed": "2025-01-18T09:00:00Z"
        }
    }


@pytest.fixture
def sample_bi_data_source():
    """Sample BI data source data."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "integration_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Data Source",
        "type": DataSourceType.SPLUNK,
        "connection_info": {
            "host": "splunk.example.com",
            "port": 8089,
            "index": "main"
        },
        "refresh_status": RefreshStatus.COMPLETED,
        "last_refresh": "2025-01-18T09:00:00Z",
        "created_at": "2025-01-18T10:00:00Z",
        "updated_at": "2025-01-18T10:00:00Z"
    }


@pytest.fixture
def auth_headers():
    """Sample authentication headers."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload."""
    return {
        "sub": "test-user@example.com",
        "user_id": "test-user-id",
        "roles": ["bi_admin", "user"],
        "permissions": ["bi:read", "bi:write", "bi:admin"],
        "exp": 1737280800,  # Future timestamp
        "iat": 1737194400,
        "iss": "splunk-mcp-integration"
    }


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    mock_settings = MagicMock()
    mock_settings.environment = "test"
    mock_settings.debug = True
    mock_settings.app_name = "BI Integration Service"
    mock_settings.app_version = "1.0.0"
    mock_settings.api_version = "v1"
    mock_settings.api_prefix = "/api/v1"
    mock_settings.database_url = TEST_DATABASE_URL
    mock_settings.redis_url = "redis://localhost:6379/1"
    mock_settings.cors_origins = ["*"]
    mock_settings.cors_allow_credentials = True
    mock_settings.cors_allow_methods = ["*"]
    mock_settings.cors_allow_headers = ["*"]
    mock_settings.rate_limit_enabled = False
    mock_settings.metrics_enabled = True
    mock_settings.log_level = "INFO"
    return mock_settings


@pytest_asyncio.fixture
async def mock_database_health():
    """Mock database health check."""
    async def _mock_health():
        return {
            "status": "healthy",
            "connection_pool": {
                "size": 10,
                "checked_in": 5,
                "checked_out": 2,
                "overflow": 0
            },
            "response_time_ms": 5.2
        }
    return _mock_health


@pytest_asyncio.fixture
async def mock_redis_health():
    """Mock Redis health check."""
    async def _mock_health():
        return {
            "status": "healthy",
            "connection_pool": {
                "created_connections": 1,
                "available_connections": 1,
                "in_use_connections": 0
            },
            "response_time_ms": 1.5
        }
    return _mock_health


@pytest.fixture
def mock_tableau_auth_response():
    """Mock Tableau authentication response."""
    return {
        "credentials": {
            "site": {
                "id": "test-site-id",
                "contentUrl": "test-site"
            },
            "user": {
                "id": "test-user-id",
                "name": "test-user"
            },
            "token": "test-auth-token"
        }
    }


@pytest.fixture
def mock_powerbi_auth_response():
    """Mock Power BI authentication response."""
    return {
        "access_token": "test-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "https://analysis.windows.net/powerbi/api/.default"
    }


@pytest.fixture
def mock_workbook_list():
    """Mock workbook list response."""
    return [
        {
            "id": "workbook-1",
            "name": "Sales Dashboard",
            "description": "Sales performance dashboard",
            "project": {"id": "project-1", "name": "Sales"},
            "size": 1024000,
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-18T10:00:00Z"
        },
        {
            "id": "workbook-2", 
            "name": "Marketing Analytics",
            "description": "Marketing campaign analytics",
            "project": {"id": "project-2", "name": "Marketing"},
            "size": 2048000,
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-18T10:00:00Z"
        }
    ]


@pytest.fixture
def mock_data_source_list():
    """Mock data source list response."""
    return [
        {
            "id": "datasource-1",
            "name": "Splunk Main Index",
            "type": "splunk",
            "connectionInfo": {
                "serverAddress": "splunk.example.com",
                "port": "8089"
            },
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-18T10:00:00Z"
        },
        {
            "id": "datasource-2",
            "name": "PostgreSQL Analytics",
            "type": "postgresql",
            "connectionInfo": {
                "serverAddress": "postgres.example.com",
                "port": "5432",
                "databaseName": "analytics"
            },
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-18T10:00:00Z"
        }
    ]


# Async context managers for testing
class AsyncContextManager:
    """Helper class for async context manager testing."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Test data helpers
def create_test_integration(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create test integration data with optional overrides."""
    base_data = {
        "name": "Test Integration",
        "provider": "tableau",
        "server_url": "https://tableau.example.com",
        "site_id": "test-site",
        "credentials": {"token_name": "test", "token_value": "test-value"},
        "configuration": {"auto_refresh": True}
    }
    
    if overrides:
        base_data.update(overrides)
    
    return base_data


def create_test_workbook(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create test workbook data with optional overrides."""
    base_data = {
        "name": "Test Workbook",
        "project_name": "Test Project",
        "description": "Test workbook description",
        "tags": ["test"]
    }
    
    if overrides:
        base_data.update(overrides)
    
    return base_data


def create_test_data_source(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create test data source data with optional overrides."""
    base_data = {
        "name": "Test Data Source",
        "type": "splunk",
        "connection_info": {
            "host": "splunk.example.com",
            "port": 8089
        }
    }
    
    if overrides:
        base_data.update(overrides)
    
    return base_data