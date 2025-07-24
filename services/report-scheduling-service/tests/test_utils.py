#!/usr/bin/env python3
"""
Comprehensive utility tests for Report Scheduling Service.

This module tests utility functions including authentication, rate limiting,
validation, security, and helper functions.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any
import time
from datetime import datetime, timedelta
import jwt
import json


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
        assert len(token) > 50
    
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
        time.sleep(0.1)
        
        result = verify_token(token)
        assert result is None
    
    def test_get_current_user_valid_token(self):
        """Test getting current user from valid token."""
        from app.utils.auth import get_current_user
        
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
    
    def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        from app.utils.auth import get_current_user
        
        mock_request = Mock()
        mock_request.headers = {}
        
        with pytest.raises(Exception):
            get_current_user(mock_request)
    
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        from app.utils.auth import get_current_user
        
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('app.utils.auth.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(Exception):
                get_current_user(mock_request)
    
    def test_hash_password(self):
        """Test password hashing."""
        from app.utils.auth import hash_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 50
    
    def test_verify_password(self):
        """Test password verification."""
        from app.utils.auth import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestRateLimiterUtils:
    """Test rate limiting utility functions."""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, mock_redis):
        """Test rate limiting when within limits."""
        from app.utils.rate_limiter import check_rate_limit
        
        mock_redis.incr.return_value = 5
        
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
        
        mock_redis.incr.return_value = 15
        
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
        
        mock_redis.incr.return_value = 3
        
        @rate_limit(limit=10, window=60)
        async def test_function(user_id: str):
            return f"Success for {user_id}"
        
        result = await test_function("test-user-123")
        assert result == "Success for test-user-123"
    
    @pytest.mark.asyncio
    async def test_rate_limit_decorator_exceeds_limit(self, mock_redis):
        """Test rate limit decorator when exceeding limits."""
        from app.utils.rate_limiter import rate_limit, RateLimitExceeded
        
        mock_redis.incr.return_value = 15
        
        @rate_limit(limit=10, window=60)
        async def test_function(user_id: str):
            return f"Success for {user_id}"
        
        with pytest.raises(RateLimitExceeded):
            await test_function("test-user-123")
    
    def test_get_rate_limit_key(self):
        """Test generating rate limit keys."""
        from app.utils.rate_limiter import get_rate_limit_key
        
        key = get_rate_limit_key("user", "test-user-123", "schedule_create")
        
        assert key is not None
        assert "user" in key
        assert "test-user-123" in key
        assert "schedule_create" in key
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiter(self, mock_redis):
        """Test sliding window rate limiter implementation."""
        from app.utils.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
        
        mock_redis.zcount.return_value = 5
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
            "test..double.dot@example.com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False
    
    def test_validate_cron_expression_valid(self):
        """Test cron expression validation with valid expressions."""
        from app.utils.validation import validate_cron_expression
        
        valid_crons = [
            "0 9 * * *",      # Daily at 9 AM
            "0 0 * * 0",      # Weekly on Sunday
            "0 0 1 * *",      # Monthly on 1st
            "0 */6 * * *",    # Every 6 hours
            "30 8 * * 1-5"    # Weekdays at 8:30 AM
        ]
        
        for cron in valid_crons:
            assert validate_cron_expression(cron) is True
    
    def test_validate_cron_expression_invalid(self):
        """Test cron expression validation with invalid expressions."""
        from app.utils.validation import validate_cron_expression
        
        invalid_crons = [
            "invalid cron",
            "60 25 32 13 8",  # Invalid values
            "* * * *",        # Too few fields
            "0 0 0 0 0 0",    # Too many fields
        ]
        
        for cron in invalid_crons:
            assert validate_cron_expression(cron) is False
    
    def test_validate_timezone_valid(self):
        """Test timezone validation with valid timezones."""
        from app.utils.validation import validate_timezone
        
        valid_timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "US/Pacific"
        ]
        
        for tz in valid_timezones:
            assert validate_timezone(tz) is True
    
    def test_validate_timezone_invalid(self):
        """Test timezone validation with invalid timezones."""
        from app.utils.validation import validate_timezone
        
        invalid_timezones = [
            "Invalid/Timezone",
            "EST",  # Deprecated
            "GMT+5",  # Not a valid tz name
            ""
        ]
        
        for tz in invalid_timezones:
            assert validate_timezone(tz) is False
    
    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        from app.utils.validation import sanitize_input
        
        malicious_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_input(malicious_input)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
    
    def test_sanitize_input_sql_injection(self):
        """Test SQL injection prevention."""
        from app.utils.validation import sanitize_input
        
        malicious_input = "'; DROP TABLE schedules; --"
        sanitized = sanitize_input(malicious_input)
        
        assert "DROP TABLE" not in sanitized.upper()
        assert "--" not in sanitized
    
    def test_validate_schedule_priority(self):
        """Test schedule priority validation."""
        from app.utils.validation import validate_schedule_priority
        
        valid_priorities = ["low", "medium", "high", "critical"]
        
        for priority in valid_priorities:
            assert validate_schedule_priority(priority) is True
        
        invalid_priorities = ["urgent", "normal", ""]
        
        for priority in invalid_priorities:
            assert validate_schedule_priority(priority) is False
    
    def test_validate_report_format(self):
        """Test report format validation."""
        from app.utils.validation import validate_report_format
        
        valid_formats = ["pdf", "csv", "xlsx", "json"]
        
        for fmt in valid_formats:
            assert validate_report_format(fmt) is True
        
        invalid_formats = ["doc", "txt", "html"]
        
        for fmt in invalid_formats:
            assert validate_report_format(fmt) is False
    
    def test_validate_delivery_method(self):
        """Test delivery method validation."""
        from app.utils.validation import validate_delivery_method
        
        valid_methods = ["email", "webhook", "sftp", "s3"]
        
        for method in valid_methods:
            assert validate_delivery_method(method) is True
        
        invalid_methods = ["ftp", "sms", "print"]
        
        for method in invalid_methods:
            assert validate_delivery_method(method) is False


class TestSecurityUtils:
    """Test security utility functions."""
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        from app.utils.security import generate_secure_token
        
        token = generate_secure_token(32)
        
        assert token is not None
        assert len(token) == 64  # 32 bytes = 64 hex chars
        assert isinstance(token, str)
        
        token2 = generate_secure_token(32)
        assert token != token2
    
    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        from app.utils.security import encrypt_data, decrypt_data
        
        original_data = "sensitive schedule configuration"
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
        
        with pytest.raises(Exception):
            decrypt_data(encrypted, wrong_key)
    
    def test_hash_sensitive_data(self):
        """Test hashing sensitive data."""
        from app.utils.security import hash_sensitive_data
        
        sensitive_data = "user_schedule_config"
        hashed = hash_sensitive_data(sensitive_data)
        
        assert hashed != sensitive_data
        assert len(hashed) == 64  # SHA256 hex string
        
        hashed2 = hash_sensitive_data(sensitive_data)
        assert hashed == hashed2
    
    def test_secure_compare(self):
        """Test timing-safe string comparison."""
        from app.utils.security import secure_compare
        
        string1 = "secret_schedule_id"
        string2 = "secret_schedule_id"
        string3 = "different_schedule_id"
        
        assert secure_compare(string1, string2) is True
        assert secure_compare(string1, string3) is False
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from app.utils.security import generate_csrf_token
        
        token = generate_csrf_token()
        
        assert token is not None
        assert len(token) > 20
        assert isinstance(token, str)
        
        token2 = generate_csrf_token()
        assert token != token2
    
    def test_validate_csrf_token(self):
        """Test CSRF token validation."""
        from app.utils.security import generate_csrf_token, validate_csrf_token
        
        token = generate_csrf_token()
        mock_session = {"csrf_token": token}
        
        assert validate_csrf_token(token, mock_session) is True
        assert validate_csrf_token("invalid_token", mock_session) is False
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
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_generate_filename(self):
        """Test filename generation."""
        from app.utils.helpers import generate_filename
        
        filename = generate_filename("daily_report", "pdf")
        
        assert filename.startswith("daily_report_")
        assert filename.endswith(".pdf")
        assert len(filename) > len("daily_report_.pdf")
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from app.utils.helpers import sanitize_filename
        
        dangerous_filename = "../../malicious<>report.pdf"
        safe_filename = sanitize_filename(dangerous_filename)
        
        assert "../" not in safe_filename
        assert "<" not in safe_filename
        assert ">" not in safe_filename
        assert safe_filename.endswith(".pdf")
    
    def test_parse_duration(self):
        """Test duration parsing."""
        from app.utils.helpers import parse_duration
        
        assert parse_duration("30s") == 30
        assert parse_duration("5m") == 300
        assert parse_duration("2h") == 7200
        assert parse_duration("1d") == 86400
        
        with pytest.raises(ValueError):
            parse_duration("invalid")
    
    def test_truncate_text(self):
        """Test text truncation."""
        from app.utils.helpers import truncate_text
        
        long_text = "This is a very long schedule description that needs to be truncated"
        
        truncated = truncate_text(long_text, 30)
        assert len(truncated) <= 30
        assert truncated.endswith("...")
        
        short_text = "Short description"
        assert truncate_text(short_text, 30) == short_text
    
    def test_deep_merge_dicts(self):
        """Test deep dictionary merging."""
        from app.utils.helpers import deep_merge_dicts
        
        dict1 = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": [1, 2]
        }
        
        dict2 = {
            "a": 10,
            "b": {"d": 30, "f": 4},
            "g": 5
        }
        
        merged = deep_merge_dicts(dict1, dict2)
        
        assert merged["a"] == 10
        assert merged["b"]["c"] == 2
        assert merged["b"]["d"] == 30
        assert merged["b"]["f"] == 4
        assert merged["g"] == 5
    
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
        
        asyncio.run(test_retry())
    
    def test_batch_process_items(self):
        """Test batch processing utility."""
        from app.utils.helpers import batch_process
        
        items = list(range(25))
        batches = list(batch_process(items, batch_size=10))
        
        assert len(batches) == 3
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        from app.utils.helpers import generate_correlation_id
        
        corr_id = generate_correlation_id()
        
        assert corr_id is not None
        assert len(corr_id) > 10
        assert isinstance(corr_id, str)
        
        corr_id2 = generate_correlation_id()
        assert corr_id != corr_id2
    
    def test_convert_to_timezone(self):
        """Test timezone conversion."""
        from app.utils.helpers import convert_to_timezone
        import pytz
        
        utc_dt = datetime.now(pytz.UTC)
        
        et_dt = convert_to_timezone(utc_dt, "US/Eastern")
        assert et_dt.tzinfo is not None
        assert et_dt.tzinfo != pytz.UTC
        
        pt_dt = convert_to_timezone(utc_dt, "US/Pacific")
        assert pt_dt.tzinfo is not None
        assert et_dt != pt_dt


class TestSchedulingUtils:
    """Test scheduling-specific utility functions."""
    
    def test_calculate_next_run_time(self):
        """Test calculating next run time from cron expression."""
        from app.utils.scheduling import calculate_next_run_time
        
        # Daily at 9 AM
        next_run = calculate_next_run_time("0 9 * * *", "UTC")
        assert next_run is not None
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()
    
    def test_calculate_next_run_time_with_timezone(self):
        """Test calculating next run time with specific timezone."""
        from app.utils.scheduling import calculate_next_run_time
        
        next_run_utc = calculate_next_run_time("0 9 * * *", "UTC")
        next_run_et = calculate_next_run_time("0 9 * * *", "US/Eastern")
        
        # Times should be different due to timezone
        assert next_run_utc != next_run_et
    
    def test_validate_schedule_frequency(self):
        """Test schedule frequency validation."""
        from app.utils.scheduling import validate_schedule_frequency
        
        # Test reasonable frequencies
        assert validate_schedule_frequency("0 9 * * *") is True  # Daily
        assert validate_schedule_frequency("0 * * * *") is True   # Hourly
        assert validate_schedule_frequency("0 0 * * 0") is True   # Weekly
        
        # Test unreasonable frequencies
        assert validate_schedule_frequency("* * * * *") is False  # Every minute
        assert validate_schedule_frequency("*/5 * * * * *") is False  # 6-field cron
    
    def test_get_schedule_description(self):
        """Test getting human-readable schedule description."""
        from app.utils.scheduling import get_schedule_description
        
        descriptions = {
            "0 9 * * *": "Daily at 9:00 AM",
            "0 0 * * 0": "Weekly on Sunday at 12:00 AM",
            "0 0 1 * *": "Monthly on the 1st at 12:00 AM",
            "0 */6 * * *": "Every 6 hours"
        }
        
        for cron, expected_desc in descriptions.items():
            desc = get_schedule_description(cron)
            assert desc is not None
            assert isinstance(desc, str)
            # Basic check that it contains key words
            if "Daily" in expected_desc:
                assert "daily" in desc.lower() or "every day" in desc.lower()
    
    def test_parse_schedule_parameters(self):
        """Test parsing schedule parameters from configuration."""
        from app.utils.scheduling import parse_schedule_parameters
        
        config = {
            "cron_expression": "0 9 * * *",
            "timezone": "America/New_York",
            "max_retries": 3,
            "timeout_minutes": 30
        }
        
        params = parse_schedule_parameters(config)
        
        assert params["cron_expression"] == config["cron_expression"]
        assert params["timezone"] == config["timezone"]
        assert params["max_retries"] == config["max_retries"]
        assert params["timeout_minutes"] == config["timeout_minutes"]
    
    def test_estimate_execution_time(self):
        """Test estimating execution time based on query complexity."""
        from app.utils.scheduling import estimate_execution_time
        
        simple_query = "search error"
        complex_query = "search * | stats count by source | sort -count | head 1000 | join source [search * | stats avg(response_time) by source]"
        
        simple_time = estimate_execution_time(simple_query)
        complex_time = estimate_execution_time(complex_query)
        
        assert simple_time > 0
        assert complex_time > simple_time
        assert isinstance(simple_time, (int, float))
        assert isinstance(complex_time, (int, float))


class TestNotificationUtils:
    """Test notification utility functions."""
    
    def test_format_email_subject(self):
        """Test email subject formatting with variables."""
        from app.utils.notifications import format_email_subject
        
        template = "Daily Report - {{date}} - {{status}}"
        variables = {
            "date": "2024-01-15",
            "status": "Success"
        }
        
        subject = format_email_subject(template, variables)
        
        assert subject == "Daily Report - 2024-01-15 - Success"
        assert "{{" not in subject
        assert "}}" not in subject
    
    def test_format_email_body(self):
        """Test email body formatting with variables."""
        from app.utils.notifications import format_email_body
        
        template = "Hello {{name}},\n\nYour report '{{report_name}}' has been generated successfully.\n\nExecution time: {{execution_time}}ms"
        variables = {
            "name": "Admin",
            "report_name": "Daily Error Report",
            "execution_time": 3500
        }
        
        body = format_email_body(template, variables)
        
        assert "Hello Admin" in body
        assert "Daily Error Report" in body
        assert "3500ms" in body
        assert "{{" not in body
    
    def test_prepare_webhook_payload(self):
        """Test preparing webhook payload."""
        from app.utils.notifications import prepare_webhook_payload
        
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "status": "completed",
            "report_size": 2048576,
            "execution_time": 45000
        }
        
        config = {
            "include_metadata": True,
            "format": "json"
        }
        
        payload = prepare_webhook_payload(execution_data, config)
        
        assert "execution_id" in payload
        assert "schedule_id" in payload
        assert "status" in payload
        assert payload["status"] == "completed"
    
    def test_validate_notification_config(self):
        """Test notification configuration validation."""
        from app.utils.notifications import validate_notification_config
        
        # Valid email config
        email_config = {
            "method": "email",
            "recipients": ["admin@example.com"],
            "subject": "Report Ready"
        }
        
        result = validate_notification_config(email_config)
        assert result["is_valid"] is True
        
        # Invalid email config
        invalid_config = {
            "method": "email",
            "recipients": [],  # Empty recipients
        }
        
        result = validate_notification_config(invalid_config)
        assert result["is_valid"] is False
        assert "errors" in result
    
    def test_generate_notification_id(self):
        """Test notification ID generation."""
        from app.utils.notifications import generate_notification_id
        
        notification_id = generate_notification_id()
        
        assert notification_id is not None
        assert isinstance(notification_id, str)
        assert len(notification_id) > 10
        
        # Should be unique
        notification_id2 = generate_notification_id()
        assert notification_id != notification_id2


class TestConfigurationUtils:
    """Test configuration utility functions."""
    
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        import os
        from app.utils.config import load_config_from_env
        
        with patch.dict(os.environ, {
            "SCHEDULER_API_PORT": "8015",
            "SCHEDULER_DEBUG": "true",
            "SCHEDULER_MAX_CONCURRENT_JOBS": "50"
        }):
            config = load_config_from_env()
            
            assert config["API_PORT"] == 8015
            assert config["DEBUG"] is True
            assert config["MAX_CONCURRENT_JOBS"] == 50
    
    def test_validate_config_values(self):
        """Test configuration validation."""
        from app.utils.config import validate_config
        
        valid_config = {
            "API_PORT": 8015,
            "DEBUG": False,
            "MAX_CONCURRENT_JOBS": 50,
            "SCHEDULER_INTERVAL": 30
        }
        
        result = validate_config(valid_config)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid configuration
        invalid_config = {
            "API_PORT": "not_a_port",
            "MAX_CONCURRENT_JOBS": -1
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
            "MAX_CONCURRENT_JOBS": 25
        }
        
        env_config = {
            "API_PORT": 8015,
            "DEBUG": True
        }
        
        merged = merge_configs(default_config, env_config)
        
        assert merged["API_PORT"] == 8015
        assert merged["DEBUG"] is True
        assert merged["MAX_CONCURRENT_JOBS"] == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
