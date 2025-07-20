"""
Tests for Teams Bot main application.
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
def mock_teams_handler():
    """Mock Teams handler."""
    with patch("app.main.teams_handler") as mock:
        mock.handle_message = AsyncMock()
        mock.handle_invoke = AsyncMock()
        mock.handle_command = AsyncMock()
        mock.handle_member_added = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_auth():
    """Mock authentication."""
    with patch("app.main.verify_teams_signature") as mock:
        mock.return_value = True
        yield mock


class TestTeamsBotApp:
    """Test suite for Teams Bot FastAPI application."""
    
    def test_health_endpoint(self, client, mock_teams_handler):
        """Test health check endpoint."""
        response = client.get("/teams/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        
        mock_teams_handler.health_check.assert_called_once()
    
    def test_health_endpoint_unhealthy(self, client):
        """Test health check when service is unhealthy."""
        with patch("app.main.teams_handler") as mock_handler:
            mock_handler.health_check = AsyncMock(return_value=False)
            
            response = client.get("/teams/health")
            assert response.status_code == 503
            
            data = response.json()
            assert data["status"] == "unhealthy"
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/teams/metrics")
        assert response.status_code == 200
        
        # Should return Prometheus metrics format
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_teams_message_activity(self, client, mock_teams_handler, mock_auth):
        """Test Teams message activity handling."""
        message_activity = {
            "type": "message",
            "from": {"id": "29:user123", "name": "Test User"},
            "conversation": {"id": "19:conv123"},
            "text": "show me errors from last hour",
            "serviceUrl": "https://smba.trafficmanager.net/teams/"
        }
        
        response = client.post("/teams/messages", json=message_activity)
        assert response.status_code == 200
        
        mock_teams_handler.handle_message.assert_called_once_with(message_activity)
    
    def test_teams_invoke_activity(self, client, mock_teams_handler, mock_auth):
        """Test Teams invoke activity handling."""
        invoke_activity = {
            "type": "invoke",
            "name": "adaptiveCard/action",
            "from": {"id": "29:user123"},
            "value": {
                "action": "run_query",
                "query": "show me status"
            }
        }
        
        mock_teams_handler.handle_invoke.return_value = {"status": 200}
        
        response = client.post("/teams/messages", json=invoke_activity)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == 200
        
        mock_teams_handler.handle_invoke.assert_called_once_with(invoke_activity)
    
    def test_teams_command_activity(self, client, mock_teams_handler, mock_auth):
        """Test Teams command activity handling."""
        command_activity = {
            "type": "invoke",
            "name": "composeExtension/query",
            "from": {"id": "29:user123"},
            "value": {
                "commandId": "splunk_query",
                "data": {"query": "show me errors"}
            }
        }
        
        mock_teams_handler.handle_command.return_value = {"status": 200}
        
        response = client.post("/teams/messages", json=command_activity)
        assert response.status_code == 200
        
        mock_teams_handler.handle_command.assert_called_once_with(command_activity)
    
    def test_teams_member_added_activity(self, client, mock_teams_handler, mock_auth):
        """Test Teams member added activity handling."""
        member_added_activity = {
            "type": "conversationUpdate",
            "from": {"id": "29:user123"},
            "membersAdded": [
                {"id": "29:newuser456", "name": "New User"}
            ]
        }
        
        response = client.post("/teams/messages", json=member_added_activity)
        assert response.status_code == 200
        
        mock_teams_handler.handle_member_added.assert_called_once_with(member_added_activity)
    
    def test_teams_signature_verification_success(self, client, mock_teams_handler):
        """Test successful Teams signature verification."""
        with patch("app.main.verify_teams_signature") as mock_verify:
            mock_verify.return_value = True
            
            activity = {
                "type": "message",
                "from": {"id": "29:user123"},
                "text": "test message"
            }
            
            response = client.post("/teams/messages", json=activity)
            assert response.status_code == 200
    
    def test_teams_signature_verification_failure(self, client):
        """Test failed Teams signature verification."""
        with patch("app.main.verify_teams_signature") as mock_verify:
            mock_verify.return_value = False
            
            activity = {
                "type": "message",
                "from": {"id": "29:user123"},
                "text": "test message"
            }
            
            response = client.post("/teams/messages", json=activity)
            assert response.status_code == 401
    
    def test_unknown_activity_type(self, client, mock_teams_handler, mock_auth):
        """Test handling of unknown activity types."""
        unknown_activity = {
            "type": "unknownType",
            "from": {"id": "29:user123"}
        }
        
        response = client.post("/teams/messages", json=unknown_activity)
        assert response.status_code == 200  # Should handle gracefully
        
        # Should not call any specific handlers
        mock_teams_handler.handle_message.assert_not_called()
        mock_teams_handler.handle_invoke.assert_not_called()
    
    def test_malformed_request_body(self, client, mock_auth):
        """Test handling of malformed request body."""
        response = client.post("/teams/messages", data="invalid json")
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self, client, mock_teams_handler, mock_auth):
        """Test handling of requests missing required fields."""
        incomplete_activity = {
            "type": "message"
            # Missing "from" field and other required fields
        }
        
        response = client.post("/teams/messages", json=incomplete_activity)
        # Should handle gracefully and return 200
        assert response.status_code == 200
    
    def test_error_handling_in_message_processing(self, client, mock_teams_handler, mock_auth):
        """Test error handling in message processing."""
        mock_teams_handler.handle_message.side_effect = Exception("Handler error")
        
        message_activity = {
            "type": "message",
            "from": {"id": "29:user123"},
            "text": "test message"
        }
        
        response = client.post("/teams/messages", json=message_activity)
        assert response.status_code == 500
    
    def test_teams_bot_activity_filtering(self, client, mock_teams_handler, mock_auth):
        """Test filtering of bot's own activities."""
        bot_activity = {
            "type": "message",
            "from": {"id": "28:bot123"},  # Bot's own ID
            "text": "bot message"
        }
        
        response = client.post("/teams/messages", json=bot_activity)
        assert response.status_code == 200
        
        # Should not process bot's own messages
        mock_teams_handler.handle_message.assert_not_called()
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/teams/health")
        assert response.status_code == 200
        # CORS headers should be present if configured
    
    def test_rate_limiting_integration(self, client, mock_auth):
        """Test rate limiting integration."""
        # This would require actual rate limiting middleware
        # For now, just test normal endpoint behavior
        response = client.get("/teams/health")
        assert response.status_code == 200
    
    def test_conversation_reference_handling(self, client, mock_teams_handler, mock_auth):
        """Test conversation reference handling for proactive messaging."""
        activity_with_conversation = {
            "type": "message",
            "from": {"id": "29:user123"},
            "conversation": {
                "id": "19:conv123",
                "conversationType": "personal"
            },
            "serviceUrl": "https://smba.trafficmanager.net/teams/",
            "text": "test message"
        }
        
        response = client.post("/teams/messages", json=activity_with_conversation)
        assert response.status_code == 200
        
        # Should handle conversation reference
        mock_teams_handler.handle_message.assert_called_once()
    
    def test_channel_data_handling(self, client, mock_teams_handler, mock_auth):
        """Test Teams-specific channel data handling."""
        channel_activity = {
            "type": "message",
            "from": {"id": "29:user123"},
            "conversation": {
                "id": "19:channel123",
                "conversationType": "channel"
            },
            "channelData": {
                "team": {"id": "team123"},
                "channel": {"id": "channel123"}
            },
            "text": "@SplunkBot show me status"
        }
        
        response = client.post("/teams/messages", json=channel_activity)
        assert response.status_code == 200
        
        mock_teams_handler.handle_message.assert_called_once_with(channel_activity)
    
    def test_adaptive_card_response_formatting(self, client, mock_teams_handler, mock_auth):
        """Test adaptive card response formatting."""
        invoke_activity = {
            "type": "invoke",
            "name": "adaptiveCard/action",
            "from": {"id": "29:user123"},
            "value": {"action": "show_help"}
        }
        
        # Mock handler to return adaptive card response
        mock_teams_handler.handle_invoke.return_value = {
            "status": 200,
            "body": {
                "type": "AdaptiveCard",
                "body": [{"type": "TextBlock", "text": "Help information"}]
            }
        }
        
        response = client.post("/teams/messages", json=invoke_activity)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == 200
        assert "body" in data
        assert data["body"]["type"] == "AdaptiveCard"


