"""
Analytics service for sharing metrics and insights.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from collections import defaultdict, Counter

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import (
    get_database, SharedResource, ShareAccessLog, ShareMetrics,
    ShareRolePermissions, SharePermissionAuditLog
)
from app.models.sharing_models import (
    ShareAnalyticsResponse, ShareStatsResponse, AccessLogEntry,
    ShareType, ShareStatus, SharePermission, AccessMethod, ShareOperation
)
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Service for generating sharing analytics and insights."""

    async def get_share_analytics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        share_types: Optional[List[ShareType]] = None,
        db: Optional[AsyncSession] = None
    ) -> ShareAnalyticsResponse:
        """Get comprehensive sharing analytics."""
        if db is None:
            db = await get_database()

        # Default date range to last 30 days
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        try:
            # Check user permissions for analytics
            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS, 
                scope="global", db=db
            )

            # Build base query based on permissions
            if permission_check.has_permission:
                # User can see all shares
                shares_query = select(SharedResource)
            else:
                # User can only see their own shares
                shares_query = select(SharedResource).where(SharedResource.created_by == user_id)

            # Apply filters
            if share_types:
                shares_query = shares_query.where(SharedResource.resource_type.in_(share_types))

            shares_query = shares_query.where(
                SharedResource.created_at >= start_date,
                SharedResource.created_at <= end_date
            )

            # Execute query
            result = await db.execute(shares_query)
            shares = result.scalars().all()

            # Calculate basic metrics
            total_shares = len(shares)
            active_shares = len([s for s in shares if s.status == ShareStatus.ACTIVE])
            expired_shares = len([s for s in shares if s.status == ShareStatus.EXPIRED])

            # Calculate breakdowns
            shares_by_type = self._calculate_breakdown(shares, lambda s: s.resource_type.value)
            shares_by_permission = self._calculate_permission_breakdown(shares)
            shares_by_access_method = self._calculate_breakdown(shares, lambda s: s.access_method.value)

            # Calculate activity metrics
            total_views = sum(s.total_views for s in shares)
            total_downloads = sum(s.total_downloads for s in shares)
            average_views = total_views / total_shares if total_shares > 0 else 0

            # Get most viewed shares
            most_viewed = sorted(shares, key=lambda s: s.total_views, reverse=True)[:10]
            most_viewed_shares = [
                {
                    "share_id": str(s.share_id),
                    "resource_name": s.resource_name,
                    "resource_type": s.resource_type.value,
                    "total_views": s.total_views,
                    "created_at": s.created_at.isoformat()
                }
                for s in most_viewed
            ]

            # Calculate time-based metrics
            week_ago = end_date - timedelta(days=7)
            month_ago = end_date - timedelta(days=30)

            shares_this_week = len([s for s in shares if s.created_at >= week_ago])
            shares_this_month = len([s for s in shares if s.created_at >= month_ago])

            # Calculate views for time periods
            views_this_week = await self._calculate_views_in_period(
                shares, week_ago, end_date, db
            )
            views_this_month = await self._calculate_views_in_period(
                shares, month_ago, end_date, db
            )

            logger.info(
                "Share analytics calculated",
                user_id=user_id,
                total_shares=total_shares,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )

            return ShareAnalyticsResponse(
                total_shares=total_shares,
                active_shares=active_shares,
                expired_shares=expired_shares,
                shares_by_type=shares_by_type,
                shares_by_permission=shares_by_permission,
                shares_by_access_method=shares_by_access_method,
                total_views_all_shares=total_views,
                total_downloads_all_shares=total_downloads,
                average_views_per_share=average_views,
                most_viewed_shares=most_viewed_shares,
                shares_created_this_week=shares_this_week,
                shares_created_this_month=shares_this_month,
                views_this_week=views_this_week,
                views_this_month=views_this_month
            )

        except Exception as e:
            logger.error(
                "Failed to calculate share analytics",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_share_stats(
        self,
        share_id: UUID,
        user_id: str,
        period_days: int = 30,
        db: Optional[AsyncSession] = None
    ) -> ShareStatsResponse:
        """Get detailed statistics for a specific share."""
        if db is None:
            db = await get_database()

        try:
            # Get share
            result = await db.execute(
                select(SharedResource).where(SharedResource.share_id == share_id)
            )
            share = result.scalar_one_or_none()

            if not share:
                raise ValueError("Share not found")

            # Check permissions
            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS,
                scope="share", scope_id=str(share_id), db=db
            )

            if not permission_check.has_permission and share.created_by != user_id:
                raise ValueError("Insufficient permissions to view share analytics")

            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=period_days)

            # Get access logs for the period
            logs_result = await db.execute(
                select(ShareAccessLog)
                .where(
                    ShareAccessLog.share_id == share_id,
                    ShareAccessLog.accessed_at >= start_date,
                    ShareAccessLog.accessed_at <= end_date
                )
                .order_by(ShareAccessLog.accessed_at.desc())
            )
            access_logs = logs_result.scalars().all()

            # Calculate daily views
            daily_views = self._calculate_daily_views(access_logs, start_date, end_date)

            # Calculate top referrers
            referrers = [log.referrer for log in access_logs if log.referrer]
            top_referrers = [
                {"referrer": ref, "count": count}
                for ref, count in Counter(referrers).most_common(10)
            ]

            # Calculate geographic distribution
            countries = [self._extract_country(log.ip_address) for log in access_logs]
            geographic_distribution = [
                {"country": country, "count": count}
                for country, count in Counter(countries).most_common(10)
                if country
            ]

            # Calculate device types
            user_agents = [log.user_agent for log in access_logs if log.user_agent]
            device_types = {
                "desktop": sum(1 for ua in user_agents if self._is_desktop(ua)),
                "mobile": sum(1 for ua in user_agents if self._is_mobile(ua)),
                "tablet": sum(1 for ua in user_agents if self._is_tablet(ua)),
                "unknown": sum(1 for ua in user_agents if not any([
                    self._is_desktop(ua), self._is_mobile(ua), self._is_tablet(ua)
                ]))
            }

            # Calculate access timeline
            access_timeline = [
                {
                    "timestamp": log.accessed_at.isoformat(),
                    "user_email": log.user_email or "anonymous",
                    "action": log.action,
                    "success": log.success,
                    "ip_address": log.ip_address
                }
                for log in access_logs[:100]  # Limit to recent 100 entries
            ]

            # Calculate performance metrics
            successful_logs = [log for log in access_logs if log.success]
            total_logs = len(access_logs)
            
            # Calculate session duration (if available)
            session_durations = [log.session_duration for log in access_logs if log.session_duration]
            avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else None

            # Calculate bounce rate (sessions with only one view)
            unique_sessions = defaultdict(list)
            for log in access_logs:
                session_key = f"{log.user_email or 'anon'}_{log.ip_address}"
                unique_sessions[session_key].append(log)
            
            single_view_sessions = sum(1 for logs in unique_sessions.values() if len(logs) == 1)
            bounce_rate = single_view_sessions / len(unique_sessions) * 100 if unique_sessions else 0

            # Calculate conversion rate (downloads vs views)
            download_logs = [log for log in access_logs if log.action == "download"]
            conversion_rate = len(download_logs) / len(successful_logs) * 100 if successful_logs else 0

            logger.info(
                "Share statistics calculated",
                share_id=str(share_id),
                user_id=user_id,
                period_days=period_days,
                total_logs=total_logs
            )

            return ShareStatsResponse(
                share_id=share_id,
                total_views=share.total_views,
                total_downloads=share.total_downloads,
                unique_viewers=share.unique_viewers,
                daily_views=daily_views,
                top_referrers=top_referrers,
                geographic_distribution=geographic_distribution,
                device_types=device_types,
                access_timeline=access_timeline,
                average_session_duration=avg_session_duration,
                bounce_rate=bounce_rate,
                conversion_rate=conversion_rate
            )

        except Exception as e:
            logger.error(
                "Failed to calculate share statistics",
                share_id=str(share_id),
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_access_logs(
        self,
        share_id: UUID,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> Tuple[List[AccessLogEntry], int]:
        """Get access logs for a share."""
        if db is None:
            db = await get_database()

        try:
            # Check permissions
            result = await db.execute(
                select(SharedResource).where(SharedResource.share_id == share_id)
            )
            share = result.scalar_one_or_none()

            if not share:
                raise ValueError("Share not found")

            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS,
                scope="share", scope_id=str(share_id), db=db
            )

            if not permission_check.has_permission and share.created_by != user_id:
                raise ValueError("Insufficient permissions to view access logs")

            # Build query
            query = select(ShareAccessLog).where(ShareAccessLog.share_id == share_id)

            if start_date:
                query = query.where(ShareAccessLog.accessed_at >= start_date)
            if end_date:
                query = query.where(ShareAccessLog.accessed_at <= end_date)

            # Get total count
            count_result = await db.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()

            # Apply pagination and ordering
            query = query.order_by(ShareAccessLog.accessed_at.desc())
            query = query.offset(offset).limit(limit)

            # Execute query
            result = await db.execute(query)
            logs = result.scalars().all()

            # Convert to response models
            log_entries = [
                AccessLogEntry(
                    log_id=log.log_id,
                    share_id=log.share_id,
                    accessed_at=log.accessed_at,
                    user_email=log.user_email,
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    referrer=log.referrer,
                    action=log.action,
                    success=log.success,
                    error_message=log.error_message,
                    session_duration=log.session_duration,
                    metadata=log.metadata
                )
                for log in logs
            ]

            logger.info(
                "Access logs retrieved",
                share_id=str(share_id),
                user_id=user_id,
                count=len(log_entries),
                total=total
            )

            return log_entries, total

        except Exception as e:
            logger.error(
                "Failed to retrieve access logs",
                share_id=str(share_id),
                user_id=user_id,
                error=str(e)
            )
            raise

    async def generate_metrics_aggregation(
        self,
        period_type: str = "day",
        date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """Generate and store aggregated metrics for a specific period."""
        if db is None:
            db = await get_database()

        if date is None:
            date = datetime.now(timezone.utc)

        try:
            # Calculate period boundaries
            start_date, end_date = self._get_period_boundaries(date, period_type)

            # Get all shares
            shares_result = await db.execute(select(SharedResource))
            shares = shares_result.scalars().all()

            for share in shares:
                # Get access logs for this period
                logs_result = await db.execute(
                    select(ShareAccessLog)
                    .where(
                        ShareAccessLog.share_id == share.share_id,
                        ShareAccessLog.accessed_at >= start_date,
                        ShareAccessLog.accessed_at < end_date
                    )
                )
                logs = logs_result.scalars().all()

                if not logs:
                    continue

                # Calculate metrics
                metrics = await self._calculate_period_metrics(share, logs)

                # Check if metrics already exist
                existing_result = await db.execute(
                    select(ShareMetrics)
                    .where(
                        ShareMetrics.share_id == share.share_id,
                        ShareMetrics.date == start_date,
                        ShareMetrics.period_type == period_type
                    )
                )
                existing_metrics = existing_result.scalar_one_or_none()

                if existing_metrics:
                    # Update existing metrics
                    for key, value in metrics.items():
                        setattr(existing_metrics, key, value)
                    existing_metrics.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new metrics
                    new_metrics = ShareMetrics(
                        share_id=share.share_id,
                        date=start_date,
                        period_type=period_type,
                        **metrics
                    )
                    db.add(new_metrics)

            await db.commit()

            logger.info(
                "Metrics aggregation completed",
                period_type=period_type,
                date=date.isoformat(),
                shares_processed=len(shares)
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to generate metrics aggregation",
                period_type=period_type,
                date=date.isoformat() if date else None,
                error=str(e)
            )
            raise

    def _calculate_breakdown(self, shares: List[SharedResource], key_func) -> Dict[str, int]:
        """Calculate breakdown by a specific attribute."""
        breakdown = defaultdict(int)
        for share in shares:
            breakdown[key_func(share)] += 1
        return dict(breakdown)

    def _calculate_permission_breakdown(self, shares: List[SharedResource]) -> Dict[str, int]:
        """Calculate breakdown by permissions."""
        breakdown = defaultdict(int)
        for share in shares:
            for permission in share.permissions:
                breakdown[permission] += 1
        return dict(breakdown)

    async def _calculate_views_in_period(
        self,
        shares: List[SharedResource],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> int:
        """Calculate total views in a specific period."""
        share_ids = [s.share_id for s in shares]
        if not share_ids:
            return 0

        result = await db.execute(
            select(func.count(ShareAccessLog.log_id))
            .where(
                ShareAccessLog.share_id.in_(share_ids),
                ShareAccessLog.accessed_at >= start_date,
                ShareAccessLog.accessed_at <= end_date,
                ShareAccessLog.action == "view",
                ShareAccessLog.success == True
            )
        )
        return result.scalar() or 0

    def _calculate_daily_views(
        self,
        logs: List[ShareAccessLog],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Calculate daily view counts."""
        daily_counts = defaultdict(int)
        
        # Count views by date
        for log in logs:
            if log.action == "view" and log.success:
                date_key = log.accessed_at.date().isoformat()
                daily_counts[date_key] += 1

        # Fill in missing dates with zero
        current_date = start_date.date()
        end_date_only = end_date.date()
        daily_views = []

        while current_date <= end_date_only:
            date_key = current_date.isoformat()
            daily_views.append({
                "date": date_key,
                "views": daily_counts.get(date_key, 0)
            })
            current_date += timedelta(days=1)

        return daily_views

    def _extract_country(self, ip_address: Optional[str]) -> Optional[str]:
        """Extract country from IP address (placeholder for GeoIP integration)."""
        if not ip_address:
            return None
        
        # Placeholder for GeoIP lookup
        # In a real implementation, you would use a GeoIP service like MaxMind
        if ip_address.startswith("192.168.") or ip_address.startswith("127."):
            return "Local"
        elif ip_address.startswith("10."):
            return "Private"
        else:
            return "Unknown"

    def _is_desktop(self, user_agent: str) -> bool:
        """Check if user agent indicates desktop browser."""
        if not user_agent:
            return False
        user_agent = user_agent.lower()
        desktop_indicators = ["windows", "macintosh", "linux", "chrome", "firefox", "safari"]
        mobile_indicators = ["mobile", "android", "iphone", "ipad", "tablet"]
        
        has_desktop = any(indicator in user_agent for indicator in desktop_indicators)
        has_mobile = any(indicator in user_agent for indicator in mobile_indicators)
        
        return has_desktop and not has_mobile

    def _is_mobile(self, user_agent: str) -> bool:
        """Check if user agent indicates mobile device."""
        if not user_agent:
            return False
        user_agent = user_agent.lower()
        mobile_indicators = ["mobile", "android", "iphone"]
        return any(indicator in user_agent for indicator in mobile_indicators)

    def _is_tablet(self, user_agent: str) -> bool:
        """Check if user agent indicates tablet device."""
        if not user_agent:
            return False
        user_agent = user_agent.lower()
        tablet_indicators = ["tablet", "ipad"]
        return any(indicator in user_agent for indicator in tablet_indicators)

    def _get_period_boundaries(self, date: datetime, period_type: str) -> Tuple[datetime, datetime]:
        """Get start and end boundaries for a period type."""
        if period_type == "hour":
            start_date = date.replace(minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(hours=1)
        elif period_type == "day":
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period_type == "week":
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=start_date.weekday())
            end_date = start_date + timedelta(weeks=1)
        elif period_type == "month":
            start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end_date = start_date.replace(year=date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=date.month + 1)
        else:
            raise ValueError(f"Invalid period type: {period_type}")

        return start_date, end_date

    async def _calculate_period_metrics(
        self,
        share: SharedResource,
        logs: List[ShareAccessLog]
    ) -> Dict[str, Any]:
        """Calculate metrics for a specific share and period."""
        successful_logs = [log for log in logs if log.success]
        view_logs = [log for log in logs if log.action == "view" and log.success]
        download_logs = [log for log in logs if log.action == "download" and log.success]

        # Basic counts
        total_views = len(view_logs)
        total_downloads = len(download_logs)

        # Unique viewers
        unique_emails = set(log.user_email for log in view_logs if log.user_email)
        unique_ips = set(log.ip_address for log in view_logs if log.ip_address)
        unique_viewers = len(unique_emails) or len(unique_ips)

        # Session metrics
        session_durations = [log.session_duration for log in logs if log.session_duration]
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else None

        # Geographic breakdown
        countries = [self._extract_country(log.ip_address) for log in view_logs]
        country_counts = dict(Counter(countries))

        # Device breakdown
        user_agents = [log.user_agent for log in view_logs if log.user_agent]
        device_breakdown = {
            "desktop": sum(1 for ua in user_agents if self._is_desktop(ua)),
            "mobile": sum(1 for ua in user_agents if self._is_mobile(ua)),
            "tablet": sum(1 for ua in user_agents if self._is_tablet(ua))
        }

        # Browser breakdown (simplified)
        browser_breakdown = {}
        for ua in user_agents:
            if "chrome" in ua.lower():
                browser_breakdown["chrome"] = browser_breakdown.get("chrome", 0) + 1
            elif "firefox" in ua.lower():
                browser_breakdown["firefox"] = browser_breakdown.get("firefox", 0) + 1
            elif "safari" in ua.lower():
                browser_breakdown["safari"] = browser_breakdown.get("safari", 0) + 1
            else:
                browser_breakdown["other"] = browser_breakdown.get("other", 0) + 1

        # Referrer breakdown
        referrers = [log.referrer for log in view_logs if log.referrer]
        referrer_counts = dict(Counter(referrers).most_common(10))

        # Error metrics
        error_logs = [log for log in logs if not log.success]
        error_count = len(error_logs)
        error_rate = error_count / len(logs) * 100 if logs else 0

        return {
            "total_views": total_views,
            "total_downloads": total_downloads,
            "unique_viewers": unique_viewers,
            "new_viewers": unique_viewers,  # Simplified for now
            "returning_viewers": 0,  # Simplified for now
            "average_session_duration": avg_session_duration,
            "bounce_rate": None,  # Would need more complex calculation
            "conversion_rate": total_downloads / total_views * 100 if total_views > 0 else 0,
            "top_countries": country_counts,
            "top_cities": {},  # Placeholder
            "device_breakdown": device_breakdown,
            "browser_breakdown": browser_breakdown,
            "os_breakdown": {},  # Placeholder
            "top_referrers": referrer_counts,
            "direct_traffic": len([r for r in referrers if not r]),
            "average_load_time": None,  # Placeholder
            "error_count": error_count,
            "error_rate": error_rate
        }


# Service instance
analytics_service = AnalyticsService()