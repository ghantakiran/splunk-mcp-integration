"""
Tests for Microsoft Teams Bot utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

from app.utils.message_formatter import MessageFormatter
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
        
        assert isinstance(result, dict)
        assert "type" in result
        # Should contain query, results, and execution time information
    
    def test_format_query_response_with_visualization(self, message_formatter):
        """Test formatting query response with visualization."""
        response = {
            "success": True,
            "data": {
                "spl_query": "search index=main | stats count",
                "data": [{"count": 10}],
                "visualizations": [
                    {
                        "image_url": "https://example.com/chart.png",
                        "title": "Event Count"
                    }
                ]
            }
        }
        
        result = message_formatter.format_query_response(response)
        
        # Should include visualization information
        result_str = str(result)
        assert "visualization" in result_str.lower() or "chart" in result_str.lower()
    
    def test_format_query_response_error(self, message_formatter):
        """Test formatting error response."""
        response = {
            "success": False,
            "error": "Invalid SPL query syntax"
        }
        
        result = message_formatter.format_query_response(response)
        
        result_str = str(result)
        assert "error" in result_str.lower()
        assert "Invalid SPL query syntax" in result_str
    
    def test_format_help_message(self, message_formatter):
        """Test formatting help message."""
        result = message_formatter.format_help_message()
        
        assert isinstance(result, dict)
        result_str = str(result)
        assert "help" in result_str.lower()
        assert "splunk" in result_str.lower()
    
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
        
        result_str = str(result)
        assert "healthy" in result_str
        assert "standard" in result_str
        assert "25" in result_str
    
    def test_format_error_message(self, message_formatter):
        """Test formatting error message."""
        error = "Connection timeout"
        
        result = message_formatter.format_error_message(error)
        
        result_str = str(result)
        assert "error" in result_str.lower()
        assert "Connection timeout" in result_str
    
    def test_format_welcome_message(self, message_formatter):
        """Test formatting welcome message."""
        user_name = "John Doe"
        
        result = message_formatter.format_welcome_message(user_name)
        
        result_str = str(result)
        assert "welcome" in result_str.lower()
        assert user_name in result_str
    
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
        assert ("more rows" in result.lower() or "truncated" in result.lower())
    
    def test_truncate_text(self, message_formatter):
        """Test text truncation."""
        long_text = "x" * 5000
        
        result = message_formatter._truncate_text(long_text, max_length=1000)
        
        assert len(result) <= 1000
        assert ("..." in result or "truncated" in result.lower())
    
    def test_format_adaptive_card_text(self, message_formatter):
        """Test adaptive card text formatting."""
        text_with_markdown = "**Bold** text with *italics* and `code`"
        
        result = message_formatter._format_adaptive_card_text(text_with_markdown)
        
        # Should preserve or convert markdown appropriately for Teams
        assert "Bold" in result
        assert "italics" in result
        assert "code" in result
    
    def test_create_teams_mention(self, message_formatter):
        """Test creating Teams mention."""
        user_id = "29:user123"
        user_name = "John Doe"
        
        result = message_formatter.create_teams_mention(user_id, user_name)
        
        assert user_id in result
        assert user_name in result
        assert "mention" in result.lower()
    
    def test_format_typing_indicator(self, message_formatter):
        """Test formatting typing indicator."""
        result = message_formatter.format_typing_indicator()
        
        # Should return appropriate typing indicator format
        assert isinstance(result, dict)
        assert "type" in result
    
    def test_format_chart_description(self, message_formatter):
        """Test formatting chart description."""
        chart_data = {
            "title": "Error Trends",
            "chart_type": "line",
            "data_points": 50
        }
        
        result = message_formatter.format_chart_description(chart_data)
        
        assert "Error Trends" in result
        assert "line" in result
        assert "50" in result
    
    def test_sanitize_teams_content(self, message_formatter):
        """Test sanitizing content for Teams."""
        unsafe_content = "<script>alert('xss')</script>Normal text"
        
        result = message_formatter._sanitize_teams_content(unsafe_content)
        
        # Should remove or escape dangerous content
        assert "<script>" not in result
        assert "Normal text" in result


class TestTeamsRateLimiter:
    """Test suite for Teams-specific RateLimiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create RateLimiter instance."""
        limiter = RateLimiter()
        limiter.redis = AsyncMock()
        return limiter
    
    @pytest.mark.asyncio
    async def test_check_personal_rate_limit(self, rate_limiter):
        """Test personal conversation rate limiting."""
        user_id = "29:user123"
        conversation_type = "personal"
        
        # Mock Redis to return current count below limit
        rate_limiter.redis.get.return_value = "5"  # Current count
        rate_limiter.redis.incr.return_value = 6
        rate_limiter.redis.expire.return_value = True
        
        result = await rate_limiter.check_conversation_rate_limit(
            user_id, conversation_type
        )
        
        assert result is True
        rate_limiter.redis.incr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_channel_rate_limit(self, rate_limiter):
        """Test channel conversation rate limiting."""
        user_id = "29:user123"
        conversation_type = "channel"
        
        # Mock Redis to return current count below limit
        rate_limiter.redis.get.return_value = "25"  # Current count
        rate_limiter.redis.incr.return_value = 26
        
        result = await rate_limiter.check_conversation_rate_limit(
            user_id, conversation_type, limit=50  # Channel limit
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit when exceeded."""
        user_id = "29:user123"
        conversation_type = "personal"
        limit = 100
        
        # Mock Redis to return count at limit
        rate_limiter.redis.get.return_value = str(limit)
        
        result = await rate_limiter.check_conversation_rate_limit(
            user_id, conversation_type, limit=limit
        )
        
        assert result is False
        rate_limiter.redis.incr.assert_not_called()  # Should not increment
    
    @pytest.mark.asyncio
    async def test_check_adaptive_card_rate_limit(self, rate_limiter):
        """Test adaptive card action rate limiting."""
        user_id = "29:user123"
        action_type = "submit"
        
        rate_limiter.redis.get.return_value = "10"
        rate_limiter.redis.incr.return_value = 11
        
        result = await rate_limiter.check_adaptive_card_rate_limit(
            user_id, action_type
        )
        
        assert result is True
        rate_limiter.redis.incr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_proactive_message_rate_limit(self, rate_limiter):
        """Test proactive message rate limiting."""
        user_id = "29:user123"
        
        rate_limiter.redis.get.return_value = "2"  # Current count
        rate_limiter.redis.incr.return_value = 3
        
        result = await rate_limiter.check_proactive_rate_limit(user_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_teams_rate_limit_status(self, rate_limiter):
        """Test getting Teams-specific rate limit status."""
        user_id = "29:user123"
        conversation_type = "personal"
        limit = 100
        
        rate_limiter.redis.get.return_value = "25"
        rate_limiter.redis.ttl.return_value = 2400  # 40 minutes remaining
        
        result = await rate_limiter.get_teams_rate_limit_status(
            user_id, conversation_type, limit
        )
        
        assert result["current_count"] == 25
        assert result["limit"] == 100
        assert result["remaining"] == 75
        assert result["conversation_type"] == conversation_type
        assert result["reset_time"] is not None
    
    @pytest.mark.asyncio
    async def test_reset_user_rate_limits(self, rate_limiter):
        """Test resetting all rate limits for a user."""
        user_id = "29:user123"
        
        # Mock Redis keys for different rate limit types
        rate_limiter.redis.keys.return_value = [
            f"teams_rate_limit:personal:{user_id}",
            f"teams_rate_limit:channel:{user_id}",
            f"teams_card_limit:{user_id}"
        ]
        
        await rate_limiter.reset_teams_rate_limits(user_id)
        
        # Should delete all user-related rate limit keys
        rate_limiter.redis.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_tenant_isolation(self, rate_limiter):
        """Test rate limiting with tenant isolation."""
        user_id = "29:user123"
        tenant_id = "tenant456"
        conversation_type = "personal"
        
        rate_limiter.redis.get.return_value = "5"
        rate_limiter.redis.incr.return_value = 6
        
        result = await rate_limiter.check_tenant_rate_limit(
            user_id, tenant_id, conversation_type
        )
        
        assert result is True
        # Should use tenant-specific key
        expected_key = f"teams_rate_limit:{conversation_type}:{tenant_id}:{user_id}"
        rate_limiter.redis.incr.assert_called_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_burst_rate_limiting(self, rate_limiter):
        """Test burst rate limiting for rapid interactions."""
        user_id = "29:user123"
        
        # Mock burst window check
        rate_limiter.redis.get.return_value = "8"  # Near burst limit
        rate_limiter.redis.incr.return_value = 9
        
        result = await rate_limiter.check_burst_rate_limit(
            user_id, burst_limit=10, window_seconds=60
        )
        
        assert result is True
        
        # Mock exceeding burst limit
        rate_limiter.redis.get.return_value = "10"
        
        result = await rate_limiter.check_burst_rate_limit(
            user_id, burst_limit=10, window_seconds=60
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit_teams(self, rate_limiter):
        """Test sliding window implementation for Teams."""
        user_id = "29:user123"
        window_size = 3600  # 1 hour
        limit = 100
        
        # Mock sliding window operations
        mock_pipeline = AsyncMock()
        rate_limiter.redis.pipeline.return_value = mock_pipeline
        mock_pipeline.zremrangebyscore.return_value = None
        mock_pipeline.zcard.return_value = 50  # Current count
        mock_pipeline.zadd.return_value = None
        mock_pipeline.expire.return_value = None
        mock_pipeline.execute.return_value = [None, 50, None, None]
        
        result = await rate_limiter.sliding_window_teams_check(
            user_id, limit, window_size
        )
        
        assert result is True
        mock_pipeline.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_redis_error_handling(self, rate_limiter):
        """Test rate limiter error handling with Redis failures."""
        user_id = "29:user123"
        conversation_type = "personal"
        
        # Mock Redis connection error
        rate_limiter.redis.get.side_effect = Exception("Redis connection error")
        
        # Should fail open (allow request) on Redis error
        result = await rate_limiter.check_conversation_rate_limit(
            user_id, conversation_type
        )
        
        assert result is True  # Fail open policy


if __name__ == "__main__":
    pytest.main([__file__])