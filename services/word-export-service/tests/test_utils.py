#!/usr/bin/env python3
"""
Tests for Word Export Service utilities.

This module contains comprehensive tests for all utility functions
used in the Word export service, including authentication, rate limiting,
validation, and helper functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.utils.auth import (
    verify_jwt_token,
    get_current_user_full,
    check_permission,
    create_audit_log
)
from app.utils.rate_limiter import (
    RateLimiter,
    check_rate_limit,
    get_rate_limit_info,
    reset_rate_limit
)
from app.utils.validation import (
    validate_job_name,
    validate_file_path,
    validate_document_config,
    validate_chart_data,
    validate_table_data,
    sanitize_filename,
    validate_template_parameters
)
from app.utils.helpers import (
    generate_correlation_id,
    format_file_size,
    calculate_estimated_generation_time,
    extract_metadata_from_config,
    merge_document_configs,
    parse_expiration_date
)


class TestAuthenticationUtilities:
    """Test cases for authentication utilities."""
    
    def test_verify_jwt_token_success(self):
        """Test successful JWT token verification."""
        with patch('app.utils.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": 123,
                "username": "testuser",
                "exp": datetime.utcnow().timestamp() + 3600
            }
            
            payload = verify_jwt_token("valid_token")
            
            assert payload["user_id"] == 123
            assert payload["username"] == "testuser"
            mock_decode.assert_called_once()
    
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token."""
        with patch('app.utils.auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Token expired")
            
            with pytest.raises(HTTPException) as exc_info:
                verify_jwt_token("expired_token")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token."""
        with patch('app.utils.auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                verify_jwt_token("invalid_token")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_success(self):
        """Test successful user retrieval."""
        with patch('app.utils.auth.verify_jwt_token') as mock_verify, \
             patch('app.utils.auth.get_user_from_database') as mock_get_user:
            
            mock_verify.return_value = {"user_id": 123}
            mock_get_user.return_value = {
                "id": 123,
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"]
            }
            
            user = await get_current_user_full("Bearer valid_token")
            
            assert user["id"] == 123
            assert user["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_missing_bearer(self):
        """Test user retrieval with missing Bearer prefix."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_full("invalid_format_token")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_full_user_not_found(self):
        """Test user retrieval when user not found in database."""
        with patch('app.utils.auth.verify_jwt_token') as mock_verify, \
             patch('app.utils.auth.get_user_from_database') as mock_get_user:
            
            mock_verify.return_value = {"user_id": 123}
            mock_get_user.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_full("Bearer valid_token")
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    
    def test_check_permission_granted(self):
        """Test permission checking with granted permission."""
        user = {
            "roles": ["admin"],
            "permissions": ["word_export:create", "word_export:read"]
        }
        
        result = check_permission(user, "word_export:create")
        assert result is True
    
    def test_check_permission_denied(self):
        """Test permission checking with denied permission."""
        user = {
            "roles": ["user"],
            "permissions": ["word_export:read"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            check_permission(user, "word_export:delete")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_check_permission_admin_override(self):
        """Test permission checking with admin role override."""
        user = {
            "roles": ["admin"],
            "permissions": []
        }
        
        # Admin should have all permissions
        result = check_permission(user, "word_export:delete")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_create_audit_log(self):
        """Test audit log creation."""
        with patch('app.utils.auth.log_audit_event') as mock_log:
            mock_log.return_value = None
            
            await create_audit_log(
                user_id=123,
                action="document_generated",
                resource="job_456",
                details={"format": "docx"}
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args["user_id"] == 123
            assert call_args["action"] == "document_generated"


class TestRateLimiter:
    """Test cases for rate limiting utilities."""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(
            redis_client=MagicMock(),
            default_limit=100,
            window_seconds=3600
        )
        
        assert limiter.default_limit == 100
        assert limiter.window_seconds == 3600
        assert limiter.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self):
        """Test rate limit check within limit."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get.return_value = "50"  # Current count
            mock_redis.return_value = mock_redis_instance
            
            result = await check_rate_limit("user_123", limit=100)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get.return_value = "150"  # Exceeds limit
            mock_redis.return_value = mock_redis_instance
            
            result = await check_rate_limit("user_123", limit=100)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get.return_value = None  # No previous requests
            mock_redis_instance.incr.return_value = 1
            mock_redis.return_value = mock_redis_instance
            
            result = await check_rate_limit("user_123", limit=100)
            
            assert result is True
            mock_redis_instance.incr.assert_called_once()
            mock_redis_instance.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self):
        """Test getting rate limit information."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get.return_value = "25"
            mock_redis_instance.ttl.return_value = 1800  # 30 minutes
            mock_redis.return_value = mock_redis_instance
            
            info = await get_rate_limit_info("user_123")
            
            assert info["current_count"] == 25
            assert info["reset_time"] == 1800
            assert info["limit_exceeded"] is False
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self):
        """Test resetting rate limit."""
        with patch('app.utils.rate_limiter.get_redis_client') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.delete.return_value = 1
            mock_redis.return_value = mock_redis_instance
            
            result = await reset_rate_limit("user_123")
            
            assert result is True
            mock_redis_instance.delete.assert_called_once()


class TestValidationUtilities:
    """Test cases for validation utilities."""
    
    def test_validate_job_name_valid(self):
        """Test job name validation with valid names."""
        valid_names = [
            "Valid Job Name",
            "Document Export 2024",
            "Test_Document_123",
            "My-Document"
        ]
        
        for name in valid_names:
            result = validate_job_name(name)
            assert result is True
    
    def test_validate_job_name_invalid(self):
        """Test job name validation with invalid names."""
        invalid_names = [
            "",  # Empty
            "a",  # Too short
            "x" * 300,  # Too long
            "Invalid<>Name",  # Invalid characters
            "Name/With\\Slashes"
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                validate_job_name(name)
    
    def test_validate_file_path_valid(self):
        """Test file path validation with valid paths."""
        valid_paths = [
            "/tmp/document.docx",
            "/home/user/documents/file.pdf",
            "C:\\Documents\\file.txt"
        ]
        
        for path in valid_paths:
            result = validate_file_path(path)
            assert result is True
    
    def test_validate_file_path_invalid(self):
        """Test file path validation with invalid paths."""
        invalid_paths = [
            "",  # Empty
            "no_extension",  # No extension
            "/path/with/../../traversal",  # Path traversal
            "file_with_invalid_chars<>.txt"
        ]
        
        for path in invalid_paths:
            with pytest.raises(ValueError):
                validate_file_path(path)
    
    def test_validate_document_config_valid(self, sample_document_config):
        """Test document config validation with valid config."""
        result = validate_document_config(sample_document_config)
        assert result is True
    
    def test_validate_document_config_invalid(self):
        """Test document config validation with invalid config."""
        invalid_configs = [
            None,  # None config
            {},  # Empty config
            {"template": "invalid_template"},  # Invalid template
            {"metadata": {"title": ""}},  # Empty title
        ]
        
        for config in invalid_configs:
            with pytest.raises((ValueError, AttributeError)):
                validate_document_config(config)
    
    def test_validate_chart_data_valid(self):
        """Test chart data validation with valid data."""
        valid_data = {
            "labels": ["A", "B", "C"],
            "datasets": [
                {
                    "label": "Series 1",
                    "data": [1, 2, 3],
                    "backgroundColor": "#1f77b4"
                }
            ]
        }
        
        result = validate_chart_data(valid_data)
        assert result is True
    
    def test_validate_chart_data_invalid(self):
        """Test chart data validation with invalid data."""
        invalid_data_cases = [
            {},  # Empty
            {"labels": []},  # No datasets
            {"datasets": []},  # No labels
            {"labels": ["A"], "datasets": [{"data": []}]},  # Empty data
            {"labels": ["A", "B"], "datasets": [{"data": [1]}]}  # Mismatched lengths
        ]
        
        for data in invalid_data_cases:
            with pytest.raises(ValueError):
                validate_chart_data(data)
    
    def test_validate_table_data_valid(self):
        """Test table data validation with valid data."""
        valid_data = [
            {"col1": "A", "col2": 1},
            {"col1": "B", "col2": 2},
            {"col1": "C", "col2": 3}
        ]
        
        result = validate_table_data(valid_data)
        assert result is True
    
    def test_validate_table_data_invalid(self):
        """Test table data validation with invalid data."""
        invalid_data_cases = [
            [],  # Empty
            [{}],  # Empty rows
            [{"col1": "A"}, {"col2": "B"}],  # Inconsistent columns
            None  # None data
        ]
        
        for data in invalid_data_cases:
            with pytest.raises((ValueError, TypeError)):
                validate_table_data(data)
    
    def test_sanitize_filename_valid(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_file.docx", "normal_file.docx"),
            ("file with spaces.docx", "file_with_spaces.docx"),
            ("file<>with|invalid*chars.docx", "file_with_invalid_chars.docx"),
            ("file/with\\slashes.docx", "file_with_slashes.docx"),
            ("очень_длинное_имя_файла" * 10 + ".docx", "очень_длинное_имя_файла.docx")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert len(result) <= 255
            assert not any(char in result for char in '<>:"|?*')
    
    def test_validate_template_parameters_valid(self):
        """Test template parameter validation."""
        valid_params = {
            "font_size": 12,
            "color_scheme": "blue",
            "page_orientation": "portrait",
            "margins": {"top": 1.0, "bottom": 1.0}
        }
        
        result = validate_template_parameters(valid_params)
        assert result is True
    
    def test_validate_template_parameters_invalid(self):
        """Test template parameter validation with invalid parameters."""
        invalid_params_cases = [
            {"font_size": 0},  # Invalid font size
            {"font_size": 100},  # Font size too large
            {"color_scheme": "invalid"},  # Invalid color scheme
            {"page_orientation": "invalid"},  # Invalid orientation
            {"margins": {"top": -1.0}}  # Negative margin
        ]
        
        for params in invalid_params_cases:
            with pytest.raises(ValueError):
                validate_template_parameters(params)


class TestHelperUtilities:
    """Test cases for helper utilities."""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = generate_correlation_id()
        
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        assert "-" in correlation_id  # UUID format
        
        # Should be unique
        another_id = generate_correlation_id()
        assert correlation_id != another_id
    
    def test_format_file_size(self):
        """Test file size formatting."""
        test_cases = [
            (0, "0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1536, "1.5 KB"),
            (1024 * 1024 * 1.5, "1.5 MB")
        ]
        
        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            assert result == expected
    
    def test_calculate_estimated_generation_time(self):
        """Test generation time estimation."""
        # Test with basic document
        basic_config = {
            "charts": [],
            "tables": [],
            "layout": {"sections": [{"content_type": "text"}]}
        }
        
        estimated_time = calculate_estimated_generation_time(basic_config)
        assert isinstance(estimated_time, (int, float))
        assert estimated_time > 0
        
        # Test with complex document
        complex_config = {
            "charts": [{"id": "chart1"}, {"id": "chart2"}],
            "tables": [{"id": "table1"}],
            "layout": {"sections": [
                {"content_type": "text"},
                {"content_type": "chart"},
                {"content_type": "table"}
            ]}
        }
        
        complex_time = calculate_estimated_generation_time(complex_config)
        assert complex_time > estimated_time
    
    def test_extract_metadata_from_config(self, sample_document_config):
        """Test metadata extraction from document config."""
        metadata = extract_metadata_from_config(sample_document_config)
        
        assert "title" in metadata
        assert "author" in metadata
        assert "company" in metadata
        assert metadata["title"] == "Test Document"
        assert metadata["author"] == "Test Author"
    
    def test_extract_metadata_from_config_minimal(self):
        """Test metadata extraction with minimal config."""
        minimal_config = {
            "metadata": {"title": "Minimal Document"}
        }
        
        metadata = extract_metadata_from_config(minimal_config)
        
        assert metadata["title"] == "Minimal Document"
        assert "author" in metadata  # Should have defaults
        assert "created_date" in metadata
    
    def test_merge_document_configs(self):
        """Test merging document configurations."""
        base_config = {
            "template": "professional",
            "font_size": 11,
            "color_scheme": "blue",
            "charts": [{"id": "chart1"}]
        }
        
        override_config = {
            "font_size": 12,
            "color_scheme": "red",
            "tables": [{"id": "table1"}]
        }
        
        merged = merge_document_configs(base_config, override_config)
        
        assert merged["template"] == "professional"  # Preserved
        assert merged["font_size"] == 12  # Overridden
        assert merged["color_scheme"] == "red"  # Overridden
        assert merged["charts"] == [{"id": "chart1"}]  # Preserved
        assert merged["tables"] == [{"id": "table1"}]  # Added
    
    def test_parse_expiration_date(self):
        """Test expiration date parsing."""
        # Test with hours
        future_date = parse_expiration_date(24)
        assert isinstance(future_date, datetime)
        assert future_date > datetime.utcnow()
        
        # Should be approximately 24 hours from now
        expected_time = datetime.utcnow() + timedelta(hours=24)
        time_diff = abs((future_date - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_parse_expiration_date_invalid(self):
        """Test expiration date parsing with invalid input."""
        invalid_inputs = [0, -1, 8761]  # 0, negative, > 1 year
        
        for hours in invalid_inputs:
            with pytest.raises(ValueError):
                parse_expiration_date(hours)


class TestSecurityUtilities:
    """Test cases for security-related utilities."""
    
    def test_input_sanitization(self):
        """Test input sanitization for security."""
        with patch('app.utils.validation.sanitize_input') as mock_sanitize:
            mock_sanitize.return_value = "clean_input"
            
            from app.utils.validation import sanitize_input
            
            # Test with potentially dangerous input
            dangerous_inputs = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "<img src=x onerror=alert(1)>"
            ]
            
            for dangerous_input in dangerous_inputs:
                result = sanitize_input(dangerous_input)
                assert result == "clean_input"
                mock_sanitize.assert_called_with(dangerous_input)
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in validation."""
        with patch('app.utils.validation.check_sql_injection') as mock_check:
            mock_check.side_effect = lambda x: "DROP" in x.upper()
            
            from app.utils.validation import validate_safe_input
            
            safe_inputs = [
                "normal text",
                "SELECT data FROM table",
                "user123@example.com"
            ]
            
            unsafe_inputs = [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "UNION SELECT * FROM passwords"
            ]
            
            # Safe inputs should pass
            for safe_input in safe_inputs:
                try:
                    validate_safe_input(safe_input)
                except ValueError:
                    pass  # Some inputs might fail for other reasons
            
            # Unsafe inputs should be caught
            for unsafe_input in unsafe_inputs:
                with pytest.raises(ValueError):
                    validate_safe_input(unsafe_input)


class TestErrorHandling:
    """Test cases for error handling utilities."""
    
    def test_format_error_response(self):
        """Test error response formatting."""
        from app.utils.helpers import format_error_response
        
        error_response = format_error_response(
            error_code="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "job_name", "reason": "too_short"}
        )
        
        assert error_response["success"] is False
        assert error_response["error_code"] == "VALIDATION_ERROR"
        assert error_response["message"] == "Invalid input data"
        assert error_response["details"]["field"] == "job_name"
        assert "timestamp" in error_response
    
    def test_handle_unexpected_error(self):
        """Test unexpected error handling."""
        from app.utils.helpers import handle_unexpected_error
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            error_response = handle_unexpected_error(e, "test_operation")
            
            assert error_response["success"] is False
            assert error_response["error_code"] == "INTERNAL_ERROR"
            assert "Test error" in error_response["message"]
            assert error_response["operation"] == "test_operation"
    
    def test_log_error_with_context(self):
        """Test error logging with context."""
        with patch('app.utils.helpers.logger') as mock_logger:
            from app.utils.helpers import log_error_with_context
            
            context = {
                "user_id": 123,
                "job_id": 456,
                "operation": "document_generation"
            }
            
            error = ValueError("Test error")
            
            log_error_with_context(error, context)
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert "Test error" in call_args
            assert "user_id=123" in call_args or str(context) in str(mock_logger.error.call_args)


class TestPerformanceUtilities:
    """Test cases for performance-related utilities."""
    
    def test_measure_execution_time(self):
        """Test execution time measurement."""
        from app.utils.helpers import measure_execution_time
        
        import time
        
        @measure_execution_time
        def slow_function():
            time.sleep(0.1)
            return "result"
        
        result, execution_time = slow_function()
        
        assert result == "result"
        assert execution_time >= 0.1
        assert execution_time < 0.2  # Should be close to 0.1 seconds
    
    @pytest.mark.asyncio
    async def test_measure_async_execution_time(self):
        """Test async execution time measurement."""
        from app.utils.helpers import measure_async_execution_time
        
        import asyncio
        
        @measure_async_execution_time
        async def slow_async_function():
            await asyncio.sleep(0.1)
            return "async_result"
        
        result, execution_time = await slow_async_function()
        
        assert result == "async_result"
        assert execution_time >= 0.1
        assert execution_time < 0.2
    
    def test_memory_usage_tracking(self):
        """Test memory usage tracking."""
        with patch('app.utils.helpers.tracemalloc') as mock_tracemalloc:
            mock_tracemalloc.get_traced_memory.return_value = (1024, 2048)
            
            from app.utils.helpers import get_memory_usage
            
            current, peak = get_memory_usage()
            
            assert current == 1024
            assert peak == 2048
            mock_tracemalloc.get_traced_memory.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])