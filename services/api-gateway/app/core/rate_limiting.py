"""
API Rate Limiting System

Provides comprehensive rate limiting capabilities with multiple algorithms,
flexible configuration, and detailed monitoring.
"""

import time
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from uuid import UUID
import asyncio

import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from .config import settings
from .logging import get_logger
from .exceptions import RateLimitExceededError

logger = get_logger(__name__)


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(str, Enum):
    """Rate limiting scopes"""
    GLOBAL = "global"
    PER_USER = "per_user"
    PER_IP = "per_ip"
    PER_ENDPOINT = "per_endpoint"
    PER_API_KEY = "per_api_key"


@dataclass
class RateLimitPolicy:
    """Rate limiting policy configuration"""
    name: str
    algorithm: RateLimitAlgorithm
    scope: RateLimitScope
    limit: int
    window_seconds: int
    burst_limit: Optional[int] = None
    refill_rate: Optional[float] = None
    enabled: bool = True
    priority: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RateLimitStatus:
    """Current rate limit status"""
    policy_name: str
    limit: int
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_time": self.reset_time.isoformat(),
            "retry_after": self.retry_after
        }


class FixedWindowRateLimiter:
    """Fixed window rate limiter implementation"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, RateLimitStatus]:
        """Check if request is within rate limit"""
        
        now = int(time.time())
        window_start = now - (now % window_seconds)
        rate_key = f"rate_limit:fixed:{key}:{window_start}"
        
        # Get current count
        current_count = await self.redis.get(rate_key)
        current_count = int(current_count) if current_count else 0
        
        # Check if limit exceeded
        if current_count >= limit:
            reset_time = datetime.fromtimestamp(window_start + window_seconds)
            retry_after = int((reset_time - datetime.now()).total_seconds())
            
            return False, RateLimitStatus(
                policy_name="fixed_window",
                limit=limit,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(1, retry_after)
            )
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, window_seconds)
        await pipe.execute()
        
        reset_time = datetime.fromtimestamp(window_start + window_seconds)
        remaining = max(0, limit - current_count - 1)
        
        return True, RateLimitStatus(
            policy_name="fixed_window",
            limit=limit,
            remaining=remaining,
            reset_time=reset_time
        )


class SlidingWindowRateLimiter:
    """Sliding window rate limiter implementation"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, RateLimitStatus]:
        """Check if request is within rate limit using sliding window"""
        
        now = time.time()
        cutoff = now - window_seconds
        rate_key = f"rate_limit:sliding:{key}"
        
        # Remove old entries and count current requests
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(rate_key, 0, cutoff)
        pipe.zcard(rate_key)
        pipe.zadd(rate_key, {str(now): now})
        pipe.expire(rate_key, window_seconds)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if limit exceeded (excluding the current request)
        if current_count >= limit:
            # Find the oldest request to determine reset time
            oldest_requests = await self.redis.zrange(rate_key, 0, 0, withscores=True)
            if oldest_requests:
                oldest_time = oldest_requests[0][1]
                reset_time = datetime.fromtimestamp(oldest_time + window_seconds)
                retry_after = int((reset_time - datetime.now()).total_seconds())
            else:
                reset_time = datetime.fromtimestamp(now + window_seconds)
                retry_after = window_seconds
            
            # Remove the request we just added since it's rejected
            await self.redis.zrem(rate_key, str(now))
            
            return False, RateLimitStatus(
                policy_name="sliding_window",
                limit=limit,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(1, retry_after)
            )
        
        remaining = max(0, limit - current_count)
        reset_time = datetime.fromtimestamp(now + window_seconds)
        
        return True, RateLimitStatus(
            policy_name="sliding_window",
            limit=limit,
            remaining=remaining,
            reset_time=reset_time
        )


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        burst_limit: Optional[int] = None,
        refill_rate: Optional[float] = None
    ) -> Tuple[bool, RateLimitStatus]:
        """Check if request is within rate limit using token bucket"""
        
        bucket_size = burst_limit or limit
        refill_rate = refill_rate or (limit / window_seconds)
        
        now = time.time()
        rate_key = f"rate_limit:bucket:{key}"
        
        # Get current bucket state
        bucket_data = await self.redis.get(rate_key)
        if bucket_data:
            bucket_info = json.loads(bucket_data)
            tokens = bucket_info["tokens"]
            last_refill = bucket_info["last_refill"]
        else:
            tokens = bucket_size
            last_refill = now
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = time_elapsed * refill_rate
        tokens = min(bucket_size, tokens + tokens_to_add)
        
        # Check if we can consume a token
        if tokens < 1:
            # Calculate when next token will be available
            time_for_token = (1 - tokens) / refill_rate
            reset_time = datetime.fromtimestamp(now + time_for_token)
            retry_after = int(time_for_token) + 1
            
            return False, RateLimitStatus(
                policy_name="token_bucket",
                limit=bucket_size,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )
        
        # Consume a token
        tokens -= 1
        
        # Save bucket state
        bucket_info = {
            "tokens": tokens,
            "last_refill": now
        }
        await self.redis.setex(
            rate_key, 
            window_seconds * 2,  # Keep state longer than window
            json.dumps(bucket_info)
        )
        
        reset_time = datetime.fromtimestamp(now + window_seconds)
        
        return True, RateLimitStatus(
            policy_name="token_bucket",
            limit=bucket_size,
            remaining=int(tokens),
            reset_time=reset_time
        )


