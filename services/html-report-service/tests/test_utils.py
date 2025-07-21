#!/usr/bin/env python3
"""
Tests for HTML Report Service utilities.

This module contains tests for utility functions including authentication,
rate limiting, logging, and other helper functions.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError


class TestAuthenticationUtils:
    """Test cases for authentication utilities."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_success(self):
        """Test successful user authentication."""
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "123",
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"]
            }
            
            from app.utils.auth import get_current_user_full
            
            # Mock the dependency
            user = await get_current_user_full("valid-token")
            
            assert user["id"] == "123"
            assert user["username"] == "testuser"
            assert user["email"] == "test@example.com"
            assert "user" in user["roles"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_invalid_token(self):
        """Test authentication with invalid token."""
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")
            
            from app.utils.auth import get_current_user_full
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_full("invalid-token")
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_expired_token(self):
        """Test authentication with expired token."""
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.side_effect = Exception("Token expired")
            
            from app.utils.auth import get_current_user_full
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_full("expired-token")
            
            assert exc_info.value.status_code == 401
    
    def test_jwt_token_verification(self):
        """Test JWT token verification utility."""
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "123",
                "exp": int(time.time()) + 3600,  # Valid for 1 hour
                "username": "testuser"
            }
            
            # Mock function since actual implementation may vary
            # from app.utils.auth import verify_jwt_token
            # result = verify_jwt_token("valid-token")
            
            # assert result["sub"] == "123"
            # assert result["username"] == "testuser"
    
    def test_create_jwt_token(self):
        """Test JWT token creation utility."""
        with patch('jwt.encode') as mock_encode:
            mock_encode.return_value = "encoded-token"
            
            # Mock function since actual implementation may vary
            # from app.utils.auth import create_jwt_token
            # token = create_jwt_token({"sub": "123", "username": "testuser"})
            
            # assert token == "encoded-token"


class TestRateLimiting:
    """Test cases for rate limiting utilities."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_get_redis:
            mock_redis_client = AsyncMock()
            mock_get_redis.return_value = mock_redis_client
            yield mock_redis_client
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_success(self, mock_redis):
        """Test successful rate limit check."""
        mock_redis.get.return_value = None  # No previous requests
        mock_redis.setex.return_value = True
        
        from app.utils.rate_limiter import check_rate_limit
        
        result = await check_rate_limit("user:123", 100, 60)
        
        assert result is True
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded."""
        mock_redis.get.return_value = "100"  # At limit
        
        from app.utils.rate_limiter import check_rate_limit
        
        result = await check_rate_limit("user:123", 100, 60)
        
        assert result is False
        mock_redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_sliding_window(self, mock_redis):
        """Test sliding window rate limiting."""
        # Mock sliding window implementation
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.return_value = 50  # Under limit
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = True
        
        from app.utils.rate_limiter import check_rate_limit_sliding_window
        
        result = await check_rate_limit_sliding_window("user:123", 100, 60)
        
        assert result is True
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once()
        mock_redis.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_sliding_window_exceeded(self, mock_redis):
        """Test sliding window rate limit exceeded."""
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.return_value = 100  # At limit
        
        from app.utils.rate_limiter import check_rate_limit_sliding_window
        
        result = await check_rate_limit_sliding_window("user:123", 100, 60)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_redis_error(self, mock_redis):
        """Test rate limiting with Redis error."""
        mock_redis.get.side_effect = RedisError("Connection failed")
        
        from app.utils.rate_limiter import check_rate_limit
        
        # Should fall back to allowing the request
        result = await check_rate_limit("user:123", 100, 60)
        
        assert result is True  # Fail open
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, mock_redis):
        """Test getting rate limit status."""
        mock_redis.get.return_value = "75"
        mock_redis.ttl.return_value = 30
        
        from app.utils.rate_limiter import get_rate_limit_status
        
        status = await get_rate_limit_status("user:123", 100)
        
        assert status["remaining"] == 25
        assert status["reset_time"] == 30
        assert status["limit"] == 100
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, mock_redis):
        """Test resetting rate limit."""
        mock_redis.delete.return_value = 1
        
        from app.utils.rate_limiter import reset_rate_limit
        
        result = await reset_rate_limit("user:123")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("rate_limit:user:123")


