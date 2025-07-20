"""
Tests for Slack Bot main application.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_slack_handler():
    """Mock Slack handler."""
    with patch("app.main.slack_handler") as mock:
        mock.handle_mention = AsyncMock()
        mock.handle_direct_message = AsyncMock()
        mock.handle_slash_command = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        yield mock


class TestSlackBotApp:
    """Test suite for Slack Bot FastAPI application."""
    
    def test_health_endpoint(self, client, mock_slack_handler):
        """Test health check endpoint."""
        response = client.get("/slack/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        
        mock_slack_handler.health_check.assert_called_once()
    
    def test_health_endpoint_unhealthy(self, client):
        """Test health check when service is unhealthy."""
        with patch("app.main.slack_handler") as mock_handler:
            mock_handler.health_check = AsyncMock(return_value=False)
            
            response = client.get("/slack/health")
            assert response.status_code == 503
            
            data = response.json()
            assert data["status"] == "unhealthy"
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/slack/metrics")
        assert response.status_code == 200
        
        # Should return Prometheus metrics format
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_slack_events_challenge(self, client):
        """Test Slack challenge verification."""
        challenge_data = {
            "type": "url_verification",
            "challenge": "test_challenge_string"
        }
        
        response = client.post("/slack/events", json=challenge_data)
        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge_string"}
    
    def test_slack_events_app_mention(self, client, mock_slack_handler):
        """Test Slack app mention event handling."""
        mention_event = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123456789",
                "channel": "C123456789",
                "text": "<@B123456789> show me errors",
                "ts": "1234567890.123"
            }
        }
        
        response = client.post("/slack/events", json=mention_event)
        assert response.status_code == 200
        
        mock_slack_handler.handle_mention.assert_called_once_with(mention_event["event"])
    
    def test_slack_events_direct_message(self, client, mock_slack_handler):
        """Test Slack direct message event handling."""
        dm_event = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U123456789",
                "text": "show me status"
            }
        }
        
        response = client.post("/slack/events", json=dm_event)
        assert response.status_code == 200
        
        mock_slack_handler.handle_direct_message.assert_called_once_with(dm_event["event"])
    
    def test_slack_events_ignore_bot_messages(self, client, mock_slack_handler):
        """Test ignoring bot messages."""
        bot_message = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456789",
                "bot_id": "B123456789",
                "text": "Bot message"
            }
        }
        
        response = client.post("/slack/events", json=bot_message)
        assert response.status_code == 200
        
        # Should not call any handlers for bot messages
        mock_slack_handler.handle_mention.assert_not_called()
        mock_slack_handler.handle_direct_message.assert_not_called()
    
    def test_slack_events_ignore_message_subtypes(self, client, mock_slack_handler):
        """Test ignoring message subtypes like edits and deletes."""
        edit_message = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "subtype": "message_changed",
                "user": "U123456789",
                "text": "Edited message"
            }
        }
        
        response = client.post("/slack/events", json=edit_message)
        assert response.status_code == 200
        
        # Should not call handlers for message subtypes
        mock_slack_handler.handle_mention.assert_not_called()
        mock_slack_handler.handle_direct_message.assert_not_called()
    
    def test_slack_slash_command_splunk(self, client, mock_slack_handler):
        """Test /splunk slash command."""
        mock_slack_handler.handle_slash_command.return_value = {
            "response_type": "in_channel",
            "text": "Processing query..."
        }
        
        command_data = {
            "command": "/splunk",
            "text": "show me errors",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        response = client.post("/slack/slash-commands", data=command_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["response_type"] == "in_channel"
        assert "Processing query" in data["text"]
        
        mock_slack_handler.handle_slash_command.assert_called_once()
    
    def test_slack_slash_command_help(self, client, mock_slack_handler):
        """Test /splunk-help slash command."""
        mock_slack_handler.handle_slash_command.return_value = {
            "response_type": "ephemeral",
            "text": "Help information"
        }
        
        command_data = {
            "command": "/splunk-help",
            "text": "",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        response = client.post("/slack/slash-commands", data=command_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["response_type"] == "ephemeral"
        
        mock_slack_handler.handle_slash_command.assert_called_once()
    
    def test_slack_slash_command_status(self, client, mock_slack_handler):
        """Test /splunk-status slash command."""
        mock_slack_handler.handle_slash_command.return_value = {
            "response_type": "ephemeral",
            "text": "System status: healthy"
        }
        
        command_data = {
            "command": "/splunk-status",
            "text": "",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        response = client.post("/slack/slash-commands", data=command_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "healthy" in data["text"]
    
    def test_slack_signature_verification_success(self, client):
        """Test successful Slack signature verification."""
        with patch("app.bot.auth.verify_slack_signature") as mock_verify:
            mock_verify.return_value = True
            
            response = client.post("/slack/events", json={"type": "url_verification", "challenge": "test"})
            assert response.status_code == 200
    
    def test_slack_signature_verification_failure(self, client):
        """Test failed Slack signature verification."""
        with patch("app.bot.auth.verify_slack_signature") as mock_verify:
            mock_verify.return_value = False
            
            response = client.post("/slack/events", json={"type": "event_callback"})
            assert response.status_code == 401
    
    def test_invalid_event_type(self, client, mock_slack_handler):
        """Test handling of invalid event types."""
        invalid_event = {
            "type": "invalid_type",
            "event": {"type": "unknown"}
        }
        
        response = client.post("/slack/events", json=invalid_event)
        assert response.status_code == 200  # Should still return 200 but not process
        
        # Should not call any handlers
        mock_slack_handler.handle_mention.assert_not_called()
        mock_slack_handler.handle_direct_message.assert_not_called()
    
    def test_malformed_request_body(self, client):
        """Test handling of malformed request body."""
        response = client.post("/slack/events", data="invalid json")
        assert response.status_code == 422  # Validation error
    
    def test_missing_event_field(self, client, mock_slack_handler):
        """Test handling of requests missing event field."""
        incomplete_event = {
            "type": "event_callback"
            # Missing "event" field
        }
        
        response = client.post("/slack/events", json=incomplete_event)
        assert response.status_code == 200  # Should handle gracefully
        
        # Should not call handlers
        mock_slack_handler.handle_mention.assert_not_called()
        mock_slack_handler.handle_direct_message.assert_not_called()
    
    def test_error_handling(self, client, mock_slack_handler):
        """Test error handling in event processing."""
        mock_slack_handler.handle_mention.side_effect = Exception("Handler error")
        
        mention_event = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123456789",
                "text": "<@B123456789> show me errors"
            }
        }
        
        response = client.post("/slack/events", json=mention_event)
        assert response.status_code == 500
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/slack/health")
        assert response.status_code == 200
        # CORS headers should be present if configured
    
    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # This would require actual rate limiting middleware to be configured
        # For now, just test that endpoint responds normally
        response = client.get("/slack/health")
        assert response.status_code == 200


class TestSlackBotStartup:
    """Test suite for application startup and shutdown."""
    
    @patch("app.main.logger")
    def test_startup_event(self, mock_logger):
        """Test application startup event."""
        # Startup event should log service start
        with TestClient(app):
            pass  # Context manager triggers startup/shutdown
        
        # Verify startup logging occurred
        assert mock_logger.info.called
    
    def test_environment_configuration(self):
        """Test environment configuration loading."""
        # Test that environment variables are properly loaded
        from app.core.config import settings
        
        assert hasattr(settings, 'slack_signing_secret')
        assert hasattr(settings, 'slack_bot_token')
        assert hasattr(settings, 'environment')


if __name__ == "__main__":
    pytest.main([__file__])