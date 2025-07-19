#!/usr/bin/env python3
"""
Analytics API endpoints.

This module provides API endpoints for CSV export analytics,
usage statistics, and performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.database import log_analytics_event
from app.models.csv_models import AnalyticsResponse
from app.utils.auth import CurrentUser, require_analytics_read, require_user_role

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/usage", response_model=AnalyticsResponse)
async def get_usage_analytics(
    current_user: CurrentUser = Depends(require_analytics_read),
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days")
):
    """Get usage analytics for the specified period."""
    try:
        # In a real implementation, this would query the analytics database
        # For demo purposes, we'll return simulated data
        
        # Simulate analytics data
        period_start = datetime.utcnow() - timedelta(days=period_days)
        
        # Generate simulated daily usage
        daily_usage = []
        for i in range(min(period_days, 30)):  # Limit to 30 days for demo
            date = period_start + timedelta(days=i)
            daily_usage.append({
                "date": date.strftime("%Y-%m-%d"),
                "jobs_created": max(0, 10 + (i % 7) * 2 - (i % 3)),
                "jobs_completed": max(0, 8 + (i % 7) * 2 - (i % 3)),
                "total_rows_exported": max(0, 1000 + (i % 7) * 500),
                "total_file_size_mb": max(0, 50 + (i % 7) * 25)
            })
        
        # Calculate summary statistics
        total_jobs = sum(day["jobs_created"] for day in daily_usage)
        successful_jobs = sum(day["jobs_completed"] for day in daily_usage)
        failed_jobs = total_jobs - successful_jobs
        
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        avg_generation_time = 2500.0 + (period_days % 10) * 100  # Simulated
        avg_file_size = sum(day["total_file_size_mb"] for day in daily_usage) / len(daily_usage) if daily_usage else 0
        avg_row_count = sum(day["total_rows_exported"] for day in daily_usage) / len(daily_usage) if daily_usage else 0
        total_data_exported_gb = sum(day["total_file_size_mb"] for day in daily_usage) / 1024
        
        # Usage by format (simulated)
        usage_by_format = {
            "csv": int(total_jobs * 0.7),
            "tsv": int(total_jobs * 0.2),
            "pipe": int(total_jobs * 0.1)
        }
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="analytics_viewed",
            event_data={
                "period_days": period_days,
                "total_jobs": total_jobs,
                "success_rate": success_rate
            }
        )
        
        return AnalyticsResponse(
            period_days=period_days,
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
            success_rate=round(success_rate, 2),
            avg_generation_time=avg_generation_time,
            avg_file_size=avg_file_size * 1024 * 1024,  # Convert to bytes
            avg_row_count=avg_row_count,
            total_data_exported_gb=round(total_data_exported_gb, 3),
            usage_by_format=usage_by_format,
            daily_usage=daily_usage
        )
        
    except Exception as e:
        logger.error(f"Failed to get usage analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage analytics"
        )


@router.get("/performance")
async def get_performance_metrics(
    current_user: CurrentUser = Depends(require_analytics_read),
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
):
    """Get performance metrics for the specified time period."""
    try:
        # Simulate performance data
        current_time = datetime.utcnow()
        
        # Generate hourly performance data
        hourly_metrics = []
        for i in range(min(hours, 24)):  # Limit to 24 hours for demo
            hour_time = current_time - timedelta(hours=i)
            hourly_metrics.append({
                "timestamp": hour_time.isoformat(),
                "avg_generation_time_ms": 2000 + (i % 5) * 500,
                "jobs_processed": max(0, 5 + (i % 3)),
                "error_rate_percent": max(0, (i % 7) * 2),
                "avg_file_size_mb": 25 + (i % 4) * 10,
                "queue_depth": max(0, 10 - (i % 6))
            })
        
        # Calculate summary metrics
        avg_generation_time = sum(m["avg_generation_time_ms"] for m in hourly_metrics) / len(hourly_metrics)
        total_jobs_processed = sum(m["jobs_processed"] for m in hourly_metrics)
        avg_error_rate = sum(m["error_rate_percent"] for m in hourly_metrics) / len(hourly_metrics)
        peak_queue_depth = max(m["queue_depth"] for m in hourly_metrics) if hourly_metrics else 0
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="performance_metrics_viewed",
            event_data={
                "hours": hours,
                "avg_generation_time": avg_generation_time,
                "total_jobs_processed": total_jobs_processed
            }
        )
        
        return {
            "period_hours": hours,
            "summary": {
                "avg_generation_time_ms": round(avg_generation_time, 2),
                "total_jobs_processed": total_jobs_processed,
                "avg_error_rate_percent": round(avg_error_rate, 2),
                "peak_queue_depth": peak_queue_depth,
                "system_health": "healthy" if avg_error_rate < 5 else "degraded"
            },
            "hourly_metrics": hourly_metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/export-patterns")
async def get_export_patterns(
    current_user: CurrentUser = Depends(require_analytics_read),
    days: int = Query(30, ge=7, le=90, description="Analysis period in days")
):
    """Get export pattern analysis."""
    try:
        # Simulate pattern analysis
        patterns = {
            "peak_hours": [9, 10, 11, 14, 15, 16],  # Business hours
            "common_formats": {
                "csv": {"count": 150, "percentage": 75.0},
                "tsv": {"count": 35, "percentage": 17.5},
                "pipe": {"count": 15, "percentage": 7.5}
            },
            "common_encodings": {
                "utf-8": {"count": 170, "percentage": 85.0},
                "utf-16": {"count": 20, "percentage": 10.0},
                "latin-1": {"count": 10, "percentage": 5.0}
            },
            "file_size_distribution": {
                "small": {"size_range": "< 1MB", "count": 80, "percentage": 40.0},
                "medium": {"size_range": "1-10MB", "count": 90, "percentage": 45.0},
                "large": {"size_range": "10-100MB", "count": 25, "percentage": 12.5},
                "xl": {"size_range": "> 100MB", "count": 5, "percentage": 2.5}
            },
            "compression_usage": {
                "none": {"count": 120, "percentage": 60.0},
                "gzip": {"count": 60, "percentage": 30.0},
                "zip": {"count": 20, "percentage": 10.0}
            },
            "error_patterns": {
                "data_validation": {"count": 5, "percentage": 50.0},
                "timeout": {"count": 3, "percentage": 30.0},
                "memory_limit": {"count": 2, "percentage": 20.0}
            }
        }
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="export_patterns_viewed",
            event_data={"analysis_days": days}
        )
        
        return {
            "analysis_period_days": days,
            "patterns": patterns,
            "recommendations": [
                "Consider using compression for files larger than 10MB",
                "UTF-8 encoding is recommended for maximum compatibility",
                "Schedule large exports during off-peak hours (after 6 PM)",
                "Use CSV format for best compatibility with Excel"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get export patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export patterns"
        )


@router.get("/user-activity")
async def get_user_activity(
    current_user: CurrentUser = Depends(require_user_role),
    days: int = Query(7, ge=1, le=30, description="Activity period in days")
):
    """Get user activity summary."""
    try:
        # Simulate user activity data
        activity_data = {
            "user_id": current_user.user_id,
            "username": current_user.username,
            "period_days": days,
            "activity_summary": {
                "total_exports": 25 + (days % 10),
                "successful_exports": 22 + (days % 8),
                "failed_exports": 3 + (days % 3),
                "total_data_exported_mb": 500 + (days * 50),
                "avg_export_size_mb": 20 + (days % 5),
                "templates_created": max(0, days // 7),
                "templates_used": 5 + (days % 4)
            },
            "recent_activity": [
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "action": "export_created",
                    "details": "Created CSV export for sales data"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
                    "action": "export_downloaded",
                    "details": "Downloaded completed export"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "action": "template_created",
                    "details": "Created new template 'Weekly Report'"
                }
            ],
            "preferences": {
                "favorite_format": "csv",
                "favorite_encoding": "utf-8",
                "uses_compression": False,
                "avg_file_size_preference": "medium"
            }
        }
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="user_activity_viewed",
            event_data={"activity_days": days}
        )
        
        return activity_data
        
    except Exception as e:
        logger.error(f"Failed to get user activity for {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user activity"
        )


@router.get("/system-health")
async def get_system_health(
    current_user: CurrentUser = Depends(require_analytics_read)
):
    """Get system health and status information."""
    try:
        # Simulate system health data
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {
                "api_service": {
                    "status": "healthy",
                    "response_time_ms": 45,
                    "uptime_hours": 168.5
                },
                "database": {
                    "status": "healthy",
                    "connection_pool_usage": 65,
                    "query_avg_time_ms": 25
                },
                "redis_cache": {
                    "status": "healthy",
                    "memory_usage_percent": 45,
                    "hit_rate_percent": 85.2
                },
                "queue_system": {
                    "status": "healthy",
                    "pending_jobs": 5,
                    "processing_jobs": 2,
                    "workers_active": 8
                }
            },
            "metrics": {
                "requests_per_minute": 45,
                "error_rate_percent": 1.2,
                "avg_response_time_ms": 250,
                "active_users": 12,
                "jobs_in_queue": 7
            },
            "alerts": []  # No alerts in healthy state
        }
        
        # Add warning if error rate is high
        if health_data["metrics"]["error_rate_percent"] > 5:
            health_data["alerts"].append({
                "level": "warning",
                "message": "Error rate above normal threshold",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Log analytics event
        await log_analytics_event(
            user_id=current_user.user_id,
            job_id=None,
            event_type="system_health_viewed",
            event_data={"overall_status": health_data["overall_status"]}
        )
        
        return health_data
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )


# Export router
__all__ = ["router"]