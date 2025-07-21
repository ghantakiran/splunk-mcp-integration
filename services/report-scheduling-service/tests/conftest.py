#!/usr/bin/env python3
"""
Comprehensive test configuration for Report Scheduling Service.

This module provides fixtures, mocks, and test utilities for comprehensive
testing of the Report Scheduling Service components including scheduling,
report generation, versioning, and delivery.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime, timedelta, timezone
import json

# Test client imports
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    from app.core.database import Base
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(test_engine) as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Mock settings for testing
@pytest.fixture
def mock_settings():
    """Mock Report Scheduling Service settings configuration."""
    with patch('app.core.config.settings') as mock:
        mock.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
        mock.REDIS_URL = "redis://localhost:6379/4"
        mock.JWT_SECRET_KEY = "test-secret-key"
        mock.JWT_ALGORITHM = "HS256"
        mock.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock.API_HOST = "0.0.0.0"
        mock.API_PORT = 8015
        mock.DEBUG = True
        mock.LOG_LEVEL = "DEBUG"
        
        # Scheduling settings
        mock.MAX_CONCURRENT_JOBS = 10
        mock.JOB_TIMEOUT_MINUTES = 60
        mock.RETRY_ATTEMPTS = 3
        mock.RETRY_DELAY_SECONDS = 30
        mock.SCHEDULER_INTERVAL_SECONDS = 30
        
        # Report settings
        mock.MAX_REPORT_SIZE_MB = 100
        mock.REPORT_RETENTION_DAYS = 30
        mock.SUPPORTED_FORMATS = ["pdf", "csv", "xlsx", "json"]
        mock.SUPPORTED_DELIVERY_METHODS = ["email", "webhook", "sftp", "s3"]
        
        # Version control settings
        mock.MAX_VERSIONS_PER_SCHEDULE = 10
        mock.VERSION_RETENTION_DAYS = 90
        mock.AUTO_VERSION_ON_CHANGE = True
        
        yield mock


@pytest.fixture
def mock_database(db_session):
    """Mock database operations."""
    with patch('app.core.database.get_db') as mock:
        mock.return_value = db_session
        yield db_session


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
        mock_client.lpush = AsyncMock()
        mock_client.rpop = AsyncMock()
        mock_client.llen = AsyncMock(return_value=0)
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
            "permissions": ["schedule:read", "schedule:write", "schedule:create", "schedule:delete"],
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
def sample_schedule_data():
    """Sample schedule data for testing."""
    return [
        {
            "name": "Daily Error Report",
            "description": "Daily report of system errors",
            "cron_expression": "0 9 * * *",  # Daily at 9 AM
            "timezone": "UTC",
            "is_active": True,
            "priority": "medium",
            "report_config": {
                "query": "search error earliest=-24h",
                "format": "pdf",
                "title": "Daily Error Summary",
                "include_charts": True,
                "chart_types": ["line", "bar"]
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["admin@example.com", "team@example.com"],
                "subject": "Daily Error Report - {{date}}",
                "include_attachments": True
            },
            "retention_days": 30,
            "max_retries": 3
        },
        {
            "name": "Weekly Performance Dashboard",
            "description": "Weekly system performance metrics",
            "cron_expression": "0 10 * * 1",  # Monday at 10 AM
            "timezone": "America/New_York",
            "is_active": True,
            "priority": "high",
            "report_config": {
                "query": "search index=performance earliest=-7d",
                "format": "xlsx",
                "title": "Weekly Performance Report",
                "include_charts": True,
                "chart_types": ["line", "area", "gauge"]
            },
            "delivery_config": {
                "method": "webhook",
                "webhook_url": "https://api.example.com/reports",
                "headers": {"Authorization": "Bearer token123"},
                "include_metadata": True
            },
            "retention_days": 90,
            "max_retries": 5
        },
        {
            "name": "Monthly Security Audit",
            "description": "Monthly security events audit",
            "cron_expression": "0 8 1 * *",  # First day of month at 8 AM
            "timezone": "UTC",
            "is_active": True,
            "priority": "critical",
            "report_config": {
                "query": "search sourcetype=security earliest=-30d",
                "format": "csv",
                "title": "Monthly Security Audit",
                "include_summary": True,
                "include_charts": False
            },
            "delivery_config": {
                "method": "sftp",
                "sftp_config": {
                    "host": "secure.example.com",
                    "port": 22,
                    "username": "reports",
                    "path": "/reports/security/"
                }
            },
            "retention_days": 365,
            "max_retries": 2
        }
    ]


@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing."""
    return [
        {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "triggered_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "status": "completed",
            "report_size_bytes": 2048576,  # 2MB
            "delivery_status": "delivered",
            "execution_time_seconds": 300,
            "retry_count": 0,
            "metadata": {
                "rows_processed": 15000,
                "charts_generated": 3,
                "delivery_method": "email",
                "recipients_count": 2
            }
        },
        {
            "execution_id": "exec-456",
            "schedule_id": "schedule-789",
            "triggered_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "started_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "completed_at": None,
            "status": "running",
            "report_size_bytes": None,
            "delivery_status": "pending",
            "execution_time_seconds": None,
            "retry_count": 1,
            "metadata": {
                "estimated_completion": datetime.now(timezone.utc) + timedelta(minutes=10),
                "progress_percentage": 65
            }
        },
        {
            "execution_id": "exec-789",
            "schedule_id": "schedule-123",
            "triggered_at": datetime.now(timezone.utc) - timedelta(hours=6),
            "started_at": datetime.now(timezone.utc) - timedelta(hours=6),
            "completed_at": datetime.now(timezone.utc) - timedelta(hours=5, minutes=30),
            "status": "failed",
            "report_size_bytes": None,
            "delivery_status": "failed",
            "execution_time_seconds": 1800,
            "retry_count": 3,
            "error_message": "Query timeout exceeded",
            "metadata": {
                "error_type": "timeout",
                "last_retry_at": datetime.now(timezone.utc) - timedelta(hours=5)
            }
        }
    ]


