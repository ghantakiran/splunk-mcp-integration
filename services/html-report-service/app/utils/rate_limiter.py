#!/usr/bin/env python3
"""
Rate limiting utilities for HTML Report Service.

This module provides rate limiting functionality using Redis
with sliding window algorithm and different limiting strategies.
"""

import time
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from structlog import get_logger

from app.core.config import settings
from app.core.redis_client import get_rate_limiter

logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers
        )


class RateLimitConfig:
    """Rate limit configuration."""
    
    def __init__(
        self,
        requests_per_window: int,
        window_seconds: int,
        burst_allowance: int = 0,
        identifier_func: Optional[callable] = None
    ):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_allowance = burst_allowance
        self.identifier_func = identifier_func or self._default_identifier
    
    def _default_identifier(self, request: Request) -> str:
        """Default identifier function using client IP."""
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"


class RateLimitManager:
    """Rate limit manager with multiple strategies."""
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        
        # Predefined rate limit configurations
        self.configs = {
            "default": RateLimitConfig(
                requests_per_window=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
                window_seconds=60,
                burst_allowance=settings.RATE_LIMIT_BURST
            ),
            "strict": RateLimitConfig(
                requests_per_window=30,
                window_seconds=60,
                burst_allowance=5
            ),
            "lenient": RateLimitConfig(
                requests_per_window=120,
                window_seconds=60,
                burst_allowance=20
            ),
            "user_based": RateLimitConfig(
                requests_per_window=100,
                window_seconds=3600,  # 1 hour
                burst_allowance=10,
                identifier_func=self._user_identifier
            ),
            "endpoint_based": RateLimitConfig(
                requests_per_window=50,
                window_seconds=300,  # 5 minutes
                burst_allowance=5,
                identifier_func=self._endpoint_identifier
            )
        }
    
    def _user_identifier(self, request: Request) -> str:
        """User-based identifier."""
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP-based identification
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _endpoint_identifier(self, request: Request) -> str:
        """Endpoint-based identifier."""
        # Combine IP and endpoint path
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        return f"endpoint:{client_ip}:{endpoint}"
    
    async def check_rate_limit(
        self,
        request: Request,
        config_name: str = "default"
    ) -> Tuple[bool, Dict[str, any]]:
        """Check if request is within rate limits."""
        if config_name not in self.configs:
            logger.warning(f"Unknown rate limit config: {config_name}")
            config_name = "default"
        
        config = self.configs[config_name]
        identifier = config.identifier_func(request)
        
        try:
            # Check basic rate limit
            is_allowed = await self.rate_limiter.is_allowed(
                identifier,
                config.requests_per_window,
                config.window_seconds
            )
            
            # Get current usage
            usage = await self.rate_limiter.get_usage(
                identifier,
                config.window_seconds
            )
            
            # Check burst allowance if needed
            if not is_allowed and config.burst_allowance > 0:
                burst_identifier = f"burst:{identifier}"
                burst_allowed = await self.rate_limiter.is_allowed(
                    burst_identifier,
                    config.burst_allowance,
                    config.window_seconds
                )
                
                if burst_allowed:
                    is_allowed = True
                    usage["burst_used"] = True
                    logger.info(
                        "Burst allowance used",
                        identifier=identifier,
                        config=config_name
                    )
            
            # Add rate limit info to response
            rate_limit_info = {
                "allowed": is_allowed,
                "limit": config.requests_per_window,
                "window_seconds": config.window_seconds,
                "current_count": usage["current_count"],
                "reset_time": usage["current_time"] + config.window_seconds,
                "identifier": identifier,
                "config": config_name
            }
            
            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    **rate_limit_info
                )
            
            return is_allowed, rate_limit_info
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return True, {
                "allowed": True,
                "error": str(e),
                "fallback": True
            }
    
    async def get_rate_limit_status(
        self,
        request: Request,
        config_name: str = "default"
    ) -> Dict[str, any]:
        """Get current rate limit status without checking."""
        if config_name not in self.configs:
            config_name = "default"
        
        config = self.configs[config_name]
        identifier = config.identifier_func(request)
        
        try:
            usage = await self.rate_limiter.get_usage(
                identifier,
                config.window_seconds
            )
            
            return {
                "identifier": identifier,
                "limit": config.requests_per_window,
                "window_seconds": config.window_seconds,
                "current_count": usage["current_count"],
                "remaining": max(0, config.requests_per_window - usage["current_count"]),
                "reset_time": usage["current_time"] + config.window_seconds,
                "config": config_name
            }
            
        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {
                "error": str(e),
                "fallback": True
            }
    
    def add_config(
        self,
        name: str,
        config: RateLimitConfig
    ):
        """Add a new rate limit configuration."""
        self.configs[name] = config
        logger.info(f"Rate limit config '{name}' added")
    
    def remove_config(self, name: str) -> bool:
        """Remove a rate limit configuration."""
        if name in self.configs and name != "default":
            del self.configs[name]
            logger.info(f"Rate limit config '{name}' removed")
            return True
        return False


