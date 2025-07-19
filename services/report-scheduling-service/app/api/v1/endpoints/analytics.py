"""
Analytics API endpoints for report scheduling metrics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.utils.auth import get_current_user, check_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/overview",
    summary="Get analytics overview",
    description="Get comprehensive analytics overview for report scheduling"
)
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get analytics overview."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        overview = await analytics_service.get_overview(
            user_id=current_user["user_id"],
            days=days
        )
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/schedules",
    summary="Get schedule analytics",
    description="Get analytics data for schedules"
)
async def get_schedule_analytics(
    period_type: str = Query("day", regex="^(hour|day|week|month)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get schedule analytics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        analytics = await analytics_service.get_schedule_analytics(
            user_id=current_user["user_id"],
            period_type=period_type,
            days=days
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting schedule analytics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/executions",
    summary="Get execution analytics",
    description="Get analytics data for executions"
)
async def get_execution_analytics(
    period_type: str = Query("day", regex="^(hour|day|week|month)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get execution analytics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        analytics = await analytics_service.get_execution_analytics(
            user_id=current_user["user_id"],
            period_type=period_type,
            days=days
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting execution analytics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/deliveries",
    summary="Get delivery analytics",
    description="Get analytics data for deliveries"
)
async def get_delivery_analytics(
    period_type: str = Query("day", regex="^(hour|day|week|month)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get delivery analytics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        analytics = await analytics_service.get_delivery_analytics(
            user_id=current_user["user_id"],
            period_type=period_type,
            days=days
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting delivery analytics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/performance",
    summary="Get performance analytics",
    description="Get performance metrics and trends"
)
async def get_performance_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get performance analytics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        performance = await analytics_service.get_performance_analytics(
            user_id=current_user["user_id"],
            days=days
        )
        
        return performance
        
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/usage",
    summary="Get usage analytics",
    description="Get user usage patterns and statistics"
)
async def get_usage_analytics(
    period_type: str = Query("day", regex="^(hour|day|week|month)$", description="Aggregation period"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get usage analytics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        usage = await analytics_service.get_usage_analytics(
            user_id=current_user["user_id"],
            period_type=period_type,
            days=days
        )
        
        return usage
        
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/trends",
    summary="Get trend analysis",
    description="Get trend analysis for various metrics"
)
async def get_trend_analysis(
    metric: str = Query("executions", regex="^(schedules|executions|deliveries|performance)$", description="Metric to analyze"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get trend analysis."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        trends = await analytics_service.get_trend_analysis(
            user_id=current_user["user_id"],
            metric=metric,
            days=days
        )
        
        return trends
        
    except Exception as e:
        logger.error(f"Error getting trend analysis: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/health",
    summary="Get system health metrics",
    description="Get system health and performance indicators"
)
async def get_health_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get system health metrics."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:read")
        
        analytics_service = AnalyticsService(db)
        health = await analytics_service.get_health_metrics()
        
        return health
        
    except Exception as e:
        logger.error(f"Error getting health metrics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/reports",
    summary="Generate analytics report",
    description="Generate a comprehensive analytics report"
)
async def generate_analytics_report(
    report_type: str = Query("summary", regex="^(summary|detailed|custom)$", description="Type of report"),
    format: str = Query("json", regex="^(json|csv|pdf)$", description="Output format"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate analytics report."""
    try:
        # Check permissions
        await check_permission(current_user, "analytics:report")
        
        analytics_service = AnalyticsService(db)
        report = await analytics_service.generate_analytics_report(
            user_id=current_user["user_id"],
            report_type=report_type,
            format=format,
            days=days
        )
        
        logger.info(f"Analytics report generated: {report_type} by user {current_user['user_id']}")
        return report
        
    except Exception as e:
        logger.error(f"Error generating analytics report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")