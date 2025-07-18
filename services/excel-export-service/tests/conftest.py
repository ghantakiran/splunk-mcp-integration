"""
Test configuration and fixtures.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.excel_models import (
    ExcelExportRequest, WorkbookConfig, WorksheetConfig, 
    CellData, CellStyle, ChartConfig, DataValidationRule,
    ExcelFormat, Theme, ChartType, CellDataType
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def auth_headers() -> dict:
    """Create authentication headers."""
    return {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_cell_data() -> list:
    """Create sample cell data."""
    return [
        [
            CellData(value="Product A", data_type=CellDataType.STRING),
            CellData(value=1000, data_type=CellDataType.NUMBER),
            CellData(value="North", data_type=CellDataType.STRING)
        ],
        [
            CellData(value="Product B", data_type=CellDataType.STRING),
            CellData(value=2000, data_type=CellDataType.NUMBER),
            CellData(value="South", data_type=CellDataType.STRING)
        ]
    ]


@pytest.fixture
def sample_worksheet_config(sample_cell_data) -> WorksheetConfig:
    """Create sample worksheet configuration."""
    return WorksheetConfig(
        name="Sales Data",
        data=sample_cell_data,
        headers=["Product", "Sales", "Region"],
        auto_filter=True,
        freeze_panes={"row": 2, "col": 1},
        charts=[
            ChartConfig(
                chart_id="sales_chart",
                chart_type=ChartType.BAR,
                title="Sales by Product",
                width=600,
                height=400,
                position={"row": 10, "col": 1}
            )
        ]
    )


@pytest.fixture
def sample_workbook_config(sample_worksheet_config) -> WorkbookConfig:
    """Create sample workbook configuration."""
    return WorkbookConfig(
        name="Sales Report",
        worksheets=[sample_worksheet_config],
        theme=Theme.OFFICE,
        properties={
            "title": "Sales Report",
            "subject": "Monthly Sales Data",
            "creator": "Test User"
        }
    )


@pytest.fixture
def sample_export_request(sample_workbook_config) -> ExcelExportRequest:
    """Create sample export request."""
    return ExcelExportRequest(
        job_name="Test Export",
        workbook_config=sample_workbook_config,
        data_source={
            "type": "test",
            "data": []
        },
        output_format=ExcelFormat.XLSX,
        theme=Theme.OFFICE,
        validation_rules=[
            DataValidationRule(
                cell_range="C2:C100",
                validation_type="list",
                formula1="North,South,East,West",
                show_dropdown=True
            )
        ]
    )


@pytest.fixture
def sample_cell_style() -> CellStyle:
    """Create sample cell style."""
    return CellStyle(
        font_name="Arial",
        font_size=12,
        font_bold=True,
        font_color="000000",
        background_color="E7E6E6",
        border_style="thin",
        text_align="center",
        number_format="0.00"
    )


@pytest.fixture
def mock_chart_data() -> dict:
    """Create mock chart data."""
    return {
        "labels": ["Product A", "Product B", "Product C"],
        "series": [
            {
                "name": "Sales",
                "values": [1000, 2000, 1500]
            },
            {
                "name": "Target",
                "values": [800, 1800, 1200]
            }
        ]
    }


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, temp_dir):
    """Setup test environment."""
    # Set test environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("EXCEL_OUTPUT_DIR", temp_dir)
    monkeypatch.setenv("DEBUG", "true")


# Mock functions
@pytest.fixture
def mock_execute_query(monkeypatch):
    """Mock database execute_query function."""
    import app.core.database
    
    async def mock_query(*args, **kwargs):
        # Return mock data based on query
        if "INSERT INTO excel_jobs" in str(args[0]):
            return 1  # Mock job ID
        elif "SELECT" in str(args[0]):
            return {
                "id": 1,
                "status": "completed",
                "user_id": 1,
                "job_name": "Test Job",
                "file_path": "/tmp/test.xlsx",
                "file_size": 1024,
                "created_at": "2024-01-01T00:00:00Z"
            }
        else:
            return None
    
    monkeypatch.setattr(app.core.database, "execute_query", mock_query)
    return mock_query


@pytest.fixture
def mock_redis_client(monkeypatch):
    """Mock Redis client."""
    import app.core.redis_client
    
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        async def get(self, key):
            return self.data.get(key)
        
        async def set(self, key, value, ex=None):
            self.data[key] = value
            return True
        
        async def delete(self, key):
            self.data.pop(key, None)
            return True
        
        async def zadd(self, key, mapping):
            return True
        
        async def zcard(self, key):
            return 0
        
        async def zremrangebyscore(self, key, min_score, max_score):
            return 0
        
        async def expire(self, key, seconds):
            return True
        
        async def ping(self):
            return True
    
    mock_redis = MockRedis()
    
    async def get_mock_redis():
        return mock_redis
    
    monkeypatch.setattr(app.core.redis_client, "get_redis_client", get_mock_redis)
    return mock_redis