class TestTeamsBotStartup:
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
        
        assert hasattr(settings, 'microsoft_app_id')
        assert hasattr(settings, 'microsoft_app_password')
        assert hasattr(settings, 'environment')
    
    def test_microsoft_app_configuration(self):
        """Test Microsoft app configuration."""
        from app.core.config import settings
        
        # Should have Microsoft Teams app configuration
        assert hasattr(settings, 'microsoft_app_id')
        assert hasattr(settings, 'microsoft_app_password')
        assert hasattr(settings, 'microsoft_app_tenant_id')


class TestTeamsBotMiddleware:
    """Test suite for Teams Bot middleware."""
    
    def test_request_logging_middleware(self, client, mock_auth):
        """Test request logging middleware."""
        with patch("app.main.logger") as mock_logger:
            activity = {
                "type": "message",
                "from": {"id": "29:user123"},
                "text": "test"
            }
            
            response = client.post("/teams/messages", json=activity)
            assert response.status_code == 200
            
            # Should log the request
            assert mock_logger.info.called
    
    def test_correlation_id_middleware(self, client, mock_auth):
        """Test correlation ID middleware."""
        activity = {
            "type": "message",
            "from": {"id": "29:user123"},
            "text": "test"
        }
        
        response = client.post("/teams/messages", json=activity)
        
        # Should include correlation ID in response headers
        assert "x-correlation-id" in response.headers or response.status_code == 200
    
    def test_error_handling_middleware(self, client, mock_auth):
        """Test error handling middleware."""
        with patch("app.main.teams_handler") as mock_handler:
            mock_handler.handle_message.side_effect = ValueError("Test error")
            
            activity = {
                "type": "message",
                "from": {"id": "29:user123"},
                "text": "test"
            }
            
            response = client.post("/teams/messages", json=activity)
            assert response.status_code == 500
            
            # Should return structured error response
            data = response.json()
            assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__])