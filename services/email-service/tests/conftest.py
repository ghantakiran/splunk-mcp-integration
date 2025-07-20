"""
Test configuration and fixtures for Email Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from app.main import app
from app.services.database_service import DatabaseService
from app.services.redis_service import RedisService
from app.services.email_processor import EmailProcessor
from app.services.report_generator import ReportGenerator
from app.models.email_models import EmailStatus, EmailType, EmailPriority
from app.utils.rate_limiter import RateLimiter


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user():
    """Mock user for authentication."""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.name = "Test User"
    user.is_active = True
    user.roles = ["user"]
    user.permissions = ["email:read", "email:send"]
    return user


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload."""
    return {
        "sub": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
        "exp": 9999999999,  # Far future expiration
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for requests."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def db_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    # Mock query operations
    mock_query_result = AsyncMock()
    mock_query_result.scalar_one_or_none = AsyncMock()
    mock_query_result.scalars = AsyncMock()
    mock_query_result.all = AsyncMock()
    session.execute = AsyncMock(return_value=mock_query_result)
    
    return session


@pytest.fixture
def mock_database_service(db_session):
    """Mock database service."""
    db_service = AsyncMock(spec=DatabaseService)
    db_service.session = db_session
    db_service.get_session = AsyncMock(return_value=db_session)
    
    # Mock user operations
    db_service.get_user = AsyncMock()
    db_service.create_user = AsyncMock()
    db_service.update_user = AsyncMock()
    
    # Mock email operations
    db_service.create_email = AsyncMock()
    db_service.get_email = AsyncMock()
    db_service.update_email_status = AsyncMock()
    db_service.list_emails = AsyncMock()
    
    # Mock template operations
    db_service.create_template = AsyncMock()
    db_service.get_template = AsyncMock()
    db_service.list_templates = AsyncMock()
    
    # Mock metrics operations
    db_service.record_metric = AsyncMock()
    db_service.get_metrics = AsyncMock()
    
    return db_service


@pytest.fixture
def mock_redis_service():
    """Mock Redis service."""
    redis_service = AsyncMock(spec=RedisService)
    
    # Mock Redis operations
    redis_service.get = AsyncMock()
    redis_service.set = AsyncMock()
    redis_service.delete = AsyncMock()
    redis_service.exists = AsyncMock()
    redis_service.expire = AsyncMock()
    redis_service.incr = AsyncMock()
    redis_service.decr = AsyncMock()
    
    # Mock list operations
    redis_service.lpush = AsyncMock()
    redis_service.rpop = AsyncMock()
    redis_service.llen = AsyncMock()
    
    # Mock hash operations
    redis_service.hget = AsyncMock()
    redis_service.hset = AsyncMock()
    redis_service.hgetall = AsyncMock()
    
    return redis_service


@pytest.fixture
def mock_email_processor(mock_database_service, mock_redis_service):
    """Mock email processor service."""
    processor = AsyncMock(spec=EmailProcessor)
    processor.db = mock_database_service
    processor.redis = mock_redis_service
    
    # Mock processing methods
    processor.process_webhook = AsyncMock()
    processor.process_query_email = AsyncMock()
    processor.send_email = AsyncMock()
    processor.process_incoming_email = AsyncMock()
    processor.start_imap_processing = AsyncMock()
    
    return processor


@pytest.fixture
def mock_report_generator(mock_database_service, mock_redis_service):
    """Mock report generator service."""
    generator = AsyncMock(spec=ReportGenerator)
    generator.db = mock_database_service
    generator.redis = mock_redis_service
    
    # Mock generation methods
    generator.generate_pdf_report = AsyncMock()
    generator.generate_csv_report = AsyncMock()
    generator.generate_html_report = AsyncMock()
    generator.generate_excel_report = AsyncMock()
    
    return generator


@pytest.fixture
def mock_rate_limiter(mock_redis_service):
    """Mock rate limiter."""
    limiter = AsyncMock(spec=RateLimiter)
    limiter.redis = mock_redis_service
    
    # Mock rate limiting methods
    limiter.check_rate_limit = AsyncMock(return_value=True)
    limiter.increment_counter = AsyncMock()
    limiter.get_rate_limit_info = AsyncMock()
    limiter.reset_rate_limit = AsyncMock()
    
    return limiter


@pytest.fixture
def mock_smtp_client():
    """Mock SMTP client."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_client = AsyncMock()
        mock_smtp.return_value = mock_client
        
        # Mock SMTP operations
        mock_client.connect = AsyncMock()
        mock_client.starttls = AsyncMock()
        mock_client.login = AsyncMock()
        mock_client.send_message = AsyncMock()
        mock_client.quit = AsyncMock()
        
        yield mock_client


@pytest.fixture
def mock_imap_client():
    """Mock IMAP client."""
    with patch('aioimaplib.IMAP4_SSL') as mock_imap:
        mock_client = AsyncMock()
        mock_imap.return_value = mock_client
        
        # Mock IMAP operations
        mock_client.wait_hello_from_server = AsyncMock()
        mock_client.login = AsyncMock()
        mock_client.select = AsyncMock()
        mock_client.search = AsyncMock()
        mock_client.fetch = AsyncMock()
        mock_client.logout = AsyncMock()
        
        yield mock_client


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        "recipient_email": "user@example.com",
        "recipient_name": "Test User",
        "subject": "Test Email Subject",
        "body_text": "This is a test email body in plain text.",
        "body_html": "<p>This is a test email body in <strong>HTML</strong>.</p>",
        "email_type": EmailType.NOTIFICATION,
        "priority": EmailPriority.NORMAL,
        "metadata": {"test": True},
    }


@pytest.fixture
def sample_email_response():
    """Sample email response for testing."""
    return {
        "id": str(uuid4()),
        "message_id": f"test-{uuid4()}@example.com",
        "status": EmailStatus.SENT,
        "recipient_email": "user@example.com",
        "subject": "Test Email Subject",
        "email_type": EmailType.NOTIFICATION,
        "priority": EmailPriority.NORMAL,
        "created_at": datetime.utcnow(),
        "sent_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_template_data():
    """Sample email template data for testing."""
    return {
        "name": "test-template",
        "description": "A test email template",
        "subject_template": "Test Subject: {{variable1}}",
        "body_text_template": "Hello {{name}}, this is a test.",
        "body_html_template": "<p>Hello <strong>{{name}}</strong>, this is a test.</p>",
        "email_type": EmailType.NOTIFICATION,
        "variables": ["name", "variable1"],
        "default_values": {"variable1": "default"},
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload for testing."""
    return {
        "id": "webhook-123",
        "type": "email.received",
        "data": {
            "message_id": "test-message-123",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "subject": "Test Webhook Email",
            "body": "This is a test webhook email",
            "timestamp": "2025-01-16T10:30:00Z",
        },
    }


@pytest.fixture
def sample_report_request():
    """Sample report request for testing."""
    return {
        "title": "Test Report",
        "description": "A test report for email service",
        "query": "index=main | stats count by source",
        "format": "pdf",
        "recipients": ["user@example.com"],
        "schedule": "daily",
        "parameters": {
            "time_range": "last_24h",
            "chart_type": "bar",
        },
    }


@pytest_asyncio.fixture
async def app_with_mocks(
    mock_database_service,
    mock_redis_service,
    mock_email_processor,
    mock_report_generator,
    mock_rate_limiter,
):
    """App instance with mocked dependencies."""
    app.state.db = mock_database_service
    app.state.redis = mock_redis_service
    app.state.email_processor = mock_email_processor
    app.state.report_generator = mock_report_generator
    app.state.rate_limiter = mock_rate_limiter
    app.state.metrics = Mock()
    
    yield app
    
    # Cleanup
    for attr in ['db', 'redis', 'email_processor', 'report_generator', 'rate_limiter', 'metrics']:
        if hasattr(app.state, attr):
            delattr(app.state, attr)


@pytest.fixture
def mock_nlp_service():
    """Mock NLP service for query processing."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "spl_query": "index=main | stats count by source",
                "confidence": 0.95,
                "intent": "count_by_source",
            },
        }
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_visualization_service():
    """Mock visualization service for chart generation."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "chart_data": {"x": [1, 2, 3], "y": [10, 20, 30]},
                "chart_url": "http://localhost:8002/charts/test-chart.png",
            },
        }
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        yield mock_client


