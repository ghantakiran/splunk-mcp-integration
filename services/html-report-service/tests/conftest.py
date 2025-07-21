#!/usr/bin/env python3
"""
Test configuration for HTML Report Service.

This module provides pytest fixtures and configuration for testing
the HTML report service components.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock the imports before importing the app modules
with patch.dict('sys.modules', {
    'app.core.database': MagicMock(),
    'app.core.redis_client': MagicMock(),
    'app.utils.auth': MagicMock(),
    'app.utils.rate_limiter': MagicMock(),
}):
    from app.models.html_models import (
        HTMLReportRequest,
        BulkHTMLReportRequest,
        JobResponse,
        JobStatus,
        OutputFormat,
        Template,
        ChartType,
        InteractiveFeature,
        ColorScheme,
        ReportConfig,
        Layout,
        LayoutSection,
        Chart,
        ChartConfig,
        ChartData,
        ChartDataset,
        Table,
        TableConfig,
        TableColumn,
        Metadata,
        CustomBranding,
        StaticDataSource,
        QueryDataSource,
        FileDataSource,
        DataSource
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings configuration."""
    with patch('app.core.config.settings') as mock:
        mock.HTML_TEMPLATE_DIR = "/tmp/templates"
        mock.HTML_OUTPUT_DIR = "/tmp/html-reports"
        mock.HTML_MAX_FILE_SIZE_MB = 50
        mock.MAX_CONCURRENT_JOBS = 10
        mock.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
        mock.CDN_BASE_URL = "https://cdn.example.com"
        mock.USE_CDN = False
        mock.ENABLE_PLOTLY = True
        mock.ENABLE_D3 = True
        mock.ENABLE_CHARTJS = True
        mock.ENABLE_DATATABLES = True
        mock.ENABLE_BOOTSTRAP = True
        yield mock


