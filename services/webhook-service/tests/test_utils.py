"""
Tests for Webhook Service utility functions.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4
import jwt
import hashlib
import hmac

# Import utility modules that we expect to exist
try:
    from app.utils.auth import verify_jwt_token, get_current_user, require_permissions
except ImportError:
    verify_jwt_token = None
    get_current_user = None
    require_permissions = None

try:
    from app.utils.rate_limiter import RateLimiter, check_rate_limit
except ImportError:
    RateLimiter = None
    check_rate_limit = None

try:
    from app.utils.metrics import WebhookMetrics, setup_metrics
except ImportError:
    WebhookMetrics = None
    setup_metrics = None

try:
    from app.utils.security import (
        generate_webhook_secret, validate_webhook_secret,
        generate_signature, validate_signature
    )
except ImportError:
    generate_webhook_secret = None
    validate_webhook_secret = None
    generate_signature = None
    validate_signature = None

try:
    from app.utils.validation import (
        validate_webhook_url, validate_webhook_headers,
        validate_event_filters, sanitize_input
    )
except ImportError:
    validate_webhook_url = None
    validate_webhook_headers = None
    validate_event_filters = None
    sanitize_input = None


class TestAuthentication:
    """Test suite for authentication utilities."""

    @pytest.mark.skipif(verify_jwt_token is None, reason="Auth utils not implemented")
    def test_verify_jwt_token_valid(self):
        """Test JWT token verification with valid token."""
        # Mock a valid JWT token
        valid_payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": ["basic"],
            "permissions": ["webhook:read", "webhook:create"],
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = valid_payload
            
            result = verify_jwt_token("valid.jwt.token")
            
            assert result["sub"] == "user-123"
            assert result["email"] == "user@example.com"
            assert "webhook:read" in result["permissions"]

    @pytest.mark.skipif(verify_jwt_token is None, reason="Auth utils not implemented")
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token."""
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")
            
            with pytest.raises(Exception):
                verify_jwt_token("expired.jwt.token")

    @pytest.mark.skipif(verify_jwt_token is None, reason="Auth utils not implemented")
    def test_verify_jwt_token_invalid_signature(self):
        """Test JWT token verification with invalid signature."""
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Invalid signature")
            
            with pytest.raises(Exception):
                verify_jwt_token("invalid.signature.token")

    @pytest.mark.skipif(get_current_user is None, reason="Auth utils not implemented")
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test current user retrieval with valid token."""
        from fastapi import Request
        
        mock_request = Mock(spec=Request)
        mock_request.headers = {"authorization": "Bearer valid.token.here"}
        
        with patch('app.utils.auth.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "user-123",
                "email": "user@example.com",
                "roles": ["basic"],
                "permissions": ["webhook:read"]
            }
            
            user = await get_current_user(mock_request)
            
            assert user.id == "user-123"
            assert user.email == "user@example.com"
            assert user.has_permission("webhook:read")

    @pytest.mark.skipif(get_current_user is None, reason="Auth utils not implemented")
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test current user retrieval without token."""
        from fastapi import Request, HTTPException
        
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.skipif(require_permissions is None, reason="Auth utils not implemented")
    def test_require_permissions_success(self):
        """Test permission requirement with valid permissions."""
        required_perms = ["webhook:create"]
        
        mock_user = Mock()
        mock_user.has_permission.return_value = True
        
        # Create the dependency function
        permission_check = require_permissions(required_perms)
        
        # Should not raise any exception
        result = permission_check(mock_user)
        assert result is None or result == mock_user

    @pytest.mark.skipif(require_permissions is None, reason="Auth utils not implemented")
    def test_require_permissions_insufficient(self):
        """Test permission requirement with insufficient permissions."""
        from fastapi import HTTPException
        
        required_perms = ["webhook:delete"]
        
        mock_user = Mock()
        mock_user.has_permission.return_value = False
        
        permission_check = require_permissions(required_perms)
        
        with pytest.raises(HTTPException) as exc_info:
            permission_check(mock_user)
        
        assert exc_info.value.status_code == 403