class RateLimitManager:
    """Central rate limiting manager"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.policies: Dict[str, RateLimitPolicy] = {}
        self.limiters = {
            RateLimitAlgorithm.FIXED_WINDOW: FixedWindowRateLimiter(redis_client),
            RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowRateLimiter(redis_client),
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketRateLimiter(redis_client)
        }
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default rate limiting policies"""
        
        # Global API limits
        self.policies["global_api"] = RateLimitPolicy(
            name="global_api",
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            scope=RateLimitScope.GLOBAL,
            limit=10000,
            window_seconds=3600,  # 10k requests per hour globally
            priority=1
        )
        
        # Per-user limits
        self.policies["user_api"] = RateLimitPolicy(
            name="user_api",
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            scope=RateLimitScope.PER_USER,
            limit=1000,
            window_seconds=3600,  # 1k requests per hour per user
            priority=2
        )
        
        # Per-IP limits (for unauthenticated requests)
        self.policies["ip_api"] = RateLimitPolicy(
            name="ip_api",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=100,
            window_seconds=3600,  # 100 requests per hour per IP
            priority=3
        )
        
        # Burst protection
        self.policies["burst_protection"] = RateLimitPolicy(
            name="burst_protection",
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            scope=RateLimitScope.PER_USER,
            limit=50,
            window_seconds=60,  # 50 requests per minute
            burst_limit=100,    # Can burst up to 100
            refill_rate=0.83,   # ~50 per minute
            priority=4
        )
        
        # High-cost endpoint limits (queries, exports, etc.)
        self.policies["heavy_operations"] = RateLimitPolicy(
            name="heavy_operations",
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            scope=RateLimitScope.PER_USER,
            limit=10,
            window_seconds=300,  # 10 heavy operations per 5 minutes
            priority=5
        )
        
        # Authentication endpoint limits
        self.policies["auth_endpoints"] = RateLimitPolicy(
            name="auth_endpoints",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=5,
            window_seconds=300,  # 5 login attempts per 5 minutes per IP
            priority=6
        )
    
    def add_policy(self, policy: RateLimitPolicy):
        """Add a custom rate limiting policy"""
        self.policies[policy.name] = policy
        logger.info(f"Added rate limiting policy: {policy.name}")
    
    def remove_policy(self, policy_name: str):
        """Remove a rate limiting policy"""
        if policy_name in self.policies:
            del self.policies[policy_name]
            logger.info(f"Removed rate limiting policy: {policy_name}")
    
    def get_applicable_policies(
        self, 
        request: Request, 
        endpoint_type: Optional[str] = None
    ) -> List[RateLimitPolicy]:
        """Get applicable policies for a request"""
        
        applicable = []
        
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            
            # Check if policy applies to this endpoint type
            if endpoint_type:
                if policy.name == "heavy_operations" and endpoint_type not in ["query", "export", "dashboard"]:
                    continue
                if policy.name == "auth_endpoints" and endpoint_type != "auth":
                    continue
            
            applicable.append(policy)
        
        # Sort by priority (lower number = higher priority)
        return sorted(applicable, key=lambda p: p.priority)
    
    def _get_rate_limit_key(
        self, 
        policy: RateLimitPolicy, 
        request: Request, 
        user_id: Optional[str] = None
    ) -> str:
        """Generate rate limit key for a policy and request"""
        
        if policy.scope == RateLimitScope.GLOBAL:
            return f"global:{policy.name}"
        elif policy.scope == RateLimitScope.PER_USER and user_id:
            return f"user:{user_id}:{policy.name}"
        elif policy.scope == RateLimitScope.PER_IP:
            client_ip = request.client.host
            return f"ip:{client_ip}:{policy.name}"
        elif policy.scope == RateLimitScope.PER_ENDPOINT:
            endpoint = request.url.path
            return f"endpoint:{endpoint}:{policy.name}"
        elif policy.scope == RateLimitScope.PER_API_KEY:
            # Would extract API key from headers
            api_key = request.headers.get("X-API-Key", "unknown")
            return f"apikey:{api_key}:{policy.name}"
        else:
            # Fallback to IP-based for unauthenticated users
            client_ip = request.client.host
            return f"ip:{client_ip}:{policy.name}"
    
    async def check_rate_limits(
        self, 
        request: Request, 
        user_id: Optional[str] = None,
        endpoint_type: Optional[str] = None
    ) -> Tuple[bool, List[RateLimitStatus]]:
        """Check all applicable rate limits for a request"""
        
        policies = self.get_applicable_policies(request, endpoint_type)
        statuses = []
        
        for policy in policies:
            key = self._get_rate_limit_key(policy, request, user_id)
            limiter = self.limiters[policy.algorithm]
            
            if policy.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                allowed, status = await limiter.check_limit(
                    key, 
                    policy.limit, 
                    policy.window_seconds,
                    policy.burst_limit,
                    policy.refill_rate
                )
            else:
                allowed, status = await limiter.check_limit(
                    key, 
                    policy.limit, 
                    policy.window_seconds
                )
            
            statuses.append(status)
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    policy=policy.name,
                    key=key,
                    limit=policy.limit,
                    window=policy.window_seconds
                )
                return False, statuses
        
        return True, statuses
    
    async def get_rate_limit_info(
        self, 
        request: Request, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limit information for a request"""
        
        policies = self.get_applicable_policies(request)
        info = {
            "policies": [],
            "limits": []
        }
        
        for policy in policies:
            key = self._get_rate_limit_key(policy, request, user_id)
            
            info["policies"].append({
                "name": policy.name,
                "algorithm": policy.algorithm.value,
                "scope": policy.scope.value,
                "limit": policy.limit,
                "window_seconds": policy.window_seconds,
                "key": key
            })
        
        return info
    
    async def reset_rate_limits(
        self, 
        request: Request, 
        user_id: Optional[str] = None,
        policy_names: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Reset rate limits for a request (admin function)"""
        
        policies = self.get_applicable_policies(request)
        if policy_names:
            policies = [p for p in policies if p.name in policy_names]
        
        results = {}
        
        for policy in policies:
            key = self._get_rate_limit_key(policy, request, user_id)
            
            # Delete all possible rate limit keys for this policy
            pattern_keys = [
                f"rate_limit:fixed:{key}:*",
                f"rate_limit:sliding:{key}",
                f"rate_limit:bucket:{key}"
            ]
            
            deleted = 0
            for pattern in pattern_keys:
                if "*" in pattern:
                    # Scan and delete matching keys
                    async for key_name in self.redis.scan_iter(match=pattern):
                        await self.redis.delete(key_name)
                        deleted += 1
                else:
                    deleted += await self.redis.delete(pattern)
            
            results[policy.name] = deleted > 0
            
            logger.info(
                "Rate limits reset",
                policy=policy.name,
                key=key,
                deleted_keys=deleted
            )
        
        return results


# Global rate limit manager instance
rate_limit_manager: Optional[RateLimitManager] = None


async def get_rate_limit_manager(redis_client: redis.Redis) -> RateLimitManager:
    """Get or create rate limit manager instance"""
    global rate_limit_manager
    
    if rate_limit_manager is None:
        rate_limit_manager = RateLimitManager(redis_client)
    
    return rate_limit_manager


def create_rate_limit_response(status: RateLimitStatus) -> JSONResponse:
    """Create rate limit exceeded response"""
    
    content = {
        "error": {
            "message": "Rate limit exceeded",
            "code": "rate_limit_exceeded",
            "details": status.to_dict()
        }
    }
    
    headers = {
        "X-RateLimit-Limit": str(status.limit),
        "X-RateLimit-Remaining": str(status.remaining),
        "X-RateLimit-Reset": str(int(status.reset_time.timestamp()))
    }
    
    if status.retry_after:
        headers["Retry-After"] = str(status.retry_after)
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=content,
        headers=headers
    )


def add_rate_limit_headers(
    response: Any, 
    statuses: List[RateLimitStatus]
) -> Any:
    """Add rate limit headers to response"""
    
    if not statuses:
        return response
    
    # Use the most restrictive limits for headers
    most_restrictive = min(statuses, key=lambda s: s.remaining)
    
    response.headers["X-RateLimit-Limit"] = str(most_restrictive.limit)
    response.headers["X-RateLimit-Remaining"] = str(most_restrictive.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(most_restrictive.reset_time.timestamp()))
    
    # Add policy information
    policy_names = [s.policy_name for s in statuses]
    response.headers["X-RateLimit-Policies"] = ",".join(policy_names)
    
    return response