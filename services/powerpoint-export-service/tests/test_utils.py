#!/usr/bin/env python3
"""
Comprehensive utility tests for PowerPoint Export Service.

This module tests utility functions including authentication, rate limiting,
validation, security, and helper functions.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any
import time
from datetime import datetime, timedelta
import jwt


class TestAuthenticationUtils:
    """Test authentication utility functions."""
    
    def test_create_access_token(self):
        """Test creating JWT access tokens."""
        from app.utils.auth import create_access_token
        
        user_data = {
            "user_id": "test-user-123",
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        token = create_access_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_create_access_token_with_expiration(self):
        """Test creating JWT tokens with custom expiration."""
        from app.utils.auth import create_access_token
        
        user_data = {"user_id": "test-user-123"}
        expires_delta = timedelta(hours=2)
        
        token = create_access_token(user_data, expires_delta=expires_delta)
        
        assert token is not None
        
        # Decode token to verify expiration
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            decoded = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
            
            # Check that expiration is set
            assert "exp" in decoded
            exp_time = datetime.fromtimestamp(decoded["exp"])
            now = datetime.now()
            expected_exp = now + expires_delta
            
            # Allow for small time differences
            assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_verify_token_valid(self):
        """Test verifying valid JWT tokens."""
        from app.utils.auth import create_access_token, verify_token
        
        user_data = {
            "user_id": "test-user-123",
            "username": "test_user"
        }
        
        token = create_access_token(user_data)
        decoded_data = verify_token(token)
        
        assert decoded_data is not None
        assert decoded_data["user_id"] == "test-user-123"
        assert decoded_data["username"] == "test_user"
    
    def test_verify_token_invalid(self):
        """Test verifying invalid JWT tokens."""
        from app.utils.auth import verify_token
        
        invalid_token = "invalid.jwt.token"
        
        result = verify_token(invalid_token)
        
        assert result is None
    
    def test_verify_token_expired(self):
        """Test verifying expired JWT tokens."""
        from app.utils.auth import create_access_token, verify_token
        
        user_data = {"user_id": "test-user-123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        
        token = create_access_token(user_data, expires_delta=expires_delta)
        
        # Wait a moment to ensure token is expired
        time.sleep(0.1)
        
        result = verify_token(token)
        
        assert result is None
    
    def test_get_current_user_valid_token(self):
        """Test getting current user from valid token."""
        from app.utils.auth import get_current_user
        
        # Mock request with valid authorization header
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer valid-jwt-token"}
        
        with patch('app.utils.auth.verify_token') as mock_verify:
            mock_verify.return_value = {
                "user_id": "test-user-123",
                "username": "test_user",
                "roles": ["user"]
            }
            
            user = get_current_user(mock_request)
            
            assert user is not None
            assert user["user_id"] == "test-user-123"
            assert user["username"] == "test_user"
    
    def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        from app.utils.auth import get_current_user
        
        # Mock request without authorization header
        mock_request = Mock()
        mock_request.headers = {}
        
        with pytest.raises(Exception):  # Should raise authentication error
            get_current_user(mock_request)
    
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        from app.utils.auth import get_current_user
        
        # Mock request with invalid authorization header
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('app.utils.auth.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(Exception):  # Should raise authentication error
                get_current_user(mock_request)
    
    def test_hash_password(self):
        """Test password hashing."""
        from app.utils.auth import hash_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password  # Should be different from original
        assert len(hashed) > 50  # Hashed passwords are typically long
    
    def test_verify_password(self):
        """Test password verification."""
        from app.utils.auth import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Incorrect password should not verify
        assert verify_password("wrong_password", hashed) is False


class TestRateLimiterUtils:
    """Test rate limiting utility functions."""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, mock_redis):
        """Test rate limiting when within limits."""
        from app.utils.rate_limiter import check_rate_limit
        
        # Mock Redis to return count within limit
        mock_redis.incr.return_value = 5  # 5 requests, limit is 10
        
        result = await check_rate_limit(
            key="user:test-user-123",
            limit=10,
            window=60,
            redis_client=mock_redis
        )
        
        assert result is True
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeds_limit(self, mock_redis):
        """Test rate limiting when exceeding limits."""
        from app.utils.rate_limiter import check_rate_limit
        
        # Mock Redis to return count exceeding limit
        mock_redis.incr.return_value = 15  # 15 requests, limit is 10
        
        result = await check_rate_limit(
            key="user:test-user-123",
            limit=10,
            window=60,
            redis_client=mock_redis
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_decorator_within_limit(self, mock_redis):
        """Test rate limit decorator when within limits."""
        from app.utils.rate_limiter import rate_limit
        
        mock_redis.incr.return_value = 3  # Within limit
        
        @rate_limit(limit=10, window=60)
        async def test_function(user_id: str):
            return f"Success for {user_id}"
        
        result = await test_function("test-user-123")
        
        assert result == "Success for test-user-123"
    
    @pytest.mark.asyncio
    async def test_rate_limit_decorator_exceeds_limit(self, mock_redis):
        """Test rate limit decorator when exceeding limits."""
        from app.utils.rate_limiter import rate_limit, RateLimitExceeded
        
        mock_redis.incr.return_value = 15  # Exceeds limit
        
        @rate_limit(limit=10, window=60)
        async def test_function(user_id: str):
            return f"Success for {user_id}"
        
        with pytest.raises(RateLimitExceeded):
            await test_function("test-user-123")
    
    def test_get_rate_limit_key(self):
        """Test generating rate limit keys."""
        from app.utils.rate_limiter import get_rate_limit_key
        
        key = get_rate_limit_key("user", "test-user-123", "generate")
        
        assert key is not None
        assert "user" in key
        assert "test-user-123" in key
        assert "generate" in key
        assert key == "rate_limit:user:test-user-123:generate"
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiter(self, mock_redis):
        """Test sliding window rate limiter implementation."""
        from app.utils.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
        
        # Mock Redis operations for sliding window
        mock_redis.zcount.return_value = 5  # 5 requests in window
        mock_redis.zadd = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        result = await limiter.is_allowed(
            key="user:test-user-123",
            limit=10,
            window=60
        )
        
        assert result is True
        mock_redis.zcount.assert_called_once()
        mock_redis.zadd.assert_called_once()


class TestValidationUtils:
    """Test validation utility functions."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        from app.utils.validation import validate_email
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@gmail.com",
            "123@numbers.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        from app.utils.validation import validate_email
        
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "test@",
            "test..double.dot@example.com",
            "test@.com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        from app.utils.validation import validate_url
        
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://subdomain.example.com/path?query=value",
            "https://localhost:8080"
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        from app.utils.validation import validate_url
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Unsupported protocol
            "https://",
            "example.com",  # Missing protocol
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False
    
    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        from app.utils.validation import sanitize_input
        
        # Test XSS prevention
        malicious_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_input(malicious_input)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
    
    def test_sanitize_input_sql_injection(self):
        """Test SQL injection prevention."""
        from app.utils.validation import sanitize_input
        
        malicious_input = "'; DROP TABLE users; --"
        sanitized = sanitize_input(malicious_input)
        
        assert "DROP TABLE" not in sanitized.upper()
        assert "--" not in sanitized
    
    def test_validate_file_extension(self):
        """Test file extension validation."""
        from app.utils.validation import validate_file_extension
        
        allowed_extensions = [".pptx", ".pdf", ".png", ".jpg"]
        
        # Valid extensions
        assert validate_file_extension("presentation.pptx", allowed_extensions) is True
        assert validate_file_extension("report.pdf", allowed_extensions) is True
        
        # Invalid extensions
        assert validate_file_extension("malware.exe", allowed_extensions) is False
        assert validate_file_extension("document.txt", allowed_extensions) is False
    
    def test_validate_file_size(self):
        """Test file size validation."""
        from app.utils.validation import validate_file_size
        
        max_size_mb = 50
        
        # Valid sizes
        assert validate_file_size(1024 * 1024, max_size_mb) is True  # 1 MB
        assert validate_file_size(25 * 1024 * 1024, max_size_mb) is True  # 25 MB
        
        # Invalid sizes
        assert validate_file_size(100 * 1024 * 1024, max_size_mb) is False  # 100 MB
        assert validate_file_size(0, max_size_mb) is False  # Empty file
    
    def test_validate_uuid_format(self):
        """Test UUID format validation."""
        from app.utils.validation import validate_uuid
        import uuid
        
        # Valid UUIDs
        valid_uuid = str(uuid.uuid4())
        assert validate_uuid(valid_uuid) is True
        
        # Invalid UUIDs
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("123456789") is False
        assert validate_uuid("") is False
    
    def test_validate_color_hex(self):
        """Test hex color validation."""
        from app.utils.validation import validate_hex_color
        
        # Valid colors
        valid_colors = ["#FF0000", "#00ff00", "#0000FF", "#123456"]
        for color in valid_colors:
            assert validate_hex_color(color) is True
        
        # Invalid colors
        invalid_colors = ["FF0000", "#GG0000", "#12345", "red"]
        for color in invalid_colors:
            assert validate_hex_color(color) is False