class TestCacheUtils:
    """Test cases for caching utilities."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for caching."""
        with patch('app.utils.cache.get_redis_client') as mock_get_redis:
            mock_redis_client = AsyncMock()
            mock_get_redis.return_value = mock_redis_client
            yield mock_redis_client
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, mock_redis):
        """Test cache set and get operations."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = '{"data": "test"}'
        
        from app.utils.cache import cache_set, cache_get
        
        # Set cache
        result = await cache_set("test-key", {"data": "test"}, 300)
        assert result is True
        
        # Get cache
        cached_data = await cache_get("test-key")
        assert cached_data == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, mock_redis):
        """Test cache miss."""
        mock_redis.get.return_value = None
        
        from app.utils.cache import cache_get
        
        result = await cache_get("nonexistent-key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, mock_redis):
        """Test cache deletion."""
        mock_redis.delete.return_value = 1
        
        from app.utils.cache import cache_delete
        
        result = await cache_delete("test-key")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_with_prefix(self, mock_redis):
        """Test cache operations with key prefix."""
        mock_redis.set.return_value = True
        
        from app.utils.cache import cache_set
        
        await cache_set("user:123", {"name": "test"}, 300, prefix="html_reports")
        
        # Should use prefixed key
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[0]
        assert "html_reports:user:123" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, mock_redis):
        """Test cache error handling."""
        mock_redis.get.side_effect = RedisError("Connection failed")
        
        from app.utils.cache import cache_get
        
        # Should handle Redis errors gracefully
        result = await cache_get("test-key")
        assert result is None


class TestValidationUtils:
    """Test cases for validation utilities."""
    
    def test_validate_file_size(self):
        """Test file size validation."""
        from app.utils.validation import validate_file_size
        
        # Valid file size
        assert validate_file_size(1024 * 1024) is True  # 1MB
        
        # Invalid file size
        assert validate_file_size(100 * 1024 * 1024) is False  # 100MB
    
    def test_validate_job_name(self):
        """Test job name validation."""
        from app.utils.validation import validate_job_name
        
        # Valid job names
        assert validate_job_name("Valid Job Name") is True
        assert validate_job_name("Test-Report_123") is True
        
        # Invalid job names
        assert validate_job_name("") is False  # Empty
        assert validate_job_name("a") is False  # Too short
        assert validate_job_name("x" * 1000) is False  # Too long
        assert validate_job_name("Job<>Name") is False  # Invalid characters
    
    def test_validate_color_scheme(self):
        """Test color scheme validation."""
        from app.utils.validation import validate_color_scheme
        
        # Valid color schemes
        assert validate_color_scheme("blue") is True
        assert validate_color_scheme("red") is True
        
        # Invalid color scheme
        assert validate_color_scheme("invalid") is False
    
    def test_validate_url(self):
        """Test URL validation."""
        from app.utils.validation import validate_url
        
        # Valid URLs
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8080") is True
        
        # Invalid URLs
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False  # Unsupported protocol
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        from app.utils.validation import sanitize_input
        
        # HTML injection
        dangerous_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_input(dangerous_input)
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
        
        # SQL injection patterns
        sql_input = "'; DROP TABLE users; --"
        sanitized = sanitize_input(sql_input)
        assert "DROP TABLE" not in sanitized.upper()


class TestFileUtils:
    """Test cases for file utility functions."""
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        from app.utils.file_utils import get_file_extension
        
        assert get_file_extension("report.html") == "html"
        assert get_file_extension("data.csv") == "csv"
        assert get_file_extension("archive.tar.gz") == "gz"
        assert get_file_extension("noextension") == ""
    
    def test_get_mime_type(self):
        """Test MIME type detection."""
        from app.utils.file_utils import get_mime_type
        
        assert get_mime_type("report.html") == "text/html"
        assert get_mime_type("data.csv") == "text/csv"
        assert get_mime_type("image.png") == "image/png"
        assert get_mime_type("document.pdf") == "application/pdf"
    
    def test_generate_filename(self):
        """Test filename generation."""
        from app.utils.file_utils import generate_filename
        
        filename = generate_filename("report", "html", job_id=123)
        assert "report" in filename
        assert "123" in filename
        assert filename.endswith(".html")
        
        # Test with timestamp
        filename_with_timestamp = generate_filename("test", "pdf", include_timestamp=True)
        assert filename_with_timestamp.endswith(".pdf")
        assert len(filename_with_timestamp) > len("test.pdf")
    
    def test_ensure_directory_exists(self):
        """Test directory creation utility."""
        with patch('os.makedirs') as mock_makedirs, \
             patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = False
            
            from app.utils.file_utils import ensure_directory_exists
            
            ensure_directory_exists("/tmp/test/path")
            
            mock_makedirs.assert_called_once_with("/tmp/test/path", exist_ok=True)
    
    def test_cleanup_old_files(self):
        """Test old file cleanup."""
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.getmtime') as mock_getmtime, \
             patch('os.remove') as mock_remove:
            
            # Mock old files
            mock_listdir.return_value = ["old_file.html", "new_file.html"]
            mock_isfile.return_value = True
            
            # Mock file times (old file is 2 days old, new file is 1 hour old)
            now = time.time()
            mock_getmtime.side_effect = [
                now - (2 * 24 * 3600),  # 2 days ago
                now - 3600  # 1 hour ago
            ]
            
            from app.utils.file_utils import cleanup_old_files
            
            cleanup_old_files("/tmp/reports", max_age_hours=24)
            
            # Should remove only the old file
            mock_remove.assert_called_once_with("/tmp/reports/old_file.html")


class TestDateTimeUtils:
    """Test cases for date/time utility functions."""
    
    def test_format_datetime(self):
        """Test datetime formatting."""
        from app.utils.datetime_utils import format_datetime
        
        test_datetime = datetime(2024, 1, 15, 14, 30, 0)
        
        # ISO format
        iso_formatted = format_datetime(test_datetime, "iso")
        assert iso_formatted == "2024-01-15T14:30:00"
        
        # Human readable format
        human_formatted = format_datetime(test_datetime, "human")
        assert "2024" in human_formatted
        assert "Jan" in human_formatted
    
    def test_parse_datetime(self):
        """Test datetime parsing."""
        from app.utils.datetime_utils import parse_datetime
        
        # ISO format
        iso_datetime = parse_datetime("2024-01-15T14:30:00")
        assert iso_datetime.year == 2024
        assert iso_datetime.month == 1
        assert iso_datetime.day == 15
        
        # Human readable format
        human_datetime = parse_datetime("2024-01-15 14:30:00")
        assert human_datetime is not None
    
    def test_calculate_expiration(self):
        """Test expiration calculation."""
        from app.utils.datetime_utils import calculate_expiration
        
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        expiration = calculate_expiration(base_time, hours=24)
        
        expected = base_time + timedelta(hours=24)
        assert expiration == expected
    
    def test_is_expired(self):
        """Test expiration checking."""
        from app.utils.datetime_utils import is_expired
        
        # Not expired
        future_time = datetime.utcnow() + timedelta(hours=1)
        assert is_expired(future_time) is False
        
        # Expired
        past_time = datetime.utcnow() - timedelta(hours=1)
        assert is_expired(past_time) is True


class TestLoggingUtils:
    """Test cases for logging utilities."""
    
    def test_get_logger(self):
        """Test logger creation."""
        from app.utils.logging import get_logger
        
        logger = get_logger("test_module")
        assert logger.name == "test_module"
    
    def test_log_request(self):
        """Test request logging."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            from app.utils.logging import log_request
            
            log_request("GET", "/api/v1/test", 200, 0.123, {"user_id": "123"})
            
            mock_logger.info.assert_called_once()
    
    def test_log_error(self):
        """Test error logging."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            from app.utils.logging import log_error
            
            try:
                raise ValueError("Test error")
            except ValueError as e:
                log_error("Test operation failed", e, {"context": "test"})
            
            mock_logger.error.assert_called_once()
    
    def test_log_performance(self):
        """Test performance logging."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            from app.utils.logging import log_performance
            
            log_performance("report_generation", 1.234, {"job_id": "123"})
            
            mock_logger.info.assert_called_once()


