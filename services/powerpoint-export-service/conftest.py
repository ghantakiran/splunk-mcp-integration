#!/usr/bin/env python3
"""
Pytest configuration and fixtures for PowerPoint Export Service tests.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment variables before importing the app
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["PPT_OUTPUT_DIR"] = tempfile.mkdtemp()
os.environ["PPT_TEMPLATE_DIR"] = tempfile.mkdtemp()

from main import app
from app.models.powerpoint_models import (
    PowerPointExportRequest,
    PresentationConfig,
    PresentationMetadata,
    Slide,
    SlideType,
    LayoutType,
    SlideContent,
    DataSource,
    StaticDataSource,
    Theme,
    OutputFormat
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup is handled by tempfile


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create mock authentication headers for testing."""
    # In a real implementation, you would create a valid JWT token
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """Create a mock user for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": ["powerpoint:create", "powerpoint:read"]
    }


@pytest.fixture
def sample_presentation_config() -> PresentationConfig:
    """Create a sample presentation configuration for testing."""
    return PresentationConfig(
        metadata=PresentationMetadata(
            title="Test Presentation",
            author="Test User",
            description="A test presentation"
        ),
        slides=[
            Slide(
                title="Test Slide",
                slide_type=SlideType.TITLE,
                layout=LayoutType.TITLE_SLIDE,
                content=SlideContent()
            )
        ],
        theme=Theme.OFFICE
    )


@pytest.fixture
def sample_data_source() -> DataSource:
    """Create a sample data source for testing."""
    return DataSource(
        source_type="static",
        static_source=StaticDataSource(
            data=[{"key": "value"}]
        )
    )


@pytest.fixture
def sample_export_request(
    sample_presentation_config: PresentationConfig,
    sample_data_source: DataSource
) -> PowerPointExportRequest:
    """Create a sample export request for testing."""
    return PowerPointExportRequest(
        job_name="Test Job",
        presentation_config=sample_presentation_config,
        data_source=sample_data_source,
        output_format=OutputFormat.PPTX
    )


# Mock functions for testing
class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self._data = {}
    
    async def get(self, key):
        return self._data.get(key)
    
    async def set(self, key, value, ex=None):
        self._data[key] = value
        return True
    
    async def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)
        return len(keys)
    
    async def ping(self):
        return True


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self._data = {}
        self._id_counter = 1
    
    async def execute(self, query, *args):
        # Simple mock implementation
        if "INSERT" in query.upper():
            job_id = self._id_counter
            self._id_counter += 1
            return job_id
        elif "SELECT" in query.upper():
            return None
        return None
    
    async def fetch(self, query, *args):
        return []
    
    async def fetchrow(self, query, *args):
        return None
    
    async def fetchval(self, query, *args):
        return self._id_counter


@pytest.fixture
def mock_redis():
    """Mock Redis fixture."""
    return MockRedis()


@pytest.fixture
def mock_database():
    """Mock database fixture."""
    return MockDatabase()