@pytest.fixture
def mock_auth():
    """Mock authentication utilities."""
    with patch('app.utils.auth.get_current_user_full') as mock:
        mock.return_value = {
            "id": 123,
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"]
        }
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter."""
    with patch('app.utils.rate_limiter.check_rate_limit') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_database():
    """Mock database operations."""
    with patch('app.core.database.get_db_session_dependency') as mock_session, \
         patch('app.core.database.create_job') as mock_create, \
         patch('app.core.database.get_db_session') as mock_get_session, \
         patch('app.core.database.update_job_status') as mock_update_status, \
         patch('app.core.database.update_job_completion') as mock_update_completion:
        
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__.return_value = None
        
        # Mock job creation
        mock_job = MagicMock()
        mock_job.id = 1
        mock_create.return_value = mock_job
        
        # Mock session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_session_instance
        mock_get_session.return_value.__aexit__.return_value = None
        
        yield {
            'session': mock_session,
            'create_job': mock_create,
            'get_session': mock_get_session,
            'update_status': mock_update_status,
            'update_completion': mock_update_completion
        }


@pytest.fixture
def sample_metadata():
    """Sample report metadata."""
    return Metadata(
        title="Test Report",
        description="A test HTML report",
        author="Test User",
        created_date=datetime.utcnow(),
        version="1.0",
        tags=["test", "sample"]
    )


@pytest.fixture
def sample_custom_branding():
    """Sample custom branding configuration."""
    return CustomBranding(
        logo_url="https://example.com/logo.png",
        primary_color="#007bff",
        secondary_color="#6c757d",
        accent_color="#28a745",
        font_family="Arial, sans-serif"
    )


@pytest.fixture
def sample_chart_config():
    """Sample chart configuration."""
    return ChartConfig(
        chart_type=ChartType.BAR,
        title="Sample Chart",
        color_scheme=ColorScheme.BLUE,
        width=800,
        height=400,
        show_legend=True,
        show_grid=True,
        responsive=True,
        interactive_features=[InteractiveFeature.ZOOM, InteractiveFeature.HOVER]
    )


@pytest.fixture
def sample_chart_data():
    """Sample chart data."""
    return ChartData(
        labels=["Q1", "Q2", "Q3", "Q4"],
        datasets=[
            ChartDataset(
                label="Sales",
                data=[100, 150, 120, 200],
                backgroundColor="#007bff"
            ),
            ChartDataset(
                label="Costs",
                data=[80, 90, 85, 110],
                backgroundColor="#dc3545"
            )
        ]
    )


@pytest.fixture
def sample_chart(sample_chart_config, sample_chart_data):
    """Sample chart."""
    return Chart(
        id="chart-1",
        config=sample_chart_config,
        data=sample_chart_data
    )


@pytest.fixture
def sample_table_columns():
    """Sample table columns."""
    return [
        TableColumn(
            name="date",
            label="Date",
            data_type="datetime",
            width=150,
            sortable=True,
            filterable=True
        ),
        TableColumn(
            name="sales",
            label="Sales",
            data_type="number",
            width=100,
            sortable=True,
            filterable=False
        ),
        TableColumn(
            name="region",
            label="Region",
            data_type="string",
            width=120,
            sortable=True,
            filterable=True
        )
    ]


@pytest.fixture
def sample_table_config(sample_table_columns):
    """Sample table configuration."""
    return TableConfig(
        title="Sample Table",
        columns=sample_table_columns,
        pagination=True,
        page_size=10,
        search=True,
        sorting=True,
        responsive=True,
        striped=True,
        export_buttons=["copy", "csv", "excel", "pdf"]
    )


@pytest.fixture
def sample_table_data():
    """Sample table data."""
    return [
        {"date": "2024-01-01", "sales": 1000, "region": "North"},
        {"date": "2024-01-02", "sales": 1200, "region": "South"},
        {"date": "2024-01-03", "sales": 800, "region": "East"},
        {"date": "2024-01-04", "sales": 1500, "region": "West"}
    ]


@pytest.fixture
def sample_table(sample_table_config, sample_table_data):
    """Sample table."""
    return Table(
        id="table-1",
        config=sample_table_config,
        data=sample_table_data
    )


@pytest.fixture
def sample_layout_sections():
    """Sample layout sections."""
    return [
        LayoutSection(
            id="section-1",
            title="Charts",
            content_type="chart",
            content_id="chart-1",
            width=12,
            height=400,
            css_classes=["chart-section"],
            custom_styles={"margin-bottom": "20px"}
        ),
        LayoutSection(
            id="section-2",
            title="Data Table",
            content_type="table",
            content_id="table-1",
            width=12,
            height=300,
            css_classes=["table-section"],
            custom_styles={}
        )
    ]


@pytest.fixture
def sample_layout(sample_layout_sections):
    """Sample layout configuration."""
    return Layout(
        title="Test Report Layout",
        sections=sample_layout_sections,
        grid_system="bootstrap",
        responsive=True
    )


@pytest.fixture
def sample_report_config(
    sample_metadata,
    sample_layout,
    sample_custom_branding
):
    """Sample report configuration."""
    return ReportConfig(
        template=Template.MODERN,
        metadata=sample_metadata,
        layout=sample_layout,
        charts=[],  # Will be populated in tests
        tables=[],  # Will be populated in tests
        enable_print_css=True,
        enable_dark_mode=True,
        custom_branding=sample_custom_branding
    )


@pytest.fixture
def sample_static_data_source():
    """Sample static data source."""
    return StaticDataSource(
        data={
            "charts": [{"name": "Sales", "values": [100, 200, 150]}],
            "tables": [{"columns": ["A", "B"], "rows": [[1, 2], [3, 4]]}]
        }
    )


@pytest.fixture
def sample_query_data_source():
    """Sample query data source."""
    return QueryDataSource(
        query="SELECT * FROM sales WHERE date >= '2024-01-01'",
        parameters={"start_date": "2024-01-01"},
        connection_id="db-conn-1"
    )


@pytest.fixture
def sample_file_data_source():
    """Sample file data source."""
    return FileDataSource(
        file_path="/tmp/sample.csv",
        file_format="csv",
        has_header=True,
        delimiter=",",
        encoding="utf-8"
    )


@pytest.fixture
def sample_data_source(sample_static_data_source):
    """Sample data source wrapper."""
    return DataSource(static_source=sample_static_data_source)


@pytest.fixture
def sample_html_report_request(sample_report_config, sample_data_source):
    """Sample HTML report request."""
    return HTMLReportRequest(
        job_name="Test HTML Report",
        report_config=sample_report_config,
        data_source=sample_data_source,
        output_format=OutputFormat.HTML,
        expires_in_hours=24
    )


@pytest.fixture
def sample_bulk_request(sample_html_report_request):
    """Sample bulk HTML report request."""
    return BulkHTMLReportRequest(
        jobs=[sample_html_report_request, sample_html_report_request],
        output_format=OutputFormat.HTML,
        template=Template.MODERN
    )


@pytest.fixture
def mock_file_operations():
    """Mock file operations."""
    with patch('aiofiles.open', create=True) as mock_open, \
         patch('os.path.exists') as mock_exists, \
         patch('os.path.getsize') as mock_getsize, \
         patch('os.makedirs') as mock_makedirs:
        
        # Mock file writing
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file
        mock_open.return_value.__aexit__.return_value = None
        
        # Mock file existence and size
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        yield {
            'open': mock_open,
            'exists': mock_exists,
            'getsize': mock_getsize,
            'makedirs': mock_makedirs
        }


@pytest.fixture
def mock_jinja_template():
    """Mock Jinja2 template."""
    mock_template = MagicMock()
    mock_template.render.return_value = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Report</title></head>
    <body>
        <h1>Test Report</h1>
        <div id="chart-1"></div>
        <table id="table-1"></table>
    </body>
    </html>
    """
    return mock_template


