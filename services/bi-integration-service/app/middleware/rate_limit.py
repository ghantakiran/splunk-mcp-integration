"""
Rate limiting middleware for BI Integration Service.
"""

import time
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..core.config import settings
from ..core.redis_client import get_redis_client
from ..core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis for distributed rate limiting."""
    
    def __init__(self, app, default_limit: int = None, default_window: int = None):
        super().__init__(app)
        self.default_limit = default_limit or settings.rate_limit_default_limit
        self.default_window = default_window or settings.rate_limit_default_window
        self.burst_limit = settings.rate_limit_burst_limit
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on user or IP."""
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/health/detailed", "/metrics"]:
            return await call_next(request)
        
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        client_ip = request.client.host if request.client else "unknown"
        
        # Use user ID if available, otherwise use IP
        identifier = user_id or client_ip
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(
            identifier, 
            request.url.path,
            request.method
        )
        
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "identifier": identifier,
                    "path": request.url.path,
                    "method": request.method,
                    "remaining": remaining,
                    "reset_time": reset_time
                }
            )
            
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded",
                        "details": f"Too many requests. Reset in {reset_time} seconds"
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version,
                        "rate_limit": {
                            "limit": self.default_limit,
                            "remaining": remaining,
                            "reset_time": reset_time
                        }
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    async def _check_rate_limit(
        self, 
        identifier: str, 
        path: str, 
        method: str
    ) -> tuple[bool, int, int]:
        """Check if request is within rate limit."""
        try:
            redis_client = await get_redis_client()
            
            # Create rate limit key
            current_time = int(time.time())
            window_start = current_time - (current_time % self.default_window)
            rate_limit_key = f"rate_limit:{identifier}:{window_start}"
            
            # Get current count
            current_count = await redis_client.get(rate_limit_key)
            current_count = int(current_count) if current_count else 0
            
            # Check if within limit
            if current_count >= self.default_limit:
                remaining = 0
                reset_time = window_start + self.default_window - current_time
                return False, remaining, reset_time
            
            # Increment counter
            pipe = redis_client.pipeline()
            pipe.incr(rate_limit_key)
            pipe.expire(rate_limit_key, self.default_window)
            await pipe.execute()
            
            # Calculate remaining and reset time
            remaining = self.default_limit - current_count - 1
            reset_time = window_start + self.default_window - current_time
            
            return True, remaining, reset_time
            
        except Exception as e:
            logger.error(
                f"Rate limit check failed: {e}",
                extra={
                    "identifier": identifier,
                    "path": path,
                    "method": method,
                    "error": str(e)
                }
            )
            
            # Allow request if rate limiting fails
            return True, self.default_limit, self.default_window