# Global rate limit manager
rate_limit_manager = RateLimitManager()


# Convenience functions
async def check_rate_limit(
    identifier: str,
    limit: int,
    window_seconds: int
) -> bool:
    """Simple rate limit check function."""
    rate_limiter = get_rate_limiter()
    return await rate_limiter.is_allowed(identifier, limit, window_seconds)


async def get_rate_limit_usage(
    identifier: str,
    window_seconds: int
) -> Dict[str, int]:
    """Get rate limit usage for an identifier."""
    rate_limiter = get_rate_limiter()
    return await rate_limiter.get_usage(identifier, window_seconds)


# FastAPI dependency for rate limiting
def create_rate_limit_dependency(config_name: str = "default"):
    """Create a FastAPI dependency for rate limiting."""
    
    async def rate_limit_dependency(request: Request):
        """Rate limit dependency function."""
        is_allowed, info = await rate_limit_manager.check_rate_limit(
            request,
            config_name
        )
        
        if not is_allowed:
            retry_after = info.get("reset_time", int(time.time()) + 60) - int(time.time())
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after=retry_after
            )
        
        # Add rate limit info to request state for response headers
        request.state.rate_limit_info = info
        
        return info
    
    return rate_limit_dependency


# Middleware for adding rate limit headers
class RateLimitHeadersMiddleware:
    """Middleware to add rate limit headers to responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Process request
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add rate limit headers if available
                headers = list(message.get("headers", []))
                
                # Try to get rate limit info from request state
                request = scope.get("state", {})
                rate_limit_info = request.get("rate_limit_info")
                
                if rate_limit_info and rate_limit_info.get("allowed"):
                    headers.extend([
                        (b"x-ratelimit-limit", str(rate_limit_info["limit"]).encode()),
                        (b"x-ratelimit-remaining", str(
                            max(0, rate_limit_info["limit"] - rate_limit_info["current_count"])
                        ).encode()),
                        (b"x-ratelimit-reset", str(rate_limit_info["reset_time"]).encode()),
                        (b"x-ratelimit-window", str(rate_limit_info["window_seconds"]).encode())
                    ])
                
                message["headers"] = headers
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


# Rate limit decorators
def rate_limit(config_name: str = "default"):
    """Decorator for applying rate limits to functions."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would need request context to work properly
            # For now, just pass through
            return await func(*args, **kwargs)
        return wrapper
    
    return decorator


# Export commonly used components
__all__ = [
    "RateLimitExceeded",
    "RateLimitConfig",
    "RateLimitManager",
    "rate_limit_manager",
    "check_rate_limit",
    "get_rate_limit_usage",
    "create_rate_limit_dependency",
    "RateLimitHeadersMiddleware",
    "rate_limit"
]