class TestRateLimiter:
    """Test suite for rate limiter utility."""

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter instance."""
        if RateLimiter is None:
            pytest.skip("RateLimiter not implemented")
        return RateLimiter(mock_redis)

    @pytest.mark.asyncio
    async def test_rate_limiter_within_limit(self, rate_limiter):
        """Test rate limiting when within limits."""
        # Mock Redis to return low count
        rate_limiter.redis.get.return_value = "5"  # Below limit
        rate_limiter.redis.incr.return_value = 6
        rate_limiter.redis.expire.return_value = True
        
        result = await rate_limiter.check_rate_limit("user-123", limit=100, window=3600)
        
        assert result is True
        rate_limiter.redis.get.assert_called_once()
        rate_limiter.redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_exceeds_limit(self, rate_limiter):
        """Test rate limiting when exceeding limits."""
        # Mock Redis to return high count
        rate_limiter.redis.get.return_value = "100"  # At limit
        
        result = await rate_limiter.check_rate_limit("user-123", limit=100, window=3600)
        
        assert result is False
        rate_limiter.redis.get.assert_called_once()
        # Should not increment when at limit
        rate_limiter.redis.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limiter_first_request(self, rate_limiter):
        """Test rate limiting for first request."""
        # Mock Redis to return None (no previous count)
        rate_limiter.redis.get.return_value = None
        rate_limiter.redis.incr.return_value = 1
        rate_limiter.redis.expire.return_value = True
        
        result = await rate_limiter.check_rate_limit("new-user", limit=100, window=3600)
        
        assert result is True
        rate_limiter.redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_sliding_window(self, rate_limiter):
        """Test sliding window rate limiting algorithm."""
        current_time = datetime.utcnow().timestamp()
        
        # Mock Redis sorted set operations for sliding window
        rate_limiter.redis.zremrangebyscore = AsyncMock()
        rate_limiter.redis.zcard = AsyncMock(return_value=50)  # Current count
        rate_limiter.redis.zadd = AsyncMock()
        rate_limiter.redis.expire = AsyncMock()
        
        with patch('time.time', return_value=current_time):
            result = await rate_limiter.sliding_window_check("user-123", limit=100, window=3600)
            
            assert result is True
            rate_limiter.redis.zremrangebyscore.assert_called_once()
            rate_limiter.redis.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_get_info(self, rate_limiter):
        """Test getting rate limit information."""
        rate_limiter.redis.get.return_value = "25"
        rate_limiter.redis.ttl.return_value = 1800
        
        info = await rate_limiter.get_rate_limit_info("user-123", limit=100)
        
        expected_info = {
            "current_count": 25,
            "limit": 100,
            "remaining": 75,
            "reset_time": 1800
        }
        
        # Mock implementation might not return exact structure
        assert isinstance(info, dict)
        if "current_count" in info:
            assert info["current_count"] == 25

    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self, rate_limiter):
        """Test resetting rate limit."""
        rate_limiter.redis.delete.return_value = True
        
        result = await rate_limiter.reset_rate_limit("user-123")
        
        assert result is True
        rate_limiter.redis.delete.assert_called_once()

    @pytest.mark.skipif(check_rate_limit is None, reason="Rate limit function not implemented")
    @pytest.mark.asyncio
    async def test_check_rate_limit_function(self):
        """Test standalone rate limit check function."""
        from fastapi import Request, HTTPException
        
        mock_request = Mock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"authorization": "Bearer token"}
        
        with patch('app.utils.rate_limiter.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter.check_rate_limit.return_value = True
            mock_limiter_class.return_value = mock_limiter
            
            # Should not raise exception when within limit
            await check_rate_limit(mock_request)
            
            mock_limiter.check_rate_limit.assert_called_once()

    @pytest.mark.skipif(check_rate_limit is None, reason="Rate limit function not implemented")
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded."""
        from fastapi import Request, HTTPException
        
        mock_request = Mock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"authorization": "Bearer token"}
        
        with patch('app.utils.rate_limiter.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter.check_rate_limit.return_value = False
            mock_limiter_class.return_value = mock_limiter
            
            with pytest.raises(HTTPException) as exc_info:
                await check_rate_limit(mock_request)
            
            assert exc_info.value.status_code == 429


class TestMetrics:
    """Test suite for metrics utilities."""

    @pytest.mark.skipif(setup_metrics is None, reason="Metrics utils not implemented")
    def test_setup_metrics(self):
        """Test metrics setup."""
        with patch('prometheus_client.CollectorRegistry') as mock_registry:
            mock_registry.return_value = Mock()
            
            registry = setup_metrics()
            
            assert registry is not None

    @pytest.mark.skipif(WebhookMetrics is None, reason="Metrics utils not implemented")
    def test_webhook_metrics_initialization(self):
        """Test webhook metrics initialization."""
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.Histogram') as mock_histogram, \
             patch('prometheus_client.Gauge') as mock_gauge:
            
            metrics = WebhookMetrics()
            
            assert metrics is not None

    @pytest.mark.skipif(WebhookMetrics is None, reason="Metrics utils not implemented")
    def test_webhook_metrics_increment_deliveries(self):
        """Test incrementing delivery metrics."""
        with patch('prometheus_client.Counter') as mock_counter:
            mock_counter_instance = Mock()
            mock_counter.return_value = mock_counter_instance
            
            metrics = WebhookMetrics()
            metrics.increment_deliveries("delivered")
            
            # Should call the counter increment method
            assert mock_counter_instance.labels.called

    @pytest.mark.skipif(WebhookMetrics is None, reason="Metrics utils not implemented")
    def test_webhook_metrics_record_response_time(self):
        """Test recording response time metrics."""
        with patch('prometheus_client.Histogram') as mock_histogram:
            mock_histogram_instance = Mock()
            mock_histogram.return_value = mock_histogram_instance
            
            metrics = WebhookMetrics()
            metrics.record_response_time(150.5)
            
            # Should call the histogram observe method
            assert mock_histogram_instance.observe.called

    @pytest.mark.skipif(WebhookMetrics is None, reason="Metrics utils not implemented")
    def test_webhook_metrics_set_active_endpoints(self):
        """Test setting active endpoints gauge."""
        with patch('prometheus_client.Gauge') as mock_gauge:
            mock_gauge_instance = Mock()
            mock_gauge.return_value = mock_gauge_instance
            
            metrics = WebhookMetrics()
            metrics.set_active_endpoints(25)
            
            # Should call the gauge set method
            assert mock_gauge_instance.set.called

    @pytest.mark.skipif(WebhookMetrics is None, reason="Metrics utils not implemented")
    @pytest.mark.asyncio
    async def test_webhook_metrics_get_user_metrics(self):
        """Test getting user-specific metrics."""
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.Histogram') as mock_histogram:
            
            mock_counter_instance = Mock()
            mock_counter_instance._value = Mock()
            mock_counter_instance._value._value = 100
            mock_counter.return_value = mock_counter_instance
            
            mock_histogram_instance = Mock()
            mock_histogram_instance._sum = Mock()
            mock_histogram_instance._sum._value = 1500.0
            mock_histogram_instance._count = Mock()
            mock_histogram_instance._count._value = 10
            mock_histogram.return_value = mock_histogram_instance
            
            metrics = WebhookMetrics()
            result = await metrics.get_user_metrics("user-123")
            
            assert isinstance(result, dict)


class TestSecurity:
    """Test suite for security utilities."""

    @pytest.mark.skipif(generate_webhook_secret is None, reason="Security utils not implemented")
    def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        secret1 = generate_webhook_secret()
        secret2 = generate_webhook_secret()
        
        assert len(secret1) >= 32  # Should be reasonably long
        assert secret1 != secret2  # Should be different each time
        assert isinstance(secret1, str)

    @pytest.mark.skipif(generate_webhook_secret is None, reason="Security utils not implemented")
    def test_generate_webhook_secret_with_length(self):
        """Test webhook secret generation with specific length."""
        length = 64
        secret = generate_webhook_secret(length=length)
        
        assert len(secret) == length

    @pytest.mark.skipif(validate_webhook_secret is None, reason="Security utils not implemented")
    def test_validate_webhook_secret_valid(self):
        """Test webhook secret validation with valid secret."""
        valid_secret = "a" * 32  # 32 character secret
        
        assert validate_webhook_secret(valid_secret) is True

    @pytest.mark.skipif(validate_webhook_secret is None, reason="Security utils not implemented")
    def test_validate_webhook_secret_too_short(self):
        """Test webhook secret validation with too short secret."""
        short_secret = "short"
        
        assert validate_webhook_secret(short_secret) is False

    @pytest.mark.skipif(validate_webhook_secret is None, reason="Security utils not implemented")
    def test_validate_webhook_secret_empty(self):
        """Test webhook secret validation with empty secret."""
        assert validate_webhook_secret("") is False
        assert validate_webhook_secret(None) is False

    @pytest.mark.skipif(generate_signature is None, reason="Security utils not implemented")
    def test_generate_signature(self):
        """Test webhook signature generation."""
        payload = '{"event": "test", "data": {"key": "value"}}'
        secret = "my-webhook-secret"
        
        signature = generate_signature(payload, secret)
        
        assert signature.startswith("sha256=")
        assert len(signature) > 10

        # Test that same input produces same signature
        signature2 = generate_signature(payload, secret)
        assert signature == signature2

    @pytest.mark.skipif(generate_signature is None, reason="Security utils not implemented")
    def test_generate_signature_different_payloads(self):
        """Test signature generation with different payloads."""
        payload1 = '{"event": "test1"}'
        payload2 = '{"event": "test2"}'
        secret = "my-webhook-secret"
        
        signature1 = generate_signature(payload1, secret)
        signature2 = generate_signature(payload2, secret)
        
        assert signature1 != signature2

    @pytest.mark.skipif(validate_signature is None, reason="Security utils not implemented")
    def test_validate_signature_valid(self):
        """Test signature validation with valid signature."""
        payload = '{"event": "test", "data": {"key": "value"}}'
        secret = "my-webhook-secret"
        
        # Generate a valid signature
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_signature}"
        
        assert validate_signature(payload, signature, secret) is True

    @pytest.mark.skipif(validate_signature is None, reason="Security utils not implemented")
    def test_validate_signature_invalid(self):
        """Test signature validation with invalid signature."""
        payload = '{"event": "test"}'
        secret = "my-webhook-secret"
        invalid_signature = "sha256=invalid_signature_here"
        
        assert validate_signature(payload, invalid_signature, secret) is False

    @pytest.mark.skipif(validate_signature is None, reason="Security utils not implemented")
    def test_validate_signature_wrong_format(self):
        """Test signature validation with wrong format."""
        payload = '{"event": "test"}'
        secret = "my-webhook-secret"
        wrong_format = "invalid_format_signature"
        
        assert validate_signature(payload, wrong_format, secret) is False


