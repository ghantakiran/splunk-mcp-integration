#!/usr/bin/env python3
"""
Comprehensive utility tests for NLP Engine Service.

This module tests utility functions, helpers, authentication, rate limiting,
validation, and other supporting functionality.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any
import jwt
import time
from datetime import datetime, timedelta
import json


class TestAuthenticationUtils:
    """Test authentication utility functions."""
    
    def test_jwt_token_creation(self):
        """Test JWT token creation."""
        from app.utils.auth import create_access_token
        
        user_data = {
            "user_id": "test-user-123",
            "username": "test_user",
            "roles": ["user"]
        }
        
        token = create_access_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_jwt_token_validation_valid(self):
        """Test validation of valid JWT token."""
        from app.utils.auth import create_access_token, validate_token
        
        user_data = {
            "user_id": "test-user-123",
            "username": "test_user",
            "roles": ["user"]
        }
        
        token = create_access_token(user_data)
        decoded = validate_token(token)
        
        assert decoded["user_id"] == user_data["user_id"]
        assert decoded["username"] == user_data["username"]
        assert decoded["roles"] == user_data["roles"]
    
    def test_jwt_token_validation_invalid(self):
        """Test validation of invalid JWT token."""
        from app.utils.auth import validate_token
        from jwt import InvalidTokenError
        
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(InvalidTokenError):
            validate_token(invalid_token)
    
    def test_jwt_token_expiration(self):
        """Test JWT token expiration handling."""
        from app.utils.auth import create_access_token, validate_token
        from jwt import ExpiredSignatureError
        
        user_data = {"user_id": "test-user-123"}
        
        # Create token with very short expiration
        with patch('app.utils.auth.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 0):
            token = create_access_token(user_data)
            
            # Wait for token to expire
            time.sleep(1)
            
            with pytest.raises(ExpiredSignatureError):
                validate_token(token)
    
    def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        from app.utils.auth import get_current_user
        
        mock_token = "valid.jwt.token"
        mock_user = {
            "user_id": "test-user-123",
            "username": "test_user",
            "roles": ["user"]
        }
        
        with patch('app.utils.auth.validate_token') as mock_validate:
            mock_validate.return_value = mock_user
            
            user = get_current_user(mock_token)
            
            assert user["user_id"] == mock_user["user_id"]
            assert user["username"] == mock_user["username"]
            mock_validate.assert_called_once_with(mock_token)
    
    def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        from app.utils.auth import get_current_user
        from jwt import InvalidTokenError
        
        mock_token = "invalid.jwt.token"
        
        with patch('app.utils.auth.validate_token') as mock_validate:
            mock_validate.side_effect = InvalidTokenError("Invalid token")
            
            with pytest.raises(InvalidTokenError):
                get_current_user(mock_token)
    
    def test_check_permissions_success(self):
        """Test permission checking with valid permissions."""
        from app.utils.auth import check_permissions
        
        user = {
            "user_id": "test-user-123",
            "permissions": ["nlp:read", "nlp:write", "spl:translate"]
        }
        
        required_permissions = ["nlp:read", "spl:translate"]
        
        result = check_permissions(user, required_permissions)
        
        assert result is True
    
    def test_check_permissions_insufficient(self):
        """Test permission checking with insufficient permissions."""
        from app.utils.auth import check_permissions
        
        user = {
            "user_id": "test-user-123",
            "permissions": ["nlp:read"]
        }
        
        required_permissions = ["nlp:read", "nlp:write"]
        
        result = check_permissions(user, required_permissions)
        
        assert result is False
    
    def test_check_role_based_access(self):
        """Test role-based access control."""
        from app.utils.auth import check_role_access
        
        user = {
            "user_id": "test-user-123",
            "roles": ["user", "analyst"]
        }
        
        # User should have access
        assert check_role_access(user, ["user"]) is True
        assert check_role_access(user, ["analyst"]) is True
        assert check_role_access(user, ["user", "admin"]) is True
        
        # User should not have access
        assert check_role_access(user, ["admin"]) is False
        assert check_role_access(user, ["superuser"]) is False


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_within_limits(self, mock_redis):
        """Test rate limiter when within limits."""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=3600)
        
        # Mock Redis operations
        mock_redis.get.return_value = "5"  # 5 requests so far
        mock_redis.expire = AsyncMock()
        
        result = await limiter.check_rate_limit("test-user-123")
        
        assert result is True
        mock_redis.incr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_exceeds_limits(self, mock_redis):
        """Test rate limiter when exceeding limits."""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=3600)
        
        # Mock Redis operations
        mock_redis.get.return_value = "100"  # Already at limit
        
        result = await limiter.check_rate_limit("test-user-123")
        
        assert result is False
        # Should not increment if at limit
        mock_redis.incr.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_first_request(self, mock_redis):
        """Test rate limiter for first request."""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=3600)
        
        # Mock Redis operations for first request
        mock_redis.get.return_value = None
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        
        result = await limiter.check_rate_limit("test-user-123")
        
        assert result is True
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiter(self, mock_redis):
        """Test sliding window rate limiter implementation."""
        from app.utils.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        
        # Mock Redis operations
        current_time = time.time()
        mock_redis.zcount.return_value = 5  # 5 requests in window
        mock_redis.zadd = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        
        with patch('time.time', return_value=current_time):
            result = await limiter.check_rate_limit("test-user-123")
        
        assert result is True
        mock_redis.zadd.assert_called_once()
        mock_redis.zremrangebyscore.assert_called_once()
    
    def test_get_rate_limit_key(self):
        """Test rate limit key generation."""
        from app.utils.rate_limiter import get_rate_limit_key
        
        key = get_rate_limit_key("test-user-123", "spl_translate")
        
        assert "test-user-123" in key
        assert "spl_translate" in key
        assert "rate_limit" in key.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, mock_redis):
        """Test rate limit reset functionality."""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=3600)
        
        mock_redis.delete = AsyncMock()
        
        await limiter.reset_rate_limit("test-user-123")
        
        mock_redis.delete.assert_called_once()


class TestValidationUtils:
    """Test validation utility functions."""
    
    def test_validate_spl_basic_syntax(self):
        """Test basic SPL syntax validation."""
        from app.utils.validation import validate_spl_syntax
        
        # Valid SPL queries
        valid_queries = [
            "search error",
            "search index=main error earliest=-1h",
            "search * | stats count by source",
            "eval new_field=field1+field2"
        ]
        
        for query in valid_queries:
            result = validate_spl_syntax(query)
            assert result["is_valid"] is True
    
    def test_validate_spl_invalid_syntax(self):
        """Test invalid SPL syntax validation."""
        from app.utils.validation import validate_spl_syntax
        
        # Invalid SPL queries
        invalid_queries = [
            "",  # Empty
            "invalid command here",
            "search | invalid_function",
            "malformed | pipe | structure |"
        ]
        
        for query in invalid_queries:
            result = validate_spl_syntax(query)
            assert result["is_valid"] is False
            assert len(result.get("errors", [])) > 0
    
    def test_validate_user_context_complete(self):
        """Test validation of complete user context."""
        from app.utils.validation import validate_user_context
        
        complete_context = {
            "user_id": "test-user-123",
            "username": "test_user",
            "roles": ["user"],
            "permissions": ["nlp:read"],
            "accessible_indexes": ["main"]
        }
        
        result = validate_user_context(complete_context)
        
        assert result["is_valid"] is True
        assert len(result.get("errors", [])) == 0
    
    def test_validate_user_context_minimal(self):
        """Test validation of minimal user context."""
        from app.utils.validation import validate_user_context
        
        minimal_context = {
            "user_id": "test-user-123",
            "roles": ["user"]
        }
        
        result = validate_user_context(minimal_context)
        
        assert result["is_valid"] is True
    
    def test_validate_user_context_missing_required(self):
        """Test validation of user context missing required fields."""
        from app.utils.validation import validate_user_context
        
        invalid_context = {
            "username": "test_user"
            # Missing user_id
        }
        
        result = validate_user_context(invalid_context)
        
        assert result["is_valid"] is False
        assert "user_id" in str(result["errors"])
    
    def test_sanitize_input_text(self):
        """Test input text sanitization."""
        from app.utils.validation import sanitize_input
        
        # Test various inputs
        test_cases = [
            ("normal text", "normal text"),
            ("text with <script>alert('xss')</script>", "text with alert('xss')"),
            ("text with\x00null bytes", "text withnull bytes"),
            ("very " * 1000 + "long text", "very " * 100 + "long text...")  # Truncation
        ]
        
        for input_text, expected_pattern in test_cases:
            result = sanitize_input(input_text)
            if expected_pattern.endswith("..."):
                assert len(result) <= 1000
            else:
                assert result == expected_pattern or result.startswith(expected_pattern.split("<")[0])
    
    def test_validate_time_range_formats(self):
        """Test time range format validation."""
        from app.utils.validation import validate_time_range
        
        valid_ranges = [
            "-1h",
            "-24h@h",
            "-7d",
            "earliest=-1h latest=now",
            "@d-1h",
            "-30m@m"
        ]
        
        for time_range in valid_ranges:
            result = validate_time_range(time_range)
            assert result["is_valid"] is True
    
    def test_validate_invalid_time_ranges(self):
        """Test invalid time range validation."""
        from app.utils.validation import validate_time_range
        
        invalid_ranges = [
            "invalid",
            "1h",  # Missing minus sign
            "-xyz",
            "",
            "-1invalid"
        ]
        
        for time_range in invalid_ranges:
            result = validate_time_range(time_range)
            assert result["is_valid"] is False


class TestQueryUtils:
    """Test query utility functions."""
    
    def test_extract_time_range_from_query(self):
        """Test time range extraction from queries."""
        from app.utils.query_utils import extract_time_range
        
        queries_with_time = [
            ("search error earliest=-1h", "-1h"),
            ("search * earliest=-24h@h latest=now", "-24h@h"),
            ("show me errors from last hour", "last hour"),
            ("find events in the past 30 minutes", "past 30 minutes")
        ]
        
        for query, expected in queries_with_time:
            result = extract_time_range(query)
            assert expected in result.lower() or result.lower() in expected.lower()
    
    def test_extract_fields_from_spl(self):
        """Test field extraction from SPL."""
        from app.utils.query_utils import extract_fields
        
        spl_queries = [
            ("search error | stats count by source", ["source"]),
            ("search * | eval new_field=field1+field2 | fields new_field", ["field1", "field2", "new_field"]),
            ("search index=main | table user, action, timestamp", ["user", "action", "timestamp"])
        ]
        
        for spl, expected_fields in spl_queries:
            result = extract_fields(spl)
            for field in expected_fields:
                assert field in result
    
    def test_detect_query_intent(self):
        """Test query intent detection."""
        from app.utils.query_utils import detect_intent
        
        intent_examples = [
            ("show me errors", "search"),
            ("count events by source", "aggregation"),
            ("create a chart of response times", "visualization"),
            ("alert when cpu usage exceeds 80%", "alerting"),
            ("top 10 users by activity", "ranking")
        ]
        
        for query, expected_intent in intent_examples:
            result = detect_intent(query)
            assert result["primary_intent"] == expected_intent or expected_intent in result["possible_intents"]
    
    def test_build_spl_from_components(self):
        """Test SPL building from components."""
        from app.utils.query_utils import build_spl
        
        components = {
            "base_search": "error",
            "index": "main",
            "time_range": "-1h",
            "aggregation": "stats count by source",
            "filters": ["severity!=low"]
        }
        
        spl = build_spl(components)
        
        assert "search" in spl
        assert "index=main" in spl
        assert "error" in spl
        assert "earliest=-1h" in spl
        assert "stats count by source" in spl
        assert "severity!=low" in spl
    
    def test_optimize_spl_structure(self):
        """Test SPL structure optimization."""
        from app.utils.query_utils import optimize_spl_structure
        
        # Unoptimized SPL
        unoptimized = "search * | search error | search severity=high | stats count"
        
        optimized = optimize_spl_structure(unoptimized)
        
        # Should combine search terms
        search_count = optimized.count("search")
        assert search_count < unoptimized.count("search")
        assert "error" in optimized
        assert "severity=high" in optimized
    
    def test_estimate_query_complexity(self):
        """Test query complexity estimation."""
        from app.utils.query_utils import estimate_complexity
        
        complexity_examples = [
            ("search error", "low"),
            ("search error | stats count by source", "medium"),
            ("search * | eval new=old+1 | stats avg(new) by source | eventstats max(avg) | where avg > max/2", "high")
        ]
        
        for spl, expected_level in complexity_examples:
            result = estimate_complexity(spl)
            assert result["level"] == expected_level or result["score"] > 0


class TestCacheUtils:
    """Test cache utility functions."""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        from app.utils.cache import generate_cache_key
        
        query = "show me errors from the last hour"
        context = {"user_id": "test-user-123"}
        
        key = generate_cache_key(query, context)
        
        assert isinstance(key, str)
        assert len(key) > 10
        
        # Same inputs should generate same key
        key2 = generate_cache_key(query, context)
        assert key == key2
        
        # Different inputs should generate different keys
        key3 = generate_cache_key("different query", context)
        assert key != key3
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, mock_redis):
        """Test cache set and get operations."""
        from app.utils.cache import cache_set, cache_get
        
        key = "test_key"
        value = {"spl": "search error", "confidence": 0.95}
        ttl = 3600
        
        # Test cache set
        await cache_set(key, value, ttl)
        mock_redis.set.assert_called_once()
        
        # Test cache get
        mock_redis.get.return_value = json.dumps(value).encode()
        result = await cache_get(key)
        
        assert result == value
        mock_redis.get.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, mock_redis):
        """Test cache miss scenario."""
        from app.utils.cache import cache_get
        
        mock_redis.get.return_value = None
        
        result = await cache_get("nonexistent_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_redis):
        """Test cache invalidation."""
        from app.utils.cache import cache_invalidate
        
        pattern = "nlp:*"
        
        mock_redis.keys.return_value = ["nlp:key1", "nlp:key2"]
        mock_redis.delete = AsyncMock()
        
        await cache_invalidate(pattern)
        
        mock_redis.keys.assert_called_once_with(pattern)
        assert mock_redis.delete.call_count == 2


class TestLoggingUtils:
    """Test logging utility functions."""
    
    def test_structured_logger_setup(self):
        """Test structured logger setup."""
        from app.utils.logging import get_structured_logger
        
        logger = get_structured_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_correlation_id_generation(self):
        """Test correlation ID generation."""
        from app.utils.logging import generate_correlation_id
        
        correlation_id = generate_correlation_id()
        
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 10
        
        # Each call should generate unique ID
        correlation_id2 = generate_correlation_id()
        assert correlation_id != correlation_id2
    
    def test_log_context_manager(self):
        """Test log context manager."""
        from app.utils.logging import LogContext
        
        with patch('app.utils.logging.logger') as mock_logger:
            with LogContext("test_operation", {"user_id": "test-123"}):
                pass
            
            # Should log start and end
            assert mock_logger.info.call_count >= 2
    
    def test_performance_logger(self):
        """Test performance logging decorator."""
        from app.utils.logging import log_performance
        
        @log_performance
        def test_function():
            time.sleep(0.1)
            return "result"
        
        with patch('app.utils.logging.logger') as mock_logger:
            result = test_function()
            
            assert result == "result"
            mock_logger.info.assert_called()
            # Should log execution time
            call_args = mock_logger.info.call_args[0][0]
            assert "execution_time" in call_args.lower()


class TestErrorHandling:
    """Test error handling utilities."""
    
    def test_format_error_response(self):
        """Test error response formatting."""
        from app.utils.errors import format_error_response
        
        error = ValueError("Invalid input")
        correlation_id = "test-correlation-123"
        
        response = format_error_response(error, correlation_id)
        
        assert "error" in response
        assert response["correlation_id"] == correlation_id
        assert "Invalid input" in response["error"]["message"]
    
    def test_handle_ai_provider_error(self):
        """Test AI provider error handling."""
        from app.utils.errors import handle_ai_provider_error
        import openai
        
        # Test rate limit error
        rate_limit_error = openai.RateLimitError(
            "Rate limit exceeded",
            response=Mock(status_code=429),
            body=None
        )
        
        response = handle_ai_provider_error(rate_limit_error)
        
        assert response["error_type"] == "rate_limit"
        assert "retry_after" in response
    
    def test_handle_validation_error(self):
        """Test validation error handling."""
        from app.utils.errors import handle_validation_error
        from pydantic import ValidationError
        
        # Create a mock validation error
        try:
            from pydantic import BaseModel, Field
            
            class TestModel(BaseModel):
                required_field: str = Field(..., min_length=1)
            
            TestModel(required_field="")
        except ValidationError as e:
            response = handle_validation_error(e)
            
            assert response["error_type"] == "validation"
            assert len(response["details"]) > 0
    
    def test_safe_execute_with_fallback(self):
        """Test safe execution with fallback."""
        from app.utils.errors import safe_execute
        
        def failing_function():
            raise Exception("Function failed")
        
        def fallback_function():
            return "fallback_result"
        
        result = safe_execute(failing_function, fallback_function)
        
        assert result == "fallback_result"
    
    def test_retry_mechanism(self):
        """Test retry mechanism utility."""
        from app.utils.errors import retry_with_backoff
        
        call_count = 0
        
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = retry_with_backoff(sometimes_failing_function, max_retries=5)
        
        assert result == "success"
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])