@pytest.fixture
def sample_version_data():
    """Sample version data for testing."""
    return [
        {
            "version_id": "v1.0.0",
            "schedule_id": "schedule-123",
            "version_number": "1.0.0",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "created_by": "user-123",
            "action": "create",
            "change_summary": "Initial version created",
            "configuration": {
                "name": "Daily Report",
                "cron_expression": "0 9 * * *",
                "report_config": {"format": "pdf"},
                "delivery_config": {"method": "email"}
            },
            "is_current": False
        },
        {
            "version_id": "v1.1.0",
            "schedule_id": "schedule-123",
            "version_number": "1.1.0",
            "created_at": datetime.now(timezone.utc) - timedelta(days=15),
            "created_by": "user-456",
            "action": "update",
            "change_summary": "Updated delivery recipients",
            "configuration": {
                "name": "Daily Report",
                "cron_expression": "0 9 * * *",
                "report_config": {"format": "pdf"},
                "delivery_config": {
                    "method": "email",
                    "recipients": ["team@example.com"]
                }
            },
            "is_current": False
        },
        {
            "version_id": "v1.2.0",
            "schedule_id": "schedule-123",
            "version_number": "1.2.0",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5),
            "created_by": "user-123",
            "action": "update",
            "change_summary": "Added charts to report",
            "configuration": {
                "name": "Daily Report",
                "cron_expression": "0 9 * * *",
                "report_config": {
                    "format": "pdf",
                    "include_charts": True
                },
                "delivery_config": {
                    "method": "email",
                    "recipients": ["team@example.com"]
                }
            },
            "is_current": True
        }
    ]


