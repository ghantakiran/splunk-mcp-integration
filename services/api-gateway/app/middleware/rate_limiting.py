"""
Rate Limiting Middleware

FastAPI middleware for applying rate limits to API requests with comprehensive
monitoring, flexible configuration, and detailed analytics.
"""

import time
from typing import Callable, Optional, List, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import redis.asyncio as redis

from ..core.rate_limiting import (
    get_rate_limit_manager,
    create_rate_limit_response,
    add_rate_limit_headers,
    RateLimitStatus
)
from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import RateLimitExceededError

logger = get_logger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with support for multiple algorithms,
    flexible policies, and comprehensive monitoring.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        redis_url: str = None,
        enabled: bool = True,
        exempt_paths: Optional[List[str]] = None,
        monitoring_enabled: bool = True
    ):
        super().__init__(app)
        self.redis_url = redis_url or settings.redis_url
        self.enabled = enabled
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        self.monitoring_enabled = monitoring_enabled
        self._redis_client: Optional[redis.Redis] = None
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get Redis client with connection pooling"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        return self._redis_client
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from rate limiting"""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    def _get_endpoint_type(self, request: Request) -> Optional[str]:
        """Determine endpoint type for specialized rate limiting"""
        path = request.url.path
        method = request.method
        
        # Authentication endpoints
        if "/auth/" in path:
            return "auth"
        
        # Query endpoints (heavy operations)
        if "/queries" in path and method == "POST":
            return "query"
        
        # Export endpoints (heavy operations)
        if "/export" in path:
            return "export"
        
        # Dashboard operations (heavy operations)
        if "/dashboards" in path and method in ["POST", "PUT"]:
            return "dashboard"
        
        # File upload endpoints
        if "/upload" in path:
            return "upload"
        
        return None
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for user-based rate limiting"""
        # Try to get user ID from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user:
            return str(user.id)
        
        # Try to extract from JWT token claims
        token_data = getattr(request.state, "token_data", None)
        if token_data:
            return token_data.get("sub")
        
        return None
    
    async def _log_rate_limit_metrics(
        self,
        request: Request,
        allowed: bool,
        statuses: List[RateLimitStatus],
        user_id: Optional[str] = None,
        response_time: Optional[float] = None
    ):
        """Log rate limiting metrics for monitoring"""
        if not self.monitoring_enabled:
            return
        
        try:
            redis_client = await self._get_redis_client()
            
            # Create metrics key
            timestamp = int(time.time() // 60)  # Minute-level metrics
            metrics_key = f"rate_limit_metrics:{timestamp}"
            
            # Increment counters
            pipe = redis_client.pipeline()
            
            # Total requests
            pipe.hincrby(metrics_key, "total_requests", 1)
            
            # Allowed/blocked requests
            if allowed:
                pipe.hincrby(metrics_key, "allowed_requests", 1)
            else:
                pipe.hincrby(metrics_key, "blocked_requests", 1)
            
            # Per-endpoint metrics
            endpoint = request.url.path
            pipe.hincrby(metrics_key, f"endpoint:{endpoint}", 1)
            
            # Per-user metrics (if authenticated)
            if user_id:
                pipe.hincrby(metrics_key, f"user:{user_id}", 1)
            
            # Per-IP metrics
            client_ip = request.client.host
            pipe.hincrby(metrics_key, f"ip:{client_ip}", 1)
            
            # Response time metrics
            if response_time:
                pipe.hset(metrics_key, "avg_response_time", response_time)
            
            # Policy-specific metrics
            for status in statuses:
                pipe.hincrby(metrics_key, f"policy:{status.policy_name}", 1)
                if not allowed:
                    pipe.hincrby(metrics_key, f"policy:{status.policy_name}:blocked", 1)
            
            # Set TTL for metrics (keep for 24 hours)
            pipe.expire(metrics_key, 86400)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to log rate limit metrics: {e}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        
        start_time = time.time()
        
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        try:
            # Get Redis client and rate limit manager
            redis_client = await self._get_redis_client()
            rate_manager = await get_rate_limit_manager(redis_client)
            
            # Extract request context
            user_id = self._extract_user_id(request)
            endpoint_type = self._get_endpoint_type(request)
            
            # Check rate limits
            allowed, statuses = await rate_manager.check_rate_limits(
                request=request,
                user_id=user_id,
                endpoint_type=endpoint_type
            )
            
            response_time = time.time() - start_time
            
            # Log metrics
            await self._log_rate_limit_metrics(
                request=request,
                allowed=allowed,
                statuses=statuses,
                user_id=user_id,
                response_time=response_time
            )
            
            # Handle rate limit exceeded
            if not allowed:
                # Find the most restrictive status for response
                most_restrictive = min(statuses, key=lambda s: s.remaining)
                
                logger.warning(
                    "Rate limit exceeded",
                    user_id=user_id,
                    client_ip=request.client.host,
                    endpoint=request.url.path,
                    method=request.method,
                    policy=most_restrictive.policy_name,
                    limit=most_restrictive.limit,
                    remaining=most_restrictive.remaining
                )
                
                return create_rate_limit_response(most_restrictive)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            response = add_rate_limit_headers(response, statuses)
            
            return response
            
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting middleware: {e}")
            # Continue without rate limiting if Redis is unavailable
            return await call_next(request)
        
        except Exception as e:
            logger.error(f"Unexpected error in rate limiting middleware: {e}")
            # Continue without rate limiting on unexpected errors
            return await call_next(request)


class RateLimitBypass:
    """Context manager for bypassing rate limits (for testing/admin)"""
    
    def __init__(self, middleware: RateLimitingMiddleware):
        self.middleware = middleware
        self.original_enabled = None
    
    def __enter__(self):
        self.original_enabled = self.middleware.enabled
        self.middleware.enabled = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.middleware.enabled = self.original_enabled


def create_rate_limiting_middleware(
    app: ASGIApp,
    redis_url: str = None,
    enabled: bool = None,
    exempt_paths: Optional[List[str]] = None
) -> RateLimitingMiddleware:
    """Factory function to create rate limiting middleware"""
    
    if enabled is None:
        enabled = settings.rate_limiting_enabled
    
    if redis_url is None:
        redis_url = settings.redis_url
    
    return RateLimitingMiddleware(
        app=app,
        redis_url=redis_url,
        enabled=enabled,
        exempt_paths=exempt_paths
    )


# Dependency for getting rate limit information in endpoints
async def get_request_rate_limits(request: Request) -> Dict[str, Any]:
    """Dependency to get rate limit information for current request"""
    
    try:
        redis_client = redis.from_url(settings.redis_url)
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Extract user ID from request
        user_id = None
        user = getattr(request.state, "user", None)
        if user:
            user_id = str(user.id)
        
        return await rate_manager.get_rate_limit_info(request, user_id)
        
    except Exception as e:
        logger.error(f"Failed to get rate limit information: {e}")
        return {"error": "Rate limit information unavailable"}


# Rate limit configuration for different endpoint types
ENDPOINT_RATE_LIMITS = {
    "auth": {
        "login": {"limit": 5, "window": 300},      # 5 attempts per 5 minutes
        "register": {"limit": 3, "window": 3600},  # 3 registrations per hour
        "password_reset": {"limit": 3, "window": 3600}
    },
    "query": {
        "execute": {"limit": 100, "window": 3600}, # 100 queries per hour
        "complex": {"limit": 10, "window": 600}    # 10 complex queries per 10 minutes
    },
    "upload": {
        "file": {"limit": 20, "window": 3600},     # 20 uploads per hour
        "large_file": {"limit": 5, "window": 3600} # 5 large files per hour
    },
    "export": {
        "report": {"limit": 10, "window": 3600},   # 10 exports per hour
        "bulk": {"limit": 3, "window": 3600}       # 3 bulk exports per hour
    }
}