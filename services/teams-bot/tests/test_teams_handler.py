"""
Tests for Microsoft Teams handler functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.bot.teams_handler import TeamsHandler
from app.models.teams_models import TeamsSession


class TestTeamsHandler:
    """Test cases for TeamsHandler."""
    
    @pytest.fixture
    async def teams_handler(self):
        """Create a TeamsHandler instance for testing."""
        handler = TeamsHandler()
        
        # Mock dependencies
        handler.splunk_service = AsyncMock()
        handler.user_service = AsyncMock()
        handler.session_service = AsyncMock()
        handler.message_formatter = MagicMock()
        handler.rate_limiter = AsyncMock()
        handler.card_builder = MagicMock()
        handler.bot_app_id = "28:bot123"
        
        return handler
    
    @pytest.mark.asyncio
    async def test_handle_message_success(self, teams_handler, mock_teams_activity):
        """Test successful message handling."""
        # Setup
        teams_handler.rate_limiter.check_rate_limit.return_value = True
        teams_handler.session_service.get_or_create_session.return_value = TeamsSession(
            id="session-123",
            user_id="29:user123",
            conversation_id="19:conv123"
        )
        teams_handler.user_service.get_user_context.return_value = {
            "user_id": "29:user123",
            "roles": ["user"],
            "accessible_indexes": ["*"]
        }
        teams_handler.splunk_service.process_query.return_value = {
            "success": True,
            "data": {
                "spl_query": "search error | head 10",
                "data": [{"count": 5}],
                "execution_time": 1.2
            }
        }
        teams_handler.message_formatter.format_query_response.return_value = {
            "type": "message",
            "text": "Results found"
        }
        teams_handler._send_activity = AsyncMock()
        
        # Execute
        await teams_handler.handle_message(mock_teams_activity)
        
        # Verify
        teams_handler.rate_limiter.check_rate_limit.assert_called_once_with("29:user123")
        teams_handler.session_service.get_or_create_session.assert_called_once()
        teams_handler.splunk_service.process_query.assert_called_once()
        teams_handler._send_activity.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_message_rate_limited(self, teams_handler, mock_teams_activity):
        """Test message handling when rate limited."""
        # Setup
        teams_handler.rate_limiter.check_rate_limit.return_value = False
        teams_handler._send_rate_limit_message = AsyncMock()
        
        # Execute
        await teams_handler.handle_message(mock_teams_activity)
        
        # Verify
        teams_handler.rate_limiter.check_rate_limit.assert_called_once_with("29:user123")
        teams_handler._send_rate_limit_message.assert_called_once()
        teams_handler.splunk_service.process_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_message_empty_text(self, teams_handler, mock_teams_activity):
        """Test message handling with empty text."""
        # Setup
        mock_teams_activity["text"] = ""
        
        # Execute
        await teams_handler.handle_message(mock_teams_activity)
        
        # Verify - should return early and not process
        teams_handler.rate_limiter.check_rate_limit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_mention_in_channel(self, teams_handler, mock_teams_mention_activity):
        """Test handling mention in channel."""
        # Setup
        teams_handler.rate_limiter.check_rate_limit.return_value = True
        teams_handler._clean_mention_text = MagicMock(return_value="show me errors")
        teams_handler._process_query = AsyncMock()
        
        # Execute
        await teams_handler.handle_message(mock_teams_mention_activity)
        
        # Verify
        teams_handler._process_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_invoke_adaptive_card_action(self, teams_handler, mock_teams_invoke_activity):
        """Test handling adaptive card action."""
        # Setup
        teams_handler._handle_adaptive_card_action = AsyncMock(return_value={"status": 200})
        
        # Execute
        result = await teams_handler.handle_invoke(mock_teams_invoke_activity)
        
        # Verify
        assert result["status"] == 200
        teams_handler._handle_adaptive_card_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_invoke_unknown_name(self, teams_handler):
        """Test handling unknown invoke name."""
        # Setup
        activity = {
            "name": "unknown/invoke",
            "value": {}
        }
        
        # Execute
        result = await teams_handler.handle_invoke(activity)
        
        # Verify
        assert result["status"] == 200
    
    @pytest.mark.asyncio
    async def test_handle_command_splunk_query(self, teams_handler):
        """Test handling Splunk query command."""
        # Setup
        activity = {
            "value": {
                "commandId": "splunk_query",
                "data": {"query": "show me errors"}
            }
        }
        teams_handler._process_query = AsyncMock()
        
        # Execute
        result = await teams_handler.handle_command(activity)
        
        # Verify
        assert result["status"] == 200
        teams_handler._process_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_command_help(self, teams_handler):
        """Test handling help command."""
        # Setup
        activity = {
            "value": {"commandId": "splunk_help"}
        }
        teams_handler._send_help_message = AsyncMock()
        
        # Execute
        result = await teams_handler.handle_command(activity)
        
        # Verify
        assert result["status"] == 200
        teams_handler._send_help_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_member_added(self, teams_handler):
        """Test handling member added event."""
        # Setup
        activity = {
            "membersAdded": [
                {"id": "29:newuser123", "name": "New User"}
            ]
        }
        teams_handler._send_welcome_message = AsyncMock()
        
        # Execute
        await teams_handler.handle_member_added(activity)
        
        # Verify
        teams_handler._send_welcome_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_member_added_bot_itself(self, teams_handler):
        """Test handling member added when bot is added."""
        # Setup
        activity = {
            "membersAdded": [
                {"id": "28:bot123", "name": "Bot"}  # Bot's own ID
            ]
        }
        teams_handler._send_welcome_message = AsyncMock()
        
        # Execute
        await teams_handler.handle_member_added(activity)
        
        # Verify - should not send welcome message to itself
        teams_handler._send_welcome_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_query_help_command(self, teams_handler):
        """Test processing help command."""
        # Setup
        activity = {"conversation": {"id": "19:conv123"}}
        teams_handler.session_service.get_or_create_session.return_value = TeamsSession(
            id="session-123",
            user_id="29:user123",
            conversation_id="19:conv123"
        )
        teams_handler._send_help_message = AsyncMock()
        
        # Execute
        await teams_handler._process_query(activity, "help")
        
        # Verify
        teams_handler._send_help_message.assert_called_once()
        teams_handler.splunk_service.process_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_query_status_command(self, teams_handler):
        """Test processing status command."""
        # Setup
        activity = {"conversation": {"id": "19:conv123"}}
        teams_handler.session_service.get_or_create_session.return_value = TeamsSession(
            id="session-123",
            user_id="29:user123",
            conversation_id="19:conv123"
        )
        teams_handler._send_status_message = AsyncMock()
        
        # Execute
        await teams_handler._process_query(activity, "status")
        
        # Verify
        teams_handler._send_status_message.assert_called_once()
        teams_handler.splunk_service.process_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_query_splunk_query(self, teams_handler):
        """Test processing actual Splunk query."""
        # Setup
        activity = {
            "from": {"id": "29:user123"},
            "conversation": {"id": "19:conv123"}
        }
        teams_handler.session_service.get_or_create_session.return_value = TeamsSession(
            id="session-123",
            user_id="29:user123",
            conversation_id="19:conv123"
        )
        teams_handler.user_service.get_user_context.return_value = {
            "user_id": "29:user123",
            "roles": ["user"]
        }
        teams_handler.splunk_service.process_query.return_value = {
            "success": True,
            "data": {"spl_query": "search error"}
        }
        teams_handler._send_typing_indicator = AsyncMock()
        teams_handler._send_initial_response = AsyncMock()
        teams_handler._send_query_results = AsyncMock()
        
        # Execute
        await teams_handler._process_query(activity, "show me errors")
        
        # Verify
        teams_handler.splunk_service.process_query.assert_called_once()
        teams_handler._send_query_results.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, teams_handler):
        """Test query processing error handling."""
        # Setup
        activity = {
            "from": {"id": "29:user123"},
            "conversation": {"id": "19:conv123"}
        }
        teams_handler.session_service.get_or_create_session.side_effect = Exception("DB error")
        teams_handler._send_error_message = AsyncMock()
        
        # Execute
        await teams_handler._process_query(activity, "show me data")
        
        # Verify
        teams_handler._send_error_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_bot_mentioned_true(self, teams_handler):
        """Test bot mention detection - positive case."""
        # Setup
        activity = {
            "entities": [
                {
                    "type": "mention",
                    "mentioned": {"id": "28:bot123"}
                }
            ]
        }
        
        # Execute
        result = teams_handler._is_bot_mentioned(activity)
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_bot_mentioned_false(self, teams_handler):
        """Test bot mention detection - negative case."""
        # Setup
        activity = {
            "entities": [
                {
                    "type": "mention",
                    "mentioned": {"id": "29:otheruser"}
                }
            ]
        }
        
        # Execute
        result = teams_handler._is_bot_mentioned(activity)
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clean_mention_text(self, teams_handler):
        """Test mention text cleaning."""
        # Setup
        activity = {
            "entities": [
                {
                    "type": "mention",
                    "text": "<at>Splunk MCP Assistant</at>",
                    "mentioned": {"id": "28:bot123"}
                }
            ]
        }
        
        # Execute
        result = teams_handler._clean_mention_text(
            "<at>Splunk MCP Assistant</at> show me errors",
            activity
        )
        
        # Verify
        assert result.strip() == "show me errors"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, teams_handler):
        """Test health check when healthy."""
        # Execute
        result = await teams_handler.health_check()
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_run_query(self, teams_handler):
        """Test handling adaptive card run query action."""
        # Setup
        activity = {
            "value": {
                "action": "run_query",
                "query": "show me status"
            }
        }
        teams_handler._process_query = AsyncMock()
        
        # Execute
        result = await teams_handler._handle_adaptive_card_action(activity)
        
        # Verify
        assert result["status"] == 200
        teams_handler._process_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_show_help(self, teams_handler):
        """Test handling adaptive card show help action."""
        # Setup
        activity = {
            "value": {"action": "show_help"}
        }
        teams_handler._send_help_message = AsyncMock()
        
        # Execute
        result = await teams_handler._handle_adaptive_card_action(activity)
        
        # Verify
        assert result["status"] == 200
        teams_handler._send_help_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_query_results_with_visualizations(self, teams_handler):
        """Test sending query results with visualizations."""
        # Setup
        activity = {"conversation": {"id": "19:conv123"}}
        response = {
            "data": {
                "spl_query": "search error",
                "data": [{"count": 5}],
                "visualizations": [
                    {"image_url": "http://example.com/chart.png", "title": "Error Chart"}
                ]
            }
        }
        teams_handler.message_formatter.format_query_response.return_value = {
            "type": "message",
            "text": "Results"
        }
        teams_handler._send_activity = AsyncMock()
        teams_handler._send_visualizations = AsyncMock()
        
        # Execute
        await teams_handler._send_query_results(activity, response)
        
        # Verify
        teams_handler._send_activity.assert_called()
        teams_handler._send_visualizations.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_visualizations(self, teams_handler):
        """Test sending visualizations."""
        # Setup
        activity = {"conversation": {"id": "19:conv123"}}
        visualizations = [
            {
                "image_url": "http://example.com/chart.png",
                "title": "Test Chart"
            }
        ]
        teams_handler.card_builder.create_visualization_card.return_value = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {"type": "AdaptiveCard"}
        }
        teams_handler._send_activity = AsyncMock()
        
        # Execute
        await teams_handler._send_visualizations(activity, visualizations)
        
        # Verify
        teams_handler.card_builder.create_visualization_card.assert_called_once()
        teams_handler._send_activity.assert_called_once()