@pytest.fixture
def sample_subscription_data():
    """Sample subscription data for testing."""
    return [
        {
            "subscription_id": "sub-123",
            "schedule_id": "schedule-456",
            "user_id": "user-123",
            "subscription_type": "email",
            "is_active": True,
            "frequency": "immediate",
            "preferences": {
                "format": "pdf",
                "include_attachments": True,
                "notification_email": "user@example.com"
            },
            "created_at": datetime.now(timezone.utc) - timedelta(days=10),
            "last_notification_at": datetime.now(timezone.utc) - timedelta(hours=24)
        },
        {
            "subscription_id": "sub-456",
            "schedule_id": "schedule-789",
            "user_id": "user-456",
            "subscription_type": "webhook",
            "is_active": True,
            "frequency": "digest",
            "preferences": {
                "webhook_url": "https://api.user.com/reports",
                "digest_interval": "daily",
                "max_items": 50
            },
            "created_at": datetime.now(timezone.utc) - timedelta(days=5),
            "last_notification_at": datetime.now(timezone.utc) - timedelta(hours=12)
        }
    ]


@pytest.fixture
def mock_scheduler():
    """Mock scheduler service."""
    with patch('app.services.scheduler_service.SchedulerService') as mock:
        mock_scheduler = Mock()
        mock_scheduler.schedule_job = AsyncMock(return_value={
            "job_id": "job-123",
            "scheduled_at": datetime.now(timezone.utc),
            "next_run": datetime.now(timezone.utc) + timedelta(hours=24)
        })
        mock_scheduler.cancel_job = AsyncMock(return_value=True)
        mock_scheduler.get_job_status = AsyncMock(return_value={
            "job_id": "job-123",
            "status": "scheduled",
            "next_run": datetime.now(timezone.utc) + timedelta(hours=24)
        })
        mock_scheduler.list_active_jobs = AsyncMock(return_value=[
            {"job_id": "job-123", "schedule_id": "schedule-456"}
        ])
        mock_scheduler.pause_job = AsyncMock(return_value=True)
        mock_scheduler.resume_job = AsyncMock(return_value=True)
        mock.return_value = mock_scheduler
        yield mock_scheduler


@pytest.fixture
def mock_report_generator():
    """Mock report generator service."""
    with patch('app.services.report_generator.ReportGenerator') as mock:
        mock_generator = Mock()
        mock_generator.generate_report = AsyncMock(return_value={
            "report_id": "report-123",
            "file_path": "/tmp/report.pdf",
            "file_size": 2048576,
            "format": "pdf",
            "generation_time_ms": 45000,
            "metadata": {
                "rows_processed": 10000,
                "charts_generated": 5,
                "pages_count": 25
            }
        })
        mock_generator.validate_query = Mock(return_value={
            "is_valid": True,
            "estimated_rows": 10000,
            "estimated_time_ms": 30000
        })
        mock_generator.get_supported_formats = Mock(return_value=["pdf", "csv", "xlsx", "json"])
        mock.return_value = mock_generator
        yield mock_generator


@pytest.fixture
def mock_delivery_service():
    """Mock delivery service."""
    with patch('app.services.delivery_service.DeliveryService') as mock:
        mock_delivery = Mock()
        mock_delivery.deliver_report = AsyncMock(return_value={
            "delivery_id": "delivery-123",
            "status": "delivered",
            "delivered_at": datetime.now(timezone.utc),
            "delivery_time_ms": 5000,
            "recipients": ["admin@example.com"],
            "metadata": {
                "delivery_method": "email",
                "message_id": "msg-456"
            }
        })
        mock_delivery.validate_delivery_config = Mock(return_value={
            "is_valid": True,
            "supported_methods": ["email", "webhook", "sftp"]
        })
        mock_delivery.test_delivery_connection = AsyncMock(return_value={
            "connection_ok": True,
            "response_time_ms": 150
        })
        mock.return_value = mock_delivery
        yield mock_delivery


