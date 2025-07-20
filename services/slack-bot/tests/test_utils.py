"""
Tests for Slack Bot utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

from app.utils.message_formatter import MessageFormatter, SlackBlockBuilder
from app.utils.rate_limiter import RateLimiter


class TestMessageFormatter:
    """Test suite for MessageFormatter."""
    
    @pytest.fixture
    def message_formatter(self):
        """Create MessageFormatter instance."""
        return MessageFormatter()
    
    def test_format_query_response_simple(self, message_formatter):
        """Test formatting simple query response."""
        response = {
            "success": True,
            "data": {
                "spl_query": "search index=main error",
                "data": [{"count": 5}],
                "execution_time": 1.2
            }
        }
        
        result = message_formatter.format_query_response(response)
        
        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain query, results, and execution time
        formatted_text = json.dumps(result)
        assert "search index=main error" in formatted_text
        assert "1.2" in formatted_text
    
    def test_format_query_response_with_visualization(self, message_formatter):
        """Test formatting query response with visualization."""
        response = {
            "success": True,
            "data": {
                "spl_query": "search index=main | stats count",
                "data": [{"count": 10}],
                "visualizations": [
                    {
                        "image_url": "http://example.com/chart.png",
                        "title": "Event Count"
                    }
                ]
            }
        }
        
        result = message_formatter.format_query_response(response)
        
        formatted_text = json.dumps(result)
        assert "http://example.com/chart.png" in formatted_text
        assert "Event Count" in formatted_text
    
    def test_format_query_response_error(self, message_formatter):
        """Test formatting error response."""
        response = {
            "success": False,
            "error": "Invalid SPL query syntax"
        }
        
        result = message_formatter.format_query_response(response)
        
        formatted_text = json.dumps(result)
        assert "error" in formatted_text.lower()
        assert "Invalid SPL query syntax" in formatted_text
    
    def test_format_help_message(self, message_formatter):
        """Test formatting help message."""
        result = message_formatter.format_help_message()
        
        assert isinstance(result, list)
        formatted_text = json.dumps(result)
        assert "help" in formatted_text.lower()
        assert "splunk" in formatted_text.lower()
    
    def test_format_status_message(self, message_formatter):
        """Test formatting status message."""
        status_data = {
            "status": "healthy",
            "services": {
                "api_gateway": {"status": "healthy", "response_time": 50}
            }
        }
        user_info = {
            "access_level": "standard",
            "query_count": 25
        }
        
        result = message_formatter.format_status_message(status_data, user_info)
        
        formatted_text = json.dumps(result)
        assert "healthy" in formatted_text
        assert "standard" in formatted_text
        assert "25" in formatted_text
    
    def test_format_error_message(self, message_formatter):
        """Test formatting error message."""
        error = "Connection timeout"
        
        result = message_formatter.format_error_message(error)
        
        formatted_text = json.dumps(result)
        assert "error" in formatted_text.lower()
        assert "Connection timeout" in formatted_text
    
    def test_format_table_data(self, message_formatter):
        """Test formatting table data."""
        data = [
            {"host": "server1", "count": 5},
            {"host": "server2", "count": 3},
            {"host": "server3", "count": 8}
        ]
        
        result = message_formatter._format_table_data(data, max_rows=10)
        
        assert "server1" in result
        assert "server2" in result
        assert "5" in result
        assert "3" in result
    
    def test_format_table_data_truncated(self, message_formatter):
        """Test formatting table data with truncation."""
        data = [{"id": i, "value": f"item{i}"} for i in range(20)]
        
        result = message_formatter._format_table_data(data, max_rows=5)
        
        assert "item0" in result
        assert "item4" in result
        assert "15 more rows" in result or "truncated" in result.lower()
    
    def test_truncate_text(self, message_formatter):
        """Test text truncation."""
        long_text = "x" * 5000
        
        result = message_formatter._truncate_text(long_text, max_length=1000)
        
        assert len(result) <= 1000
        assert "..." in result or "truncated" in result.lower()
    
    def test_escape_slack_text(self, message_formatter):
        """Test Slack text escaping."""
        text_with_special_chars = "Text with <special> &chars& *bold*"
        
        result = message_formatter._escape_slack_text(text_with_special_chars)
        
        # Should escape Slack special characters
        assert "&lt;" in result or "<" not in result
        assert "&amp;" in result or "&chars&" not in result


class TestSlackBlockBuilder:
    """Test suite for SlackBlockBuilder."""
    
    @pytest.fixture
    def block_builder(self):
        """Create SlackBlockBuilder instance."""
        return SlackBlockBuilder()
    
    def test_create_section_block(self, block_builder):
        """Test creating section block."""
        text = "Test section text"
        
        result = block_builder.section(text)
        
        assert result["type"] == "section"
        assert result["text"]["type"] == "mrkdwn"
        assert result["text"]["text"] == text
    
    def test_create_section_block_with_accessory(self, block_builder):
        """Test creating section block with accessory."""
        text = "Test text"
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": "Click me"},
            "action_id": "test_action"
        }
        
        result = block_builder.section(text, accessory=button)
        
        assert result["accessory"] == button
    
    def test_create_actions_block(self, block_builder):
        """Test creating actions block."""
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": "Test"},
            "action_id": "test"
        }
        
        result = block_builder.actions([button])
        
        assert result["type"] == "actions"
        assert len(result["elements"]) == 1
        assert result["elements"][0] == button
    
    def test_create_divider_block(self, block_builder):
        """Test creating divider block."""
        result = block_builder.divider()
        
        assert result["type"] == "divider"
    
    def test_create_context_block(self, block_builder):
        """Test creating context block."""
        elements = [
            {"type": "mrkdwn", "text": "Context text"}
        ]
        
        result = block_builder.context(elements)
        
        assert result["type"] == "context"
        assert result["elements"] == elements
    
    def test_create_header_block(self, block_builder):
        """Test creating header block."""
        text = "Header Text"
        
        result = block_builder.header(text)
        
        assert result["type"] == "header"
        assert result["text"]["type"] == "plain_text"
        assert result["text"]["text"] == text
    
    def test_create_button_element(self, block_builder):
        """Test creating button element."""
        text = "Click me"
        action_id = "test_action"
        value = "test_value"
        
        result = block_builder.button(text, action_id, value)
        
        assert result["type"] == "button"
        assert result["text"]["text"] == text
        assert result["action_id"] == action_id
        assert result["value"] == value
    
    def test_create_button_element_with_style(self, block_builder):
        """Test creating button with style."""
        result = block_builder.button("Danger", "danger_action", style="danger")
        
        assert result["style"] == "danger"
    
    def test_create_select_element(self, block_builder):
        """Test creating select element."""
        placeholder = "Choose option"
        action_id = "select_action"
        options = [
            {"text": {"type": "plain_text", "text": "Option 1"}, "value": "opt1"},
            {"text": {"type": "plain_text", "text": "Option 2"}, "value": "opt2"}
        ]
        
        result = block_builder.select(placeholder, action_id, options)
        
        assert result["type"] == "static_select"
        assert result["placeholder"]["text"] == placeholder
        assert result["action_id"] == action_id
        assert len(result["options"]) == 2


class TestRateLimiter:
    """Test suite for RateLimiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create RateLimiter instance."""
        limiter = RateLimiter()
        limiter.redis = AsyncMock()
        return limiter
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter):
        """Test rate limit check when allowed."""
        # Setup
        user_id = "U123456789"
        limit = 100
        window = 3600  # 1 hour
        
        # Mock Redis to return current count below limit
        rate_limiter.redis.get.return_value = "5"  # Current count
        rate_limiter.redis.incr.return_value = 6
        rate_limiter.redis.expire.return_value = True
        
        # Execute
        result = await rate_limiter.check_rate_limit(user_id, limit, window)
        
        # Verify
        assert result is True
        rate_limiter.redis.incr.assert_called_once_with(f"rate_limit:{user_id}")
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit check when exceeded."""
        # Setup
        user_id = "U123456789"
        limit = 100
        window = 3600
        
        # Mock Redis to return count at limit
        rate_limiter.redis.get.return_value = "100"
        
        # Execute
        result = await rate_limiter.check_rate_limit(user_id, limit, window)
        
        # Verify
        assert result is False
        rate_limiter.redis.incr.assert_not_called()  # Should not increment
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_new_user(self, rate_limiter):
        """Test rate limit check for new user."""
        # Setup
        user_id = "U999999999"
        limit = 100
        window = 3600
        
        # Mock Redis to return None (new user)
        rate_limiter.redis.get.return_value = None
        rate_limiter.redis.incr.return_value = 1
        
        # Execute
        result = await rate_limiter.check_rate_limit(user_id, limit, window)
        
        # Verify
        assert result is True
        rate_limiter.redis.incr.assert_called_once()
        rate_limiter.redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limiter):
        """Test getting rate limit status."""
        # Setup
        user_id = "U123456789"
        limit = 100
        window = 3600
        
        rate_limiter.redis.get.return_value = "25"
        rate_limiter.redis.ttl.return_value = 2400  # 40 minutes remaining
        
        # Execute
        result = await rate_limiter.get_rate_limit_status(user_id, limit, window)
        
        # Verify
        assert result["current_count"] == 25
        assert result["limit"] == 100
        assert result["remaining"] == 75
        assert result["reset_time"] is not None
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limiter):
        """Test resetting rate limit."""
        # Setup
        user_id = "U123456789"
        
        # Execute
        await rate_limiter.reset_rate_limit(user_id)
        
        # Verify
        rate_limiter.redis.delete.assert_called_once_with(f"rate_limit:{user_id}")
    
    @pytest.mark.asyncio
    async def test_check_burst_limit(self, rate_limiter):
        """Test burst rate limiting."""
        # Setup
        user_id = "U123456789"
        burst_limit = 10
        burst_window = 60  # 1 minute
        
        # Mock Redis for burst limiting
        rate_limiter.redis.get.return_value = "5"
        rate_limiter.redis.incr.return_value = 6
        
        # Execute
        result = await rate_limiter.check_burst_limit(user_id, burst_limit, burst_window)
        
        # Verify
        assert result is True
        rate_limiter.redis.incr.assert_called_with(f"burst_limit:{user_id}")
    
    @pytest.mark.asyncio
    async def test_rate_limiter_redis_error(self, rate_limiter):
        """Test rate limiter with Redis error."""
        # Setup
        user_id = "U123456789"
        rate_limiter.redis.get.side_effect = Exception("Redis connection error")
        
        # Execute - should allow request on Redis error (fail open)
        result = await rate_limiter.check_rate_limit(user_id)
        
        # Verify
        assert result is True  # Fail open policy
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit(self, rate_limiter):
        """Test sliding window rate limiting implementation."""
        # Setup
        user_id = "U123456789"
        limit = 100
        window = 3600
        
        # Mock sliding window data
        current_time = datetime.utcnow().timestamp()
        window_start = current_time - window
        
        # Mock Redis pipeline for sliding window
        mock_pipeline = AsyncMock()
        rate_limiter.redis.pipeline.return_value = mock_pipeline
        mock_pipeline.zremrangebyscore.return_value = None
        mock_pipeline.zcard.return_value = 50  # Current count
        mock_pipeline.zadd.return_value = None
        mock_pipeline.expire.return_value = None
        mock_pipeline.execute.return_value = [None, 50, None, None]
        
        # Execute
        result = await rate_limiter.sliding_window_check(user_id, limit, window)
        
        # Verify
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])