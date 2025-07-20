"""
Real-time metrics collection and background processing service.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import json

from app.core.database import get_database, SharedResource, ShareAccessLog, ShareMetrics
from app.services.analytics_service import analytics_service
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Service for real-time metrics collection and background processing."""

    def __init__(self):
        self.is_running = False
        self.collection_interval = getattr(settings, 'METRICS_COLLECTION_INTERVAL', 300)  # 5 minutes
        self.aggregation_interval = getattr(settings, 'METRICS_AGGREGATION_INTERVAL', 3600)  # 1 hour

    async def start_collection(self):
        """Start the metrics collection background tasks."""
        if self.is_running:
            logger.warning("Metrics collection already running")
            return

        self.is_running = True
        logger.info("Starting metrics collection service")

        # Start background tasks
        await asyncio.gather(
            self._real_time_collection_task(),
            self._periodic_aggregation_task(),
            self._cleanup_task(),
            return_exceptions=True
        )

    async def stop_collection(self):
        """Stop the metrics collection background tasks."""
        self.is_running = False
        logger.info("Stopping metrics collection service")

    async def _real_time_collection_task(self):
        """Continuously collect real-time metrics."""
        logger.info("Starting real-time metrics collection task")
        
        while self.is_running:
            try:
                await self._collect_real_time_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(
                    "Error in real-time metrics collection",
                    error=str(e)
                )
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _periodic_aggregation_task(self):
        """Periodically aggregate metrics into time-based buckets."""
        logger.info("Starting periodic metrics aggregation task")
        
        while self.is_running:
            try:
                await self._aggregate_metrics()
                await asyncio.sleep(self.aggregation_interval)
            except Exception as e:
                logger.error(
                    "Error in periodic metrics aggregation",
                    error=str(e)
                )
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _cleanup_task(self):
        """Cleanup old metrics and logs periodically."""
        logger.info("Starting metrics cleanup task")
        
        # Run cleanup daily
        cleanup_interval = 24 * 3600  # 24 hours
        
        while self.is_running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(cleanup_interval)
            except Exception as e:
                logger.error(
                    "Error in metrics cleanup",
                    error=str(e)
                )
                await asyncio.sleep(3600)  # Wait 1 hour before retrying

    async def _collect_real_time_metrics(self):
        """Collect real-time metrics from active shares."""
        async with get_database() as db:
            try:
                # Get current timestamp
                now = datetime.now(timezone.utc)
                collection_window = now - timedelta(minutes=5)

                # Collect metrics for recently active shares
                from sqlalchemy import select, func
                
                # Get shares with recent activity
                recent_activity_query = select(ShareAccessLog.share_id).where(
                    ShareAccessLog.accessed_at >= collection_window
                ).distinct()
                
                result = await db.execute(recent_activity_query)
                active_share_ids = [row[0] for row in result.fetchall()]

                if not active_share_ids:
                    logger.debug("No recent share activity found")
                    return

                # Update metrics for active shares
                metrics_updated = 0
                for share_id in active_share_ids:
                    try:
                        await self._update_share_real_time_metrics(share_id, db)
                        metrics_updated += 1
                    except Exception as e:
                        logger.warning(
                            "Failed to update metrics for share",
                            share_id=str(share_id),
                            error=str(e)
                        )

                await db.commit()
                
                logger.debug(
                    "Real-time metrics collection completed",
                    active_shares=len(active_share_ids),
                    metrics_updated=metrics_updated
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Real-time metrics collection failed",
                    error=str(e)
                )
                raise

    async def _update_share_real_time_metrics(self, share_id, db):
        """Update real-time metrics for a specific share."""
        from sqlalchemy import select, func, and_
        
        # Calculate current metrics from access logs
        now = datetime.now(timezone.utc)
        
        # Total views and downloads
        total_views_result = await db.execute(
            select(func.count(ShareAccessLog.log_id))
            .where(
                and_(
                    ShareAccessLog.share_id == share_id,
                    ShareAccessLog.action == "view",
                    ShareAccessLog.success == True
                )
            )
        )
        total_views = total_views_result.scalar() or 0

        total_downloads_result = await db.execute(
            select(func.count(ShareAccessLog.log_id))
            .where(
                and_(
                    ShareAccessLog.share_id == share_id,
                    ShareAccessLog.action == "download",
                    ShareAccessLog.success == True
                )
            )
        )
        total_downloads = total_downloads_result.scalar() or 0

        # Unique viewers
        unique_viewers_result = await db.execute(
            select(func.count(func.distinct(ShareAccessLog.user_email)))
            .where(
                and_(
                    ShareAccessLog.share_id == share_id,
                    ShareAccessLog.action == "view",
                    ShareAccessLog.success == True,
                    ShareAccessLog.user_email.is_not(None)
                )
            )
        )
        unique_viewers_email = unique_viewers_result.scalar() or 0

        # If no email-based unique viewers, count by IP
        if unique_viewers_email == 0:
            unique_viewers_ip_result = await db.execute(
                select(func.count(func.distinct(ShareAccessLog.ip_address)))
                .where(
                    and_(
                        ShareAccessLog.share_id == share_id,
                        ShareAccessLog.action == "view",
                        ShareAccessLog.success == True,
                        ShareAccessLog.ip_address.is_not(None)
                    )
                )
            )
            unique_viewers = unique_viewers_ip_result.scalar() or 0
        else:
            unique_viewers = unique_viewers_email

        # Update share record
        share_result = await db.execute(
            select(SharedResource).where(SharedResource.share_id == share_id)
        )
        share = share_result.scalar_one_or_none()

        if share:
            share.total_views = total_views
            share.total_downloads = total_downloads
            share.unique_viewers = unique_viewers
            share.last_accessed_at = now

        logger.debug(
            "Share metrics updated",
            share_id=str(share_id),
            total_views=total_views,
            total_downloads=total_downloads,
            unique_viewers=unique_viewers
        )

    async def _aggregate_metrics(self):
        """Aggregate metrics into time-based buckets."""
        async with get_database() as db:
            try:
                current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                
                # Generate hourly aggregations for the previous hour
                previous_hour = current_hour - timedelta(hours=1)
                
                await analytics_service.generate_metrics_aggregation(
                    period_type="hour",
                    date=previous_hour,
                    db=db
                )

                # Generate daily aggregations if it's a new day
                if current_hour.hour == 0:
                    previous_day = current_hour - timedelta(days=1)
                    await analytics_service.generate_metrics_aggregation(
                        period_type="day",
                        date=previous_day,
                        db=db
                    )

                # Generate weekly aggregations if it's Monday at midnight
                if current_hour.hour == 0 and current_hour.weekday() == 0:
                    previous_week = current_hour - timedelta(weeks=1)
                    await analytics_service.generate_metrics_aggregation(
                        period_type="week",
                        date=previous_week,
                        db=db
                    )

                # Generate monthly aggregations if it's the first day of the month
                if current_hour.hour == 0 and current_hour.day == 1:
                    previous_month = current_hour - timedelta(days=current_hour.day)
                    await analytics_service.generate_metrics_aggregation(
                        period_type="month",
                        date=previous_month,
                        db=db
                    )

                logger.info(
                    "Metrics aggregation completed",
                    hour=previous_hour.isoformat()
                )

            except Exception as e:
                logger.error(
                    "Metrics aggregation failed",
                    error=str(e)
                )
                raise

    async def _cleanup_old_data(self):
        """Clean up old metrics and logs to maintain database performance."""
        async with get_database() as db:
            try:
                now = datetime.now(timezone.utc)
                
                # Clean up old access logs (keep last 90 days)
                log_retention_days = getattr(settings, 'ACCESS_LOG_RETENTION_DAYS', 90)
                log_cutoff_date = now - timedelta(days=log_retention_days)
                
                from sqlalchemy import delete
                
                delete_logs_result = await db.execute(
                    delete(ShareAccessLog).where(
                        ShareAccessLog.accessed_at < log_cutoff_date
                    )
                )
                deleted_logs = delete_logs_result.rowcount

                # Clean up old aggregated metrics (keep last 1 year)
                metrics_retention_days = getattr(settings, 'METRICS_RETENTION_DAYS', 365)
                metrics_cutoff_date = now - timedelta(days=metrics_retention_days)
                
                delete_metrics_result = await db.execute(
                    delete(ShareMetrics).where(
                        ShareMetrics.date < metrics_cutoff_date
                    )
                )
                deleted_metrics = delete_metrics_result.rowcount

                await db.commit()

                logger.info(
                    "Data cleanup completed",
                    deleted_logs=deleted_logs,
                    deleted_metrics=deleted_metrics,
                    log_cutoff_date=log_cutoff_date.isoformat(),
                    metrics_cutoff_date=metrics_cutoff_date.isoformat()
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Data cleanup failed",
                    error=str(e)
                )
                raise

    async def collect_share_interaction_metrics(
        self,
        share_id: str,
        action: str,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Collect metrics for a specific share interaction (called from share access)."""
        try:
            async with get_database() as db:
                # Record the interaction metrics in a separate metrics collection
                # This can be used for real-time analytics dashboards
                
                # For now, we'll store this in a simple format
                # In production, you might want to use a time-series database
                metrics_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "share_id": share_id,
                    "action": action,
                    "user_email": user_email,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "session_duration": session_duration,
                    "metadata": metadata or {}
                }

                # This could be sent to a message queue or time-series database
                # For now, we'll just log it for real-time processing
                logger.info(
                    "Share interaction metrics collected",
                    **{k: v for k, v in metrics_data.items() if v is not None}
                )

                # Update any in-memory caches or real-time counters here
                await self._update_real_time_counters(share_id, action)

        except Exception as e:
            logger.error(
                "Failed to collect interaction metrics",
                share_id=share_id,
                action=action,
                error=str(e)
            )

    async def _update_real_time_counters(self, share_id: str, action: str):
        """Update real-time counters for immediate analytics."""
        # This could update Redis counters for real-time dashboards
        # For now, we'll just log the update
        logger.debug(
            "Real-time counter updated",
            share_id=share_id,
            action=action
        )

    async def get_real_time_metrics(self, share_id: Optional[str] = None) -> Dict[str, Any]:
        """Get real-time metrics for dashboard display."""
        try:
            # This would typically fetch from Redis or a time-series database
            # For now, we'll return a simplified response
            
            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_shares": 0,
                "current_viewers": 0,
                "requests_per_minute": 0,
                "average_response_time": 0,
                "error_rate": 0
            }

            if share_id:
                # Get specific share metrics
                async with get_database() as db:
                    from sqlalchemy import select, func, and_
                    
                    # Get recent activity (last 5 minutes)
                    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    
                    recent_activity_result = await db.execute(
                        select(func.count(ShareAccessLog.log_id))
                        .where(
                            and_(
                                ShareAccessLog.share_id == share_id,
                                ShareAccessLog.accessed_at >= recent_cutoff
                            )
                        )
                    )
                    recent_activity = recent_activity_result.scalar() or 0
                    
                    metrics.update({
                        "share_id": share_id,
                        "recent_activity": recent_activity
                    })

            return metrics

        except Exception as e:
            logger.error(
                "Failed to get real-time metrics",
                share_id=share_id,
                error=str(e)
            )
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Failed to retrieve metrics"
            }


# Global metrics collector instance
metrics_collector = MetricsCollector()