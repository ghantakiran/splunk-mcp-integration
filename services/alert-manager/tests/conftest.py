"""
Shared test fixtures and configuration for Alert Manager service tests.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Import application components
from app.models.alert import (
    AlertRule, AlertIncident, AlertRuleCreate, AlertRuleUpdate, NaturalLanguageAlertRequest,
    AlertStatus, IncidentStatus, IncidentSeverity, ConditionType
)
from app.models.notification import (
    NotificationChannel, NotificationTemplate, NotificationHistory,
    NotificationChannelCreate, ChannelType
)
from app.models.escalation import (
    EscalationRule, EscalationRuleCreate
)
from app.services.alert_engine import AlertEngine
from app.services.notification_service import NotificationService
from app.services.correlation_engine import CorrelationEngine, CorrelationGroup
from app.services.escalation_service import EscalationService


@pytest.fixture
def mock_database():
    """Mock database session."""
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = Mock()
    db.execute = AsyncMock()
    db.scalar = AsyncMock()
    db.scalars = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock()
    redis.expire = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.flushdb = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    
    # Mock Redis operations for caching
    redis.hget = AsyncMock()
    redis.hset = AsyncMock()
    redis.hdel = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    
    # Mock Redis operations for queuing
    redis.lpush = AsyncMock()
    redis.rpop = AsyncMock()
    redis.llen = AsyncMock(return_value=0)
    
    return redis


@pytest.fixture
def mock_current_user():
    """Mock current user."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "organization_id": "test-org-123",
        "roles": ["alert_manager"],
        "permissions": [
            "alert:create", "alert:read", "alert:update", "alert:delete",
            "notification:create", "notification:read", "notification:update",
            "escalation:create", "escalation:read"
        ]
    }


