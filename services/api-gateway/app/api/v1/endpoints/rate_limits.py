"""
Rate limiting management and monitoring endpoints
"""

import time
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query as QueryParam, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as redis

from ....core.config import settings
from ....core.logging import get_logger
from ....api.deps import get_async_session, get_current_user, require_permissions
from ....models.user import User
from ....models.responses import SuccessResponse, COMMON_RESPONSES
from ....core.rate_limiting import (
    get_rate_limit_manager,
    RateLimitPolicy,
    RateLimitAlgorithm,
    RateLimitScope,
    RateLimitStatus
)
from ....middleware.rate_limiting import get_request_rate_limits
from ....core.audit import audit_action, AuditAction, AuditResource

router = APIRouter()
logger = get_logger(__name__)


async def get_redis_client() -> redis.Redis:
    """Get Redis client for rate limiting operations"""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get current rate limit status",
    description="Retrieve current rate limiting status for the authenticated user",
    responses=COMMON_RESPONSES
)
async def get_rate_limit_status(
    rate_limits: Dict[str, Any] = Depends(get_request_rate_limits),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current rate limit status for the user"""
    
    try:
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Get detailed status for user
        user_id = str(current_user.id)
        
        # Check current status for all applicable policies
        from fastapi import Request
        
        # Create a mock request to check limits
        # In a real implementation, this would use the actual request
        mock_request = type('MockRequest', (), {
            'client': type('Client', (), {'host': '127.0.0.1'}),
            'url': type('URL', (), {'path': '/api/v1/test'}),
            'method': 'GET'
        })()
        
        allowed, statuses = await rate_manager.check_rate_limits(
            request=mock_request,
            user_id=user_id
        )
        
        return {
            "user_id": user_id,
            "rate_limiting_enabled": True,
            "current_status": "within_limits" if allowed else "rate_limited",
            "policies": rate_limits.get("policies", []),
            "limits": [status.to_dict() for status in statuses],
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        return {
            "error": "Unable to retrieve rate limit status",
            "rate_limiting_enabled": False
        }


@router.get(
    "/policies",
    status_code=status.HTTP_200_OK,
    summary="Get rate limiting policies",
    description="Retrieve all configured rate limiting policies",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:read"]))]
)
async def get_rate_limit_policies(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all configured rate limiting policies"""
    
    try:
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        policies_data = []
        for policy in rate_manager.policies.values():
            policies_data.append(policy.to_dict())
        
        await audit_action(
            db=None,  # No DB session needed for this operation
            user_id=current_user.id,
            action=AuditAction.READ,
            resource=AuditResource.SYSTEM,
            resource_id="rate_limit_policies",
            details={"admin_access": True}
        )
        
        return {
            "policies": policies_data,
            "total_policies": len(policies_data),
            "algorithms_available": [algo.value for algo in RateLimitAlgorithm],
            "scopes_available": [scope.value for scope in RateLimitScope]
        }
        
    except Exception as e:
        logger.error(f"Failed to get rate limit policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve rate limiting policies"
        )


@router.post(
    "/policies",
    status_code=status.HTTP_201_CREATED,
    summary="Create rate limiting policy",
    description="Create a new rate limiting policy (admin only)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:create"]))]
)
async def create_rate_limit_policy(
    policy_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new rate limiting policy"""
    
    try:
        # Validate and create policy
        policy = RateLimitPolicy(
            name=policy_data["name"],
            algorithm=RateLimitAlgorithm(policy_data["algorithm"]),
            scope=RateLimitScope(policy_data["scope"]),
            limit=policy_data["limit"],
            window_seconds=policy_data["window_seconds"],
            burst_limit=policy_data.get("burst_limit"),
            refill_rate=policy_data.get("refill_rate"),
            enabled=policy_data.get("enabled", True),
            priority=policy_data.get("priority", 10)
        )
        
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Add policy to manager
        rate_manager.add_policy(policy)
        
        await audit_action(
            db=None,
            user_id=current_user.id,
            action=AuditAction.CREATE,
            resource=AuditResource.SYSTEM,
            resource_id=f"rate_limit_policy:{policy.name}",
            details=policy.to_dict()
        )
        
        logger.info(
            "Rate limiting policy created",
            policy_name=policy.name,
            created_by=str(current_user.id)
        )
        
        return {
            "message": "Rate limiting policy created successfully",
            "policy": policy.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid policy configuration: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to create rate limit policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create rate limiting policy"
        )


@router.put(
    "/policies/{policy_name}",
    status_code=status.HTTP_200_OK,
    summary="Update rate limiting policy",
    description="Update an existing rate limiting policy (admin only)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:update"]))]
)
async def update_rate_limit_policy(
    policy_name: str,
    policy_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update an existing rate limiting policy"""
    
    try:
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Check if policy exists
        if policy_name not in rate_manager.policies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rate limiting policy '{policy_name}' not found"
            )
        
        # Update policy
        existing_policy = rate_manager.policies[policy_name]
        
        # Update fields if provided
        if "algorithm" in policy_data:
            existing_policy.algorithm = RateLimitAlgorithm(policy_data["algorithm"])
        if "scope" in policy_data:
            existing_policy.scope = RateLimitScope(policy_data["scope"])
        if "limit" in policy_data:
            existing_policy.limit = policy_data["limit"]
        if "window_seconds" in policy_data:
            existing_policy.window_seconds = policy_data["window_seconds"]
        if "burst_limit" in policy_data:
            existing_policy.burst_limit = policy_data["burst_limit"]
        if "refill_rate" in policy_data:
            existing_policy.refill_rate = policy_data["refill_rate"]
        if "enabled" in policy_data:
            existing_policy.enabled = policy_data["enabled"]
        if "priority" in policy_data:
            existing_policy.priority = policy_data["priority"]
        
        await audit_action(
            db=None,
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            resource=AuditResource.SYSTEM,
            resource_id=f"rate_limit_policy:{policy_name}",
            details={"changes": policy_data}
        )
        
        logger.info(
            "Rate limiting policy updated",
            policy_name=policy_name,
            updated_by=str(current_user.id)
        )
        
        return {
            "message": "Rate limiting policy updated successfully",
            "policy": existing_policy.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid policy configuration: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to update rate limit policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update rate limiting policy"
        )


