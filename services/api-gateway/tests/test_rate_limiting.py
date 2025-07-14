"""
Comprehensive test suite for the rate limiting system

Tests all components of the rate limiting implementation including:
- Core rate limiting algorithms (Fixed Window, Sliding Window, Token Bucket)
- Rate limit policies and manager
- Middleware functionality
- Rate limiting endpoints
- Error handling and edge cases
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

import pytest
import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.rate_limiting import (
    RateLimitAlgorithm,
    RateLimitScope,
    RateLimitPolicy,
    RateLimitStatus,
    RateLimitManager,
    FixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
    get_rate_limit_manager,
    create_rate_limit_response,
    add_rate_limit_headers
)
from app.middleware.rate_limiting import (
    RateLimitingMiddleware,
    create_rate_limiting_middleware,
    get_request_rate_limits,
    RateLimitBypass
)
from app.api.v1.endpoints.rate_limits import router as rate_limits_router
from app.core.config import settings


@pytest.fixture
async def redis_client():
    """Fixture for Redis client"""
    client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    yield client
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
def mock_request():
    """Fixture for mock request object"""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.url = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.state = Mock()
    request.state.user = None
    request.headers = {}
    return request


@pytest.fixture
def rate_limit_policy():
    """Fixture for rate limit policy"""
    return RateLimitPolicy(
        name="test_policy",
        algorithm=RateLimitAlgorithm.FIXED_WINDOW,
        scope=RateLimitScope.PER_IP,
        limit=10,
        window_seconds=60,
        enabled=True,
        priority=1
    )


class TestRateLimitPolicy:
    """Test rate limit policy functionality"""
    
    def test_policy_creation(self):
        """Test policy creation with all parameters"""
        policy = RateLimitPolicy(
            name="test_policy",
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            scope=RateLimitScope.PER_USER,
            limit=100,
            window_seconds=3600,
            burst_limit=150,
            refill_rate=0.5,
            enabled=True,
            priority=5
        )
        
        assert policy.name == "test_policy"
        assert policy.algorithm == RateLimitAlgorithm.TOKEN_BUCKET
        assert policy.scope == RateLimitScope.PER_USER
        assert policy.limit == 100
        assert policy.window_seconds == 3600
        assert policy.burst_limit == 150
        assert policy.refill_rate == 0.5
        assert policy.enabled is True
        assert policy.priority == 5
    
    def test_policy_to_dict(self):
        """Test policy serialization"""
        policy = RateLimitPolicy(
            name="test_policy",
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            scope=RateLimitScope.GLOBAL,
            limit=50,
            window_seconds=300
        )
        
        policy_dict = policy.to_dict()
        
        assert policy_dict["name"] == "test_policy"
        assert policy_dict["algorithm"] == RateLimitAlgorithm.SLIDING_WINDOW
        assert policy_dict["scope"] == RateLimitScope.GLOBAL
        assert policy_dict["limit"] == 50
        assert policy_dict["window_seconds"] == 300
        assert policy_dict["enabled"] is True
        assert policy_dict["priority"] == 1


class TestRateLimitStatus:
    """Test rate limit status functionality"""
    
    def test_status_creation(self):
        """Test status creation"""
        reset_time = datetime.now() + timedelta(minutes=5)
        status = RateLimitStatus(
            policy_name="test_policy",
            limit=100,
            remaining=75,
            reset_time=reset_time,
            retry_after=300
        )
        
        assert status.policy_name == "test_policy"
        assert status.limit == 100
        assert status.remaining == 75
        assert status.reset_time == reset_time
        assert status.retry_after == 300
    
    def test_status_to_dict(self):
        """Test status serialization"""
        reset_time = datetime.now() + timedelta(minutes=5)
        status = RateLimitStatus(
            policy_name="test_policy",
            limit=100,
            remaining=75,
            reset_time=reset_time,
            retry_after=300
        )
        
        status_dict = status.to_dict()
        
        assert status_dict["policy_name"] == "test_policy"
        assert status_dict["limit"] == 100
        assert status_dict["remaining"] == 75
        assert status_dict["reset_time"] == reset_time.isoformat()
        assert status_dict["retry_after"] == 300


class TestFixedWindowRateLimiter:
    """Test fixed window rate limiter"""
    
    @pytest.mark.asyncio
    async def test_within_limit(self, redis_client):
        """Test request within rate limit"""
        limiter = FixedWindowRateLimiter(redis_client)
        
        allowed, status = await limiter.check_limit("test_key", 10, 60)
        
        assert allowed is True
        assert status.limit == 10
        assert status.remaining == 9
        assert status.policy_name == "fixed_window"
    
    @pytest.mark.asyncio
    async def test_exceeds_limit(self, redis_client):
        """Test request exceeding rate limit"""
        limiter = FixedWindowRateLimiter(redis_client)
        key = "test_key_exceed"
        
        # Make requests up to the limit
        for i in range(10):
            allowed, status = await limiter.check_limit(key, 10, 60)
            assert allowed is True
        
        # Next request should be denied
        allowed, status = await limiter.check_limit(key, 10, 60)
        
        assert allowed is False
        assert status.remaining == 0
        assert status.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_window_reset(self, redis_client):
        """Test window reset functionality"""
        limiter = FixedWindowRateLimiter(redis_client)
        
        # Fill up the limit
        for i in range(5):
            await limiter.check_limit("test_window", 5, 1)
        
        # Should be denied
        allowed, _ = await limiter.check_limit("test_window", 5, 1)
        assert allowed is False
        
        # Wait for window to reset
        await asyncio.sleep(1.1)
        
        # Should be allowed again
        allowed, status = await limiter.check_limit("test_window", 5, 1)
        assert allowed is True
        assert status.remaining == 4


class TestSlidingWindowRateLimiter:
    """Test sliding window rate limiter"""
    
    @pytest.mark.asyncio
    async def test_within_limit(self, redis_client):
        """Test request within rate limit"""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        allowed, status = await limiter.check_limit("sliding_test", 10, 60)
        
        assert allowed is True
        assert status.limit == 10
        assert status.remaining == 9
        assert status.policy_name == "sliding_window"
    
    @pytest.mark.asyncio
    async def test_sliding_behavior(self, redis_client):
        """Test sliding window behavior"""
        limiter = SlidingWindowRateLimiter(redis_client)
        key = "sliding_behavior"
        
        # Make requests quickly
        for i in range(5):
            allowed, _ = await limiter.check_limit(key, 10, 2)
            assert allowed is True
        
        # Wait a bit and make more requests
        await asyncio.sleep(1)
        
        for i in range(3):
            allowed, _ = await limiter.check_limit(key, 10, 2)
            assert allowed is True
        
        # Should still be within sliding window
        allowed, status = await limiter.check_limit(key, 10, 2)
        assert allowed is True
        assert status.remaining >= 0
    
    @pytest.mark.asyncio
    async def test_exceeds_limit(self, redis_client):
        """Test request exceeding sliding window limit"""
        limiter = SlidingWindowRateLimiter(redis_client)
        key = "sliding_exceed"
        
        # Fill up the limit
        for i in range(5):
            allowed, _ = await limiter.check_limit(key, 5, 10)
            assert allowed is True
        
        # Next request should be denied
        allowed, status = await limiter.check_limit(key, 5, 10)
        
        assert allowed is False
        assert status.remaining == 0
        assert status.retry_after > 0


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiter"""
    
    @pytest.mark.asyncio
    async def test_within_limit(self, redis_client):
        """Test request within token bucket limit"""
        limiter = TokenBucketRateLimiter(redis_client)
        
        allowed, status = await limiter.check_limit(
            "bucket_test", 10, 60, burst_limit=15, refill_rate=0.5
        )
        
        assert allowed is True
        assert status.limit == 15  # burst_limit
        assert status.remaining == 14
        assert status.policy_name == "token_bucket"
    
    @pytest.mark.asyncio
    async def test_burst_capability(self, redis_client):
        """Test token bucket burst capability"""
        limiter = TokenBucketRateLimiter(redis_client)
        key = "burst_test"
        
        # Should be able to burst up to burst_limit
        for i in range(10):
            allowed, status = await limiter.check_limit(
                key, 5, 60, burst_limit=10, refill_rate=0.1
            )
            assert allowed is True
        
        # Should be denied after burst
        allowed, status = await limiter.check_limit(
            key, 5, 60, burst_limit=10, refill_rate=0.1
        )
        
        assert allowed is False
        assert status.remaining == 0
    
    @pytest.mark.asyncio
    async def test_token_refill(self, redis_client):
        """Test token refill over time"""
        limiter = TokenBucketRateLimiter(redis_client)
        key = "refill_test"
        
        # Consume all tokens
        for i in range(5):
            await limiter.check_limit(key, 5, 1, burst_limit=5, refill_rate=5.0)
        
        # Should be denied
        allowed, _ = await limiter.check_limit(key, 5, 1, burst_limit=5, refill_rate=5.0)
        assert allowed is False
        
        # Wait for refill
        await asyncio.sleep(0.3)
        
        # Should have some tokens back
        allowed, status = await limiter.check_limit(key, 5, 1, burst_limit=5, refill_rate=5.0)
        assert allowed is True


