"""
Test configuration and fixtures for Report Scheduling Service.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.schedule_models import (
    ScheduleStatus, ExecutionStatus, DeliveryMethod, ReportFormat, Priority
)


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(test_engine) as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user() -> dict:
    """Create a mock user for testing."""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": [
            "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
            "subscription:create", "subscription:read", "subscription:update", "subscription:delete",
            "execution:read", "execution:retry", "execution:download",
            "analytics:read"
        ]
    }


@pytest.fixture
def mock_admin_user() -> dict:
    """Create a mock admin user for testing."""
    return {
        "user_id": "admin-user-123",
        "username": "adminuser",
        "email": "admin@example.com",
        "roles": ["admin"],
        "permissions": [
            "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
            "subscription:create", "subscription:read", "subscription:update", "subscription:delete", "subscription:test",
            "execution:read", "execution:retry", "execution:cancel", "execution:download", "execution:delete", "execution:logs",
            "analytics:read", "analytics:report",
            "system:admin"
        ]
    }


@pytest.fixture
def mock_jwt_token() -> str:
    """Create a mock JWT token for testing."""
    import jwt
    from datetime import timedelta
    
    payload = {
        "sub": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": [
            "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
            "subscription:create", "subscription:read", "subscription:update", "subscription:delete",
            "execution:read", "execution:retry", "execution:download",
            "analytics:read"
        ],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def mock_admin_jwt_token() -> str:
    """Create a mock admin JWT token for testing."""
    import jwt
    from datetime import timedelta
    
    payload = {
        "sub": "admin-user-123",
        "username": "adminuser",
        "email": "admin@example.com",
        "roles": ["admin"],
        "permissions": [
            "schedule:create", "schedule:read", "schedule:update", "schedule:delete", "schedule:execute",
            "subscription:create", "subscription:read", "subscription:update", "subscription:delete", "subscription:test",
            "execution:read", "execution:retry", "execution:cancel", "execution:download", "execution:delete", "execution:logs",
            "analytics:read", "analytics:report",
            "system:admin"
        ],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def sample_schedule_data() -> dict:
    """Create sample schedule data for testing."""
    return {
        "name": "Test Schedule",
        "description": "A test schedule for unit testing",
        "cron_expression": "0 9 * * 1",  # Every Monday at 9 AM
        "timezone": "UTC",
        "query": "search index=main error | head 100",
        "query_type": "spl",
        "time_range": {
            "earliest": "-1d",
            "latest": "now"
        },
        "report_format": "pdf",
        "delivery_configs": [
            {
                "method": "email",
                "config": {
                    "to": "test@example.com",
                    "subject": "Weekly Error Report"
                }
            }
        ]
    }


@pytest.fixture
def sample_subscription_data() -> dict:
    """Create sample subscription data for testing."""
    return {
        "schedule_id": str(uuid4()),
        "delivery_method": "email",
        "delivery_config": {
            "email": "subscriber@example.com",
            "template": "default",
            "include_attachment": True
        },
        "active": True,
        "preferences": {
            "notification_on_success": True,
            "notification_on_failure": True
        }
    }


@pytest.fixture
def sample_execution_data() -> dict:
    """Create sample execution data for testing."""
    return {
        "schedule_id": str(uuid4()),
        "status": "completed",
        "scheduled_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "duration_seconds": 45.2,
        "report_file_path": "/tmp/reports/test_report.pdf",
        "report_size_bytes": 1024000,
        "records_processed": 150,
        "delivery_results": {
            "total_deliveries": 1,
            "successful_deliveries": 1,
            "failed_deliveries": 0
        }
    }


@pytest.fixture
def auth_headers(mock_jwt_token: str) -> dict:
    """Create authentication headers for testing."""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def admin_auth_headers(mock_admin_jwt_token: str) -> dict:
    """Create admin authentication headers for testing."""
    return {"Authorization": f"Bearer {mock_admin_jwt_token}"}


@pytest_asyncio.fixture
async def created_schedule(db_session: AsyncSession, mock_user: dict, sample_schedule_data: dict):
    """Create a test schedule in the database."""
    from app.core.database import ReportSchedule
    
    schedule = ReportSchedule(
        user_id=mock_user["user_id"],
        name=sample_schedule_data["name"],
        description=sample_schedule_data["description"],
        status=ScheduleStatus.ACTIVE,
        cron_expression=sample_schedule_data["cron_expression"],
        timezone=sample_schedule_data["timezone"],
        query=sample_schedule_data["query"],
        query_type=sample_schedule_data["query_type"],
        time_range=sample_schedule_data["time_range"],
        report_format=ReportFormat.PDF,
        delivery_configs=sample_schedule_data["delivery_configs"],
        priority=Priority.MEDIUM
    )
    
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    
    return schedule


@pytest_asyncio.fixture
async def created_subscription(db_session: AsyncSession, mock_user: dict, created_schedule, sample_subscription_data: dict):
    """Create a test subscription in the database."""
    from app.core.database import ReportSubscription
    
    subscription = ReportSubscription(
        user_id=mock_user["user_id"],
        schedule_id=created_schedule.schedule_id,
        delivery_method=DeliveryMethod.EMAIL,
        delivery_config=sample_subscription_data["delivery_config"],
        active=sample_subscription_data["active"],
        preferences=sample_subscription_data["preferences"]
    )
    
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    
    return subscription


@pytest_asyncio.fixture
async def created_execution(db_session: AsyncSession, created_schedule, sample_execution_data: dict):
    """Create a test execution in the database."""
    from app.core.database import ScheduleExecution
    
    execution = ScheduleExecution(
        schedule_id=created_schedule.schedule_id,
        status=ExecutionStatus.COMPLETED,
        scheduled_at=sample_execution_data["scheduled_at"],
        started_at=sample_execution_data["started_at"],
        completed_at=sample_execution_data["completed_at"],
        duration_seconds=sample_execution_data["duration_seconds"],
        report_file_path=sample_execution_data["report_file_path"],
        report_size_bytes=sample_execution_data["report_size_bytes"],
        records_processed=sample_execution_data["records_processed"],
        delivery_results=sample_execution_data["delivery_results"]
    )
    
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    
    return execution


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock external service responses
@pytest.fixture
def mock_nlp_response():
    """Mock NLP service response."""
    return {
        "success": True,
        "spl_query": "search index=main error | head 100",
        "confidence": 0.95,
        "entities": ["error"],
        "metadata": {
            "processing_time": 0.5,
            "model_version": "1.0"
        }
    }


@pytest.fixture
def mock_visualization_response():
    """Mock visualization service response."""
    return {
        "success": True,
        "chart_url": "http://localhost:8002/charts/test-chart-123.png",
        "chart_type": "bar",
        "metadata": {
            "width": 800,
            "height": 600,
            "format": "png"
        }
    }


@pytest.fixture
def mock_export_response():
    """Mock export service response."""
    return {
        "success": True,
        "file_path": "/tmp/reports/test_report.pdf",
        "file_size": 1024000,
        "download_url": "http://localhost:8009/download/test_report.pdf",
        "generation_time": 15.3,
        "metadata": {
            "pages": 5,
            "format": "pdf"
        }
    }


@pytest.fixture
def mock_email_response():
    """Mock email service response."""
    return {
        "success": True,
        "message_id": "test-message-123",
        "delivery_status": "sent",
        "recipients": ["test@example.com"],
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


# Helper functions for tests
def assert_response_structure(response_data: dict, expected_keys: list):
    """Assert that response has expected structure."""
    assert isinstance(response_data, dict)
    for key in expected_keys:
        assert key in response_data


def assert_error_response(response_data: dict, expected_status_code: int = None):
    """Assert that response is an error response."""
    assert isinstance(response_data, dict)
    assert "detail" in response_data or "message" in response_data
    
    if expected_status_code:
        # This would be checked in the actual test, not in the response data
        pass


def create_test_data_batch(count: int, base_data: dict) -> list:
    """Create a batch of test data items."""
    return [
        {**base_data, "name": f"{base_data.get('name', 'Test')} {i}"}
        for i in range(count)
    ]