@pytest.fixture
def mock_jinja_env(mock_jinja_template):
    """Mock Jinja2 environment."""
    with patch('jinja2.Environment') as mock_env_class:
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_jinja_template
        mock_env_class.return_value = mock_env
        yield mock_env


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    # Import the app here to avoid import issues
    with patch.dict('sys.modules', {
        'app.core.database': MagicMock(),
        'app.core.redis_client': MagicMock(),
        'app.utils.auth': MagicMock(),
        'app.utils.rate_limiter': MagicMock(),
    }):
        from main import app
        return TestClient(app)


# Test data helpers
def create_test_job_response(job_id: int = 1, status: JobStatus = JobStatus.PENDING) -> JobResponse:
    """Create a test job response."""
    return JobResponse(
        job_id=job_id,
        status=status,
        message="Test job created",
        created_at=datetime.utcnow()
    )


def create_test_error_data(error_code: str = "TEST_ERROR", message: str = "Test error") -> Dict[str, Any]:
    """Create test error data."""
    return {
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


# Mock data for testing
MOCK_ANALYTICS_DATA = {
    "period_days": 30,
    "total_jobs": 100,
    "successful_jobs": 95,
    "failed_jobs": 5,
    "success_rate": 95.0,
    "avg_generation_time": 3500.0,
    "avg_file_size": 1500000.0,
    "avg_chart_count": 2.0,
    "avg_table_count": 1.5,
    "usage_by_format": {"html": 80, "pdf": 15, "png": 5},
    "usage_by_template": {"modern": 60, "classic": 25, "minimal": 15},
    "daily_usage": [
        {"date": "2024-01-01", "count": 3},
        {"date": "2024-01-02", "count": 5},
        {"date": "2024-01-03", "count": 4}
    ]
}

MOCK_CAPABILITIES_DATA = {
    "supported_formats": ["html", "pdf", "png"],
    "supported_templates": ["modern", "classic", "minimal", "dark", "corporate"],
    "supported_chart_types": ["bar", "column", "line", "pie", "area", "scatter"],
    "supported_interactive_features": ["zoom", "pan", "filter", "hover", "click"],
    "max_file_size_mb": 50,
    "max_concurrent_jobs": 10,
    "features": [
        "Interactive charts",
        "Responsive tables",
        "Custom templates",
        "Export capabilities"
    ]
}