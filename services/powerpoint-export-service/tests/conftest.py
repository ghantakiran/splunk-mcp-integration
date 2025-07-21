#!/usr/bin/env python3
"""
Comprehensive test configuration for PowerPoint Export Service.

This module provides fixtures, mocks, and test utilities for comprehensive
testing of the PowerPoint Export Service components including presentation
generation, template management, and export functionality.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import tempfile
import os
import io
from datetime import datetime, timedelta
import json

# Test client imports
from fastapi.testclient import TestClient
from httpx import AsyncClient


# Mock settings for testing
@pytest.fixture
def mock_settings():
    """Mock PowerPoint Export Service settings configuration."""
    with patch('app.core.config.settings') as mock:
        mock.DATABASE_URL = "postgresql://test:test@localhost/test_powerpoint_export"
        mock.REDIS_URL = "redis://localhost:6379/3"
        mock.JWT_SECRET_KEY = "test-secret-key"
        mock.JWT_ALGORITHM = "HS256"
        mock.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock.API_HOST = "0.0.0.0"
        mock.API_PORT = 8011
        mock.DEBUG = True
        mock.LOG_LEVEL = "DEBUG"
        mock.PPT_MAX_SLIDES = 100
        mock.PPT_MAX_FILE_SIZE_MB = 50
        mock.DEFAULT_THEME = "office"
        mock.DEFAULT_ANIMATION = "fade"
        mock.DEFAULT_TRANSITION = "fade"
        mock.AVAILABLE_THEMES = ["office", "modern", "colorful", "dark", "minimal"]
        mock.AVAILABLE_ANIMATIONS = ["none", "fade", "slide", "zoom", "flip"]
        mock.AVAILABLE_TRANSITIONS = ["none", "fade", "slide", "push", "cover", "uncover"]
        mock.CHART_TYPES = ["bar", "column", "line", "pie", "area", "scatter", "doughnut", "radar"]
        mock.CONCURRENT_JOBS = 10
        mock.JOB_TIMEOUT_SECONDS = 600
        mock.FILE_RETENTION_HOURS = 168  # 7 days
        yield mock


@pytest.fixture
def mock_database():
    """Mock database operations."""
    with patch('app.core.database.get_db_session') as mock:
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = None
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_session


@pytest.fixture
def mock_redis():
    """Mock Redis operations."""
    with patch('app.core.redis_client.get_redis_client') as mock:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.set = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.exists.return_value = False
        mock_client.expire = AsyncMock()
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.close = AsyncMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_auth():
    """Mock authentication utilities."""
    with patch('app.utils.auth.get_current_user') as mock:
        mock_user = {
            "user_id": "test-user-123",
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["user"],
            "permissions": ["ppt:read", "ppt:write", "ppt:create", "ppt:delete"],
            "is_active": True
        }
        mock.return_value = mock_user
        yield mock_user


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_presentation_data():
    """Sample presentation data for testing."""
    return {
        "title": "Quarterly Business Review",
        "subtitle": "Q4 2024 Performance Analysis",
        "author": "Analytics Team",
        "company": "Acme Corporation",
        "slides": [
            {
                "title": "Executive Summary",
                "content": [
                    "Revenue increased by 15% YoY",
                    "Customer satisfaction at all-time high",
                    "Successful product launches in Q4"
                ],
                "layout": "title_and_content"
            },
            {
                "title": "Revenue Trends",
                "content": [],
                "layout": "title_only",
                "chart": {
                    "type": "line",
                    "data": [
                        {"month": "Oct", "revenue": 1200000},
                        {"month": "Nov", "revenue": 1350000},
                        {"month": "Dec", "revenue": 1450000}
                    ],
                    "title": "Monthly Revenue Growth"
                }
            },
            {
                "title": "Key Performance Indicators",
                "content": [],
                "layout": "comparison",
                "charts": [
                    {
                        "type": "bar",
                        "data": [
                            {"category": "Sales", "value": 95},
                            {"category": "Marketing", "value": 87},
                            {"category": "Support", "value": 92}
                        ],
                        "title": "Department Performance"
                    },
                    {
                        "type": "pie",
                        "data": [
                            {"label": "Product A", "value": 45},
                            {"label": "Product B", "value": 35},
                            {"label": "Product C", "value": 20}
                        ],
                        "title": "Revenue by Product"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_presentation_configurations():
    """Sample presentation configuration data for testing."""
    return [
        {
            "theme": "office",
            "animation": "fade",
            "transition": "slide",
            "output_format": "pptx",
            "include_charts": True,
            "chart_style": "modern",
            "font_family": "Calibri",
            "font_size": 18,
            "color_scheme": "blue"
        },
        {
            "theme": "modern",
            "animation": "zoom",
            "transition": "push",
            "output_format": "pdf",
            "include_charts": True,
            "chart_style": "minimal",
            "font_family": "Arial",
            "font_size": 16,
            "color_scheme": "green"
        },
        {
            "theme": "dark",
            "animation": "flip",
            "transition": "cover",
            "output_format": "png",
            "include_charts": False,
            "chart_style": "dark",
            "font_family": "Helvetica",
            "font_size": 20,
            "color_scheme": "purple"
        }
    ]


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return [
        {
            "name": "Business Report Template",
            "description": "Professional business presentation template",
            "theme": "office",
            "slides": [
                {
                    "layout": "title_slide",
                    "elements": [
                        {"type": "title", "placeholder": "{{title}}"},
                        {"type": "subtitle", "placeholder": "{{subtitle}}"},
                        {"type": "author", "placeholder": "{{author}}"}
                    ]
                },
                {
                    "layout": "section_header",
                    "elements": [
                        {"type": "title", "placeholder": "{{section_title}}"}
                    ]
                },
                {
                    "layout": "title_and_content",
                    "elements": [
                        {"type": "title", "placeholder": "{{slide_title}}"},
                        {"type": "content", "placeholder": "{{content}}"}
                    ]
                }
            ],
            "variables": ["title", "subtitle", "author", "section_title", "slide_title", "content"],
            "is_active": True
        },
        {
            "name": "Analytics Dashboard Template",
            "description": "Data visualization presentation template",
            "theme": "modern",
            "slides": [
                {
                    "layout": "title_slide",
                    "elements": [
                        {"type": "title", "placeholder": "{{dashboard_title}}"},
                        {"type": "subtitle", "placeholder": "Data Analysis Report"}
                    ]
                },
                {
                    "layout": "chart_slide",
                    "elements": [
                        {"type": "title", "placeholder": "{{chart_title}}"},
                        {"type": "chart", "placeholder": "{{chart_data}}"}
                    ]
                }
            ],
            "variables": ["dashboard_title", "chart_title", "chart_data"],
            "is_active": True
        }
    ]


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return [
        {
            "job_id": "job-123",
            "user_id": "test-user-123",
            "status": "completed",
            "created_at": datetime.now() - timedelta(hours=2),
            "updated_at": datetime.now() - timedelta(minutes=30),
            "file_path": "/tmp/presentations/job-123.pptx",
            "file_size": 2048576,  # 2MB
            "metadata": {
                "slides_count": 15,
                "charts_count": 8,
                "processing_time_ms": 45000,
                "theme": "office",
                "output_format": "pptx"
            }
        },
        {
            "job_id": "job-456",
            "user_id": "test-user-123",
            "status": "processing",
            "created_at": datetime.now() - timedelta(minutes=10),
            "updated_at": datetime.now() - timedelta(minutes=2),
            "file_path": None,
            "file_size": None,
            "metadata": {
                "slides_count": 25,
                "charts_count": 12,
                "theme": "modern",
                "output_format": "pdf"
            }
        },
        {
            "job_id": "job-789",
            "user_id": "test-user-456",
            "status": "failed",
            "created_at": datetime.now() - timedelta(hours=1),
            "updated_at": datetime.now() - timedelta(minutes=45),
            "file_path": None,
            "file_size": None,
            "metadata": {
                "error": "Invalid chart data format",
                "theme": "dark",
                "output_format": "pptx"
            }
        }
    ]


@pytest.fixture
def mock_python_pptx():
    """Mock python-pptx operations."""
    with patch('pptx.Presentation') as mock_presentation_class:
        # Create mock presentation instance
        mock_presentation = Mock()
        
        # Mock slides
        mock_slide = Mock()
        mock_slide.shapes = Mock()
        mock_slide.slide_layout = Mock()
        
        # Mock shapes
        mock_shape = Mock()
        mock_shape.text_frame = Mock()
        mock_shape.text_frame.text = ""
        mock_shape.width = 100
        mock_shape.height = 100
        
        # Mock slide layouts
        mock_slide_layout = Mock()
        mock_slide_layout.placeholders = [mock_shape]
        
        # Mock slide master and layouts
        mock_slide_master = Mock()
        mock_slide_master.slide_layouts = [mock_slide_layout]
        
        # Configure presentation mock
        mock_presentation.slides = Mock()
        mock_presentation.slides.add_slide.return_value = mock_slide
        mock_presentation.slide_master = mock_slide_master
        mock_presentation.save = Mock()
        
        # Configure presentation class mock
        mock_presentation_class.return_value = mock_presentation
        
        yield {
            "presentation_class": mock_presentation_class,
            "presentation": mock_presentation,
            "slide": mock_slide,
            "shape": mock_shape,
            "slide_layout": mock_slide_layout
        }


@pytest.fixture
def mock_matplotlib():
    """Mock matplotlib for chart generation."""
    with patch('matplotlib.pyplot') as mock_plt, \
         patch('matplotlib.figure.Figure') as mock_figure_class:
        
        # Mock figure and axis
        mock_fig = Mock()
        mock_ax = Mock()
        
        # Configure pyplot methods
        mock_plt.figure.return_value = mock_fig
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig = Mock()
        mock_plt.close = Mock()
        
        # Configure figure methods
        mock_fig.add_subplot.return_value = mock_ax
        mock_fig.savefig = Mock()
        
        # Configure axis methods
        mock_ax.bar = Mock()
        mock_ax.plot = Mock()
        mock_ax.pie = Mock()
        mock_ax.scatter = Mock()
        mock_ax.set_title = Mock()
        mock_ax.set_xlabel = Mock()
        mock_ax.set_ylabel = Mock()
        mock_ax.legend = Mock()
        
        yield {
            "plt": mock_plt,
            "fig": mock_fig,
            "ax": mock_ax
        }


@pytest.fixture
def mock_powerpoint_generator():
    """Mock PowerPoint generator service."""
    with patch('app.services.powerpoint_generator.PowerPointGenerator') as mock:
        mock_gen = Mock()
        mock_gen.generate_presentation = AsyncMock(return_value={
            "job_id": "test-job-123",
            "status": "completed",
            "file_path": "/tmp/test_presentation.pptx",
            "file_size": 2048576,
            "metadata": {
                "slides_count": 10,
                "charts_count": 5,
                "processing_time_ms": 30000,
                "theme": "office",
                "output_format": "pptx"
            }
        })
        mock_gen.create_from_template = AsyncMock(return_value={
            "job_id": "template-job-123",
            "template_id": "template-456",
            "status": "completed",
            "file_path": "/tmp/template_presentation.pptx"
        })
        mock_gen.validate_presentation_data = Mock(return_value={"is_valid": True, "errors": []})
        mock_gen.get_supported_themes = Mock(return_value=["office", "modern", "colorful", "dark", "minimal"])
        mock_gen.get_supported_formats = Mock(return_value=["pptx", "pdf", "png", "jpg"])
        mock.return_value = mock_gen
        yield mock_gen


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_data = {
            "temp_dir": temp_dir,
            "created_files": [],
            "file_contents": {}
        }
        
        def mock_create_pptx_file(file_path: str, content: bytes = None):
            """Create a mock PPTX file."""
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Create a simple mock PPTX file (ZIP format)
            if content is None:
                content = b"PK\x03\x04mock_pptx_content"
            
            with open(full_path, 'wb') as f:
                f.write(content)
            
            mock_data["created_files"].append(file_path)
            mock_data["file_contents"][file_path] = content
            return full_path
        
        def mock_read_file(file_path: str):
            full_path = os.path.join(temp_dir, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    return f.read()
            return None
        
        def mock_get_file_size(file_path: str):
            full_path = os.path.join(temp_dir, file_path)
            if os.path.exists(full_path):
                return os.path.getsize(full_path)
            return 0
        
        mock_data["create_pptx_file"] = mock_create_pptx_file
        mock_data["read_file"] = mock_read_file
        mock_data["get_file_size"] = mock_get_file_size
        yield mock_data


@pytest.fixture
def sample_chart_data():
    """Sample chart data for testing."""
    return [
        {
            "type": "bar",
            "data": [
                {"category": "Q1", "value": 100},
                {"category": "Q2", "value": 150},
                {"category": "Q3", "value": 120},
                {"category": "Q4", "value": 180}
            ],
            "title": "Quarterly Revenue",
            "x_label": "Quarter",
            "y_label": "Revenue (K)",
            "color_scheme": "blue"
        },
        {
            "type": "line",
            "data": [
                {"x": "Jan", "y": 85},
                {"x": "Feb", "y": 90},
                {"x": "Mar", "y": 88},
                {"x": "Apr", "y": 95},
                {"x": "May", "y": 92}
            ],
            "title": "Monthly Performance",
            "x_label": "Month",
            "y_label": "Score",
            "color_scheme": "green"
        },
        {
            "type": "pie",
            "data": [
                {"label": "Product A", "value": 45},
                {"label": "Product B", "value": 30},
                {"label": "Product C", "value": 15},
                {"label": "Others", "value": 10}
            ],
            "title": "Market Share Distribution",
            "show_percentages": True,
            "color_scheme": "rainbow"
        }
    ]


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client(mock_settings, mock_database, mock_redis):
    """FastAPI test client with mocked dependencies."""
    from main import app
    
    # Override dependencies with mocks
    with patch('app.core.config.settings', mock_settings):
        client = TestClient(app)
        yield client


@pytest.fixture
async def async_client(mock_settings, mock_database, mock_redis):
    """Async HTTP client for testing."""
    from main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Utility functions for tests
def create_mock_response(status_code: int, json_data: Dict[str, Any]) -> Mock:
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    return mock_response


def assert_job_structure(job_data: Dict[str, Any]) -> bool:
    """Assert that job data has valid structure."""
    required_fields = ["job_id", "status", "created_at"]
    return all(field in job_data for field in required_fields)


def assert_template_structure(template_data: Dict[str, Any]) -> bool:
    """Assert that template data has valid structure."""
    required_fields = ["template_id", "name", "theme", "slides"]
    return all(field in template_data for field in required_fields)


def assert_presentation_structure(presentation_data: Dict[str, Any]) -> bool:
    """Assert that presentation data has valid structure."""
    required_fields = ["title", "slides"]
    return all(field in presentation_data for field in required_fields)


def generate_mock_pptx_data() -> bytes:
    """Generate mock PPTX file data for testing."""
    # PPTX files are ZIP archives, so create a minimal ZIP-like structure
    return b"PK\x03\x04\x14\x00\x00\x00\x08\x00mock_pptx_content_for_testing"


def create_mock_presentation_html() -> str:
    """Create mock presentation HTML for testing."""
    return """
    <div class="presentation-preview">
        <div class="slide" data-slide="1">
            <h1>Test Presentation</h1>
            <p>This is a mock presentation slide for testing.</p>
        </div>
        <div class="slide" data-slide="2">
            <h2>Chart Slide</h2>
            <div class="chart-container">
                <canvas id="chart-1"></canvas>
            </div>
        </div>
    </div>
    """


# Test configuration
pytest_plugins = []

# Configure async testing
@pytest.fixture(autouse=True)
def configure_async_testing():
    """Configure async testing environment."""
    # Set async test timeout
    import asyncio
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())