# Helper functions for tests

def create_mock_email_message(**kwargs):
    """Create a mock email message with default values."""
    defaults = {
        "id": uuid4(),
        "message_id": f"test-{uuid4()}@example.com",
        "sender_email": "sender@example.com",
        "recipient_email": "recipient@example.com",
        "subject": "Test Subject",
        "body_text": "Test body",
        "email_type": EmailType.NOTIFICATION,
        "priority": EmailPriority.NORMAL,
        "status": EmailStatus.PENDING,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    
    message = Mock()
    for key, value in defaults.items():
        setattr(message, key, value)
    
    return message


def create_mock_email_template(**kwargs):
    """Create a mock email template with default values."""
    defaults = {
        "id": uuid4(),
        "name": "test-template",
        "subject_template": "Test Subject",
        "body_text_template": "Test body",
        "email_type": EmailType.NOTIFICATION,
        "is_active": True,
        "version": 1,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    
    template = Mock()
    for key, value in defaults.items():
        setattr(template, key, value)
    
    return template


def create_mock_user(**kwargs):
    """Create a mock user with default values."""
    defaults = {
        "id": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "is_active": True,
        "roles": ["user"],
        "permissions": ["email:read", "email:send"],
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    
    user = Mock()
    for key, value in defaults.items():
        setattr(user, key, value)
    
    return user