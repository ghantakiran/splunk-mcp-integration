"""
API endpoints for sharing analytics and metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.sharing_models import (
    ShareAnalyticsResponse, ShareStatsResponse, ShareAccessLogsResponse,
    ShareType, AccessLogEntry
)
from app.services.analytics_service import analytics_service
from app.utils.auth import get_current_user
from app.utils.rate_limiter import rate_limit
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/overview",
    response_model=ShareAnalyticsResponse,
    summary="Get sharing analytics overview"
)
async def get_analytics_overview(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    share_types: Optional[List[ShareType]] = Query(None, description="Filter by share types"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("analytics_overview", max_requests=50, window_seconds=60))
):
    """
    Get comprehensive sharing analytics overview.
    
    Returns analytics data including:
    - Total shares, active/expired counts
    - Breakdown by type, permissions, access method
    - Activity metrics (views, downloads)
    - Time-based analytics
    - Most viewed shares
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        analytics = await analytics_service.get_share_analytics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            share_types=share_types,
            db=db
        )
        
        logger.info(
            "Analytics overview retrieved",
            user_id=user_id,
            total_shares=analytics.total_shares,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None
        )
        
        return analytics

    except ValueError as e:
        logger.warning(
            "Analytics overview failed - validation error",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Analytics overview failed",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics overview"
        )


@router.get(
    "/shares/{share_id}/stats",
    response_model=ShareStatsResponse,
    summary="Get detailed statistics for a specific share"
)
async def get_share_statistics(
    share_id: UUID,
    period_days: int = Query(30, ge=1, le=365, description="Number of days to include in statistics"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("share_stats", max_requests=100, window_seconds=60))
):
    """
    Get detailed statistics for a specific share.
    
    Returns comprehensive statistics including:
    - View and download metrics
    - Daily activity timeline
    - Geographic distribution
    - Device type breakdown
    - Top referrers
    - Performance metrics
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        stats = await analytics_service.get_share_stats(
            share_id=share_id,
            user_id=user_id,
            period_days=period_days,
            db=db
        )
        
        logger.info(
            "Share statistics retrieved",
            share_id=str(share_id),
            user_id=user_id,
            period_days=period_days,
            total_views=stats.total_views
        )
        
        return stats

    except ValueError as e:
        logger.warning(
            "Share statistics failed - validation error",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Share statistics failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve share statistics"
        )


@router.get(
    "/shares/{share_id}/access-logs",
    response_model=ShareAccessLogsResponse,
    summary="Get access logs for a specific share"
)
async def get_share_access_logs(
    share_id: UUID,
    limit: int = Query(50, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    start_date: Optional[datetime] = Query(None, description="Start date for log period"),
    end_date: Optional[datetime] = Query(None, description="End date for log period"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("access_logs", max_requests=100, window_seconds=60))
):
    """
    Get access logs for a specific share.
    
    Returns paginated access logs with filtering options:
    - Timestamp and user information
    - Actions performed (view, download, etc.)
    - Success/failure status
    - IP addresses and user agents
    - Error messages for failed attempts
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        logs, total = await analytics_service.get_access_logs(
            share_id=share_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            db=db
        )
        
        logger.info(
            "Access logs retrieved",
            share_id=str(share_id),
            user_id=user_id,
            count=len(logs),
            total=total
        )
        
        return ShareAccessLogsResponse(
            items=logs,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(logs) < total
        )

    except ValueError as e:
        logger.warning(
            "Access logs retrieval failed - validation error",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Access logs retrieval failed",
            share_id=str(share_id),
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve access logs"
        )