class TestSecurityUtils:
    """Test security utility functions."""
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        from app.utils.security import generate_secure_token
        
        token = generate_secure_token(32)
        
        assert token is not None
        assert len(token) == 64  # 32 bytes = 64 hex chars
        assert isinstance(token, str)
        
        # Generate another token to ensure uniqueness
        token2 = generate_secure_token(32)
        assert token != token2
    
    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        from app.utils.security import encrypt_data, decrypt_data
        
        original_data = "sensitive information"
        encryption_key = "test-encryption-key-32-bytes!!!"
        
        encrypted = encrypt_data(original_data, encryption_key)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        
        decrypted = decrypt_data(encrypted, encryption_key)
        assert decrypted == original_data
    
    def test_encrypt_decrypt_invalid_key(self):
        """Test encryption with invalid key."""
        from app.utils.security import encrypt_data, decrypt_data
        
        original_data = "sensitive information"
        correct_key = "test-encryption-key-32-bytes!!!"
        wrong_key = "wrong-encryption-key-32-bytes!!!"
        
        encrypted = encrypt_data(original_data, correct_key)
        
        # Decryption with wrong key should fail
        with pytest.raises(Exception):
            decrypt_data(encrypted, wrong_key)
    
    def test_hash_sensitive_data(self):
        """Test hashing sensitive data."""
        from app.utils.security import hash_sensitive_data
        
        sensitive_data = "user_personal_info"
        hashed = hash_sensitive_data(sensitive_data)
        
        assert hashed != sensitive_data
        assert len(hashed) == 64  # SHA256 produces 64 char hex string
        
        # Same input should produce same hash
        hashed2 = hash_sensitive_data(sensitive_data)
        assert hashed == hashed2
    
    def test_secure_compare(self):
        """Test timing-safe string comparison."""
        from app.utils.security import secure_compare
        
        string1 = "secret_value"
        string2 = "secret_value"
        string3 = "different_value"
        
        # Same strings should match
        assert secure_compare(string1, string2) is True
        
        # Different strings should not match
        assert secure_compare(string1, string3) is False
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from app.utils.security import generate_csrf_token
        
        token = generate_csrf_token()
        
        assert token is not None
        assert len(token) > 20  # Should be reasonably long
        assert isinstance(token, str)
        
        # Generate another to ensure uniqueness
        token2 = generate_csrf_token()
        assert token != token2
    
    def test_validate_csrf_token(self):
        """Test CSRF token validation."""
        from app.utils.security import generate_csrf_token, validate_csrf_token
        
        token = generate_csrf_token()
        
        # Mock session with token
        mock_session = {"csrf_token": token}
        
        # Valid token should pass
        assert validate_csrf_token(token, mock_session) is True
        
        # Invalid token should fail
        assert validate_csrf_token("invalid_token", mock_session) is False
        
        # Missing session token should fail
        assert validate_csrf_token(token, {}) is False


