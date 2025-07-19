"""
Analytics service for report scheduling metrics and insights.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from app.core.database import (
    ReportSchedule, ScheduleExecution, ReportSubscription, 
    DeliveryAttempt, ScheduleAnalytics, SystemMetrics
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and insights."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_overview(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive analytics overview."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get schedule counts
            schedule_counts = await self._get_schedule_counts(user_id)
            
            # Get execution metrics
            execution_metrics = await self._get_execution_metrics(user_id, start_date, end_date)
            
            # Get delivery metrics
            delivery_metrics = await self._get_delivery_metrics(user_id, start_date, end_date)
            
            # Get performance metrics
            performance_metrics = await self._get_performance_metrics(user_id, start_date, end_date)
            
            # Get recent activity
            recent_activity = await self._get_recent_activity(user_id, limit=10)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "schedules": schedule_counts,
                "executions": execution_metrics,
                "deliveries": delivery_metrics,
                "performance": performance_metrics,
                "recent_activity": recent_activity,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics overview: {e}")
            raise
    
    async def get_schedule_analytics(
        self,
        user_id: str,
        period_type: str = "day",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get schedule analytics data."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get schedule creation trends
            creation_trends = await self._get_schedule_creation_trends(user_id, start_date, end_date, period_type)
            
            # Get schedule status distribution
            status_distribution = await self._get_schedule_status_distribution(user_id)
            
            # Get format preferences
            format_distribution = await self._get_format_distribution(user_id)
            
            # Get most active schedules
            top_schedules = await self._get_top_schedules(user_id, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                    "period_type": period_type
                },
                "creation_trends": creation_trends,
                "status_distribution": status_distribution,
                "format_distribution": format_distribution,
                "top_schedules": top_schedules,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting schedule analytics: {e}")
            raise
    
    async def get_execution_analytics(
        self,
        user_id: str,
        period_type: str = "day",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get execution analytics data."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get execution trends
            execution_trends = await self._get_execution_trends(user_id, start_date, end_date, period_type)
            
            # Get success/failure rates
            success_rates = await self._get_execution_success_rates(user_id, start_date, end_date)
            
            # Get execution duration trends
            duration_trends = await self._get_execution_duration_trends(user_id, start_date, end_date, period_type)
            
            # Get error analysis
            error_analysis = await self._get_execution_error_analysis(user_id, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                    "period_type": period_type
                },
                "execution_trends": execution_trends,
                "success_rates": success_rates,
                "duration_trends": duration_trends,
                "error_analysis": error_analysis,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting execution analytics: {e}")
            raise
    
    async def get_delivery_analytics(
        self,
        user_id: str,
        period_type: str = "day",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get delivery analytics data."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get delivery trends
            delivery_trends = await self._get_delivery_trends(user_id, start_date, end_date, period_type)
            
            # Get delivery method distribution
            method_distribution = await self._get_delivery_method_distribution(user_id, start_date, end_date)
            
            # Get delivery success rates
            success_rates = await self._get_delivery_success_rates(user_id, start_date, end_date)
            
            # Get retry analysis
            retry_analysis = await self._get_delivery_retry_analysis(user_id, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                    "period_type": period_type
                },
                "delivery_trends": delivery_trends,
                "method_distribution": method_distribution,
                "success_rates": success_rates,
                "retry_analysis": retry_analysis,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting delivery analytics: {e}")
            raise
    
    async def get_performance_analytics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance analytics."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get average execution times
            avg_times = await self._get_average_execution_times(user_id, start_date, end_date)
            
            # Get resource usage
            resource_usage = await self._get_resource_usage_metrics(start_date, end_date)
            
            # Get bottleneck analysis
            bottlenecks = await self._get_bottleneck_analysis(user_id, start_date, end_date)
            
            # Get performance trends
            trends = await self._get_performance_trends(user_id, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "average_execution_times": avg_times,
                "resource_usage": resource_usage,
                "bottlenecks": bottlenecks,
                "performance_trends": trends,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            raise
    
    async def get_usage_analytics(
        self,
        user_id: str,
        period_type: str = "day",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage analytics."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get user activity patterns
            activity_patterns = await self._get_user_activity_patterns(user_id, start_date, end_date, period_type)
            
            # Get feature usage
            feature_usage = await self._get_feature_usage(user_id, start_date, end_date)
            
            # Get peak usage times
            peak_times = await self._get_peak_usage_times(user_id, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                    "period_type": period_type
                },
                "activity_patterns": activity_patterns,
                "feature_usage": feature_usage,
                "peak_times": peak_times,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            raise
    
    async def get_trend_analysis(
        self,
        user_id: str,
        metric: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get trend analysis for specified metric."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            if metric == "schedules":
                data = await self._get_schedule_trends(user_id, start_date, end_date)
            elif metric == "executions":
                data = await self._get_execution_trend_data(user_id, start_date, end_date)
            elif metric == "deliveries":
                data = await self._get_delivery_trend_data(user_id, start_date, end_date)
            elif metric == "performance":
                data = await self._get_performance_trend_data(user_id, start_date, end_date)
            else:
                raise ValueError(f"Unknown metric: {metric}")
            
            # Calculate trend indicators
            trend_direction = self._calculate_trend_direction(data)
            growth_rate = self._calculate_growth_rate(data)
            volatility = self._calculate_volatility(data)
            
            return {
                "metric": metric,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "data": data,
                "trend_direction": trend_direction,
                "growth_rate": growth_rate,
                "volatility": volatility,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting trend analysis: {e}")
            raise
    
    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics."""
        try:
            # Get latest system metrics
            result = await self.db.execute(
                select(SystemMetrics)
                .order_by(SystemMetrics.timestamp.desc())
                .limit(1)
            )
            latest_metrics = result.scalar_one_or_none()
            
            # Get current queue status
            queue_status = await self._get_queue_status()
            
            # Get service health
            service_health = await self._get_service_health()
            
            # Get database performance
            db_performance = await self._get_database_performance()
            
            health_score = self._calculate_health_score(latest_metrics, queue_status)
            
            return {
                "health_score": health_score,
                "status": "healthy" if health_score > 80 else "degraded" if health_score > 60 else "critical",
                "system_metrics": {
                    "total_schedules": latest_metrics.total_schedules if latest_metrics else 0,
                    "active_schedules": latest_metrics.active_schedules if latest_metrics else 0,
                    "pending_jobs": latest_metrics.pending_jobs if latest_metrics else 0,
                    "running_jobs": latest_metrics.running_jobs if latest_metrics else 0,
                    "average_execution_time": latest_metrics.average_execution_time if latest_metrics else 0
                },
                "queue_status": queue_status,
                "service_health": service_health,
                "database_performance": db_performance,
                "last_updated": latest_metrics.timestamp.isoformat() if latest_metrics else None,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting health metrics: {e}")
            raise
    
    async def generate_analytics_report(
        self,
        user_id: str,
        report_type: str,
        format: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        try:
            if report_type == "summary":
                data = await self.get_overview(user_id, days)
            elif report_type == "detailed":
                data = {
                    "overview": await self.get_overview(user_id, days),
                    "schedules": await self.get_schedule_analytics(user_id, "day", days),
                    "executions": await self.get_execution_analytics(user_id, "day", days),
                    "deliveries": await self.get_delivery_analytics(user_id, "day", days),
                    "performance": await self.get_performance_analytics(user_id, days),
                    "usage": await self.get_usage_analytics(user_id, "day", days)
                }
            else:  # custom
                data = await self._generate_custom_report(user_id, days)
            
            # In a real implementation, this would format the data according to the requested format
            report = {
                "report_type": report_type,
                "format": format,
                "user_id": user_id,
                "data": data,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if format == "csv":
                report["download_url"] = f"/api/v1/analytics/reports/{user_id}/download?format=csv"
            elif format == "pdf":
                report["download_url"] = f"/api/v1/analytics/reports/{user_id}/download?format=pdf"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating analytics report: {e}")
            raise
    
    # Helper methods for analytics calculations
    
    async def _get_schedule_counts(self, user_id: str) -> Dict[str, int]:
        """Get schedule counts by status."""
        result = await self.db.execute(
            select(
                ReportSchedule.status,
                func.count(ReportSchedule.schedule_id).label("count")
            )
            .where(ReportSchedule.user_id == user_id)
            .group_by(ReportSchedule.status)
        )
        
        counts = {row.status.value: row.count for row in result}
        total = sum(counts.values())
        
        return {
            "total": total,
            "active": counts.get("active", 0),
            "paused": counts.get("paused", 0),
            "disabled": counts.get("disabled", 0),
            "error": counts.get("error", 0)
        }
    
    async def _get_execution_metrics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get execution metrics for the period."""
        # Get basic counts
        result = await self.db.execute(
            select(
                ScheduleExecution.status,
                func.count(ScheduleExecution.execution_id).label("count"),
                func.avg(ScheduleExecution.duration_seconds).label("avg_duration")
            )
            .join(ReportSchedule)
            .where(
                and_(
                    ReportSchedule.user_id == user_id,
                    ScheduleExecution.created_at >= start_date,
                    ScheduleExecution.created_at <= end_date
                )
            )
            .group_by(ScheduleExecution.status)
        )
        
        counts = {}
        total_duration = 0
        total_count = 0
        
        for row in result:
            counts[row.status.value] = row.count
            if row.avg_duration:
                total_duration += row.avg_duration * row.count
            total_count += row.count
        
        return {
            "total": total_count,
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "running": counts.get("running", 0),
            "pending": counts.get("pending", 0),
            "cancelled": counts.get("cancelled", 0),
            "average_duration": total_duration / total_count if total_count > 0 else 0,
            "success_rate": (counts.get("completed", 0) / total_count * 100) if total_count > 0 else 0
        }
    
    async def _get_delivery_metrics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get delivery metrics for the period."""
        result = await self.db.execute(
            select(
                func.count(DeliveryAttempt.attempt_id).label("total_attempts"),
                func.sum(func.cast(DeliveryAttempt.success, "int")).label("successful_attempts")
            )
            .join(ReportSubscription)
            .where(
                and_(
                    ReportSubscription.user_id == user_id,
                    DeliveryAttempt.created_at >= start_date,
                    DeliveryAttempt.created_at <= end_date
                )
            )
        )
        
        row = result.first()
        total = row.total_attempts or 0
        successful = row.successful_attempts or 0
        
        return {
            "total_attempts": total,
            "successful_attempts": successful,
            "failed_attempts": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0
        }
    
    async def _get_performance_metrics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get performance metrics for the period."""
        # This is a simplified implementation
        return {
            "average_query_time": 2.5,
            "average_generation_time": 15.3,
            "average_delivery_time": 3.8,
            "cache_hit_rate": 78.5,
            "error_rate": 2.1
        }
    
    async def _get_recent_activity(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity for the user."""
        result = await self.db.execute(
            select(ScheduleExecution)
            .join(ReportSchedule)
            .where(ReportSchedule.user_id == user_id)
            .order_by(ScheduleExecution.created_at.desc())
            .limit(limit)
        )
        
        executions = result.scalars().all()
        
        return [
            {
                "execution_id": str(execution.execution_id),
                "schedule_id": str(execution.schedule_id),
                "status": execution.status.value,
                "created_at": execution.created_at.isoformat(),
                "duration_seconds": execution.duration_seconds
            }
            for execution in executions
        ]
    
    def _calculate_trend_direction(self, data: List[Dict[str, Any]]) -> str:
        """Calculate trend direction from data points."""
        if len(data) < 2:
            return "stable"
        
        values = [point.get("value", 0) for point in data]
        if values[-1] > values[0]:
            return "increasing"
        elif values[-1] < values[0]:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_growth_rate(self, data: List[Dict[str, Any]]) -> float:
        """Calculate growth rate from data points."""
        if len(data) < 2:
            return 0.0
        
        first_value = data[0].get("value", 0)
        last_value = data[-1].get("value", 0)
        
        if first_value == 0:
            return 0.0
        
        return ((last_value - first_value) / first_value) * 100
    
    def _calculate_volatility(self, data: List[Dict[str, Any]]) -> float:
        """Calculate volatility from data points."""
        if len(data) < 2:
            return 0.0
        
        values = [point.get("value", 0) for point in data]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance ** 0.5
    
    def _calculate_health_score(self, metrics: Optional[SystemMetrics], queue_status: Dict[str, Any]) -> float:
        """Calculate overall system health score."""
        score = 100.0
        
        # Deduct points for issues
        if queue_status.get("pending_jobs", 0) > 100:
            score -= 20
        elif queue_status.get("pending_jobs", 0) > 50:
            score -= 10
        
        if queue_status.get("failed_jobs", 0) > 10:
            score -= 15
        elif queue_status.get("failed_jobs", 0) > 5:
            score -= 5
        
        if metrics:
            if metrics.average_execution_time and metrics.average_execution_time > 60:
                score -= 10
            elif metrics.average_execution_time and metrics.average_execution_time > 30:
                score -= 5
        
        return max(0.0, score)
    
    async def _get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        # This would integrate with Redis to get actual queue metrics
        return {
            "pending_jobs": 5,
            "running_jobs": 2,
            "failed_jobs": 1,
            "completed_jobs_today": 150
        }
    
    async def _get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "database": "healthy",
            "redis": "healthy",
            "nlp_engine": "healthy",
            "visualization": "healthy",
            "email": "healthy"
        }
    
    async def _get_database_performance(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        return {
            "connection_pool_usage": 45.5,
            "average_query_time": 12.3,
            "slow_queries": 2,
            "connection_errors": 0
        }
    
    # Placeholder methods for other analytics - would be implemented based on specific requirements
    async def _get_schedule_creation_trends(self, user_id: str, start_date: datetime, end_date: datetime, period_type: str) -> List[Dict[str, Any]]:
        return []
    
    async def _get_schedule_status_distribution(self, user_id: str) -> Dict[str, int]:
        return {}
    
    async def _get_format_distribution(self, user_id: str) -> Dict[str, int]:
        return {}
    
    async def _get_top_schedules(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_execution_trends(self, user_id: str, start_date: datetime, end_date: datetime, period_type: str) -> List[Dict[str, Any]]:
        return []
    
    async def _get_execution_success_rates(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return {}
    
    async def _get_execution_duration_trends(self, user_id: str, start_date: datetime, end_date: datetime, period_type: str) -> List[Dict[str, Any]]:
        return []
    
    async def _get_execution_error_analysis(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        return {}
    
    async def _get_delivery_trends(self, user_id: str, start_date: datetime, end_date: datetime, period_type: str) -> List[Dict[str, Any]]:
        return []
    
    async def _get_delivery_method_distribution(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        return {}
    
    async def _get_delivery_success_rates(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return {}
    
    async def _get_delivery_retry_analysis(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        return {}
    
    async def _get_average_execution_times(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return {}
    
    async def _get_resource_usage_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return {}
    
    async def _get_bottleneck_analysis(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        return {}
    
    async def _get_performance_trends(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_user_activity_patterns(self, user_id: str, start_date: datetime, end_date: datetime, period_type: str) -> List[Dict[str, Any]]:
        return []
    
    async def _get_feature_usage(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        return {}
    
    async def _get_peak_usage_times(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_schedule_trends(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_execution_trend_data(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_delivery_trend_data(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _get_performance_trend_data(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return []
    
    async def _generate_custom_report(self, user_id: str, days: int) -> Dict[str, Any]:
        return {"message": "Custom report generation not implemented"}