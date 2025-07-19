#!/usr/bin/env python3
"""
Pytest configuration and fixtures for CSV Export Service tests.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import app
from app.core.config import settings
from app.utils.auth import create_user_token


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_user():
    """Mock user data."""
    return {
        "user_id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "role": "user",
        "is_active": True
    }


@pytest.fixture
def admin_user():
    """Mock admin user data."""
    return {
        "user_id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture
def auth_token(mock_user):
    """Create authentication token for mock user."""
    return create_user_token(
        user_id=mock_user["user_id"],
        username=mock_user["username"],
        role=mock_user["role"]
    )


@pytest.fixture
def admin_token(admin_user):
    """Create authentication token for admin user."""
    return create_user_token(
        user_id=admin_user["user_id"],
        username=admin_user["username"],
        role=admin_user["role"]
    )


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Create admin authorization headers."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def sample_csv_export_request():
    """Sample CSV export request data."""
    return {
        "job_name": "Test Export",
        "data_source": {
            "source_type": "static",
            "static_source": {
                "data": [
                    {"id": 1, "name": "Alice", "value": 100.5},
                    {"id": 2, "name": "Bob", "value": 200.0},
                    {"id": 3, "name": "Charlie", "value": 150.75}
                ]
            }
        },
        "export_config": {
            "export_format": "csv",
            "formatting": {
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "line_terminator": "\n"
            },
            "header_config": {
                "include_header": True,
                "header_case": "original"
            },
            "data_processing": {
                "null_handling": "empty_string",
                "trim_whitespace": True,
                "remove_empty_rows": False,
                "remove_duplicate_rows": False
            },
            "compression": {
                "compression_type": "none"
            }
        },
        "expires_in_hours": 24,
        "priority": 5
    }


@pytest.fixture
def sample_template_request():
    """Sample template request data."""
    return {
        "name": "Test Template",
        "description": "Template for testing",
        "export_config": {
            "export_format": "csv",
            "formatting": {
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"'
            },
            "header_config": {
                "include_header": True
            },
            "data_processing": {
                "null_handling": "empty_string",
                "trim_whitespace": True
            },
            "compression": {
                "compression_type": "none"
            }
        },
        "is_default": False
    }


@pytest.fixture
def mock_database():
    """Mock database functions."""
    with pytest.mock.patch("app.core.database.get_user_by_id") as mock_get_user, \
         pytest.mock.patch("app.core.database.create_export_job") as mock_create_job, \
         pytest.mock.patch("app.core.database.get_job_by_id") as mock_get_job, \
         pytest.mock.patch("app.core.database.get_user_jobs") as mock_get_jobs, \
         pytest.mock.patch("app.core.database.create_template") as mock_create_template, \
         pytest.mock.patch("app.core.database.get_user_templates") as mock_get_templates, \
         pytest.mock.patch("app.core.database.log_analytics_event") as mock_log_event:
        
        # Configure mocks
        mock_get_user.return_value = AsyncMock(return_value={
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "is_active": True
        })
        
        mock_create_job.return_value = AsyncMock(return_value=123)
        
        mock_get_job.return_value = AsyncMock(return_value={
            "job_id": 123,
            "user_id": 1,
            "job_name": "Test Export",
            "status": "completed",
            "file_path": "/tmp/test.csv",
            "file_size": 1024,
            "row_count": 10,
            "column_count": 3,
            "created_at": "2024-01-01T00:00:00",
            "export_config": {"export_format": "csv"}
        })
        
        mock_get_jobs.return_value = AsyncMock(return_value=[])
        mock_create_template.return_value = AsyncMock(return_value=456)
        mock_get_templates.return_value = AsyncMock(return_value=[])
        mock_log_event.return_value = AsyncMock()
        
        yield {
            "get_user_by_id": mock_get_user,
            "create_export_job": mock_create_job,
            "get_job_by_id": mock_get_job,
            "get_user_jobs": mock_get_jobs,
            "create_template": mock_create_template,
            "get_user_templates": mock_get_templates,
            "log_analytics_event": mock_log_event
        }


@pytest.fixture
def mock_redis():
    """Mock Redis functions."""
    with pytest.mock.patch("app.core.redis_client.get_cache_manager") as mock_cache, \
         pytest.mock.patch("app.core.redis_client.get_queue_manager") as mock_queue:
        
        # Mock cache manager
        cache_manager = MagicMock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock(return_value=True)
        cache_manager.delete = AsyncMock(return_value=True)
        cache_manager.exists = AsyncMock(return_value=False)
        mock_cache.return_value = cache_manager
        
        # Mock queue manager
        queue_manager = MagicMock()
        queue_manager.enqueue = AsyncMock(return_value=True)
        queue_manager.dequeue = AsyncMock(return_value=None)
        queue_manager.mark_completed = AsyncMock(return_value=True)
        queue_manager.get_queue_size = AsyncMock(return_value={"pending": 0, "processing": 0, "total": 0})
        mock_queue.return_value = queue_manager
        
        yield {
            "cache_manager": cache_manager,
            "queue_manager": queue_manager
        }


@pytest.fixture
def mock_csv_generator():
    """Mock CSV generator."""
    with pytest.mock.patch("app.services.csv_generator.csv_generator") as mock_gen:
        mock_gen.generate_csv = AsyncMock(return_value=(True, "/tmp/test.csv", None))
        mock_gen.validate_data = AsyncMock(return_value={
            "is_valid": True,
            "row_count": 10,
            "column_count": 3,
            "issues": [],
            "warnings": [],
            "estimated_file_size_mb": 0.5
        })
        yield mock_gen


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("CSV_OUTPUT_DIR", "/tmp/csv-test-exports")


# Test utilities
def assert_response_success(response, expected_status=200):
    """Assert that response is successful."""
    assert response.status_code == expected_status
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if "success" in data:
            assert data["success"] is True


def assert_response_error(response, expected_status=400):
    """Assert that response is an error."""
    assert response.status_code == expected_status
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        assert "detail" in data or "error" in data