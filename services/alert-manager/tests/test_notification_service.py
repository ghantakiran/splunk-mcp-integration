"""
Tests for Notification Service functionality.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.notification_service import NotificationService
from app.models.notification import NotificationChannel, ChannelType
from app.models.alert import AlertIncident


@pytest.fixture
def notification_service():
    """Create NotificationService instance for testing."""
    return NotificationService()


@pytest.fixture
def sample_email_channel():
    """Sample email notification channel."""
    return NotificationChannel(
        id="email_channel_1",
        name="Test Email Channel",
        channel_type=ChannelType.EMAIL.value,
        config={
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_use_tls": True,
            "from_email": "alerts@test.com",
            "from_name": "Test Alerts",
            "default_recipients": ["admin@test.com"]
        },
        created_by="test_user",
        is_active=True
    )


@pytest.fixture
def sample_slack_channel():
    """Sample Slack notification channel."""
    return NotificationChannel(
        id="slack_channel_1",
        name="Test Slack Channel",
        channel_type=ChannelType.SLACK.value,
        config={
            "webhook_url": "https://hooks.slack.com/test",
            "channel": "#alerts",
            "username": "AlertBot"
        },
        created_by="test_user",
        is_active=True
    )


@pytest.fixture
def sample_incident():
    """Sample alert incident."""
    return AlertIncident(
        id="incident_1",
        rule_id="rule_1",
        status="open",
        severity="high",
        title="High CPU Usage Alert",
        description="CPU usage has exceeded 80% threshold",
        trigger_value=85.5,
        triggered_at=datetime.utcnow(),
        trigger_data=[
            {"host": "server1", "cpu_usage": 85.5, "_time": "2025-01-16T10:00:00Z"}
        ]
    )


@pytest.fixture
def sample_rule():
    """Sample alert rule."""
    rule = MagicMock()
    rule.id = "rule_1"
    rule.name = "CPU Usage Alert"
    rule.description = "Monitor CPU usage"
    rule.spl_query = "search index=main | where cpu_usage > 80"
    return rule


class TestNotificationService:
    """Test cases for NotificationService."""
    
    @pytest.mark.asyncio
    async def test_render_template(
        self, notification_service, sample_incident, sample_rule
    ):
        """Test template rendering with incident data."""
        template_content = {
            "subject": "Alert: {{ incident.title }}",
            "body": "Severity: {{ incident.severity }}\nValue: {{ incident.trigger_value }}"
        }
        
        rendered = await notification_service._render_template(
            template_content, sample_incident, sample_rule
        )
        
        assert "High CPU Usage Alert" in rendered["subject"]
        assert "high" in rendered["body"]
        assert "85.5" in rendered["body"]
    
    @pytest.mark.asyncio
    async def test_get_slack_color(self, notification_service):
        """Test Slack color mapping by severity."""
        assert notification_service._get_slack_color("critical") == "danger"
        assert notification_service._get_slack_color("high") == "warning"
        assert notification_service._get_slack_color("low") == "good"
    
    @pytest.mark.asyncio
    async def test_get_teams_color(self, notification_service):
        """Test Teams color mapping by severity."""
        assert notification_service._get_teams_color("critical") == "ff0000"
        assert notification_service._get_teams_color("high") == "ff6600"
        assert notification_service._get_teams_color("info") == "0078d4"
    
    @pytest.mark.asyncio
    @patch('app.services.notification_service.aiosmtplib.send')
    async def test_send_email_success(
        self, mock_send, notification_service, sample_email_channel, sample_incident
    ):
        """Test successful email sending."""
        mock_send.return_value = None
        
        result = await notification_service._send_email(
            channel=sample_email_channel,
            subject="Test Alert",
            content="Test alert content",
            recipients=["test@example.com"]
        )
        
        assert result["external_id"].startswith("email_")
        assert result["recipients"] == ["test@example.com"]
        mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.notification_service.httpx.AsyncClient')
    async def test_send_slack_success(
        self, mock_client, notification_service, sample_slack_channel
    ):
        """Test successful Slack notification sending."""
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.text = "ok"
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await notification_service._send_slack(
            channel=sample_slack_channel,
            subject="Test Alert",
            content="Test alert content"
        )
        
        assert result["external_id"].startswith("slack_")
        assert result["channel"] == "#alerts"
        assert result["webhook_response"] == "ok"
    
    @pytest.mark.asyncio
    @patch('app.services.notification_service.httpx.AsyncClient')
    async def test_send_teams_success(
        self, mock_client, notification_service
    ):
        """Test successful Teams notification sending."""
        # Create Teams channel
        teams_channel = NotificationChannel(
            id="teams_channel_1",
            name="Test Teams Channel",
            channel_type=ChannelType.TEAMS.value,
            config={"webhook_url": "https://outlook.office.com/test"},
            created_by="test_user"
        )
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.text = "1"
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await notification_service._send_teams(
            channel=teams_channel,
            subject="Test Alert",
            content="Test alert content",
            metadata={"severity": "high"}
        )
        
        assert result["external_id"].startswith("teams_")
        assert result["webhook_response"] == "1"
    
    @pytest.mark.asyncio
    @patch('app.services.notification_service.httpx.AsyncClient')
    async def test_send_webhook_success(
        self, mock_client, notification_service
    ):
        """Test successful webhook notification sending."""
        # Create webhook channel
        webhook_channel = NotificationChannel(
            id="webhook_channel_1",
            name="Test Webhook Channel",
            channel_type=ChannelType.WEBHOOK.value,
            config={
                "url": "https://api.example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            created_by="test_user"
        )
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "received"}'
        
        mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
        
        result = await notification_service._send_webhook(
            channel=webhook_channel,
            subject="Test Alert",
            content="Test alert content"
        )
        
        assert result["external_id"].startswith("webhook_")
        assert result["status_code"] == 200
        assert result["url"] == "https://api.example.com/webhook"
    
    @pytest.mark.asyncio
    async def test_send_sms_placeholder(self, notification_service):
        """Test SMS notification (placeholder implementation)."""
        # Create SMS channel
        sms_channel = NotificationChannel(
            id="sms_channel_1",
            name="Test SMS Channel",
            channel_type=ChannelType.SMS.value,
            config={
                "provider": "twilio",
                "from_number": "+1234567890",
                "default_recipients": ["+1987654321"]
            },
            created_by="test_user"
        )
        
        result = await notification_service._send_sms(
            channel=sms_channel,
            subject="Test Alert",
            content="Test alert content"
        )
        
        assert result["external_id"].startswith("sms_")
        assert result["provider"] == "twilio"
    
    @pytest.mark.asyncio
    async def test_test_notification_channel_success(
        self, notification_service, sample_email_channel
    ):
        """Test notification channel testing functionality."""
        with patch.object(notification_service, '_send_email') as mock_send:
            mock_send.return_value = {"external_id": "test_123", "status": "sent"}
            
            result = await notification_service.test_notification_channel(
                channel=sample_email_channel,
                test_recipient="test@example.com"
            )
            
            assert result["success"] is True
            assert "Test notification sent successfully" in result["message"]
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_notification_channel_failure(
        self, notification_service, sample_email_channel
    ):
        """Test notification channel testing with failure."""
        with patch.object(notification_service, '_send_email') as mock_send:
            mock_send.side_effect = Exception("SMTP server unavailable")
            
            result = await notification_service.test_notification_channel(
                channel=sample_email_channel,
                test_recipient="test@example.com"
            )
            
            assert result["success"] is False
            assert "Test notification failed" in result["message"]
            assert "SMTP server unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_default_template(self, notification_service):
        """Test getting default templates."""
        template = notification_service._get_default_template("alert_triggered", "email")
        
        assert "subject" in template
        assert "body" in template
        assert "Alert" in template["subject"] or "Alert" in template["body"]
    
    @pytest.mark.asyncio
    async def test_send_single_notification_success(
        self, notification_service, sample_email_channel, sample_incident
    ):
        """Test sending single notification successfully."""
        with patch.object(notification_service, '_send_email') as mock_send:
            mock_send.return_value = {"external_id": "email_123", "status": "sent"}
            
            notification = await notification_service._send_single_notification(
                channel=sample_email_channel,
                incident=sample_incident,
                subject="Test Alert",
                content="Test content",
                recipients=["test@example.com"]
            )
            
            assert notification.status == "sent"
            assert notification.incident_id == sample_incident.id
            assert notification.channel_id == sample_email_channel.id
            assert notification.recipient == "test@example.com"
            assert notification.external_id == "email_123"
    
    @pytest.mark.asyncio
    async def test_send_single_notification_failure(
        self, notification_service, sample_email_channel, sample_incident
    ):
        """Test sending single notification with failure."""
        with patch.object(notification_service, '_send_email') as mock_send:
            mock_send.side_effect = Exception("Network error")
            
            notification = await notification_service._send_single_notification(
                channel=sample_email_channel,
                incident=sample_incident,
                subject="Test Alert",
                content="Test content",
                recipients=["test@example.com"]
            )
            
            assert notification.status == "failed"
            assert "Network error" in notification.error_message


if __name__ == "__main__":
    pytest.main([__file__])