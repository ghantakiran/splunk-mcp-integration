"""
Test configuration and fixtures for PDF Export Service.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import tempfile
import os
from datetime import datetime

from app.main import app
from app.core.config import settings
from app.core.database import create_db_pool, close_db_pool
from app.core.redis_client import create_redis_pool, close_redis_pool


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Create test database pool."""
    # Use test database settings
    test_db_url = settings.DATABASE_URL.replace("/pdfservice", "/test_pdfservice")
    
    # Create test database pool
    pool = await create_db_pool()
    
    # Run migrations/setup
    await setup_test_database(pool)
    
    yield pool
    
    # Cleanup
    await close_db_pool()


@pytest.fixture(scope="session")
async def redis_pool():
    """Create test Redis pool."""
    pool = await create_redis_pool()
    yield pool
    await close_redis_pool()


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_user():
    """Create mock user for testing."""
    return {
        "id": 1,
        "external_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "user",
        "permissions": {"pdf:create": True, "pdf:read": True},
        "preferences": {},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def mock_template():
    """Create mock template for testing."""
    return {
        "id": 1,
        "name": "Test Template",
        "template_type": "report",
        "description": "Test template for unit tests",
        "template_content": """
        <html>
        <head><title>{{ title }}</title></head>
        <body>
            <h1>{{ title }}</h1>
            <p>{{ content }}</p>
        </body>
        </html>
        """,
        "css_content": "body { font-family: Arial; }",
        "variables": {"title": "Test Report", "content": "Test content"},
        "layout_config": {"page_size": "a4", "orientation": "portrait"},
        "created_by": 1,
        "is_active": True,
        "is_default": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def mock_pdf_job():
    """Create mock PDF job for testing."""
    return {
        "id": 1,
        "user_id": 1,
        "template_id": 1,
        "job_name": "Test PDF Job",
        "status": "pending",
        "parameters": {"title": "Test PDF", "content": "Test content"},
        "data_source": {"type": "test", "data": []},
        "output_format": "pdf",
        "file_path": None,
        "file_size": None,
        "page_count": None,
        "error_message": None,
        "generation_time_ms": None,
        "created_at": datetime.now(),
        "started_at": None,
        "completed_at": None
    }


@pytest.fixture
def mock_pdf_generator():
    """Create mock PDF generator."""
    generator = AsyncMock()
    generator.generate_pdf.return_value = {
        "file_path": "/tmp/test.pdf",
        "file_size": 1024,
        "page_count": 1,
        "filename": "test.pdf"
    }
    generator.get_job_status.return_value = {
        "job_id": 1,
        "status": "completed",
        "runtime_seconds": 5.0
    }
    generator.cancel_job.return_value = True
    return generator


@pytest.fixture
def mock_template_service():
    """Create mock template service."""
    service = AsyncMock()
    service.create_template.return_value = {
        "id": 1,
        "name": "Test Template",
        "template_type": "report",
        "description": "Test template",
        "template_content": "<html><body>{{ content }}</body></html>",
        "css_content": "body { font-family: Arial; }",
        "variables": {},
        "layout_config": {},
        "created_by": 1,
        "is_active": True,
        "is_default": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    service.get_template.return_value = service.create_template.return_value
    service.list_templates.return_value = {
        "templates": [service.create_template.return_value],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1
    }
    service.preview_template.return_value = {
        "template_id": 1,
        "preview_html": "<html><body>Preview content</body></html>",
        "preview_css": "body { font-family: Arial; }",
        "variables": {}
    }
    return service


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = AsyncMock()
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = True
    client.exists.return_value = False
    client.ping.return_value = True
    return client


@pytest.fixture
def mock_database():
    """Create mock database operations."""
    db = AsyncMock()
    db.execute_query.return_value = None
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    return db


@pytest.fixture
def sample_template_content():
    """Sample template content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{{ title }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }
            .content { margin: 30px 0; }
            .footer { text-align: center; border-top: 1px solid #ccc; padding-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ title }}</h1>
            <p>Generated on {{ generation_date }}</p>
        </div>
        <div class="content">
            {{ content }}
            {% if charts %}
            <div class="charts">
                {% for chart in charts %}
                <div class="chart">
                    <h3>{{ chart.title }}</h3>
                    <img src="{{ chart.image }}" alt="{{ chart.title }}">
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        <div class="footer">
            <p>Generated by PDF Export Service</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "title": "Test Report",
        "content": "This is test content for the PDF generation test.",
        "generation_date": "2024-01-01 10:00:00",
        "charts": [
            {
                "title": "Sample Chart",
                "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            }
        ]
    }


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    # Mock JWT token
    mock_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwibmFtZSI6IlRlc3QgVXNlciIsImlhdCI6MTUxNjIzOTAyMn0.test_signature"
    return {"Authorization": f"Bearer {mock_token}"}


@pytest.fixture
def pdf_generation_request():
    """Create PDF generation request for testing."""
    return {
        "template_id": 1,
        "job_name": "Test PDF Generation",
        "output_format": "pdf",
        "parameters": {
            "title": "Test Report",
            "content": "Test content for PDF generation"
        },
        "data_source": {
            "type": "test",
            "data": []
        },
        "layout_config": {
            "page_size": "a4",
            "orientation": "portrait",
            "margin_top": 20,
            "margin_bottom": 20,
            "margin_left": 20,
            "margin_right": 20
        }
    }


@pytest.fixture
def template_create_request():
    """Create template creation request for testing."""
    return {
        "name": "Test Template",
        "template_type": "report",
        "description": "Test template for unit tests",
        "template_content": "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>",
        "css_content": "body { font-family: Arial, sans-serif; }",
        "variables": {"title": "Default Title", "content": "Default Content"},
        "layout_config": {"page_size": "a4", "orientation": "portrait"}
    }


async def setup_test_database(pool):
    """Set up test database with initial data."""
    # Create test user
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO pdf_users (external_id, email, name, role, permissions)
            VALUES ('test_user_123', 'test@example.com', 'Test User', 'user', '{"pdf:create": true, "pdf:read": true}')
            ON CONFLICT (external_id) DO NOTHING
        """)
        
        # Create test template
        await conn.execute("""
            INSERT INTO pdf_templates (name, template_type, description, template_content, 
                                     css_content, variables, layout_config, created_by, is_active)
            VALUES ('Test Template', 'report', 'Test template', 
                   '<html><body><h1>{{ title }}</h1></body></html>',
                   'body { font-family: Arial; }', '{}', '{}', 1, true)
            ON CONFLICT DO NOTHING
        """)


@pytest.fixture
def mock_weasyprint():
    """Mock WeasyPrint HTML class."""
    mock_html = MagicMock()
    mock_html.write_pdf.return_value = b"Mock PDF content"
    return mock_html


@pytest.fixture
def mock_chart_service():
    """Mock chart service responses."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"Mock chart image data"
    return mock_response


# Custom pytest markers
pytest_plugins = ["pytest_asyncio"]