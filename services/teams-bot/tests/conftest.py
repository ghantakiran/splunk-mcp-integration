"""
Pytest configuration and fixtures for Microsoft Teams bot tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.models.teams_models import TeamsUser, UserContext, TeamsSession


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_teams_user():
    """Create a mock Teams user."""
    return TeamsUser(
        id="29:user123",
        name="Test User",
        email="test@example.com",
        aad_object_id="aad-123",
        tenant_id="tenant-123",
        conversation_type="personal",
        is_admin=False,
        is_bot=False
    )


@pytest.fixture
def mock_user_context():
    """Create a mock user context."""
    return UserContext(
        user_id="29:user123",
        roles=["user"],
        permissions={"read": True, "search": True},
        accessible_indexes=["*"],
        preferences={},
        access_level="standard",
        teams_tenant_id="tenant-123",
        aad_object_id="aad-123"
    )


@pytest.fixture
def mock_teams_session():
    """Create a mock Teams session."""
    return TeamsSession(
        id="session-123",
        user_id="29:user123",
        conversation_id="19:conv123",
        started_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        history=[],
        context={},
        preferences={},
        is_active=True
    )


@pytest.fixture
def mock_teams_activity():
    """Create a mock Teams activity."""
    return {
        "type": "message",
        "id": "activity-123",
        "timestamp": "2025-01-16T10:30:00Z",
        "from": {
            "id": "29:user123",
            "name": "Test User",
            "aadObjectId": "aad-123"
        },
        "conversation": {
            "id": "19:conv123",
            "conversationType": "personal",
            "tenantId": "tenant-123"
        },
        "recipient": {
            "id": "28:bot123",
            "name": "Splunk MCP Assistant"
        },
        "text": "show me errors from last hour",
        "channelId": "msteams",
        "serviceUrl": "https://smba.trafficmanager.net/teams/",
        "entities": [],
        "channelData": {
            "tenant": {
                "id": "tenant-123"
            }
        }
    }


@pytest.fixture
def mock_teams_mention_activity():
    """Create a mock Teams mention activity."""
    return {
        "type": "message",
        "id": "activity-mention-123",
        "timestamp": "2025-01-16T10:30:00Z",
        "from": {
            "id": "29:user123",
            "name": "Test User"
        },
        "conversation": {
            "id": "19:channel123",
            "conversationType": "channel",
            "tenantId": "tenant-123"
        },
        "recipient": {
            "id": "28:bot123",
            "name": "Splunk MCP Assistant"
        },
        "text": "<at>Splunk MCP Assistant</at> show me errors",
        "channelId": "msteams",
        "serviceUrl": "https://smba.trafficmanager.net/teams/",
        "entities": [
            {
                "type": "mention",
                "text": "<at>Splunk MCP Assistant</at>",
                "mentioned": {
                    "id": "28:bot123",
                    "name": "Splunk MCP Assistant"
                }
            }
        ]
    }


@pytest.fixture
def mock_teams_invoke_activity():
    """Create a mock Teams invoke activity."""
    return {
        "type": "invoke",
        "name": "adaptiveCard/action",
        "id": "invoke-123",
        "from": {
            "id": "29:user123",
            "name": "Test User"
        },
        "conversation": {
            "id": "19:conv123",
            "conversationType": "personal"
        },
        "value": {
            "action": "run_query",
            "query": "show me system status"
        },
        "channelId": "msteams",
        "serviceUrl": "https://smba.trafficmanager.net/teams/"
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
        user_id="29:user123",
        roles=["user"],
        accessible_indexes=["*"]
    )
    service.get_user_info.return_value = {
        "user_id": "29:user123",
        "access_level": "standard",
        "roles": ["user"],
        "accessible_indexes": ["*"],
        "name": "Test User"
    }
    return service


@pytest.fixture
def mock_session_service():
    """Create a mock session service."""
    service = AsyncMock()
    service.get_or_create_session.return_value = TeamsSession(
        id="session-123",
        user_id="29:user123",
        conversation_id="19:conv123"
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
    formatter.format_query_response.return_value = {
        "type": "message",
        "text": "**Query Results**\n```search error | head 10```\n\n📊 **Results:** 5 records"
    }
    formatter.format_help_message.return_value = "**Teams Bot Help**"
    formatter.format_error_message.return_value = "❌ **Error**\nSomething went wrong"
    return formatter


@pytest.fixture
def mock_adaptive_card_builder():
    """Create a mock adaptive card builder."""
    builder = MagicMock()
    builder.create_help_card.return_value = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [{"type": "TextBlock", "text": "Help"}]
        }
    }
    builder.create_status_card.return_value = {
        "contentType": "application/vnd.microsoft.card.adaptive", 
        "content": {
            "type": "AdaptiveCard",
            "body": [{"type": "TextBlock", "text": "Status"}]
        }
    }
    return builder


@pytest.fixture
def mock_bot_framework_activity():
    """Create a mock Bot Framework Activity."""
    from botbuilder.schema import Activity, ActivityTypes, ChannelAccount
    
    return Activity(
        type=ActivityTypes.message,
        id="activity-123",
        from_property=ChannelAccount(id="29:user123", name="Test User"),
        recipient=ChannelAccount(id="28:bot123", name="Bot"),
        conversation={"id": "19:conv123"},
        text="test message",
        channel_id="msteams"
    )