@router.get(
    "/metrics/summary",
    summary="Get analytics metrics summary"
)
async def get_metrics_summary(
    period: str = Query("day", regex="^(hour|day|week|month)$", description="Metrics period"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("metrics_summary", max_requests=30, window_seconds=60))
):
    """
    Get analytics metrics summary for a specific period.
    
    Returns aggregated metrics including:
    - Total activity across all shares
    - Performance trends
    - User engagement metrics
    - System utilization statistics
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Check if user has global analytics permissions
        from app.services.role_permission_service import role_permission_service
        from app.models.sharing_models import ShareOperation
        
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.VIEW_ANALYTICS, "global", db=db
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view system metrics"
            )

        # Calculate summary metrics based on period
        now = datetime.now()
        if period == "hour":
            start_time = now - timedelta(hours=24)  # Last 24 hours
        elif period == "day":
            start_time = now - timedelta(days=30)   # Last 30 days
        elif period == "week":
            start_time = now - timedelta(weeks=12)  # Last 12 weeks
        else:  # month
            start_time = now - timedelta(days=365)  # Last 12 months

        # Get analytics for the period
        analytics = await analytics_service.get_share_analytics(
            user_id=user_id,
            start_date=start_time,
            end_date=now,
            db=db
        )

        # Create summary response
        summary = {
            "period": period,
            "start_date": start_time.isoformat(),
            "end_date": now.isoformat(),
            "total_shares": analytics.total_shares,
            "active_shares": analytics.active_shares,
            "total_views": analytics.total_views_all_shares,
            "total_downloads": analytics.total_downloads_all_shares,
            "average_views_per_share": analytics.average_views_per_share,
            "shares_by_type": analytics.shares_by_type,
            "top_share_types": sorted(
                analytics.shares_by_type.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "engagement_rate": (
                analytics.total_downloads_all_shares / analytics.total_views_all_shares * 100
                if analytics.total_views_all_shares > 0 else 0
            ),
            "growth_metrics": {
                "shares_this_week": analytics.shares_created_this_week,
                "shares_this_month": analytics.shares_created_this_month,
                "views_this_week": analytics.views_this_week,
                "views_this_month": analytics.views_this_month
            }
        }
        
        logger.info(
            "Metrics summary retrieved",
            user_id=user_id,
            period=period,
            total_shares=analytics.total_shares
        )
        
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Metrics summary failed",
            error=str(e),
            user_id=current_user.get("sub"),
            period=period
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics summary"
        )


@router.get(
    "/dashboard",
    summary="Get analytics dashboard data"
)
async def get_analytics_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("analytics_dashboard", max_requests=20, window_seconds=60))
):
    """
    Get comprehensive analytics dashboard data.
    
    Returns dashboard-ready data including:
    - Key performance indicators (KPIs)
    - Trend charts data
    - Top performing shares
    - User activity insights
    - System health metrics
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Get analytics for different periods
        now = datetime.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)

        # Get current period analytics
        current_analytics = await analytics_service.get_share_analytics(
            user_id=user_id,
            start_date=last_30_days,
            end_date=now,
            db=db
        )

        # Get previous period for comparison
        previous_period_start = last_30_days - timedelta(days=30)
        previous_analytics = await analytics_service.get_share_analytics(
            user_id=user_id,
            start_date=previous_period_start,
            end_date=last_30_days,
            db=db
        )

        # Calculate growth rates
        def calculate_growth(current: int, previous: int) -> float:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100

        # Build dashboard data
        dashboard_data = {
            "summary_cards": {
                "total_shares": {
                    "value": current_analytics.total_shares,
                    "growth": calculate_growth(
                        current_analytics.total_shares,
                        previous_analytics.total_shares
                    ),
                    "label": "Total Shares"
                },
                "total_views": {
                    "value": current_analytics.total_views_all_shares,
                    "growth": calculate_growth(
                        current_analytics.total_views_all_shares,
                        previous_analytics.total_views_all_shares
                    ),
                    "label": "Total Views"
                },
                "active_shares": {
                    "value": current_analytics.active_shares,
                    "growth": calculate_growth(
                        current_analytics.active_shares,
                        previous_analytics.active_shares
                    ),
                    "label": "Active Shares"
                },
                "average_views": {
                    "value": round(current_analytics.average_views_per_share, 1),
                    "growth": calculate_growth(
                        int(current_analytics.average_views_per_share),
                        int(previous_analytics.average_views_per_share)
                    ),
                    "label": "Avg Views per Share"
                }
            },
            "charts": {
                "shares_by_type": {
                    "type": "pie",
                    "data": current_analytics.shares_by_type,
                    "title": "Shares by Type"
                },
                "shares_by_permission": {
                    "type": "bar",
                    "data": current_analytics.shares_by_permission,
                    "title": "Shares by Permission"
                },
                "activity_trend": {
                    "type": "line",
                    "data": {
                        "this_week": current_analytics.views_this_week,
                        "this_month": current_analytics.views_this_month,
                        "shares_this_week": current_analytics.shares_created_this_week,
                        "shares_this_month": current_analytics.shares_created_this_month
                    },
                    "title": "Activity Trends"
                }
            },
            "top_shares": current_analytics.most_viewed_shares[:5],
            "insights": {
                "most_popular_type": max(
                    current_analytics.shares_by_type.items(),
                    key=lambda x: x[1],
                    default=("None", 0)
                )[0],
                "engagement_rate": (
                    current_analytics.total_downloads_all_shares / 
                    current_analytics.total_views_all_shares * 100
                    if current_analytics.total_views_all_shares > 0 else 0
                ),
                "average_share_lifetime": "30 days",  # Placeholder
                "peak_usage_day": "Monday"  # Placeholder
            },
            "metadata": {
                "generated_at": now.isoformat(),
                "period": "Last 30 days",
                "user_has_global_access": True  # Would be determined by permissions
            }
        }
        
        logger.info(
            "Analytics dashboard data retrieved",
            user_id=user_id,
            total_shares=current_analytics.total_shares
        )
        
        return dashboard_data

    except Exception as e:
        logger.error(
            "Analytics dashboard failed",
            error=str(e),
            user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics dashboard"
        )


@router.post(
    "/metrics/generate",
    summary="Generate metrics aggregation"
)
async def generate_metrics_aggregation(
    period_type: str = Query("day", regex="^(hour|day|week|month)$", description="Period type for aggregation"),
    date: Optional[datetime] = Query(None, description="Specific date for aggregation"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("metrics_generation", max_requests=10, window_seconds=300))
):
    """
    Generate and store aggregated metrics for a specific period.
    
    This endpoint is typically used by scheduled jobs or administrators
    to pre-calculate metrics for performance optimization.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Check admin permissions
        from app.services.role_permission_service import role_permission_service
        from app.models.sharing_models import ShareOperation
        
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.MANAGE_PERMISSIONS, "global", db=db
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to generate metrics"
            )

        await analytics_service.generate_metrics_aggregation(
            period_type=period_type,
            date=date,
            db=db
        )
        
        logger.info(
            "Metrics aggregation generated",
            user_id=user_id,
            period_type=period_type,
            date=date.isoformat() if date else None
        )
        
        return {
            "success": True,
            "message": f"Metrics aggregation generated for {period_type}",
            "period_type": period_type,
            "date": date.isoformat() if date else datetime.now().isoformat(),
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Metrics aggregation failed",
            error=str(e),
            user_id=current_user.get("sub"),
            period_type=period_type
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics aggregation"
        )