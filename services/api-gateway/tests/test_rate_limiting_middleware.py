"""
Dedicated tests for rate limiting middleware functionality

Focuses on middleware-specific behavior, request handling,
and integration with FastAPI applications.
"""

import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

import pytest
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.responses import JSONResponse

from app.middleware.rate_limiting import (
    RateLimitingMiddleware,
    create_rate_limiting_middleware,
    get_request_rate_limits,
    RateLimitBypass,
    ENDPOINT_RATE_LIMITS
)
from app.core.rate_limiting import RateLimitStatus, RateLimitManager
from app.models.user import User


class TestRateLimitingMiddlewareIntegration:
    """Test middleware integration with FastAPI applications"""
    
    def create_test_app_with_auth(self):
        """Create test app with authentication and rate limiting"""
        app = FastAPI()
        
        # Add rate limiting middleware
        middleware = RateLimitingMiddleware(
            app,
            redis_url="redis://localhost:6379/1",
            enabled=True,
            exempt_paths=["/health", "/public"],
            monitoring_enabled=True
        )
        app.add_middleware(type(middleware), **middleware.__dict__)
        
        # Mock user for authentication
        async def get_current_user():
            user = Mock(spec=User)
            user.id = "test_user_123"
            user.username = "testuser"
            user.roles = ["user"]
            return user
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/protected")
        async def protected_endpoint(current_user: User = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}
        
        @app.post("/api/v1/auth/login")
        async def login():
            return {"token": "test_token"}
        
        @app.post("/api/v1/queries")
        async def execute_query():
            return {"results": []}
        
        @app.get("/api/v1/export/report")
        async def export_report():
            return {"download_url": "http://example.com/report.pdf"}
        
        @app.post("/api/v1/upload")
        async def upload_file():
            return {"file_id": "uploaded_123"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_middleware_request_lifecycle(self):
        """Test complete request lifecycle through middleware"""
        app = self.create_test_app_with_auth()
        
        with patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            # Mock rate limit manager
            mock_manager = AsyncMock(spec=RateLimitManager)
            mock_manager.check_rate_limits.return_value = (True, [
                RateLimitStatus(
                    policy_name="test_policy",
                    limit=100,
                    remaining=99,
                    reset_time=time.time() + 3600
                )
            ])
            mock_manager_factory.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/protected")
                
                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers
                
                # Verify rate limit manager was called
                mock_manager.check_rate_limits.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_exempt_paths(self):
        """Test that exempt paths bypass rate limiting"""
        app = self.create_test_app_with_auth()
        
        with patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            mock_manager = AsyncMock()
            mock_manager_factory.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test exempt paths
                for path in ["/health", "/public"]:
                    response = await client.get(path)
                    assert response.status_code == 200
                    # Rate limit headers should not be present
                    assert "X-RateLimit-Limit" not in response.headers
                
                # Rate limit manager should not be called for exempt paths
                mock_manager.check_rate_limits.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_endpoint_type_detection(self):
        """Test endpoint type detection for specialized rate limiting"""
        app = self.create_test_app_with_auth()
        
        test_cases = [
            ("/api/v1/auth/login", "POST", "auth"),
            ("/api/v1/queries", "POST", "query"),
            ("/api/v1/export/report", "GET", "export"),
            ("/api/v1/upload", "POST", "upload"),
            ("/api/v1/users", "GET", None),  # Regular endpoint
        ]
        
        middleware = RateLimitingMiddleware(Mock(), redis_url="redis://localhost:6379/1")
        
        for path, method, expected_type in test_cases:
            request = Mock(spec=Request)
            request.url.path = path
            request.method = method
            
            detected_type = middleware._get_endpoint_type(request)
            assert detected_type == expected_type, f"Failed for {method} {path}"
    
    @pytest.mark.asyncio
    async def test_middleware_user_extraction(self):
        """Test user ID extraction from request state"""
        middleware = RateLimitingMiddleware(Mock(), redis_url="redis://localhost:6379/1")
        
        # Test with user in state
        request_with_user = Mock(spec=Request)
        request_with_user.state.user = Mock()
        request_with_user.state.user.id = "user_123"
        request_with_user.state.token_data = None
        
        user_id = middleware._extract_user_id(request_with_user)
        assert user_id == "user_123"
        
        # Test with token data
        request_with_token = Mock(spec=Request)
        request_with_token.state.user = None
        request_with_token.state.token_data = {"sub": "token_user_456"}
        
        user_id = middleware._extract_user_id(request_with_token)
        assert user_id == "token_user_456"
        
        # Test with no user info
        request_no_user = Mock(spec=Request)
        request_no_user.state.user = None
        request_no_user.state.token_data = None
        
        user_id = middleware._extract_user_id(request_no_user)
        assert user_id is None
    
    @pytest.mark.asyncio
    async def test_middleware_rate_limit_exceeded(self):
        """Test middleware behavior when rate limit is exceeded"""
        app = self.create_test_app_with_auth()
        
        with patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            # Mock rate limit manager to deny requests
            mock_manager = AsyncMock(spec=RateLimitManager)
            mock_manager.check_rate_limits.return_value = (False, [
                RateLimitStatus(
                    policy_name="test_policy",
                    limit=10,
                    remaining=0,
                    reset_time=time.time() + 300,
                    retry_after=300
                )
            ])
            mock_manager_factory.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/protected")
                
                assert response.status_code == 429
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers
                assert "Retry-After" in response.headers
                
                data = response.json()
                assert data["error"]["code"] == "rate_limit_exceeded"
    
    @pytest.mark.asyncio
    async def test_middleware_redis_failure_fallback(self):
        """Test middleware fallback when Redis is unavailable"""
        app = self.create_test_app_with_auth()
        
        with patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            # Mock Redis failure
            mock_manager_factory.side_effect = Exception("Redis connection failed")
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/protected")
                
                # Request should still succeed despite Redis failure
                assert response.status_code == 200
                # No rate limit headers should be present
                assert "X-RateLimit-Limit" not in response.headers
    
    @pytest.mark.asyncio
    async def test_middleware_metrics_logging(self):
        """Test middleware metrics logging functionality"""
        app = self.create_test_app_with_auth()
        
        with patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory, \
             patch.object(RateLimitingMiddleware, '_log_rate_limit_metrics') as mock_log_metrics:
            
            mock_manager = AsyncMock(spec=RateLimitManager)
            mock_manager.check_rate_limits.return_value = (True, [])
            mock_manager_factory.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/protected")
                
                assert response.status_code == 200
                # Metrics logging should be called
                mock_log_metrics.assert_called_once()


class TestRateLimitingMiddlewareConfiguration:
    """Test middleware configuration and factory functions"""
    
    def test_create_rate_limiting_middleware_defaults(self):
        """Test middleware creation with default settings"""
        app = FastAPI()
        
        with patch('app.middleware.rate_limiting.settings') as mock_settings:
            mock_settings.rate_limiting_enabled = True
            mock_settings.redis_url = "redis://localhost:6379"
            
            middleware = create_rate_limiting_middleware(app)
            
            assert middleware.enabled is True
            assert middleware.redis_url == "redis://localhost:6379"
            assert "/health" in middleware.exempt_paths
            assert middleware.monitoring_enabled is True
    
    def test_create_rate_limiting_middleware_custom(self):
        """Test middleware creation with custom settings"""
        app = FastAPI()
        
        custom_exempt_paths = ["/custom", "/api/v1/health"]
        middleware = create_rate_limiting_middleware(
            app,
            redis_url="redis://custom:6379",
            enabled=False,
            exempt_paths=custom_exempt_paths
        )
        
        assert middleware.enabled is False
        assert middleware.redis_url == "redis://custom:6379"
        assert middleware.exempt_paths == custom_exempt_paths
    
    def test_middleware_exempt_path_checking(self):
        """Test exempt path checking logic"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379",
            exempt_paths=["/health", "/api/v1/docs", "/static"]
        )
        
        # Test exact matches
        assert middleware._is_exempt_path("/health") is True
        assert middleware._is_exempt_path("/api/v1/docs") is True
        
        # Test prefix matches
        assert middleware._is_exempt_path("/health/check") is True
        assert middleware._is_exempt_path("/api/v1/docs/swagger.json") is True
        assert middleware._is_exempt_path("/static/css/main.css") is True
        
        # Test non-matches
        assert middleware._is_exempt_path("/api/v1/users") is False
        assert middleware._is_exempt_path("/dashboard") is False


class TestRateLimitBypass:
    """Test rate limit bypass functionality"""
    
    def test_bypass_context_manager(self):
        """Test bypass context manager functionality"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379",
            enabled=True
        )
        
        # Initially enabled
        assert middleware.enabled is True
        
        # Use bypass context manager
        with RateLimitBypass(middleware) as bypass:
            assert middleware.enabled is False
            assert bypass.middleware == middleware
        
        # Should be restored after context
        assert middleware.enabled is True
    
    def test_bypass_exception_handling(self):
        """Test bypass context manager with exceptions"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379",
            enabled=True
        )
        
        try:
            with RateLimitBypass(middleware):
                assert middleware.enabled is False
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still be restored after exception
        assert middleware.enabled is True
    
    def test_bypass_nested_usage(self):
        """Test nested bypass usage"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379",
            enabled=True
        )
        
        with RateLimitBypass(middleware):
            assert middleware.enabled is False
            
            # Nested bypass should work
            with RateLimitBypass(middleware):
                assert middleware.enabled is False
            
            # Should still be disabled after inner context
            assert middleware.enabled is False
        
        # Should be restored after outer context
        assert middleware.enabled is True