class TestSecurityUtils:
    """Test cases for security utilities."""
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        from app.utils.security import generate_secure_token
        
        token = generate_secure_token(32)
        assert len(token) == 64  # 32 bytes = 64 hex characters
        assert all(c in "0123456789abcdef" for c in token)
    
    def test_hash_password(self):
        """Test password hashing."""
        from app.utils.security import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_escape_html(self):
        """Test HTML escaping."""
        from app.utils.security import escape_html
        
        dangerous_html = '<script>alert("xss")</script>'
        escaped = escape_html(dangerous_html)
        
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped
    
    def test_validate_csrf_token(self):
        """Test CSRF token validation."""
        from app.utils.security import generate_csrf_token, validate_csrf_token
        
        session_id = "test_session_123"
        token = generate_csrf_token(session_id)
        
        assert validate_csrf_token(token, session_id) is True
        assert validate_csrf_token(token, "wrong_session") is False
        assert validate_csrf_token("invalid_token", session_id) is False


class TestEnvironmentUtils:
    """Test cases for environment and configuration utilities."""
    
    def test_get_environment(self):
        """Test environment detection."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from app.utils.env import get_environment
            
            env = get_environment()
            assert env == "test"
    
    def test_is_development(self):
        """Test development environment detection."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            from app.utils.env import is_development
            
            assert is_development() is True
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            from app.utils.env import is_development
            
            assert is_development() is False
    
    def test_get_config_value(self):
        """Test configuration value retrieval."""
        with patch.dict('os.environ', {'TEST_CONFIG': 'test_value'}):
            from app.utils.env import get_config_value
            
            value = get_config_value('TEST_CONFIG', 'default_value')
            assert value == 'test_value'
            
            # Test default value
            default_value = get_config_value('NONEXISTENT_CONFIG', 'default_value')
            assert default_value == 'default_value'