@router.delete(
    "/policies/{policy_name}",
    status_code=status.HTTP_200_OK,
    summary="Delete rate limiting policy",
    description="Delete a rate limiting policy (admin only)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:delete"]))]
)
async def delete_rate_limit_policy(
    policy_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a rate limiting policy"""
    
    try:
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Check if policy exists
        if policy_name not in rate_manager.policies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rate limiting policy '{policy_name}' not found"
            )
        
        # Don't allow deletion of core policies
        core_policies = ["global_api", "user_api", "ip_api", "burst_protection"]
        if policy_name in core_policies:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot delete core policy '{policy_name}'"
            )
        
        # Remove policy
        rate_manager.remove_policy(policy_name)
        
        await audit_action(
            db=None,
            user_id=current_user.id,
            action=AuditAction.DELETE,
            resource=AuditResource.SYSTEM,
            resource_id=f"rate_limit_policy:{policy_name}",
            details={"policy_name": policy_name}
        )
        
        logger.info(
            "Rate limiting policy deleted",
            policy_name=policy_name,
            deleted_by=str(current_user.id)
        )
        
        return {
            "message": f"Rate limiting policy '{policy_name}' deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete rate limit policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete rate limiting policy"
        )


@router.post(
    "/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset rate limits",
    description="Reset rate limits for a user or IP address (admin only)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:reset"]))]
)
async def reset_rate_limits(
    target_user_id: Optional[str] = QueryParam(None, description="User ID to reset limits for"),
    target_ip: Optional[str] = QueryParam(None, description="IP address to reset limits for"),
    policy_names: Optional[List[str]] = QueryParam(None, description="Specific policies to reset"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reset rate limits for a specific user or IP address"""
    
    if not target_user_id and not target_ip:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must specify either target_user_id or target_ip"
        )
    
    try:
        redis_client = await get_redis_client()
        rate_manager = await get_rate_limit_manager(redis_client)
        
        # Create mock request for reset operation
        mock_request = type('MockRequest', (), {
            'client': type('Client', (), {'host': target_ip or '127.0.0.1'}),
            'url': type('URL', (), {'path': '/api/v1/test'}),
            'method': 'GET'
        })()
        
        # Reset rate limits
        results = await rate_manager.reset_rate_limits(
            request=mock_request,
            user_id=target_user_id,
            policy_names=policy_names
        )
        
        await audit_action(
            db=None,
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            resource=AuditResource.SYSTEM,
            resource_id="rate_limits_reset",
            details={
                "target_user_id": target_user_id,
                "target_ip": target_ip,
                "policy_names": policy_names,
                "results": results
            }
        )
        
        logger.info(
            "Rate limits reset",
            target_user_id=target_user_id,
            target_ip=target_ip,
            policy_names=policy_names,
            reset_by=str(current_user.id),
            results=results
        )
        
        return {
            "message": "Rate limits reset successfully",
            "target_user_id": target_user_id,
            "target_ip": target_ip,
            "policies_reset": results,
            "total_policies_affected": sum(1 for success in results.values() if success)
        }
        
    except Exception as e:
        logger.error(f"Failed to reset rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset rate limits"
        )


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get rate limiting metrics",
    description="Retrieve rate limiting usage metrics and analytics (admin only)",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["rate_limits:read"]))]
)
async def get_rate_limit_metrics(
    time_range: str = QueryParam("1h", description="Time range: 1h, 6h, 24h, 7d"),
    granularity: str = QueryParam("minute", description="Granularity: minute, hour, day"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get rate limiting metrics and analytics"""
    
    try:
        redis_client = await get_redis_client()
        
        # Calculate time range
        time_ranges = {
            "1h": 3600,
            "6h": 21600,
            "24h": 86400,
            "7d": 604800
        }
        
        if time_range not in time_ranges:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid time range. Must be one of: 1h, 6h, 24h, 7d"
            )
        
        seconds = time_ranges[time_range]
        granularity_seconds = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        if granularity not in granularity_seconds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid granularity. Must be one of: minute, hour, day"
            )
        
        bucket_size = granularity_seconds[granularity]
        
        # Get metrics from Redis
        now = int(time.time())
        start_time = now - seconds
        
        metrics_data = {
            "time_range": time_range,
            "granularity": granularity,
            "start_time": start_time,
            "end_time": now,
            "buckets": []
        }
        
        # Collect metrics for each time bucket
        for timestamp in range(start_time, now, bucket_size):
            bucket_timestamp = timestamp // bucket_size * bucket_size
            metrics_key = f"rate_limit_metrics:{bucket_timestamp // 60}"  # Minute-based keys
            
            bucket_data = await redis_client.hgetall(metrics_key)
            
            bucket_metrics = {
                "timestamp": bucket_timestamp,
                "total_requests": int(bucket_data.get("total_requests", 0)),
                "allowed_requests": int(bucket_data.get("allowed_requests", 0)),
                "blocked_requests": int(bucket_data.get("blocked_requests", 0)),
                "avg_response_time": float(bucket_data.get("avg_response_time", 0))
            }
            
            metrics_data["buckets"].append(bucket_metrics)
        
        # Calculate summary statistics
        total_requests = sum(bucket["total_requests"] for bucket in metrics_data["buckets"])
        total_blocked = sum(bucket["blocked_requests"] for bucket in metrics_data["buckets"])
        
        metrics_data["summary"] = {
            "total_requests": total_requests,
            "total_blocked": total_blocked,
            "block_rate_percentage": (total_blocked / total_requests * 100) if total_requests > 0 else 0,
            "avg_requests_per_bucket": total_requests / len(metrics_data["buckets"]) if metrics_data["buckets"] else 0
        }
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Failed to get rate limit metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve rate limiting metrics"
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Rate limiting system health",
    description="Check the health of the rate limiting system",
    responses=COMMON_RESPONSES
)
async def get_rate_limiting_health() -> Dict[str, Any]:
    """Check rate limiting system health"""
    
    try:
        redis_client = await get_redis_client()
        
        # Test Redis connectivity
        start_time = time.time()
        await redis_client.ping()
        redis_latency = time.time() - start_time
        
        # Test rate limit manager
        rate_manager = await get_rate_limit_manager(redis_client)
        policies_count = len(rate_manager.policies)
        
        return {
            "status": "healthy",
            "redis_connected": True,
            "redis_latency_ms": round(redis_latency * 1000, 2),
            "policies_loaded": policies_count,
            "rate_limiting_enabled": settings.rate_limiting_enabled,
            "timestamp": time.time()
        }
        
    except redis.RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "error": "Redis connection failed",
            "rate_limiting_enabled": False,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Rate limiting health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Rate limiting system error",
            "timestamp": time.time()
        }