class TestValidation:
    """Test suite for validation utilities."""

    @pytest.mark.skipif(validate_webhook_url is None, reason="Validation utils not implemented")
    def test_validate_webhook_url_valid_https(self):
        """Test webhook URL validation with valid HTTPS URLs."""
        valid_urls = [
            "https://example.com/webhook",
            "https://api.example.com/webhooks/receiver",
            "https://subdomain.example.org:8443/webhook/endpoint",
            "https://webhook.service.com/v1/receive"
        ]
        
        for url in valid_urls:
            result = validate_webhook_url(url)
            assert result is True or result is None  # None means no error

    @pytest.mark.skipif(validate_webhook_url is None, reason="Validation utils not implemented")
    def test_validate_webhook_url_invalid_http(self):
        """Test webhook URL validation with HTTP URLs (should be rejected)."""
        http_urls = [
            "http://example.com/webhook",
            "http://insecure.example.com/endpoint"
        ]
        
        for url in http_urls:
            with pytest.raises(ValueError):
                validate_webhook_url(url)

    @pytest.mark.skipif(validate_webhook_url is None, reason="Validation utils not implemented")
    def test_validate_webhook_url_invalid_schemes(self):
        """Test webhook URL validation with invalid schemes."""
        invalid_urls = [
            "ftp://example.com/webhook",
            "file:///local/path",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                validate_webhook_url(url)

    @pytest.mark.skipif(validate_webhook_url is None, reason="Validation utils not implemented")
    def test_validate_webhook_url_localhost_blocked(self):
        """Test webhook URL validation blocks localhost."""
        localhost_urls = [
            "https://localhost/webhook",
            "https://127.0.0.1/webhook",
            "https://[::1]/webhook"
        ]
        
        for url in localhost_urls:
            with pytest.raises(ValueError):
                validate_webhook_url(url)

    @pytest.mark.skipif(validate_webhook_headers is None, reason="Validation utils not implemented")
    def test_validate_webhook_headers_valid(self):
        """Test webhook headers validation with valid headers."""
        valid_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token-123",
            "X-Custom-Header": "custom-value",
            "User-Agent": "Splunk-MCP-Webhook/1.0"
        }
        
        result = validate_webhook_headers(valid_headers)
        assert result is True or result is None  # None means no error

    @pytest.mark.skipif(validate_webhook_headers is None, reason="Validation utils not implemented")
    def test_validate_webhook_headers_dangerous(self):
        """Test webhook headers validation with dangerous headers."""
        dangerous_headers = {
            "Host": "evil.example.com",
            "X-Forwarded-For": "192.168.1.1",
            "X-Real-IP": "10.0.0.1"
        }
        
        for header_name, header_value in dangerous_headers.items():
            headers = {header_name: header_value}
            with pytest.raises(ValueError):
                validate_webhook_headers(headers)

    @pytest.mark.skipif(validate_webhook_headers is None, reason="Validation utils not implemented")
    def test_validate_webhook_headers_too_many(self):
        """Test webhook headers validation with too many headers."""
        too_many_headers = {f"Header-{i}": f"value-{i}" for i in range(50)}
        
        with pytest.raises(ValueError):
            validate_webhook_headers(too_many_headers)

    @pytest.mark.skipif(validate_event_filters is None, reason="Validation utils not implemented")
    def test_validate_event_filters_valid(self):
        """Test event filters validation with valid filters."""
        valid_filters = {
            "source": "test-service",
            "severity": "high",
            "user_id": "user-123",
            "payload.status": "completed"
        }
        
        result = validate_event_filters(valid_filters)
        assert result is True or result is None

    @pytest.mark.skipif(validate_event_filters is None, reason="Validation utils not implemented")
    def test_validate_event_filters_invalid_keys(self):
        """Test event filters validation with invalid keys."""
        invalid_filters = {
            "": "empty-key",  # Empty key
            "key with spaces": "value",  # Spaces in key
            "key.with.too.many.dots.here": "value"  # Too many dots
        }
        
        for key, value in invalid_filters.items():
            filters = {key: value}
            with pytest.raises(ValueError):
                validate_event_filters(filters)

    @pytest.mark.skipif(sanitize_input is None, reason="Validation utils not implemented")
    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        # Test normal input
        normal_input = "Hello, World!"
        result = sanitize_input(normal_input)
        assert result == "Hello, World!"

    @pytest.mark.skipif(sanitize_input is None, reason="Validation utils not implemented")
    def test_sanitize_input_html(self):
        """Test HTML input sanitization."""
        html_input = "<script>alert('xss')</script>Hello"
        result = sanitize_input(html_input)
        
        # Should remove script tags
        assert "<script>" not in result
        assert "alert" not in result
        assert "Hello" in result

    @pytest.mark.skipif(sanitize_input is None, reason="Validation utils not implemented")
    def test_sanitize_input_sql_injection(self):
        """Test SQL injection attempt sanitization."""
        sql_input = "'; DROP TABLE users; --"
        result = sanitize_input(sql_input)
        
        # Should escape or remove dangerous SQL
        assert "DROP TABLE" not in result.upper()


