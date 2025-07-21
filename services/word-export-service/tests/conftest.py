#!/usr/bin/env python3
"""
Test configuration for Word Export Service.

This module provides pytest fixtures and configuration for testing
the Word export service components.
"""

import asyncio
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
    from app.models.word_models import (
        WordExportRequest,
        BulkWordExportRequest,
        JobResponse,
        JobStatus,
        OutputFormat,
        Template,
        FontFamily,
        ColorScheme,
        ChartType,
        DocumentConfig,
        DocumentMetadata,
        DocumentLayout,
        DocumentSection,
        Chart,
        ChartConfig,
        ChartData,
        Table,
        TableConfig,
        TableColumn,
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
        mock.WORD_OUTPUT_DIR = "/tmp/word-exports"
        mock.WORD_TEMPLATE_DIR = "/tmp/templates"
        mock.WORD_MAX_FILE_SIZE_MB = 50
        mock.MAX_CONCURRENT_JOBS = 10
        mock.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
        mock.WORD_DEFAULT_FONT = "Calibri"
        mock.WORD_DEFAULT_FONT_SIZE = 11
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
def sample_document_metadata():
    """Sample document metadata."""
    return DocumentMetadata(
        title="Test Document",
        subject="Test Subject",
        author="Test Author",
        company="Test Company",
        keywords=["test", "sample"],
        created_date=datetime.utcnow(),
        version="1.0"
    )


@pytest.fixture
def sample_document_sections():
    """Sample document sections."""
    return [
        DocumentSection(
            id="intro",
            title="Introduction",
            content_type="text",
            text_content="This is the introduction section.",
            order=1
        ),
        DocumentSection(
            id="chart-section",
            title="Chart Analysis",
            content_type="chart",
            chart_id="chart-1",
            order=2
        ),
        DocumentSection(
            id="table-section",
            title="Data Table",
            content_type="table",
            table_id="table-1",
            order=3
        )
    ]


@pytest.fixture
def sample_document_layout(sample_document_sections):
    """Sample document layout."""
    return DocumentLayout(
        sections=sample_document_sections,
        page_size="A4",
        page_orientation="portrait",
        margins={"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
    )


@pytest.fixture
def sample_chart_config():
    """Sample chart configuration."""
    return ChartConfig(
        chart_type=ChartType.BAR,
        title="Sample Chart",
        width=400,
        height=300,
        show_legend=True,
        show_grid=True
    )


@pytest.fixture
def sample_chart_data():
    """Sample chart data."""
    return ChartData(
        labels=["Q1", "Q2", "Q3", "Q4"],
        datasets=[
            {
                "label": "Sales",
                "data": [100, 150, 120, 200],
                "backgroundColor": "#007bff"
            }
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
            width=120
        ),
        TableColumn(
            name="sales",
            label="Sales",
            data_type="number",
            width=100
        ),
        TableColumn(
            name="region",
            label="Region",
            data_type="string",
            width=100
        )
    ]


@pytest.fixture
def sample_table_config(sample_table_columns):
    """Sample table configuration."""
    return TableConfig(
        title="Sample Table",
        columns=sample_table_columns,
        show_header=True,
        stripe_rows=True
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
def sample_document_config(
    sample_document_metadata,
    sample_document_layout
):
    """Sample document configuration."""
    return DocumentConfig(
        metadata=sample_document_metadata,
        template=Template.PROFESSIONAL,
        layout=sample_document_layout,
        font_family=FontFamily.CALIBRI,
        font_size=11,
        color_scheme=ColorScheme.BLUE,
        charts=[],  # Will be populated in tests
        tables=[]   # Will be populated in tests
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
def sample_word_export_request(sample_document_config, sample_data_source):
    """Sample Word export request."""
    return WordExportRequest(
        job_name="Test Word Document",
        document_config=sample_document_config,
        data_source=sample_data_source,
        output_format=OutputFormat.DOCX,
        expires_in_hours=24
    )


@pytest.fixture
def sample_bulk_request(sample_word_export_request):
    """Sample bulk Word export request."""
    return BulkWordExportRequest(
        jobs=[sample_word_export_request, sample_word_export_request],
        output_format=OutputFormat.DOCX,
        template=Template.PROFESSIONAL
    )


@pytest.fixture
def mock_file_operations():
    """Mock file operations."""
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.getsize') as mock_getsize, \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.remove') as mock_remove:
        
        # Mock file existence and size
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        yield {
            'exists': mock_exists,
            'getsize': mock_getsize,
            'makedirs': mock_makedirs,
            'remove': mock_remove
        }


@pytest.fixture
def mock_python_docx():
    """Mock python-docx Document."""
    with patch('docx.Document') as mock_document_class:
        mock_document = MagicMock()
        mock_document_class.return_value = mock_document
        
        # Mock document properties
        mock_document.core_properties = MagicMock()
        mock_document.sections = [MagicMock()]
        
        # Mock paragraph and run methods
        mock_paragraph = MagicMock()
        mock_run = MagicMock()
        mock_paragraph.add_run.return_value = mock_run
        mock_document.add_paragraph.return_value = mock_paragraph
        mock_document.add_heading.return_value = mock_paragraph
        
        # Mock table methods
        mock_table = MagicMock()
        mock_row = MagicMock()
        mock_cell = MagicMock()
        mock_row.cells = [mock_cell, mock_cell, mock_cell]
        mock_table.add_row.return_value = mock_row
        mock_table.rows = [mock_row]
        mock_document.add_table.return_value = mock_table
        
        # Mock save method
        mock_document.save = MagicMock()
        
        yield mock_document


@pytest.fixture
def mock_matplotlib():
    """Mock matplotlib operations."""
    with patch('matplotlib.pyplot.subplots') as mock_subplots, \
         patch('matplotlib.pyplot.close') as mock_close, \
         patch('io.BytesIO') as mock_bytesio:
        
        # Mock figure and axes
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        
        # Mock BytesIO for image buffer
        mock_buffer = MagicMock()
        mock_buffer.read.return_value = b"fake_image_data"
        mock_buffer.seek.return_value = None
        mock_bytesio.return_value = mock_buffer
        
        yield {
            'fig': mock_fig,
            'ax': mock_ax,
            'buffer': mock_buffer,
            'close': mock_close
        }


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
    "avg_page_count": 5.2,
    "avg_chart_count": 1.8,
    "avg_table_count": 1.2,
    "usage_by_format": {"docx": 80, "pdf": 15, "txt": 5},
    "usage_by_template": {"professional": 60, "corporate": 25, "academic": 15},
    "daily_usage": [
        {"date": "2024-01-01", "count": 3},
        {"date": "2024-01-02", "count": 5},
        {"date": "2024-01-03", "count": 4}
    ]
}

MOCK_CAPABILITIES_DATA = {
    "supported_formats": ["docx", "pdf", "txt"],
    "supported_templates": ["professional", "corporate", "academic", "report", "minimal"],
    "supported_chart_types": ["bar", "line", "pie", "area", "scatter", "table"],
    "max_file_size_mb": 50,
    "max_concurrent_jobs": 10,
    "supported_fonts": ["Calibri", "Arial", "Times New Roman", "Helvetica"],
    "features": [
        "Chart embedding",
        "Table formatting",
        "Custom templates",
        "Multiple output formats",
        "Professional styling"
    ]
}