class TestGetRequestRateLimits:
    """Test rate limit dependency function"""
    
    @pytest.mark.asyncio
    async def test_get_request_rate_limits_success(self):
        """Test successful rate limit information retrieval"""
        mock_request = Mock(spec=Request)
        mock_request.state.user = Mock()
        mock_request.state.user.id = "user_123"
        
        with patch('app.middleware.rate_limiting.redis.from_url') as mock_redis, \
             patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            
            # Mock Redis client
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # Mock rate manager
            mock_manager = AsyncMock()
            mock_manager.get_rate_limit_info.return_value = {
                "policies": [{"name": "test_policy", "limit": 100}],
                "limits": []
            }
            mock_manager_factory.return_value = mock_manager
            
            result = await get_request_rate_limits(mock_request)
            
            assert "policies" in result
            assert len(result["policies"]) == 1
            assert result["policies"][0]["name"] == "test_policy"
    
    @pytest.mark.asyncio
    async def test_get_request_rate_limits_no_user(self):
        """Test rate limit info retrieval without user"""
        mock_request = Mock(spec=Request)
        mock_request.state.user = None
        
        with patch('app.middleware.rate_limiting.redis.from_url') as mock_redis, \
             patch('app.middleware.rate_limiting.get_rate_limit_manager') as mock_manager_factory:
            
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            mock_manager = AsyncMock()
            mock_manager.get_rate_limit_info.return_value = {"policies": [], "limits": []}
            mock_manager_factory.return_value = mock_manager
            
            result = await get_request_rate_limits(mock_request)
            
            # Should call with user_id=None
            mock_manager.get_rate_limit_info.assert_called_once_with(mock_request, None)
    
    @pytest.mark.asyncio
    async def test_get_request_rate_limits_error(self):
        """Test rate limit info retrieval with error"""
        mock_request = Mock(spec=Request)
        
        with patch('app.middleware.rate_limiting.redis.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            result = await get_request_rate_limits(mock_request)
            
            assert "error" in result
            assert result["error"] == "Rate limit information unavailable"


class TestEndpointRateLimitsConfiguration:
    """Test endpoint-specific rate limit configuration"""
    
    def test_endpoint_rate_limits_structure(self):
        """Test that endpoint rate limits are properly structured"""
        assert "auth" in ENDPOINT_RATE_LIMITS
        assert "query" in ENDPOINT_RATE_LIMITS
        assert "upload" in ENDPOINT_RATE_LIMITS
        assert "export" in ENDPOINT_RATE_LIMITS
        
        # Test auth endpoint limits
        auth_limits = ENDPOINT_RATE_LIMITS["auth"]
        assert "login" in auth_limits
        assert "register" in auth_limits
        assert "password_reset" in auth_limits
        
        # Verify structure of individual limits
        login_limit = auth_limits["login"]
        assert "limit" in login_limit
        assert "window" in login_limit
        assert isinstance(login_limit["limit"], int)
        assert isinstance(login_limit["window"], int)
    
    def test_auth_endpoint_limits(self):
        """Test authentication endpoint rate limits"""
        auth_limits = ENDPOINT_RATE_LIMITS["auth"]
        
        # Login should be more restrictive
        assert auth_limits["login"]["limit"] <= 10
        assert auth_limits["login"]["window"] >= 300  # At least 5 minutes
        
        # Registration should be very restrictive
        assert auth_limits["register"]["limit"] <= 5
        assert auth_limits["register"]["window"] >= 3600  # At least 1 hour
    
    def test_query_endpoint_limits(self):
        """Test query endpoint rate limits"""
        query_limits = ENDPOINT_RATE_LIMITS["query"]
        
        # Regular queries should be reasonable
        assert query_limits["execute"]["limit"] >= 50
        
        # Complex queries should be more restrictive
        assert query_limits["complex"]["limit"] <= query_limits["execute"]["limit"]
    
    def test_upload_endpoint_limits(self):
        """Test upload endpoint rate limits"""
        upload_limits = ENDPOINT_RATE_LIMITS["upload"]
        
        # Large file uploads should be more restrictive
        assert upload_limits["large_file"]["limit"] <= upload_limits["file"]["limit"]
    
    def test_export_endpoint_limits(self):
        """Test export endpoint rate limits"""
        export_limits = ENDPOINT_RATE_LIMITS["export"]
        
        # Bulk exports should be more restrictive
        assert export_limits["bulk"]["limit"] <= export_limits["report"]["limit"]


class TestMiddlewareMetricsLogging:
    """Test middleware metrics and logging functionality"""
    
    @pytest.mark.asyncio
    async def test_metrics_logging_success(self):
        """Test successful metrics logging"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379/1",
            monitoring_enabled=True
        )
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/test"
        mock_request.client.host = "192.168.1.1"
        
        mock_statuses = [
            RateLimitStatus(
                policy_name="test_policy",
                limit=100,
                remaining=99,
                reset_time=time.time() + 3600
            )
        ]
        
        with patch.object(middleware, '_get_redis_client') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_pipeline = AsyncMock()
            mock_redis_client.pipeline.return_value = mock_pipeline
            mock_redis.return_value = mock_redis_client
            
            await middleware._log_rate_limit_metrics(
                request=mock_request,
                allowed=True,
                statuses=mock_statuses,
                user_id="user_123",
                response_time=0.5
            )
            
            # Verify pipeline operations
            mock_redis_client.pipeline.assert_called_once()
            mock_pipeline.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_logging_disabled(self):
        """Test metrics logging when disabled"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379/1",
            monitoring_enabled=False
        )
        
        mock_request = Mock(spec=Request)
        
        with patch.object(middleware, '_get_redis_client') as mock_redis:
            await middleware._log_rate_limit_metrics(
                request=mock_request,
                allowed=True,
                statuses=[],
                user_id=None,
                response_time=0.1
            )
            
            # Redis client should not be called when monitoring is disabled
            mock_redis.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_metrics_logging_error_handling(self):
        """Test metrics logging error handling"""
        middleware = RateLimitingMiddleware(
            Mock(),
            redis_url="redis://localhost:6379/1",
            monitoring_enabled=True
        )
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/test"
        mock_request.client.host = "192.168.1.1"
        
        with patch.object(middleware, '_get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis error")
            
            # Should not raise exception even if Redis fails
            await middleware._log_rate_limit_metrics(
                request=mock_request,
                allowed=True,
                statuses=[],
                user_id=None,
                response_time=0.1
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])