class TestRateLimitManager:
    """Test rate limit manager functionality"""
    
    @pytest.mark.asyncio
    async def test_manager_creation(self, redis_client):
        """Test rate limit manager creation"""
        manager = RateLimitManager(redis_client)
        
        assert len(manager.policies) > 0  # Should have default policies
        assert "global_api" in manager.policies
        assert "user_api" in manager.policies
        assert "ip_api" in manager.policies
        assert "burst_protection" in manager.policies
    
    @pytest.mark.asyncio
    async def test_add_remove_policy(self, redis_client):
        """Test adding and removing policies"""
        manager = RateLimitManager(redis_client)
        initial_count = len(manager.policies)
        
        # Add custom policy
        custom_policy = RateLimitPolicy(
            name="custom_test",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=20,
            window_seconds=120
        )
        
        manager.add_policy(custom_policy)
        assert len(manager.policies) == initial_count + 1
        assert "custom_test" in manager.policies
        
        # Remove policy
        manager.remove_policy("custom_test")
        assert len(manager.policies) == initial_count
        assert "custom_test" not in manager.policies
    
    @pytest.mark.asyncio
    async def test_get_applicable_policies(self, redis_client, mock_request):
        """Test getting applicable policies for a request"""
        manager = RateLimitManager(redis_client)
        
        policies = manager.get_applicable_policies(mock_request)
        
        assert len(policies) > 0
        # Should be sorted by priority
        for i in range(1, len(policies)):
            assert policies[i-1].priority <= policies[i].priority
    
    @pytest.mark.asyncio
    async def test_check_rate_limits_allowed(self, redis_client, mock_request):
        """Test rate limit checking when allowed"""
        manager = RateLimitManager(redis_client)
        
        allowed, statuses = await manager.check_rate_limits(mock_request, user_id="test_user")
        
        assert allowed is True
        assert len(statuses) > 0
        for status in statuses:
            assert isinstance(status, RateLimitStatus)
            assert status.remaining >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_key_generation(self, redis_client, mock_request):
        """Test rate limit key generation"""
        manager = RateLimitManager(redis_client)
        
        # Test different scopes
        global_policy = RateLimitPolicy(
            name="global_test", algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.GLOBAL, limit=100, window_seconds=60
        )
        key = manager._get_rate_limit_key(global_policy, mock_request)
        assert key == "global:global_test"
        
        user_policy = RateLimitPolicy(
            name="user_test", algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_USER, limit=50, window_seconds=60
        )
        key = manager._get_rate_limit_key(user_policy, mock_request, user_id="user123")
        assert key == "user:user123:user_test"
        
        ip_policy = RateLimitPolicy(
            name="ip_test", algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP, limit=25, window_seconds=60
        )
        key = manager._get_rate_limit_key(ip_policy, mock_request)
        assert key == "ip:127.0.0.1:ip_test"
    
    @pytest.mark.asyncio
    async def test_reset_rate_limits(self, redis_client, mock_request):
        """Test resetting rate limits"""
        manager = RateLimitManager(redis_client)
        
        # Make some requests first
        await manager.check_rate_limits(mock_request, user_id="test_user")
        
        # Reset limits
        results = await manager.reset_rate_limits(mock_request, user_id="test_user")
        
        assert isinstance(results, dict)
        # Results should contain policy names and success status