class TestHelperUtils:
    """Test helper utility functions."""
    
    def test_format_file_size(self):
        """Test file size formatting."""
        from app.utils.helpers import format_file_size
        
        assert format_file_size(512) == "512 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1.5 * 1024 * 1024) == "1.5 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_generate_filename(self):
        """Test filename generation."""
        from app.utils.helpers import generate_filename
        
        filename = generate_filename("presentation", "pptx")
        
        assert filename.startswith("presentation_")
        assert filename.endswith(".pptx")
        assert len(filename) > len("presentation_.pptx")  # Should include timestamp
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from app.utils.helpers import sanitize_filename
        
        dangerous_filename = "../../malicious<>file.pptx"
        safe_filename = sanitize_filename(dangerous_filename)
        
        assert "../" not in safe_filename
        assert "<" not in safe_filename
        assert ">" not in safe_filename
        assert safe_filename.endswith(".pptx")
    
    def test_parse_duration(self):
        """Test duration parsing."""
        from app.utils.helpers import parse_duration
        
        assert parse_duration("30s") == 30
        assert parse_duration("5m") == 300
        assert parse_duration("2h") == 7200
        assert parse_duration("1d") == 86400
        
        # Invalid durations
        with pytest.raises(ValueError):
            parse_duration("invalid")
    
    def test_truncate_text(self):
        """Test text truncation."""
        from app.utils.helpers import truncate_text
        
        long_text = "This is a very long text that needs to be truncated"
        
        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")
        
        # Short text should not be truncated
        short_text = "Short text"
        assert truncate_text(short_text, 20) == short_text
    
    def test_deep_merge_dicts(self):
        """Test deep dictionary merging."""
        from app.utils.helpers import deep_merge_dicts
        
        dict1 = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": [1, 2]
        }
        
        dict2 = {
            "a": 10,  # Should override
            "b": {"d": 30, "f": 4},  # Should merge nested
            "g": 5  # Should add new key
        }
        
        merged = deep_merge_dicts(dict1, dict2)
        
        assert merged["a"] == 10
        assert merged["b"]["c"] == 2  # From dict1
        assert merged["b"]["d"] == 30  # Overridden from dict2
        assert merged["b"]["f"] == 4  # Added from dict2
        assert merged["g"] == 5  # Added from dict2
    
    def test_retry_async_operation(self):
        """Test async operation retry utility."""
        import asyncio
        from app.utils.helpers import retry_async
        
        call_count = 0
        
        @retry_async(max_attempts=3, delay=0.1)
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Operation failed")
            return "success"
        
        async def test_retry():
            result = await failing_operation()
            assert result == "success"
            assert call_count == 3
        
        # Run the async test
        asyncio.run(test_retry())
    
    def test_batch_process_items(self):
        """Test batch processing utility."""
        from app.utils.helpers import batch_process
        
        items = list(range(25))  # 25 items
        batches = list(batch_process(items, batch_size=10))
        
        assert len(batches) == 3  # 3 batches
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5  # Last batch with remaining items
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        from app.utils.helpers import generate_correlation_id
        
        corr_id = generate_correlation_id()
        
        assert corr_id is not None
        assert len(corr_id) > 10  # Should be reasonably long
        assert isinstance(corr_id, str)
        
        # Should be unique
        corr_id2 = generate_correlation_id()
        assert corr_id != corr_id2
    
    def test_convert_to_timezone(self):
        """Test timezone conversion."""
        from app.utils.helpers import convert_to_timezone
        from datetime import datetime
        import pytz
        
        utc_dt = datetime.now(pytz.UTC)
        
        # Convert to Eastern Time
        et_dt = convert_to_timezone(utc_dt, "US/Eastern")
        
        assert et_dt.tzinfo is not None
        assert et_dt.tzinfo != pytz.UTC
        
        # Convert to Pacific Time
        pt_dt = convert_to_timezone(utc_dt, "US/Pacific")
        
        assert pt_dt.tzinfo is not None
        assert et_dt != pt_dt  # Should be different times