@pytest.fixture
def mock_analytics_service():
    """Mock analytics service."""
    with patch('app.services.analytics_service.AnalyticsService') as mock:
        mock_analytics = Mock()
        mock_analytics.get_schedule_analytics = AsyncMock(return_value={
            "schedule_id": "schedule-123",
            "total_executions": 150,
            "success_rate": 0.96,
            "average_execution_time_ms": 35000,
            "average_report_size_mb": 2.5,
            "last_30_days": {
                "executions": 45,
                "failures": 2,
                "avg_size_mb": 2.8
            }
        })
        mock_analytics.get_system_analytics = AsyncMock(return_value={
            "total_schedules": 25,
            "active_schedules": 20,
            "total_executions_today": 35,
            "success_rate_today": 0.97,
            "queue_length": 8,
            "average_processing_time_ms": 42000
        })
        mock_analytics.get_user_analytics = AsyncMock(return_value={
            "user_id": "user-123",
            "schedules_created": 8,
            "reports_generated": 120,
            "data_consumed_mb": 350.5,
            "favorite_formats": ["pdf", "xlsx"]
        })
        mock.return_value = mock_analytics
        yield mock_analytics


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_data = {
            "temp_dir": temp_dir,
            "created_files": [],
            "file_contents": {}
        }
        
        def mock_create_report_file(file_path: str, content: bytes = None, format_type: str = "pdf"):
            """Create a mock report file."""
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if content is None:
                if format_type == "pdf":
                    content = b"PDF-1.4 mock_pdf_content"
                elif format_type == "csv":
                    content = b"header1,header2,header3\nvalue1,value2,value3\n"
                elif format_type == "xlsx":
                    content = b"PK\x03\x04mock_xlsx_content"
                else:
                    content = b"mock_report_content"
            
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
        
        mock_data["create_report_file"] = mock_create_report_file
        mock_data["read_file"] = mock_read_file
        mock_data["get_file_size"] = mock_get_file_size
        yield mock_data


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


def assert_schedule_structure(schedule_data: Dict[str, Any]) -> bool:
    """Assert that schedule data has valid structure."""
    required_fields = ["schedule_id", "name", "cron_expression", "is_active"]
    return all(field in schedule_data for field in required_fields)


def assert_execution_structure(execution_data: Dict[str, Any]) -> bool:
    """Assert that execution data has valid structure."""
    required_fields = ["execution_id", "schedule_id", "triggered_at", "status"]
    return all(field in execution_data for field in required_fields)


def assert_version_structure(version_data: Dict[str, Any]) -> bool:
    """Assert that version data has valid structure."""
    required_fields = ["version_id", "version_number", "created_at", "action"]
    return all(field in version_data for field in required_fields)


def generate_mock_report_data(format_type: str = "pdf") -> bytes:
    """Generate mock report file data for testing."""
    if format_type == "pdf":
        return b"PDF-1.4 mock_pdf_report_content"
    elif format_type == "csv":
        return b"timestamp,event_count,error_rate\n2024-01-01,1000,0.02\n2024-01-02,1100,0.01\n"
    elif format_type == "xlsx":
        return b"PK\x03\x04\x14\x00\x00\x00\x08\x00mock_xlsx_report_content"
    elif format_type == "json":
        return b'{"report_data": [{"timestamp": "2024-01-01", "count": 1000}]}'
    else:
        return b"mock_report_content"


def create_mock_cron_expression(frequency: str = "daily") -> str:
    """Create mock cron expressions for different frequencies."""
    expressions = {
        "hourly": "0 * * * *",
        "daily": "0 9 * * *",
        "weekly": "0 9 * * 1",
        "monthly": "0 9 1 * *",
        "yearly": "0 9 1 1 *"
    }
    return expressions.get(frequency, "0 9 * * *")


# Test configuration
pytest_plugins = []

# Configure async testing
@pytest.fixture(autouse=True)
def configure_async_testing():
    """Configure async testing environment."""
    # Set async test timeout
    import asyncio
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())