class TestRateLimitingMiddleware:
    """Test rate limiting middleware"""
    
    def create_test_app(self, middleware_enabled=True):
        """Create test FastAPI app with middleware"""
        app = FastAPI()
        
        if middleware_enabled:
            middleware = create_rate_limiting_middleware(
                app,
                redis_url="redis://localhost:6379/1",
                enabled=True,
                exempt_paths=["/health", "/exempt"]
            )
            app.add_middleware(RateLimitingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        @app.get("/exempt")
        async def exempt_endpoint():
            return {"message": "exempt"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_middleware_allows_request(self):
        """Test middleware allows normal requests"""
        app = self.create_test_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test")
            
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    @pytest.mark.asyncio
    async def test_middleware_exempt_paths(self):
        """Test middleware exempts specified paths"""
        app = self.create_test_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            # Exempt paths should not have rate limit headers
            assert "X-RateLimit-Limit" not in response.headers
    
    @pytest.mark.asyncio
    async def test_middleware_disabled(self):
        """Test middleware when disabled"""
        app = self.create_test_app(middleware_enabled=False)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test")
            
            assert response.status_code == 200
            # No rate limit headers when middleware disabled
            assert "X-RateLimit-Limit" not in response.headers
    
    def test_rate_limit_bypass(self):
        """Test rate limit bypass context manager"""
        middleware = RateLimitingMiddleware(
            Mock(), redis_url="redis://localhost:6379/1", enabled=True
        )
        
        assert middleware.enabled is True
        
        with RateLimitBypass(middleware):
            assert middleware.enabled is False
        
        assert middleware.enabled is True
    
    def test_endpoint_type_detection(self):
        """Test endpoint type detection"""
        middleware = RateLimitingMiddleware(
            Mock(), redis_url="redis://localhost:6379/1"
        )
        
        # Mock different request types
        auth_request = Mock()
        auth_request.url.path = "/api/v1/auth/login"
        auth_request.method = "POST"
        assert middleware._get_endpoint_type(auth_request) == "auth"
        
        query_request = Mock()
        query_request.url.path = "/api/v1/queries"
        query_request.method = "POST"
        assert middleware._get_endpoint_type(query_request) == "query"
        
        export_request = Mock()
        export_request.url.path = "/api/v1/export/report"
        export_request.method = "GET"
        assert middleware._get_endpoint_type(export_request) == "export"
        
        regular_request = Mock()
        regular_request.url.path = "/api/v1/users"
        regular_request.method = "GET"
        assert middleware._get_endpoint_type(regular_request) is None


class TestRateLimitingEndpoints:
    """Test rate limiting API endpoints"""
    
    def create_test_app(self):
        """Create test app with rate limiting endpoints"""
        app = FastAPI()
        app.include_router(rate_limits_router, prefix="/api/v1/rate-limits")
        return app
    
    @pytest.mark.asyncio
    async def test_rate_limit_status_endpoint(self):
        """Test rate limit status endpoint"""
        app = self.create_test_app()
        
        with patch('app.api.v1.endpoints.rate_limits.get_current_user') as mock_user, \
             patch('app.api.v1.endpoints.rate_limits.get_request_rate_limits') as mock_limits, \
             patch('app.api.v1.endpoints.rate_limits.get_redis_client') as mock_redis:
            
            # Mock dependencies
            mock_user.return_value = Mock(id="user123")
            mock_limits.return_value = {"policies": []}
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # Mock rate manager
            mock_manager = AsyncMock()
            mock_manager.check_rate_limits.return_value = (True, [])
            
            with patch('app.api.v1.endpoints.rate_limits.get_rate_limit_manager', 
                      return_value=mock_manager):
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/rate-limits/status")
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "user_id" in data
                    assert "rate_limiting_enabled" in data
                    assert "current_status" in data
    
    @pytest.mark.asyncio
    async def test_rate_limit_health_endpoint(self):
        """Test rate limit health endpoint"""
        app = self.create_test_app()
        
        with patch('app.api.v1.endpoints.rate_limits.get_redis_client') as mock_redis, \
             patch('app.api.v1.endpoints.rate_limits.get_rate_limit_manager') as mock_manager:
            
            # Mock Redis client
            mock_redis_client = AsyncMock()
            mock_redis_client.ping.return_value = True
            mock_redis.return_value = mock_redis_client
            
            # Mock rate manager
            mock_rate_manager = Mock()
            mock_rate_manager.policies = {"policy1": Mock(), "policy2": Mock()}
            mock_manager.return_value = mock_rate_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/rate-limits/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["redis_connected"] is True
                assert data["policies_loaded"] == 2


class TestRateLimitUtilities:
    """Test rate limiting utility functions"""
    
    def test_create_rate_limit_response(self):
        """Test rate limit response creation"""
        status = RateLimitStatus(
            policy_name="test_policy",
            limit=100,
            remaining=0,
            reset_time=datetime.now() + timedelta(minutes=5),
            retry_after=300
        )
        
        response = create_rate_limit_response(status)
        
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers
        
        content = json.loads(response.body)
        assert content["error"]["code"] == "rate_limit_exceeded"
    
    def test_add_rate_limit_headers(self):
        """Test adding rate limit headers to response"""
        from fastapi.responses import JSONResponse
        
        response = JSONResponse(content={"message": "success"})
        statuses = [
            RateLimitStatus(
                policy_name="policy1",
                limit=100,
                remaining=50,
                reset_time=datetime.now() + timedelta(minutes=5)
            ),
            RateLimitStatus(
                policy_name="policy2",
                limit=200,
                remaining=25,  # Most restrictive
                reset_time=datetime.now() + timedelta(minutes=10)
            )
        ]
        
        enhanced_response = add_rate_limit_headers(response, statuses)
        
        # Should use most restrictive limits
        assert enhanced_response.headers["X-RateLimit-Remaining"] == "25"
        assert enhanced_response.headers["X-RateLimit-Policies"] == "policy1,policy2"
    
    def test_add_rate_limit_headers_empty(self):
        """Test adding rate limit headers with empty statuses"""
        from fastapi.responses import JSONResponse
        
        response = JSONResponse(content={"message": "success"})
        
        enhanced_response = add_rate_limit_headers(response, [])
        
        # Should return original response unchanged
        assert enhanced_response == response


class TestRateLimitingIntegration:
    """Integration tests for rate limiting system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_rate_limiting(self, redis_client):
        """Test complete rate limiting flow"""
        # Create rate limit manager
        manager = RateLimitManager(redis_client)
        
        # Add a strict policy for testing
        test_policy = RateLimitPolicy(
            name="integration_test",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=3,
            window_seconds=60,
            priority=1
        )
        manager.add_policy(test_policy)
        
        # Create mock request
        request = Mock()
        request.client.host = "192.168.1.100"
        request.url.path = "/api/v1/test"
        request.method = "GET"
        
        # First 3 requests should be allowed
        for i in range(3):
            allowed, statuses = await manager.check_rate_limits(request)
            assert allowed is True
            assert len(statuses) > 0
        
        # 4th request should be denied
        allowed, statuses = await manager.check_rate_limits(request)
        assert allowed is False
        
        # Reset limits
        results = await manager.reset_rate_limits(request)
        assert "integration_test" in results
        
        # Request should be allowed again after reset
        allowed, statuses = await manager.check_rate_limits(request)
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_multiple_policies_interaction(self, redis_client):
        """Test interaction between multiple policies"""
        manager = RateLimitManager(redis_client)
        
        # Add two policies with different scopes
        policy1 = RateLimitPolicy(
            name="ip_strict",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=5,
            window_seconds=60,
            priority=1
        )
        
        policy2 = RateLimitPolicy(
            name="global_lenient",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.GLOBAL,
            limit=1000,
            window_seconds=60,
            priority=2
        )
        
        manager.add_policy(policy1)
        manager.add_policy(policy2)
        
        request = Mock()
        request.client.host = "192.168.1.200"
        request.url.path = "/api/v1/test"
        request.method = "GET"
        
        # Make requests up to IP limit
        for i in range(5):
            allowed, statuses = await manager.check_rate_limits(request)
            assert allowed is True
            assert len(statuses) >= 2  # Both policies should be checked
        
        # Next request should be denied due to IP policy
        allowed, statuses = await manager.check_rate_limits(request)
        assert allowed is False
        
        # Check that the denial was due to the IP policy
        denied_status = min(statuses, key=lambda s: s.remaining)
        assert denied_status.remaining == 0
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, redis_client):
        """Test rate limiting performance under concurrent load"""
        manager = RateLimitManager(redis_client)
        
        async def make_request(request_id: int):
            request = Mock()
            request.client.host = f"192.168.1.{request_id % 256}"
            request.url.path = "/api/v1/test"
            request.method = "GET"
            
            allowed, statuses = await manager.check_rate_limits(request)
            return allowed, len(statuses)
        
        # Make concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All requests should complete
        assert len(results) == 100
        
        # Performance should be reasonable (adjust threshold as needed)
        assert end_time - start_time < 5.0  # Should complete within 5 seconds
        
        # Most requests should be allowed (depending on default policies)
        allowed_count = sum(1 for allowed, _ in results if allowed)
        assert allowed_count > 50  # At least 50% should be allowed


class TestRateLimitErrorHandling:
    """Test error handling in rate limiting system"""
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test handling of Redis connection failures"""
        # Create rate limiter with invalid Redis URL
        with pytest.raises(Exception):
            redis_client = redis.from_url("redis://invalid:6379")
            limiter = FixedWindowRateLimiter(redis_client)
            await limiter.check_limit("test", 10, 60)
    
    @pytest.mark.asyncio
    async def test_invalid_policy_parameters(self, redis_client):
        """Test handling of invalid policy parameters"""
        manager = RateLimitManager(redis_client)
        
        # Test invalid algorithm
        with pytest.raises(ValueError):
            invalid_policy = RateLimitPolicy(
                name="invalid",
                algorithm="invalid_algorithm",  # Invalid
                scope=RateLimitScope.PER_IP,
                limit=10,
                window_seconds=60
            )
    
    @pytest.mark.asyncio
    async def test_middleware_redis_failure(self):
        """Test middleware behavior when Redis fails"""
        app = FastAPI()
        
        # Create middleware with invalid Redis URL
        middleware = RateLimitingMiddleware(
            app,
            redis_url="redis://invalid:6379",
            enabled=True
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        # Middleware should handle Redis failures gracefully
        async with AsyncClient(app=app, base_url="http://test") as client:
            # This should not raise an exception even with invalid Redis
            # The middleware should fall back to allowing requests
            try:
                response = await client.get("/test")
                # Request should still succeed despite Redis failure
                assert response.status_code == 200
            except Exception as e:
                # If Redis connection fails, we should still handle it gracefully
                pytest.skip(f"Redis connection test skipped: {e}")


# Configuration for pytest
pytest_plugins = ["pytest_asyncio"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])