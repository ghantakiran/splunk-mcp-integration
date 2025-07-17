"""
Rate limiting utilities for Email Service.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.redis_service import RedisService

logger = get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.default_limit = settings.rate_limit_per_user
        self.window_size = settings.rate_limit_window
    
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        cost: int = 1,
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key (usually user_id or IP)
            limit: Maximum requests per window
            window: Time window in seconds
            cost: Cost of this request (default 1)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        if not limit:
            limit = self.default_limit
        if not window:
            window = self.window_size
        
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=window)
            
            # Use Redis sorted set for sliding window
            rate_key = f"rate_limit:{key}"
            
            # Remove old entries
            await self.redis.client.zremrangebyscore(
                rate_key,
                0,
                window_start.timestamp()
            )
            
            # Count current requests
            current_count = await self.redis.client.zcard(rate_key)
            
            if current_count + cost > limit:
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    current_count=current_count,
                    limit=limit,
                    window=window,
                )
                return False
            
            # Add current request(s)
            for i in range(cost):
                await self.redis.client.zadd(
                    rate_key,
                    {f"{current_time.timestamp()}:{i}": current_time.timestamp()}
                )
            
            # Set expiration for cleanup
            await self.redis.client.expire(rate_key, window * 2)
            
            return True
            
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), key=key)
            # Fail open - allow request if rate limiter is broken
            return True
    
    async def get_rate_limit_status(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get current rate limit status for a key."""
        if not limit:
            limit = self.default_limit
        if not window:
            window = self.window_size
        
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=window)
            
            rate_key = f"rate_limit:{key}"
            
            # Remove old entries
            await self.redis.client.zremrangebyscore(
                rate_key,
                0,
                window_start.timestamp()
            )
            
            # Count current requests
            current_count = await self.redis.client.zcard(rate_key)
            
            # Calculate reset time (when oldest request expires)
            oldest_entries = await self.redis.client.zrange(
                rate_key, 0, 0, withscores=True
            )
            
            reset_time = None
            if oldest_entries:
                oldest_timestamp = oldest_entries[0][1]
                reset_time = datetime.fromtimestamp(oldest_timestamp) + timedelta(seconds=window)
            
            return {
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "used": current_count,
                "window_seconds": window,
                "reset_time": reset_time.isoformat() if reset_time else None,
            }
            
        except Exception as e:
            logger.error("Rate limit status check failed", error=str(e), key=key)
            return {
                "limit": limit,
                "remaining": limit,
                "used": 0,
                "window_seconds": window,
                "reset_time": None,
                "error": str(e),
            }
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key."""
        try:
            rate_key = f"rate_limit:{key}"
            result = await self.redis.client.delete(rate_key)
            logger.info("Rate limit reset", key=key, success=bool(result))
            return bool(result)
        except Exception as e:
            logger.error("Rate limit reset failed", error=str(e), key=key)
            return False
    
    async def check_user_rate_limit(self, user_id: str) -> bool:
        """Check rate limit for a specific user."""
        return await self.check_rate_limit(f"user:{user_id}")
    
    async def check_domain_rate_limit(self, domain: str) -> bool:
        """Check rate limit for an email domain."""
        return await self.check_rate_limit(
            f"domain:{domain}",
            limit=settings.rate_limit_per_domain,
        )
    
    async def check_ip_rate_limit(self, ip_address: str) -> bool:
        """Check rate limit for an IP address."""
        return await self.check_rate_limit(
            f"ip:{ip_address}",
            limit=settings.rate_limit_per_user * 5,  # Higher limit for IP
        )
    
    async def check_email_sending_limit(
        self,
        user_id: str,
        email_type: str = "general",
    ) -> bool:
        """Check email sending rate limit for a user."""
        key = f"email_send:{user_id}:{email_type}"
        
        # Different limits for different email types
        limits = {
            "query": 20,     # 20 query emails per hour
            "report": 10,    # 10 reports per hour  
            "alert": 50,     # 50 alerts per hour
            "general": 30,   # 30 general emails per hour
        }
        
        limit = limits.get(email_type, limits["general"])
        return await self.check_rate_limit(key, limit=limit)
    
    async def get_user_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive rate limit status for a user."""
        try:
            user_status = await self.get_rate_limit_status(f"user:{user_id}")
            
            # Get email-specific limits
            email_types = ["query", "report", "alert", "general"]
            email_limits = {}
            
            for email_type in email_types:
                key = f"email_send:{user_id}:{email_type}"
                limits = {
                    "query": 20,
                    "report": 10, 
                    "alert": 50,
                    "general": 30,
                }
                limit = limits.get(email_type, limits["general"])
                email_limits[email_type] = await self.get_rate_limit_status(key, limit=limit)
            
            return {
                "user_general": user_status,
                "email_sending": email_limits,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error("User rate limit status failed", error=str(e), user_id=user_id)
            return {"error": str(e)}