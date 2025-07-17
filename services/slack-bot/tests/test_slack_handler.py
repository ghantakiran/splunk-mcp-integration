"""
Tests for Slack handler functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.bot.slack_handler import SlackHandler
from app.models.slack_models import UserSession


class TestSlackHandler:
    """Test cases for SlackHandler."""
    
    @pytest.fixture
    async def slack_handler(self):
        """Create a SlackHandler instance for testing."""
        handler = SlackHandler()
        
        # Mock dependencies
        handler.client = AsyncMock()
        handler.splunk_service = AsyncMock()
        handler.user_service = AsyncMock()
        handler.session_service = AsyncMock()
        handler.message_formatter = MagicMock()
        handler.rate_limiter = AsyncMock()
        handler.bot_user_id = "B123456789"
        
        return handler
    
    @pytest.mark.asyncio
    async def test_handle_mention_success(self, slack_handler):
        """Test successful mention handling."""
        # Setup
        event = {
            "user": "U123456789",
            "channel": "C123456789",
            "text": "<@B123456789> show me errors from last hour",
            "ts": "1234567890.123"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        slack_handler.session_service.get_or_create_session.return_value = UserSession(
            id="session-123",
            user_id="U123456789",
            channel_id="C123456789"
        )
        slack_handler.user_service.get_user_context.return_value = {
            "user_id": "U123456789",
            "roles": ["user"],
            "accessible_indexes": ["*"]
        }
        slack_handler.splunk_service.process_query.return_value = {
            "success": True,
            "data": {
                "spl_query": "search error | head 10",
                "data": [{"count": 5}],
                "execution_time": 1.2
            }
        }
        slack_handler.message_formatter.format_query_response.return_value = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Results found*"}}
        ]
        
        # Execute
        await slack_handler.handle_mention(event)
        
        # Verify
        slack_handler.rate_limiter.check_rate_limit.assert_called_once_with("U123456789")
        slack_handler.session_service.get_or_create_session.assert_called_once()
        slack_handler.splunk_service.process_query.assert_called_once()
        slack_handler.client.chat_postMessage.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_mention_rate_limited(self, slack_handler):
        """Test mention handling when rate limited."""
        # Setup
        event = {
            "user": "U123456789",
            "channel": "C123456789",
            "text": "<@B123456789> show me errors",
            "ts": "1234567890.123"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = False
        
        # Execute
        await slack_handler.handle_mention(event)
        
        # Verify
        slack_handler.rate_limiter.check_rate_limit.assert_called_once_with("U123456789")
        slack_handler.client.chat_postMessage.assert_called_once()
        
        # Check that rate limit message was sent
        call_args = slack_handler.client.chat_postMessage.call_args
        assert "too quickly" in call_args[1]["text"]
    
    @pytest.mark.asyncio
    async def test_handle_mention_empty_query(self, slack_handler):
        """Test mention handling with empty query."""
        # Setup
        event = {
            "user": "U123456789",
            "channel": "C123456789",
            "text": "<@B123456789>",
            "ts": "1234567890.123"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        slack_handler.message_formatter.format_help_message.return_value = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Help*"}}
        ]
        
        # Execute
        await slack_handler.handle_mention(event)
        
        # Verify help message was sent
        slack_handler.message_formatter.format_help_message.assert_called_once()
        slack_handler.client.chat_postMessage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_direct_message(self, slack_handler):
        """Test direct message handling."""
        # Setup
        event = {
            "user": "U123456789",
            "channel": "D123456789",
            "text": "show me server status"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        slack_handler.session_service.get_or_create_session.return_value = UserSession(
            id="session-123",
            user_id="U123456789",
            channel_id="D123456789"
        )
        slack_handler.user_service.get_user_context.return_value = {
            "user_id": "U123456789",
            "roles": ["user"]
        }
        slack_handler.splunk_service.process_query.return_value = {
            "success": True,
            "data": {"status": "healthy"}
        }
        
        # Execute
        await slack_handler.handle_direct_message(event)
        
        # Verify
        slack_handler.splunk_service.process_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_direct_message_disabled(self, slack_handler):
        """Test direct message handling when disabled."""
        # Setup
        event = {
            "user": "U123456789",
            "channel": "D123456789",
            "text": "show me status"
        }
        
        with patch('app.bot.slack_handler.settings') as mock_settings:
            mock_settings.enable_direct_messages = False
            
            # Execute
            await slack_handler.handle_direct_message(event)
            
            # Verify no processing occurred
            slack_handler.splunk_service.process_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_slash_command_splunk(self, slack_handler):
        """Test /splunk slash command."""
        # Setup
        command_data = {
            "command": "/splunk",
            "text": "show me errors",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        
        # Execute
        result = await slack_handler.handle_slash_command(command_data)
        
        # Verify
        assert result["response_type"] == "in_channel"
        assert "Processing query" in result["text"]
        slack_handler.rate_limiter.check_rate_limit.assert_called_once_with("U123456789")
    
    @pytest.mark.asyncio
    async def test_handle_slash_command_help(self, slack_handler):
        """Test /splunk-help slash command."""
        # Setup
        command_data = {
            "command": "/splunk-help",
            "text": "",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        
        # Execute
        result = await slack_handler.handle_slash_command(command_data)
        
        # Verify
        assert result["response_type"] == "ephemeral"
        assert "Splunk MCP Bot Help" in result["text"]
    
    @pytest.mark.asyncio
    async def test_handle_slash_command_status(self, slack_handler):
        """Test /splunk-status slash command."""
        # Setup
        command_data = {
            "command": "/splunk-status",
            "text": "",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = True
        slack_handler.splunk_service.get_system_status.return_value = {
            "status": "healthy",
            "services": {"api_gateway": {"status": "healthy"}}
        }
        slack_handler.user_service.get_user_info.return_value = {
            "access_level": "standard",
            "accessible_indexes": ["*"]
        }
        
        # Execute
        result = await slack_handler.handle_slash_command(command_data)
        
        # Verify
        assert result["response_type"] == "ephemeral"
        assert "healthy" in result["text"]
    
    @pytest.mark.asyncio
    async def test_handle_slash_command_rate_limited(self, slack_handler):
        """Test slash command when rate limited."""
        # Setup
        command_data = {
            "command": "/splunk",
            "text": "show me data",
            "user_id": "U123456789",
            "channel_id": "C123456789"
        }
        
        slack_handler.rate_limiter.check_rate_limit.return_value = False
        
        # Execute
        result = await slack_handler.handle_slash_command(command_data)
        
        # Verify
        assert "Rate limit exceeded" in result["text"]
    
    @pytest.mark.asyncio
    async def test_clean_mention_text(self, slack_handler):
        """Test mention text cleaning."""
        # Test cases
        test_cases = [
            ("<@B123456789> show me errors", "show me errors"),
            ("<@B123456789>", ""),
            ("show me <@B123456789> errors", "show me  errors"),
            ("<@U987654321> show me errors", "show me errors"),  # Other user mention
            ("no mentions here", "no mentions here")
        ]
        
        for input_text, expected in test_cases:
            result = slack_handler._clean_mention_text(input_text)
            assert result.strip() == expected.strip()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, slack_handler):
        """Test health check when healthy."""
        slack_handler.client.auth_test.return_value = {"ok": True}
        
        result = await slack_handler.health_check()
        
        assert result is True
        slack_handler.client.auth_test.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, slack_handler):
        """Test health check when unhealthy."""
        slack_handler.client.auth_test.side_effect = Exception("Connection failed")
        
        result = await slack_handler.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_query_help_command(self, slack_handler):
        """Test processing help command."""
        slack_handler.session_service.get_or_create_session.return_value = UserSession(
            id="session-123",
            user_id="U123456789",
            channel_id="C123456789"
        )
        slack_handler.message_formatter.format_help_message.return_value = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Help*"}}
        ]
        
        await slack_handler._process_query("U123456789", "C123456789", "help")
        
        slack_handler.message_formatter.format_help_message.assert_called_once()
        slack_handler.client.chat_postMessage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_status_command(self, slack_handler):
        """Test processing status command."""
        slack_handler.session_service.get_or_create_session.return_value = UserSession(
            id="session-123",
            user_id="U123456789",
            channel_id="C123456789"
        )
        slack_handler.splunk_service.get_system_status.return_value = {
            "status": "healthy"
        }
        slack_handler.user_service.get_user_info.return_value = {
            "access_level": "standard"
        }
        slack_handler.message_formatter.format_status_message.return_value = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Status*"}}
        ]
        
        await slack_handler._process_query("U123456789", "C123456789", "status")
        
        slack_handler.splunk_service.get_system_status.assert_called_once()
        slack_handler.client.chat_postMessage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, slack_handler):
        """Test query processing error handling."""
        slack_handler.session_service.get_or_create_session.side_effect = Exception("DB error")
        slack_handler.message_formatter.format_error_message.return_value = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Error*"}}
        ]
        
        await slack_handler._process_query("U123456789", "C123456789", "show me data")
        
        # Should send error message
        slack_handler.client.chat_postMessage.assert_called()
        slack_handler.message_formatter.format_error_message.assert_called_once()