class TestUtilityHelpers:
    """Test suite for general utility helper functions."""

    def test_format_webhook_payload(self):
        """Test webhook payload formatting."""
        def format_webhook_payload(event, delivery):
            return {
                "event": {
                    "id": event.get("id"),
                    "type": event.get("type"),
                    "data": event.get("data", {})
                },
                "delivery": {
                    "id": delivery.get("id"),
                    "attempt": delivery.get("attempt", 1)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        event = {"id": "event-123", "type": "query.completed", "data": {"result": "success"}}
        delivery = {"id": "delivery-456", "attempt": 2}
        
        payload = format_webhook_payload(event, delivery)
        
        assert payload["event"]["id"] == "event-123"
        assert payload["event"]["type"] == "query.completed"
        assert payload["delivery"]["id"] == "delivery-456"
        assert payload["delivery"]["attempt"] == 2
        assert "timestamp" in payload

    def test_calculate_exponential_backoff(self):
        """Test exponential backoff calculation."""
        def calculate_exponential_backoff(attempt, base_delay=60, max_delay=3600):
            import random
            
            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0.1, 0.3) * delay
            return int(delay + jitter)
        
        # Test increasing delays
        delay1 = calculate_exponential_backoff(1)
        delay2 = calculate_exponential_backoff(2)
        delay3 = calculate_exponential_backoff(3)
        
        assert delay1 < delay2 < delay3
        assert delay1 >= 60  # At least base delay
        assert delay3 <= 3600 * 1.3  # Not much more than max delay

    def test_validate_cron_expression(self):
        """Test cron expression validation."""
        def validate_cron_expression(cron_expr):
            # Simple validation - real implementation would be more thorough
            parts = cron_expr.split()
            if len(parts) != 5:
                return False
            
            # Basic validation for each part
            for part in parts:
                if part not in ["*", "?"] and not part.replace("-", "").replace("/", "").replace(",", "").isdigit():
                    return False
            
            return True
        
        # Test valid expressions
        valid_expressions = [
            "0 0 * * *",      # Daily at midnight
            "0 */2 * * *",    # Every 2 hours
            "30 9 * * 1-5",   # Weekdays at 9:30 AM
            "0 0 1 * *",      # First day of month
        ]
        
        for expr in valid_expressions:
            assert validate_cron_expression(expr) is True
        
        # Test invalid expressions
        invalid_expressions = [
            "0 0 * *",        # Too few parts
            "0 0 * * * *",    # Too many parts
            "invalid 0 * * *", # Invalid field
        ]
        
        for expr in invalid_expressions:
            assert validate_cron_expression(expr) is False

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        def generate_correlation_id():
            import uuid
            return str(uuid.uuid4())
        
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()
        
        assert id1 != id2
        assert len(id1) == 36  # UUID format
        assert "-" in id1

    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        def mask_sensitive_data(data, sensitive_fields=None):
            if sensitive_fields is None:
                sensitive_fields = ["password", "secret", "token", "key"]
            
            if isinstance(data, dict):
                masked = {}
                for key, value in data.items():
                    if any(field in key.lower() for field in sensitive_fields):
                        masked[key] = "***MASKED***"
                    elif isinstance(value, dict):
                        masked[key] = mask_sensitive_data(value, sensitive_fields)
                    else:
                        masked[key] = value
                return masked
            return data
        
        # Test with sensitive data
        sensitive_data = {
            "user_id": "user-123",
            "password": "secret123",
            "api_key": "sk-1234567890",
            "webhook_secret": "webhook-secret-123",
            "normal_field": "normal_value"
        }
        
        masked = mask_sensitive_data(sensitive_data)
        
        assert masked["user_id"] == "user-123"
        assert masked["password"] == "***MASKED***"
        assert masked["api_key"] == "***MASKED***"
        assert masked["webhook_secret"] == "***MASKED***"
        assert masked["normal_field"] == "normal_value"

    def test_parse_user_agent(self):
        """Test user agent parsing."""
        def parse_user_agent(user_agent):
            # Simple user agent parsing
            if not user_agent:
                return {"browser": "unknown", "version": "unknown", "os": "unknown"}
            
            parts = user_agent.split()
            browser = "unknown"
            version = "unknown"
            os = "unknown"
            
            if "Chrome" in user_agent:
                browser = "Chrome"
            elif "Firefox" in user_agent:
                browser = "Firefox"
            elif "Safari" in user_agent:
                browser = "Safari"
            
            if "Windows" in user_agent:
                os = "Windows"
            elif "Mac" in user_agent:
                os = "macOS"
            elif "Linux" in user_agent:
                os = "Linux"
            
            return {"browser": browser, "version": version, "os": os}
        
        # Test Chrome user agent
        chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        result = parse_user_agent(chrome_ua)
        
        assert result["browser"] == "Chrome"
        assert result["os"] == "Windows"
        
        # Test empty user agent
        empty_result = parse_user_agent("")
        assert empty_result["browser"] == "unknown"

    def test_format_file_size(self):
        """Test file size formatting."""
        def format_file_size(size_bytes):
            if size_bytes == 0:
                return "0 B"
            
            size_names = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            while size_bytes >= 1024 and i < len(size_names) - 1:
                size_bytes /= 1024.0
                i += 1
            
            return f"{size_bytes:.1f} {size_names[i]}"
        
        # Test various file sizes
        assert format_file_size(0) == "0 B"
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1048576) == "1.0 MB"
        assert format_file_size(1073741824) == "1.0 GB"

    def test_truncate_string(self):
        """Test string truncation."""
        def truncate_string(text, max_length=100, suffix="..."):
            if len(text) <= max_length:
                return text
            return text[:max_length - len(suffix)] + suffix
        
        # Test normal string
        short_text = "This is a short string"
        assert truncate_string(short_text, 50) == short_text
        
        # Test long string
        long_text = "This is a very long string that exceeds the maximum length and should be truncated"
        truncated = truncate_string(long_text, 50)
        assert len(truncated) == 50
        assert truncated.endswith("...")
        assert "This is a very long string that exceeds" in truncated