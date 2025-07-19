"""
Test configuration and fixtures for JSON/XML Export Service.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the app directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app.core.config import settings
from app.models.json_xml_models import ExportConfiguration, ExportFormat, JsonFormatting, XmlFormatting
from main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_data() -> list:
    """Sample data for testing exports."""
    return [
        {
            "id": 1,
            "name": "Test Record 1",
            "timestamp": "2025-01-01T10:00:00Z",
            "value": 100,
            "category": "A",
            "metadata": {"source": "test", "processed": True}
        },
        {
            "id": 2,
            "name": "Test Record 2",
            "timestamp": "2025-01-01T11:00:00Z",
            "value": 200,
            "category": "B",
            "metadata": {"source": "test", "processed": False}
        },
        {
            "id": 3,
            "name": "Test Record 3",
            "timestamp": "2025-01-01T12:00:00Z",
            "value": 300,
            "category": "A",
            "metadata": {"source": "production", "processed": True}
        }
    ]


@pytest.fixture
def json_export_config() -> ExportConfiguration:
    """JSON export configuration for testing."""
    return ExportConfiguration(
        format=ExportFormat.JSON,
        encoding="utf-8",
        json_config=JsonFormatting(
            indent=2,
            sort_keys=True,
            ensure_ascii=False
        ),
        include_metadata=True,
        flatten_nested=False
    )


@pytest.fixture
def xml_export_config() -> ExportConfiguration:
    """XML export configuration for testing."""
    return ExportConfiguration(
        format=ExportFormat.XML,
        encoding="utf-8",
        xml_config=XmlFormatting(
            pretty_print=True,
            root_tag="records",
            item_tag="record",
            xml_declaration=True
        ),
        include_metadata=True,
        flatten_nested=False
    )


@pytest.fixture
def jsonl_export_config() -> ExportConfiguration:
    """JSON Lines export configuration for testing."""
    return ExportConfiguration(
        format=ExportFormat.JSONL,
        encoding="utf-8",
        json_config=JsonFormatting(
            sort_keys=True,
            ensure_ascii=False
        ),
        include_metadata=False,
        flatten_nested=False
    )


@pytest.fixture
def mock_user() -> dict:
    """Mock authenticated user for testing."""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": [
            "json_xml_export:create",
            "json_xml_export:read",
            "json_xml_export:delete"
        ]
    }


@pytest.fixture
def auth_headers(mock_user: dict) -> dict:
    """Authentication headers for API requests."""
    # In real tests, you would generate a proper JWT token
    # For now, we'll use a mock token
    return {
        "Authorization": "Bearer mock-jwt-token-for-testing"
    }


@pytest.fixture
def large_sample_data() -> list:
    """Large sample data for performance testing."""
    return [
        {
            "id": i,
            "name": f"Record {i}",
            "timestamp": f"2025-01-01T{i % 24:02d}:00:00Z",
            "value": i * 10,
            "category": chr(65 + (i % 5)),  # A, B, C, D, E
            "data": {
                "nested_field": f"nested_value_{i}",
                "array_field": [i, i+1, i+2],
                "boolean_field": i % 2 == 0
            }
        }
        for i in range(1000)
    ]


@pytest.fixture
def nested_sample_data() -> list:
    """Nested sample data for flattening tests."""
    return [
        {
            "user": {
                "id": 1,
                "profile": {
                    "name": "John Doe",
                    "contact": {
                        "email": "john@example.com",
                        "phone": "123-456-7890"
                    }
                },
                "preferences": {
                    "theme": "dark",
                    "notifications": ["email", "push"]
                }
            },
            "activity": {
                "login_count": 50,
                "last_login": "2025-01-01T10:00:00Z",
                "sessions": [
                    {"id": "session1", "duration": 3600},
                    {"id": "session2", "duration": 1800}
                ]
            }
        }
    ]


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Override settings for testing
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use different DB for tests
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["EXPORT_STORAGE_PATH"] = "/tmp/test-exports"
    
    # Ensure test export directory exists
    os.makedirs("/tmp/test-exports", exist_ok=True)
    
    yield
    
    # Cleanup after tests
    import shutil
    if os.path.exists("/tmp/test-exports"):
        shutil.rmtree("/tmp/test-exports", ignore_errors=True)