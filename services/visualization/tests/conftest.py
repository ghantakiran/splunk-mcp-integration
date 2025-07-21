#!/usr/bin/env python3
"""
Comprehensive test configuration for Visualization Service.

This module provides fixtures, mocks, and test utilities for comprehensive
testing of the Visualization Service components including chart generation,
dashboard management, exports, and interactive features.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import tempfile
import os
import base64
from datetime import datetime, timedelta
import json

# Test client imports
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Mock settings for testing
@pytest.fixture
def mock_settings():
    """Mock Visualization Service settings configuration."""
    with patch('app.core.config.settings') as mock:
        mock.DATABASE_URL = "postgresql://test:test@localhost/test_visualization"
        mock.REDIS_URL = "redis://localhost:6379/2"
        mock.JWT_SECRET_KEY = "test-secret-key"
        mock.JWT_ALGORITHM = "HS256"
        mock.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock.API_HOST = "0.0.0.0"
        mock.API_PORT = 8002
        mock.DEBUG = True
        mock.LOG_LEVEL = "DEBUG"
        mock.CHART_CACHE_TTL = 3600
        mock.MAX_CHART_SIZE = 10000
        mock.SUPPORTED_FORMATS = ["png", "pdf", "svg", "html"]
        mock.DEFAULT_THEME = "default"
        mock.MAX_DASHBOARD_PANELS = 20
        mock.EXPORT_TIMEOUT_SECONDS = 300
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
            "permissions": ["viz:read", "viz:write", "viz:create"],
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
def sample_chart_data():
    """Sample chart data for testing."""
    return [
        {"_time": "2024-01-01T10:00:00", "count": 120, "source": "app1"},
        {"_time": "2024-01-01T10:05:00", "count": 150, "source": "app1"},
        {"_time": "2024-01-01T10:10:00", "count": 180, "source": "app1"},
        {"_time": "2024-01-01T10:00:00", "count": 80, "source": "app2"},
        {"_time": "2024-01-01T10:05:00", "count": 95, "source": "app2"},
        {"_time": "2024-01-01T10:10:00", "count": 110, "source": "app2"}
    ]

@pytest.fixture
def sample_chart_configurations():
    """Sample chart configuration data for testing."""
    return [
        {
            "chart_type": "line",
            "title": "Events Over Time",
            "x_field": "_time",
            "y_field": "count",
            "group_by": "source",
            "theme": "default",
            "width": 800,
            "height": 400,
            "interactive": True
        },
        {
            "chart_type": "bar",
            "title": "Event Count by Source",
            "x_field": "source",
            "y_field": "count",
            "aggregation": "sum",
            "color_scheme": "viridis",
            "show_legend": True
        },
        {
            "chart_type": "pie",
            "title": "Source Distribution",
            "value_field": "count",
            "label_field": "source",
            "show_percentages": True,
            "donut": False
        },
        {
            "chart_type": "heatmap",
            "title": "Activity Heatmap",
            "x_field": "_time",
            "y_field": "source",
            "z_field": "count",
            "color_scale": "Blues"
        },
        {
            "chart_type": "scatter",
            "title": "Response Time vs Load",
            "x_field": "load",
            "y_field": "response_time",
            "size_field": "count",
            "color_field": "source"
        }
    ]

@pytest.fixture
def sample_dashboard_configurations():
    """Sample dashboard configuration data for testing."""
    return [
        {
            "title": "System Overview Dashboard",
            "description": "Main system monitoring dashboard",
            "layout": {
                "type": "grid",
                "columns": 2,
                "rows": 2
            },
            "panels": [
                {
                    "id": "panel1",
                    "title": "Error Trends",
                    "chart_config": {
                        "chart_type": "line",
                        "title": "Error Count Over Time",
                        "x_field": "_time",
                        "y_field": "error_count"
                    },
                    "position": {"x": 0, "y": 0, "w": 1, "h": 1}
                },
                {
                    "id": "panel2",
                    "title": "Top Errors",
                    "chart_config": {
                        "chart_type": "bar",
                        "title": "Most Common Errors",
                        "x_field": "error_type",
                        "y_field": "count"
                    },
                    "position": {"x": 1, "y": 0, "w": 1, "h": 1}
                }
            ],
            "refresh_interval": 300,
            "auto_refresh": True
        },
        {
            "title": "Performance Dashboard",
            "description": "Application performance metrics",
            "layout": {
                "type": "flexible",
                "responsive": True
            },
            "panels": [
                {
                    "id": "perf1",
                    "title": "Response Times",
                    "chart_config": {
                        "chart_type": "line",
                        "title": "Average Response Time",
                        "x_field": "_time",
                        "y_field": "avg_response_time"
                    }
                }
            ]
        }
    ]

@pytest.fixture
def sample_export_configurations():
    """Sample export configuration data for testing."""
    return [
        {
            "format": "png",
            "width": 1200,
            "height": 800,
            "dpi": 300,
            "background_color": "white",
            "include_title": True,
            "include_legend": True
        },
        {
            "format": "pdf",
            "page_size": "A4",
            "orientation": "landscape",
            "margins": {"top": 20, "right": 20, "bottom": 20, "left": 20},
            "include_metadata": True
        },
        {
            "format": "svg",
            "width": 800,
            "height": 600,
            "include_css": True,
            "embed_fonts": True
        },
        {
            "format": "html",
            "interactive": True,
            "include_plotly": True,
            "theme": "plotly_dark",
            "responsive": True
        }
    ]

@pytest.fixture
def mock_plotly():
    """Mock Plotly operations."""
    with patch('plotly.graph_objects') as mock_go, \
         patch('plotly.express') as mock_px, \
         patch('plotly.io') as mock_pio:
        
        # Mock Figure
        mock_figure = Mock()
        mock_figure.to_html.return_value = "<div>Mock Chart HTML</div>"
        mock_figure.to_image.return_value = b"mock_image_data"
        mock_figure.to_json.return_value = '{"data": [], "layout": {}}'
        mock_figure.update_layout = Mock(return_value=mock_figure)
        mock_figure.update_traces = Mock(return_value=mock_figure)
        mock_figure.add_trace = Mock(return_value=mock_figure)
        
        # Mock constructors
        mock_go.Figure.return_value = mock_figure
        mock_go.Scatter.return_value = Mock()
        mock_go.Bar.return_value = Mock()
        mock_go.Pie.return_value = Mock()
        mock_go.Heatmap.return_value = Mock()
        
        # Mock Plotly Express
        mock_px.line.return_value = mock_figure
        mock_px.bar.return_value = mock_figure
        mock_px.pie.return_value = mock_figure
        mock_px.scatter.return_value = mock_figure
        mock_px.imshow.return_value = mock_figure
        
        # Mock IO operations
        mock_pio.to_image.return_value = b"mock_image_data"
        mock_pio.to_html.return_value = "<div>Mock Chart HTML</div>"
        
        yield {
            "go": mock_go,
            "px": mock_px,
            "pio": mock_pio,
            "figure": mock_figure
        }

@pytest.fixture
def mock_chart_generator():
    """Mock chart generator service."""
    with patch('app.services.chart_generator.ChartGenerator') as mock:
        mock_gen = Mock()
        mock_gen.generate_chart = AsyncMock(return_value={
            "chart_id": "test-chart-123",
            "chart_html": "<div>Mock Chart</div>",
            "chart_json": '{"data": [], "layout": {}}',
            "metadata": {
                "chart_type": "line",
                "data_points": 100,
                "generation_time_ms": 150
            }
        })
        mock_gen.validate_data = Mock(return_value=True)
        mock_gen.select_chart_type = Mock(return_value="line")
        mock.return_value = mock_gen
        yield mock_gen

@pytest.fixture
def mock_chart_export():
    """Mock chart export service."""
    with patch('app.services.chart_export.ChartExportService') as mock:
        mock_export = Mock()
        mock_export.export_chart = AsyncMock(return_value={
            "export_id": "export-123",
            "file_path": "/tmp/chart.png",
            "file_size": 1024,
            "format": "png",
            "metadata": {
                "width": 800,
                "height": 600,
                "dpi": 150
            }
        })
        mock_export.get_supported_formats.return_value = ["png", "pdf", "svg", "html"]
        mock.return_value = mock_export
        yield mock_export

@pytest.fixture
def mock_dashboard_builder():
    """Mock dashboard builder service."""
    with patch('app.services.dashboard_builder.DashboardBuilder') as mock:
        mock_builder = Mock()
        mock_builder.create_dashboard = AsyncMock(return_value={
            "dashboard_id": "dashboard-123",
            "layout_html": "<div>Mock Dashboard</div>",
            "panels": [
                {"panel_id": "panel1", "chart_id": "chart1"},
                {"panel_id": "panel2", "chart_id": "chart2"}
            ],
            "metadata": {
                "panel_count": 2,
                "creation_time_ms": 500
            }
        })
        mock_builder.validate_layout = Mock(return_value=True)
        mock_builder.optimize_layout = Mock(return_value={"optimized": True})
        mock.return_value = mock_builder
        yield mock_builder

@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_data = {
            "temp_dir": temp_dir,
            "created_files": [],
            "file_contents": {}
        }
        
        def mock_write_file(file_path: str, content: bytes):
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
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
        
        mock_data["write_file"] = mock_write_file
        mock_data["read_file"] = mock_read_file
        yield mock_data

@pytest.fixture
def sample_interactive_features():
    """Sample interactive chart features data."""
    return {
        "zoom": {"enabled": True, "type": "xy"},
        "pan": {"enabled": True, "type": "xy"},
        "hover": {
            "enabled": True,
            "show_closest": True,
            "compare": False
        },
        "click": {
            "enabled": True,
            "mode": "select"
        },
        "brush": {
            "enabled": True,
            "axis": "x"
        },
        "crossfilter": {
            "enabled": False
        },
        "animation": {
            "enabled": True,
            "duration": 500,
            "easing": "cubic-in-out"
        }
    }

@pytest.fixture
def sample_customization_options():
    """Sample chart customization options."""
    return {
        "colors": {
            "primary": "#1f77b4",
            "secondary": "#ff7f0e",
            "background": "#ffffff",
            "grid": "#e0e0e0"
        },
        "fonts": {
            "title": {"family": "Arial", "size": 16, "color": "#333333"},
            "axes": {"family": "Arial", "size": 12, "color": "#666666"},
            "legend": {"family": "Arial", "size": 10, "color": "#999999"}
        },
        "layout": {
            "margin": {"top": 50, "right": 50, "bottom": 50, "left": 50},
            "padding": {"top": 10, "right": 10, "bottom": 10, "left": 10}
        },
        "axes": {
            "x": {
                "show_grid": True,
                "show_line": True,
                "show_ticks": True,
                "title": "Time"
            },
            "y": {
                "show_grid": True,
                "show_line": True,
                "show_ticks": True,
                "title": "Count"
            }
        },
        "legend": {
            "show": True,
            "position": "top-right",
            "orientation": "vertical"
        }
    }

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client(mock_settings, mock_database, mock_redis):
    """FastAPI test client with mocked dependencies."""
    from app.main import app
    
    # Override dependencies with mocks
    with patch('app.core.config.settings', mock_settings):
        client = TestClient(app)
        yield client

@pytest.fixture
async def async_client(mock_settings, mock_database, mock_redis):
    """Async HTTP client for testing."""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Utility functions for tests
def create_mock_response(status_code: int, json_data: Dict[str, Any]) -> Mock:
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    return mock_response

def assert_chart_structure(chart_data: Dict[str, Any]) -> bool:
    """Assert that chart data has valid structure."""
    required_fields = ["chart_id", "chart_html", "metadata"]
    return all(field in chart_data for field in required_fields)

def assert_dashboard_structure(dashboard_data: Dict[str, Any]) -> bool:
    """Assert that dashboard data has valid structure."""
    required_fields = ["dashboard_id", "layout_html", "panels"]
    return all(field in dashboard_data for field in required_fields)

def generate_mock_image_data(format: str = "png") -> bytes:
    """Generate mock image data for testing."""
    if format == "png":
        return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    elif format == "svg":
        return b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>'
    else:
        return b"mock_image_data"

def create_mock_chart_html() -> str:
    """Create mock chart HTML for testing."""
    return """
    <div id="chart-container">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <div id="chart" style="width:800px;height:600px;"></div>
        <script>
            var data = [{"x": [1, 2, 3], "y": [1, 2, 3], "type": "scatter"}];
            var layout = {"title": "Test Chart"};
            Plotly.newPlot("chart", data, layout);
        </script>
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