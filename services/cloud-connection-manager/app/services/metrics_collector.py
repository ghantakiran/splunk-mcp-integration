"""
Metrics Collector Service for gathering and aggregating connection performance metrics.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.redis_client import get_redis_client
from app.models.connection_models import (
    ConnectionEndpoint, ConnectionPool, ConnectionMetrics, ConnectionHealth,
    EndpointStatus, HealthStatus
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates performance metrics for connection endpoints."""
    
    def __init__(self, connection_pool_manager, health_monitor):
        self.connection_pool_manager = connection_pool_manager
        self.health_monitor = health_monitor
        self.collection_interval = 60  # seconds
        self.running = False
        self._redis = None
        
        # In-memory metrics buffers for real-time aggregation
        self.request_metrics = defaultdict(lambda: {
            "request_count": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "timeout_requests": 0,
            "response_times": deque(maxlen=1000),  # Keep last 1000 response times
            "error_count": 0,
            "last_reset": time.time()
        })
        
        # System metrics collection task
        self.collection_task = None
    
    async def start(self):
        """Start metrics collection."""
        if self.running:
            return
        
        logger.info("Starting Metrics Collector...")
        
        try:
            # Initialize Redis client
            self._redis = await get_redis_client()
            
            # Start collection task
            self.collection_task = asyncio.create_task(
                self._collection_loop(),
                name="metrics_collection"
            )
            
            self.running = True
            logger.info("Metrics Collector started")
            
        except Exception as e:
            logger.error(f"Failed to start Metrics Collector: {str(e)}")
            raise
    
    async def stop(self):
        """Stop metrics collection."""
        if not self.running:
            return
        
        logger.info("Stopping Metrics Collector...")
        
        self.running = False
        
        # Cancel collection task
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping metrics collection: {str(e)}")
        
        logger.info("Metrics Collector stopped")
    
    async def record_request_metrics(self, endpoint_id: int, response_time_ms: float, 
                                   success: bool, timeout: bool = False):
        """Record request metrics for an endpoint."""
        metrics = self.request_metrics[endpoint_id]
        
        metrics["request_count"] += 1
        if success:
            metrics["successful_requests"] += 1
        else:
            metrics["failed_requests"] += 1
            metrics["error_count"] += 1
        
        if timeout:
            metrics["timeout_requests"] += 1
        
        metrics["response_times"].append(response_time_ms)
        
        # Also cache in Redis for real-time access
        if self._redis:
            try:
                cache_key = f"metrics:realtime:{endpoint_id}"
                await self._redis.hincrby(cache_key, "request_count", 1)
                if success:
                    await self._redis.hincrby(cache_key, "successful_requests", 1)
                else:
                    await self._redis.hincrby(cache_key, "failed_requests", 1)
                
                # Set expiration
                await self._redis.expire(cache_key, 3600)  # 1 hour
                
            except Exception as e:
                logger.debug(f"Failed to cache request metrics: {str(e)}")
    
    async def get_real_time_metrics(self, endpoint_id: int) -> Dict[str, Any]:
        """Get real-time metrics for an endpoint."""
        metrics = self.request_metrics[endpoint_id]
        response_times = list(metrics["response_times"])
        
        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_response_time = self._calculate_percentile(sorted_times, 95)
            p99_response_time = self._calculate_percentile(sorted_times, 99)
        else:
            avg_response_time = min_response_time = max_response_time = None
            p95_response_time = p99_response_time = None
        
        # Calculate error rate
        total_requests = metrics["request_count"]
        error_rate = (metrics["failed_requests"] / total_requests * 100) if total_requests > 0 else 0
        timeout_rate = (metrics["timeout_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "endpoint_id": endpoint_id,
            "request_count": metrics["request_count"],
            "successful_requests": metrics["successful_requests"],
            "failed_requests": metrics["failed_requests"],
            "timeout_requests": metrics["timeout_requests"],
            "error_rate": round(error_rate, 2),
            "timeout_rate": round(timeout_rate, 2),
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
            "min_response_time_ms": round(min_response_time, 2) if min_response_time else None,
            "max_response_time_ms": round(max_response_time, 2) if max_response_time else None,
            "p95_response_time_ms": round(p95_response_time, 2) if p95_response_time else None,
            "p99_response_time_ms": round(p99_response_time, 2) if p99_response_time else None,
            "last_reset": datetime.fromtimestamp(metrics["last_reset"])
        }
    
    async def get_historical_metrics(self, endpoint_id: int, 
                                   hours: int = 24,
                                   interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get historical metrics for an endpoint."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionMetrics)
                .where(
                    and_(
                        ConnectionMetrics.endpoint_id == endpoint_id,
                        ConnectionMetrics.timestamp >= since,
                        ConnectionMetrics.interval_minutes == interval_minutes
                    )
                )
                .order_by(ConnectionMetrics.timestamp.desc())
                .limit(1000)  # Limit to prevent excessive data
            )
            metrics_records = result.scalars().all()
            
            return [
                {
                    "timestamp": record.timestamp,
                    "interval_minutes": record.interval_minutes,
                    "request_count": record.request_count,
                    "successful_requests": record.successful_requests,
                    "failed_requests": record.failed_requests,
                    "timeout_requests": record.timeout_requests,
                    "error_rate": record.error_rate,
                    "timeout_rate": record.timeout_rate,
                    "avg_response_time_ms": record.avg_response_time_ms,
                    "min_response_time_ms": record.min_response_time_ms,
                    "max_response_time_ms": record.max_response_time_ms,
                    "p95_response_time_ms": record.p95_response_time_ms,
                    "p99_response_time_ms": record.p99_response_time_ms,
                    "active_connections": record.active_connections,
                    "peak_connections": record.peak_connections,
                    "connection_pool_usage": record.connection_pool_usage,
                    "circuit_breaker_trips": record.circuit_breaker_trips
                }
                for record in metrics_records
            ]
    
    async def get_aggregate_metrics(self, endpoint_ids: List[int] = None,
                                  hours: int = 24) -> Dict[str, Any]:
        """Get aggregated metrics across endpoints."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_async_session() as session:
            # Build query
            query = select(ConnectionMetrics).where(ConnectionMetrics.timestamp >= since)
            if endpoint_ids:
                query = query.where(ConnectionMetrics.endpoint_id.in_(endpoint_ids))
            
            result = await session.execute(query)
            metrics_records = result.scalars().all()
            
            if not metrics_records:
                return {
                    "total_requests": 0,
                    "total_successful": 0,
                    "total_failed": 0,
                    "overall_error_rate": 0,
                    "avg_response_time_ms": None,
                    "endpoints_count": len(endpoint_ids) if endpoint_ids else 0,
                    "period_hours": hours
                }
            
            # Aggregate metrics
            total_requests = sum(record.request_count for record in metrics_records)
            total_successful = sum(record.successful_requests for record in metrics_records)
            total_failed = sum(record.failed_requests for record in metrics_records)
            
            # Calculate weighted average response time
            total_weighted_response_time = 0
            total_weight = 0
            for record in metrics_records:
                if record.avg_response_time_ms and record.request_count > 0:
                    total_weighted_response_time += record.avg_response_time_ms * record.request_count
                    total_weight += record.request_count
            
            avg_response_time = (total_weighted_response_time / total_weight) if total_weight > 0 else None
            error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0
            
            # Get unique endpoints
            unique_endpoints = set(record.endpoint_id for record in metrics_records)
            
            return {
                "total_requests": total_requests,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "overall_error_rate": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
                "endpoints_count": len(unique_endpoints),
                "period_hours": hours,
                "period_start": since,
                "period_end": datetime.utcnow()
            }
    
    async def get_performance_insights(self, endpoint_id: int = None) -> Dict[str, Any]:
        """Get performance insights and recommendations."""
        insights = {
            "recommendations": [],
            "alerts": [],
            "performance_score": 100,
            "trends": {}
        }
        
        # Get recent metrics for analysis
        hours = 24
        if endpoint_id:
            metrics = await self.get_historical_metrics(endpoint_id, hours=hours)
            endpoints_to_analyze = [endpoint_id]
        else:
            # Analyze all endpoints
            aggregate_metrics = await self.get_aggregate_metrics(hours=hours)
            async with get_async_session() as session:
                result = await session.execute(
                    select(ConnectionEndpoint.id)
                    .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
                )
                endpoints_to_analyze = result.scalars().all()
        
        # Analyze each endpoint
        for ep_id in endpoints_to_analyze:
            ep_metrics = await self.get_historical_metrics(ep_id, hours=hours)
            if not ep_metrics:
                continue
            
            # Calculate performance score factors
            recent_metrics = ep_metrics[:12]  # Last 12 data points (1 hour if 5-min intervals)
            
            if recent_metrics:
                avg_error_rate = statistics.mean([m["error_rate"] for m in recent_metrics])
                avg_response_time = statistics.mean([
                    m["avg_response_time_ms"] for m in recent_metrics 
                    if m["avg_response_time_ms"] is not None
                ])
                
                # Performance scoring
                error_score = max(0, 100 - (avg_error_rate * 10))  # -10 points per % error
                response_time_score = max(0, 100 - (avg_response_time / 100))  # -1 point per 100ms
                
                endpoint_score = (error_score + response_time_score) / 2
                insights["performance_score"] = min(insights["performance_score"], endpoint_score)
                
                # Generate recommendations
                if avg_error_rate > 5:
                    insights["alerts"].append(f"High error rate ({avg_error_rate:.1f}%) on endpoint {ep_id}")
                    insights["recommendations"].append(f"Investigate error causes for endpoint {ep_id}")
                
                if avg_response_time > 3000:  # 3 seconds
                    insights["alerts"].append(f"Slow response time ({avg_response_time:.0f}ms) on endpoint {ep_id}")
                    insights["recommendations"].append(f"Optimize performance for endpoint {ep_id}")
                
                # Trend analysis
                if len(ep_metrics) >= 24:  # Need enough data points
                    early_metrics = ep_metrics[-12:]  # 12 hours ago
                    recent_metrics = ep_metrics[:12]   # Recent 12 data points
                    
                    early_avg_response = statistics.mean([
                        m["avg_response_time_ms"] for m in early_metrics 
                        if m["avg_response_time_ms"] is not None
                    ])
                    recent_avg_response = statistics.mean([
                        m["avg_response_time_ms"] for m in recent_metrics 
                        if m["avg_response_time_ms"] is not None
                    ])
                    
                    if recent_avg_response > early_avg_response * 1.2:  # 20% increase
                        insights["trends"][f"endpoint_{ep_id}"] = "degrading_performance"
                        insights["recommendations"].append(f"Performance degrading on endpoint {ep_id}")
                    elif recent_avg_response < early_avg_response * 0.8:  # 20% improvement
                        insights["trends"][f"endpoint_{ep_id}"] = "improving_performance"
        
        # General recommendations based on overall health
        health_summary = await self.health_monitor.get_overall_health_summary()
        if health_summary["health_percentage"] < 80:
            insights["alerts"].append("Overall system health below 80%")
            insights["recommendations"].append("Review and address unhealthy endpoints")
        
        # Connection pool recommendations
        pool_stats = await self.connection_pool_manager.get_pool_statistics()
        for endpoint_id, pool_info in pool_stats["pools"].items():
            if pool_info["success_rate"] < 95:
                insights["recommendations"].append(
                    f"Low success rate ({pool_info['success_rate']:.1f}%) for endpoint {endpoint_id}"
                )
        
        insights["performance_score"] = round(insights["performance_score"], 1)
        return insights
    
    async def _collection_loop(self):
        """Main metrics collection loop."""
        logger.debug("Starting metrics collection loop")
        
        while self.running:
            try:
                # Collect and aggregate metrics for all active endpoints
                await self._collect_endpoint_metrics()
                
                # Clean up old metrics data
                await self._cleanup_old_metrics()
                
                # Reset in-memory buffers periodically
                await self._reset_metrics_buffers()
                
                # Wait for next collection cycle
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                logger.debug("Metrics collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}")
                # Wait before retrying on error
                await asyncio.sleep(min(self.collection_interval, 30))
    
    async def _collect_endpoint_metrics(self):
        """Collect metrics for all active endpoints."""
        try:
            async with get_async_session() as session:
                # Get all active endpoints
                result = await session.execute(
                    select(ConnectionEndpoint)
                    .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
                    .options(selectinload(ConnectionEndpoint.pools))
                )
                endpoints = result.scalars().all()
                
                for endpoint in endpoints:
                    await self._collect_single_endpoint_metrics(session, endpoint)
                
        except Exception as e:
            logger.error(f"Error collecting endpoint metrics: {str(e)}")
    
    async def _collect_single_endpoint_metrics(self, session: AsyncSession, 
                                             endpoint: ConnectionEndpoint):
        """Collect metrics for a single endpoint."""
        try:
            # Get in-memory metrics
            metrics = self.request_metrics[endpoint.id]
            response_times = list(metrics["response_times"])
            
            # Calculate aggregated values
            if response_times:
                avg_response_time = statistics.mean(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)
                p95_response_time = self._calculate_percentile(sorted(response_times), 95)
                p99_response_time = self._calculate_percentile(sorted(response_times), 99)
            else:
                avg_response_time = min_response_time = max_response_time = None
                p95_response_time = p99_response_time = None
            
            # Calculate rates
            total_requests = metrics["request_count"]
            error_rate = (metrics["failed_requests"] / total_requests * 100) if total_requests > 0 else 0
            timeout_rate = (metrics["timeout_requests"] / total_requests * 100) if total_requests > 0 else 0
            
            # Get connection pool information
            active_connections = 0
            peak_connections = 0
            connection_pool_usage = 0
            
            for pool in endpoint.pools:
                active_connections += pool.active_connections
                peak_connections += pool.current_size
                if pool.max_size > 0:
                    usage = (pool.current_size / pool.max_size) * 100
                    connection_pool_usage = max(connection_pool_usage, usage)
            
            # Create metrics record for different intervals
            intervals = [1, 5, 15, 60]  # 1min, 5min, 15min, 1hour
            current_time = datetime.utcnow()
            
            for interval in intervals:
                # Check if we should record this interval
                if self._should_record_interval(interval):
                    metrics_record = ConnectionMetrics(
                        endpoint_id=endpoint.id,
                        timestamp=current_time.replace(second=0, microsecond=0),
                        interval_minutes=interval,
                        request_count=metrics["request_count"],
                        successful_requests=metrics["successful_requests"],
                        failed_requests=metrics["failed_requests"],
                        timeout_requests=metrics["timeout_requests"],
                        avg_response_time_ms=avg_response_time,
                        min_response_time_ms=min_response_time,
                        max_response_time_ms=max_response_time,
                        p95_response_time_ms=p95_response_time,
                        p99_response_time_ms=p99_response_time,
                        active_connections=active_connections,
                        peak_connections=peak_connections,
                        connection_pool_usage=connection_pool_usage,
                        error_rate=error_rate,
                        timeout_rate=timeout_rate,
                        circuit_breaker_trips=0  # Would need to track this in circuit breaker
                    )
                    
                    session.add(metrics_record)
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error collecting metrics for endpoint {endpoint.id}: {str(e)}")
    
    def _should_record_interval(self, interval_minutes: int) -> bool:
        """Determine if we should record metrics for this interval."""
        current_minute = datetime.utcnow().minute
        
        if interval_minutes == 1:
            return True  # Always record 1-minute intervals
        elif interval_minutes == 5:
            return current_minute % 5 == 0
        elif interval_minutes == 15:
            return current_minute % 15 == 0
        elif interval_minutes == 60:
            return current_minute == 0
        
        return False
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0
        
        index = (percentile / 100) * (len(sorted_values) - 1)
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics data based on retention policy."""
        try:
            # Keep detailed metrics for 7 days, aggregated for 30 days
            detailed_cutoff = datetime.utcnow() - timedelta(days=7)
            aggregated_cutoff = datetime.utcnow() - timedelta(days=30)
            
            async with get_async_session() as session:
                # Delete old detailed metrics (1-minute intervals)
                await session.execute(
                    ConnectionMetrics.__table__.delete().where(
                        and_(
                            ConnectionMetrics.interval_minutes == 1,
                            ConnectionMetrics.timestamp < detailed_cutoff
                        )
                    )
                )
                
                # Delete very old aggregated metrics
                await session.execute(
                    ConnectionMetrics.__table__.delete().where(
                        ConnectionMetrics.timestamp < aggregated_cutoff
                    )
                )
                
                # Delete old health records (keep 30 days)
                health_cutoff = datetime.utcnow() - timedelta(days=30)
                await session.execute(
                    ConnectionHealth.__table__.delete().where(
                        ConnectionHealth.check_timestamp < health_cutoff
                    )
                )
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")
    
    async def _reset_metrics_buffers(self):
        """Reset in-memory metrics buffers periodically."""
        current_time = time.time()
        reset_interval = 3600  # Reset every hour
        
        for endpoint_id, metrics in list(self.request_metrics.items()):
            if current_time - metrics["last_reset"] > reset_interval:
                # Keep the structure but reset counters
                self.request_metrics[endpoint_id] = {
                    "request_count": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "timeout_requests": 0,
                    "response_times": deque(maxlen=1000),
                    "error_count": 0,
                    "last_reset": current_time
                }