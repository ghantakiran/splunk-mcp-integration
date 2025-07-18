"""
Test configuration and fixtures for ITSM Service.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_database
from app.models.itsm_models import Base as ITSMBase
from app.models.user_models import Base as UserBase, ITSMUser
from app.utils.auth import get_current_user, User

# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(ITSMBase.metadata.create_all)
        await conn.run_sync(UserBase.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(ITSMBase.metadata.drop_all)
        await conn.run_sync(UserBase.metadata.drop_all)


@pytest.fixture
def test_user() -> User:
    """Create a test user."""
    return User({
        "id": "test-user-id",
        "email": "test@example.com",
        "full_name": "Test User",
        "roles": ["itsm_user"],
        "permissions": [
            "itsm:integration:read",
            "itsm:integration:create",
            "itsm:ticket:read",
            "itsm:ticket:create",
            "itsm:workflow:read",
            "itsm:sync:view"
        ],
        "active": True
    })


@pytest.fixture
def admin_user() -> User:
    """Create an admin test user."""
    return User({
        "id": "admin-user-id",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "roles": ["itsm_admin"],
        "permissions": [
            "itsm:integration:create",
            "itsm:integration:read",
            "itsm:integration:update",
            "itsm:integration:delete",
            "itsm:ticket:create",
            "itsm:ticket:read",
            "itsm:ticket:update",
            "itsm:ticket:delete",
            "itsm:workflow:create",
            "itsm:workflow:read",
            "itsm:workflow:update",
            "itsm:workflow:delete",
            "itsm:workflow:execute",
            "itsm:sync:manage",
            "itsm:sync:view",
            "itsm:sync:resolve_conflicts",
            "itsm:analytics:view",
            "itsm:analytics:export",
            "itsm:admin:manage_users",
            "itsm:admin:manage_settings",
            "itsm:admin:view_logs",
        ],
        "active": True
    })


@pytest.fixture
def client(db_session: AsyncSession, test_user: User) -> TestClient:
    """Create a test client with database and user overrides."""
    
    def override_get_database():
        return db_session
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_database] = override_get_database
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db_session: AsyncSession, admin_user: User) -> TestClient:
    """Create a test client with admin user."""
    
    def override_get_database():
        return db_session
    
    def override_get_current_user():
        return admin_user
    
    app.dependency_overrides[get_database] = override_get_database
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_itsm_user(db_session: AsyncSession) -> ITSMUser:
    """Create a test ITSM user in the database."""
    user = ITSMUser(
        email="test@example.com",
        full_name="Test User",
        roles=["itsm_user"],
        permissions=[
            "itsm:integration:read",
            "itsm:integration:create",
            "itsm:ticket:read",
            "itsm:ticket:create"
        ]
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
def mock_servicenow_manager():
    """Create a mock ServiceNow manager."""
    mock_manager = AsyncMock()
    
    # Mock connection test
    mock_manager.test_connection.return_value = (True, "Connection successful")
    
    # Mock ticket creation
    mock_manager.create_ticket.return_value = {
        "sys_id": "test-ticket-id",
        "number": "INC0001234",
        "state": "1",
        "short_description": "Test Incident",
        "description": "Test incident description",
        "priority": "4",
        "assigned_to": "test.user",
        "assignment_group": "IT Support",
        "created_on": "2025-01-16 10:30:00",
        "updated_on": "2025-01-16 10:30:00",
        "raw_data": {}
    }
    
    # Mock ticket update
    mock_manager.update_ticket.return_value = {
        "sys_id": "test-ticket-id",
        "number": "INC0001234",
        "state": "2",
        "short_description": "Updated Test Incident",
        "description": "Updated test incident description",
        "priority": "3",
        "assigned_to": "test.user",
        "assignment_group": "IT Support",
        "created_on": "2025-01-16 10:30:00",
        "updated_on": "2025-01-16 11:00:00",
        "raw_data": {}
    }
    
    # Mock ticket retrieval
    mock_manager.get_ticket.return_value = {
        "sys_id": "test-ticket-id",
        "number": "INC0001234",
        "state": "1",
        "short_description": "Test Incident",
        "description": "Test incident description",
        "priority": "4",
        "assigned_to": "test.user",
        "assignment_group": "IT Support",
        "created_on": "2025-01-16 10:30:00",
        "updated_on": "2025-01-16 10:30:00",
        "raw_data": {}
    }
    
    # Mock ticket search
    mock_manager.search_tickets.return_value = [
        {
            "sys_id": "test-ticket-1",
            "number": "INC0001234",
            "state": "1",
            "short_description": "Test Incident 1",
            "description": "Test incident 1 description",
            "priority": "4",
            "assigned_to": "test.user1",
            "assignment_group": "IT Support",
            "created_on": "2025-01-16 10:30:00",
            "updated_on": "2025-01-16 10:30:00",
            "raw_data": {}
        },
        {
            "sys_id": "test-ticket-2", 
            "number": "INC0001235",
            "state": "2",
            "short_description": "Test Incident 2",
            "description": "Test incident 2 description",
            "priority": "3",
            "assigned_to": "test.user2",
            "assignment_group": "IT Support",
            "created_on": "2025-01-16 10:35:00",
            "updated_on": "2025-01-16 10:35:00",
            "raw_data": {}
        }
    ]
    
    # Mock tables
    mock_manager.get_tables.return_value = [
        {"name": "incident", "label": "Incident", "description": "Incident Management"},
        {"name": "problem", "label": "Problem", "description": "Problem Management"},
        {"name": "change_request", "label": "Change Request", "description": "Change Management"}
    ]
    
    return mock_manager


@pytest.fixture
def mock_jira_manager():
    """Create a mock Jira manager."""
    mock_manager = AsyncMock()
    
    # Mock connection test
    mock_manager.test_connection.return_value = (True, "Connection successful")
    
    # Mock ticket creation
    mock_manager.create_ticket.return_value = {
        "id": "10001",
        "key": "TEST-123",
        "summary": "Test Issue",
        "description": "Test issue description",
        "status": "To Do",
        "priority": "Medium",
        "assignee": "test.user",
        "reporter": "test.reporter",
        "created": "2025-01-16T10:30:00.000Z",
        "updated": "2025-01-16T10:30:00.000Z",
        "project": "TEST",
        "issue_type": "Task",
        "raw_data": {}
    }
    
    # Mock ticket update
    mock_manager.update_ticket.return_value = {
        "id": "10001",
        "key": "TEST-123",
        "summary": "Updated Test Issue",
        "description": "Updated test issue description",
        "status": "In Progress",
        "priority": "High",
        "assignee": "test.user",
        "reporter": "test.reporter",
        "created": "2025-01-16T10:30:00.000Z",
        "updated": "2025-01-16T11:00:00.000Z",
        "project": "TEST",
        "issue_type": "Task",
        "raw_data": {}
    }
    
    # Mock ticket retrieval
    mock_manager.get_ticket.return_value = {
        "id": "10001",
        "key": "TEST-123",
        "summary": "Test Issue",
        "description": "Test issue description",
        "status": "To Do",
        "priority": "Medium",
        "assignee": "test.user",
        "reporter": "test.reporter",
        "created": "2025-01-16T10:30:00.000Z",
        "updated": "2025-01-16T10:30:00.000Z",
        "project": "TEST",
        "issue_type": "Task",
        "raw_data": {}
    }
    
    # Mock ticket search
    mock_manager.search_tickets.return_value = [
        {
            "id": "10001",
            "key": "TEST-123",
            "summary": "Test Issue 1",
            "description": "Test issue 1 description",
            "status": "To Do",
            "priority": "Medium",
            "assignee": "test.user1",
            "reporter": "test.reporter",
            "created": "2025-01-16T10:30:00.000Z",
            "updated": "2025-01-16T10:30:00.000Z",
            "project": "TEST",
            "issue_type": "Task",
            "raw_data": {}
        },
        {
            "id": "10002",
            "key": "TEST-124",
            "summary": "Test Issue 2",
            "description": "Test issue 2 description",
            "status": "In Progress",
            "priority": "High",
            "assignee": "test.user2",
            "reporter": "test.reporter",
            "created": "2025-01-16T10:35:00.000Z",
            "updated": "2025-01-16T10:35:00.000Z",
            "project": "TEST",
            "issue_type": "Bug",
            "raw_data": {}
        }
    ]
    
    # Mock projects
    mock_manager.get_projects.return_value = [
        {
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
            "description": "Test project description",
            "project_type": "software",
            "lead": "test.lead"
        }
    ]
    
    # Mock issue types
    mock_manager.get_issue_types.return_value = [
        {
            "id": "1",
            "name": "Task",
            "description": "A task that needs to be done",
            "subtask": False
        },
        {
            "id": "2",
            "name": "Bug",
            "description": "A bug that needs to be fixed",
            "subtask": False
        }
    ]
    
    return mock_manager


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    mock_client = AsyncMock()
    
    # Mock basic operations
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = True
    mock_client.exists.return_value = False
    mock_client.expire.return_value = True
    mock_client.close.return_value = None
    
    return mock_client


@pytest.fixture
def sample_integration_data():
    """Sample integration data for testing."""
    return {
        "name": "Test ServiceNow Integration",
        "description": "Test integration for ServiceNow",
        "provider": "servicenow",
        "endpoint_url": "https://test.service-now.com",
        "credentials": {
            "instance": "test",
            "username": "testuser",
            "password": "testpass"
        },
        "connection_config": {
            "timeout": 30,
            "verify_ssl": True
        },
        "sync_enabled": True,
        "sync_interval_minutes": 15,
        "bidirectional_sync": True,
        "field_mappings": {
            "incident": {
                "title": "short_description",
                "description": "description",
                "priority": "priority",
                "status": "state"
            }
        },
        "table_mappings": {
            "incident": "incident",
            "problem": "problem"
        }
    }


@pytest.fixture
def sample_ticket_data():
    """Sample ticket data for testing."""
    return {
        "title": "Test Incident",
        "description": "This is a test incident",
        "priority": "medium",
        "category": "Software",
        "subcategory": "Application",
        "assigned_to": "test.user",
        "assigned_group": "IT Support",
        "custom_fields": {
            "business_impact": "low",
            "urgency": "medium"
        }
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "Test automation workflow",
        "trigger_type": "manual",
        "trigger_config": {
            "conditions": []
        },
        "steps": [
            {
                "id": "step1",
                "name": "Create Ticket",
                "type": "create_ticket",
                "config": {
                    "provider": "servicenow",
                    "table": "incident",
                    "ticket_data": {
                        "title": "Automated Incident",
                        "description": "Created by workflow",
                        "priority": "medium"
                    }
                },
                "on_success": {
                    "set_variables": {
                        "ticket_id": {
                            "from_result": "sys_id"
                        }
                    }
                }
            }
        ],
        "variables": {
            "environment": "test"
        },
        "timeout_minutes": 30,
        "retry_attempts": 3,
        "retry_delay_seconds": 60
    }