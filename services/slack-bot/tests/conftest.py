"""
Pytest configuration and fixtures for Slack bot tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.models.slack_models import SlackUser, UserContext, UserSession


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_slack_user():
    """Create a mock Slack user."""
    return SlackUser(
        id="U123456789",
        name="testuser",
        real_name="Test User",
        email="test@example.com",
        team_id="T123456789",
        is_admin=False,
        is_owner=False,
        is_bot=False,
        timezone="UTC"
    )


@pytest.fixture
def mock_user_context():
    """Create a mock user context."""
    return UserContext(
        user_id="U123456789",
        roles=["user"],
        permissions={"read": True, "search": True},
        accessible_indexes=["*"],
        preferences={},
        access_level="standard"
    )


@pytest.fixture
def mock_user_session():
    """Create a mock user session."""
    return UserSession(
        id="session-123",
        user_id="U123456789",
        channel_id="C123456789",
        started_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        history=[],
        context={},
        preferences={},
        is_active=True
    )


@pytest.fixture
def mock_slack_event():
    """Create a mock Slack event."""
    return {
        "type": "app_mention",
        "user": "U123456789",
        "channel": "C123456789",
        "text": "<@B123456789> show me errors",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "team": "T123456789"
    }


@pytest.fixture
def mock_slack_command():
    """Create a mock Slack slash command."""
    return {
        "token": "verification_token",
        "team_id": "T123456789",
        "team_domain": "test-team",
        "channel_id": "C123456789",
        "channel_name": "general",
        "user_id": "U123456789",
        "user_name": "testuser",
        "command": "/splunk",
        "text": "show me errors",
        "response_url": "https://hooks.slack.com/commands/response",
        "trigger_id": "trigger123"
    }


@pytest.fixture
def mock_database():
    """Create a mock database connection."""
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    return mock_pool


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    return mock_redis


@pytest.fixture
def mock_slack_client():
    """Create a mock Slack client."""
    client = AsyncMock()
    client.auth_test.return_value = {
        "ok": True,
        "user_id": "B123456789",
        "team_id": "T123456789"
    }
    client.chat_postMessage.return_value = {
        "ok": True,
        "ts": "1234567890.123"
    }
    client.conversations_typing.return_value = {"ok": True}
    return client


@pytest.fixture
def mock_splunk_service():
    """Create a mock Splunk service."""
    service = AsyncMock()
    service.process_query.return_value = {
        "success": True,
        "data": {
            "spl_query": "search error | head 10",
            "data": [{"count": 5}],
            "execution_time": 1.2,
            "confidence_score": 0.95
        }
    }
    service.get_system_status.return_value = {
        "status": "healthy",
        "services": {
            "api_gateway": {"status": "healthy"},
            "nlp_engine": {"status": "healthy"}
        }
    }
    return service


@pytest.fixture
def mock_user_service():
    """Create a mock user service."""
    service = AsyncMock()
    service.get_user_context.return_value = UserContext(
        user_id="U123456789",
        roles=["user"],
        accessible_indexes=["*"]
    )
    service.get_user_info.return_value = {
        "user_id": "U123456789",
        "access_level": "standard",
        "roles": ["user"],
        "accessible_indexes": ["*"]
    }
    return service


@pytest.fixture
def mock_session_service():
    """Create a mock session service."""
    service = AsyncMock()
    service.get_or_create_session.return_value = UserSession(
        id="session-123",
        user_id="U123456789",
        channel_id="C123456789"
    )
    service.update_session.return_value = True
    return service


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter."""
    limiter = AsyncMock()
    limiter.check_rate_limit.return_value = True
    limiter.get_user_rate_limit_status.return_value = {
        "requests_used": 5,
        "requests_limit": 100,
        "requests_remaining": 95
    }
    return limiter


@pytest.fixture
def mock_message_formatter():
    """Create a mock message formatter."""
    formatter = MagicMock()
    formatter.format_query_response.return_value = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Query Results*\n```search error | head 10```"
            }
        }
    ]
    formatter.format_help_message.return_value = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Splunk MCP Bot Help*"
            }
        }
    ]
    formatter.format_error_message.return_value = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "❌ *Error*\nSomething went wrong"
            }
        }
    ]
    return formatter