class TestConfigurationUtils:
    """Test configuration utility functions."""
    
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        from app.utils.config import load_config_from_env
        
        with patch.dict(os.environ, {
            "PPT_API_PORT": "8011",
            "PPT_DEBUG": "true",
            "PPT_MAX_SLIDES": "100"
        }):
            config = load_config_from_env()
            
            assert config["API_PORT"] == 8011
            assert config["DEBUG"] is True
            assert config["MAX_SLIDES"] == 100
    
    def test_validate_config_values(self):
        """Test configuration validation."""
        from app.utils.config import validate_config
        
        valid_config = {
            "API_PORT": 8011,
            "DEBUG": False,
            "MAX_SLIDES": 100,
            "DEFAULT_THEME": "office"
        }
        
        result = validate_config(valid_config)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid configuration
        invalid_config = {
            "API_PORT": "not_a_port",  # Should be integer
            "MAX_SLIDES": -1  # Should be positive
        }
        
        result = validate_config(invalid_config)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    def test_merge_config_sources(self):
        """Test merging configuration from multiple sources."""
        from app.utils.config import merge_configs
        
        default_config = {
            "API_PORT": 8000,
            "DEBUG": False,
            "MAX_SLIDES": 50
        }
        
        env_config = {
            "API_PORT": 8011,  # Override
            "DEBUG": True      # Override
        }
        
        merged = merge_configs(default_config, env_config)
        
        assert merged["API_PORT"] == 8011  # From env
        assert merged["DEBUG"] is True     # From env
        assert merged["MAX_SLIDES"] == 50  # From default


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])