@pytest.fixture
def sample_alert_rule():
    """Sample alert rule for testing."""
    return AlertRule(
        id="alert-rule-123",
        name="High CPU Usage Alert",
        description="Alert when CPU usage exceeds 80% for 5 minutes",
        created_by="test-user-123",
        organization_id="test-org-123",
        spl_query="search index=main source=system | stats avg(cpu_usage) as avg_cpu | where avg_cpu > 80",
        conditions=[
            {
                "type": "threshold",
                "field": "avg_cpu",
                "operator": ">",
                "value": 80.0,
                "time_window": 300
            }
        ],
        severity="high",
        status=AlertStatus.ACTIVE.value,
        is_continuous=True,
        evaluation_interval=60,
        threshold_value=80.0,
        threshold_operator=">",
        time_window=300,
        max_incidents_per_hour=5,
        suppression_window=900,
        auto_resolve_timeout=3600,
        tags=["performance", "cpu", "system"],
        metadata={"environment": "production", "team": "infrastructure"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_alert_incident():
    """Sample alert incident for testing."""
    return AlertIncident(
        id="incident-123",
        rule_id="alert-rule-123",
        status=IncidentStatus.OPEN.value,
        severity="high",
        title="High CPU Usage Detected",
        description="CPU usage exceeded 80% threshold",
        trigger_value=85.5,
        triggered_at=datetime.utcnow(),
        trigger_data=[
            {
                "host": "server-01",
                "cpu_usage": 85.5,
                "_time": datetime.utcnow().isoformat(),
                "source": "system"
            },
            {
                "host": "server-02", 
                "cpu_usage": 82.1,
                "_time": datetime.utcnow().isoformat(),
                "source": "system"
            }
        ],
        affected_entities=["server-01", "server-02"],
        correlation_id=None,
        escalation_level=0,
        notification_sent=False,
        metadata={"query_duration": 2.5, "result_count": 2}
    )


@pytest.fixture
def sample_notification_channel():
    """Sample notification channel for testing."""
    return NotificationChannel(
        id="channel-123",
        name="Test Email Channel",
        channel_type=ChannelType.EMAIL.value,
        config={
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_use_tls": True,
            "from_email": "alerts@test.com",
            "from_name": "Test Alert System",
            "default_recipients": ["admin@test.com", "oncall@test.com"]
        },
        created_by="test-user-123",
        organization_id="test-org-123",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_slack_channel():
    """Sample Slack notification channel for testing."""
    return NotificationChannel(
        id="slack-channel-123",
        name="Test Slack Channel",
        channel_type=ChannelType.SLACK.value,
        config={
            "webhook_url": "https://hooks.slack.com/services/test/webhook",
            "channel": "#alerts",
            "username": "AlertBot",
            "icon_emoji": ":warning:",
            "default_mentions": ["@channel"]
        },
        created_by="test-user-123",
        organization_id="test-org-123",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_teams_channel():
    """Sample Teams notification channel for testing."""
    return NotificationChannel(
        id="teams-channel-123",
        name="Test Teams Channel",
        channel_type=ChannelType.TEAMS.value,
        config={
            "webhook_url": "https://outlook.office.com/webhook/test",
            "title_prefix": "Alert:",
            "theme_color": "ff6600"
        },
        created_by="test-user-123",
        organization_id="test-org-123",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_escalation_rule():
    """Sample escalation rule for testing."""
    return EscalationRule(
        id="escalation-rule-123",
        name="Standard Escalation",
        description="Standard escalation workflow for high severity alerts",
        alert_rule_id="alert-rule-123",
        created_by="test-user-123",
        organization_id="test-org-123",
        escalation_levels=[
            {
                "level": 1,
                "delay_minutes": 0,
                "notification_channels": ["channel-123"],
                "assignees": ["oncall@test.com"],
                "conditions": {"severity": ["high", "critical"]}
            },
            {
                "level": 2,
                "delay_minutes": 15,
                "notification_channels": ["slack-channel-123"],
                "assignees": ["manager@test.com"],
                "conditions": {"status": "open", "age_minutes": 15}
            },
            {
                "level": 3,
                "delay_minutes": 30,
                "notification_channels": ["teams-channel-123"],
                "assignees": ["director@test.com"],
                "conditions": {"status": "open", "age_minutes": 30}
            }
        ],
        max_escalations=3,
        auto_resolve=True,
        auto_resolve_timeout=3600,
        is_active=True,
        metadata={"team": "infrastructure", "priority": "high"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_alert_rule_create():
    """Sample alert rule creation request."""
    return AlertRuleCreate(
        name="New CPU Alert",
        description="Monitor CPU usage across servers",
        spl_query="search index=main source=system | stats avg(cpu_usage) as cpu_avg",
        severity=IncidentSeverity.HIGH,
        is_continuous=True,
        evaluation_interval=300,
        threshold_value=85.0,
        threshold_operator=">",
        time_window=600,
        max_incidents_per_hour=10,
        suppression_window=1800,
        auto_resolve_timeout=7200,
        tags=["performance", "monitoring"],
        metadata={"env": "prod", "team": "ops"}
    )


@pytest.fixture
def sample_natural_language_request():
    """Sample natural language alert request."""
    return NaturalLanguageAlertRequest(
        description="Alert me when error rate exceeds 5% for more than 10 minutes",
        severity=IncidentSeverity.HIGH,
        tags=["errors", "application"],
        additional_context={
            "environment": "production",
            "service": "api-gateway",
            "team": "backend"
        }
    )


@pytest.fixture
def sample_notification_channel_create():
    """Sample notification channel creation request."""
    return NotificationChannelCreate(
        name="Production Alerts",
        channel_type=ChannelType.EMAIL,
        config={
            "smtp_host": "smtp.company.com",
            "smtp_port": 587,
            "smtp_use_tls": True,
            "from_email": "alerts@company.com",
            "default_recipients": ["team@company.com"]
        },
        description="Main email channel for production alerts"
    )


@pytest.fixture
def sample_correlation_group():
    """Sample correlation group for testing."""
    incidents = [
        AlertIncident(
            id=f"incident-{i}",
            rule_id="alert-rule-123",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title=f"Server {i} Alert",
            description=f"Issue detected on server {i}",
            triggered_at=datetime.utcnow() - timedelta(minutes=i*2)
        )
        for i in range(1, 4)
    ]
    
    return CorrelationGroup(
        id="correlation-group-123",
        incidents=incidents,
        correlation_type="time_window",
        correlation_score=0.85,
        created_at=datetime.utcnow() - timedelta(minutes=10),
        last_updated=datetime.utcnow()
    )


@pytest.fixture
def mock_alert_engine():
    """Mock alert engine service."""
    engine = Mock(spec=AlertEngine)
    engine.create_alert_from_natural_language = AsyncMock()
    engine.parse_natural_language = AsyncMock()
    engine.generate_spl_query = AsyncMock()
    engine.test_alert_rule = AsyncMock()
    engine.evaluate_alert_rule = AsyncMock()
    engine.get_alert_conditions = AsyncMock()
    return engine


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    service = Mock(spec=NotificationService)
    service.send_notification = AsyncMock()
    service.test_notification_channel = AsyncMock()
    service.render_template = AsyncMock()
    service.get_notification_history = AsyncMock()
    service.verify_channel_config = AsyncMock()
    return service


@pytest.fixture
def mock_correlation_engine():
    """Mock correlation engine service."""
    engine = Mock(spec=CorrelationEngine)
    engine.correlate_incident = AsyncMock()
    engine.get_correlation_groups = AsyncMock()
    engine.update_correlation_group = AsyncMock()
    engine.cleanup_expired_groups = AsyncMock()
    engine.get_correlation_analytics = AsyncMock()
    return engine


@pytest.fixture
def mock_escalation_service():
    """Mock escalation service."""
    service = Mock(spec=EscalationService)
    service.evaluate_escalation = AsyncMock()
    service.escalate_incident = AsyncMock()
    service.test_escalation_rule = AsyncMock()
    service.get_escalation_history = AsyncMock()
    service.create_escalation_rule = AsyncMock()
    return service


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external service calls."""
    client = AsyncMock()
    
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    mock_response.text = "success"
    mock_response.raise_for_status = AsyncMock()
    
    client.get = AsyncMock(return_value=mock_response)
    client.post = AsyncMock(return_value=mock_response)
    client.put = AsyncMock(return_value=mock_response)
    client.delete = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def sample_spl_query_result():
    """Sample SPL query result for testing."""
    return {
        "results": [
            {
                "_time": "2025-01-16T10:00:00Z",
                "host": "server-01",
                "cpu_usage": 85.5,
                "memory_usage": 72.3,
                "disk_usage": 45.1
            },
            {
                "_time": "2025-01-16T10:01:00Z", 
                "host": "server-02",
                "cpu_usage": 82.1,
                "memory_usage": 68.9,
                "disk_usage": 51.2
            }
        ],
        "count": 2,
        "summary": {
            "avg_cpu": 83.8,
            "max_cpu": 85.5,
            "min_cpu": 82.1,
            "total_hosts": 2
        },
        "execution_time": 2.5,
        "query": "search index=main source=system | stats avg(cpu_usage) as avg_cpu"
    }


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "incident": {
            "id": "incident-123",
            "title": "High CPU Usage Alert",
            "severity": "high",
            "trigger_value": 85.5,
            "threshold": 80.0,
            "status": "open"
        },
        "rule": {
            "name": "CPU Usage Monitor",
            "description": "Monitor CPU usage across servers"
        },
        "organization": {
            "name": "Test Company",
            "environment": "production"
        },
        "timestamp": datetime.utcnow().isoformat(),
        "dashboard_url": "https://splunk.company.com/dashboard/alerts"
    }


# Mock authentication and authorization
@pytest.fixture
def mock_get_current_user():
    """Mock get_current_user dependency."""
    with patch("app.api.v1.endpoints.get_current_user") as mock:
        mock.return_value = {
            "id": "test-user-123",
            "email": "test@example.com", 
            "organization_id": "test-org-123",
            "roles": ["alert_manager"],
            "permissions": ["alert:create", "alert:read", "notification:create"]
        }
        yield mock


@pytest.fixture
def mock_get_db():
    """Mock get_db dependency."""
    with patch("app.api.v1.endpoints.get_db") as mock:
        mock.return_value = mock_database()
        yield mock


# Mock external services
@pytest.fixture
def mock_nlp_service():
    """Mock NLP service for SPL translation."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "spl_query": "search index=main | where cpu_usage > 80",
            "confidence": 0.95,
            "conditions": [
                {
                    "field": "cpu_usage",
                    "operator": ">", 
                    "value": 80,
                    "type": "threshold"
                }
            ]
        }
        mock_response.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_smtp_client():
    """Mock SMTP client for email notifications."""
    with patch("aiosmtplib.send") as mock_send:
        mock_send.return_value = None
        yield mock_send


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return {
        "alerts": {
            "total_rules": 25,
            "active_rules": 20,
            "paused_rules": 3,
            "error_rules": 2,
            "total_incidents": 150,
            "open_incidents": 12,
            "resolved_incidents": 138,
            "avg_resolution_time": 1800  # seconds
        },
        "notifications": {
            "total_sent": 500,
            "email_sent": 300,
            "slack_sent": 150,
            "teams_sent": 50,
            "failed_notifications": 15,
            "success_rate": 97.0
        },
        "correlation": {
            "total_groups": 8,
            "active_groups": 3,
            "noise_reduction": 45.2  # percentage
        },
        "escalation": {
            "total_escalations": 25,
            "level_1_escalations": 15,
            "level_2_escalations": 8,
            "level_3_escalations": 2,
            "avg_escalation_time": 900  # seconds
        }
    }


@pytest_asyncio.fixture
async def alert_engine_instance():
    """Real AlertEngine instance for integration testing."""
    return AlertEngine()


@pytest_asyncio.fixture
async def notification_service_instance():
    """Real NotificationService instance for integration testing."""
    return NotificationService()


@pytest_asyncio.fixture
async def correlation_engine_instance():
    """Real CorrelationEngine instance for integration testing."""
    return CorrelationEngine()


@pytest_asyncio.fixture
async def escalation_service_instance():
    """Real EscalationService instance for integration testing."""
    return EscalationService()


# Utility functions for test data generation
def create_test_alert_rule(**kwargs) -> AlertRule:
    """Create a test alert rule with default values."""
    defaults = {
        "id": str(uuid4()),
        "name": "Test Alert Rule",
        "description": "Test alert rule description",
        "created_by": "test-user-123",
        "organization_id": "test-org-123",
        "spl_query": "search index=main | stats count",
        "conditions": [],
        "severity": "medium",
        "status": AlertStatus.ACTIVE.value,
        "is_continuous": True,
        "evaluation_interval": 300,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    defaults.update(kwargs)
    return AlertRule(**defaults)


def create_test_alert_incident(**kwargs) -> AlertIncident:
    """Create a test alert incident with default values."""
    defaults = {
        "id": str(uuid4()),
        "rule_id": "alert-rule-123",
        "status": IncidentStatus.OPEN.value,
        "severity": "medium",
        "title": "Test Alert Incident",
        "description": "Test alert incident description",
        "triggered_at": datetime.utcnow(),
        "trigger_data": [],
        "metadata": {}
    }
    defaults.update(kwargs)
    return AlertIncident(**defaults)


def create_test_notification_channel(**kwargs) -> NotificationChannel:
    """Create a test notification channel with default values."""
    defaults = {
        "id": str(uuid4()),
        "name": "Test Channel",
        "channel_type": ChannelType.EMAIL.value,
        "config": {"default_recipients": ["test@example.com"]},
        "created_by": "test-user-123",
        "organization_id": "test-org-123",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    defaults.update(kwargs)
    return NotificationChannel(**defaults)