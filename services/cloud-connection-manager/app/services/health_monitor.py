"""
Health Monitor Service for continuous endpoint health checking and monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.redis_client import get_redis_client
from app.models.connection_models import (
    ConnectionEndpoint, ConnectionHealth, ConnectionMetrics,
    EndpointStatus, HealthStatus
)

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors health of all connection endpoints."""
    
    def __init__(self, connection_pool_manager):
        self.connection_pool_manager = connection_pool_manager
        self.monitoring_tasks: Dict[int, asyncio.Task] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 10  # seconds
        self.running = False
        self._redis = None
        
    async def start(self):
        """Start health monitoring for all active endpoints."""
        if self.running:
            return
        
        logger.info("Starting Health Monitor...")
        
        try:
            # Initialize Redis client
            self._redis = await get_redis_client()
            
            # Load all active endpoints and start monitoring
            async with get_async_session() as session:
                result = await session.execute(
                    select(ConnectionEndpoint)
                    .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
                )
                endpoints = result.scalars().all()
                
                for endpoint in endpoints:
                    await self._start_endpoint_monitoring(endpoint)
            
            self.running = True
            logger.info(f"Health Monitor started for {len(self.monitoring_tasks)} endpoints")
            
        except Exception as e:
            logger.error(f"Failed to start Health Monitor: {str(e)}")
            raise
    
    async def stop(self):
        """Stop health monitoring for all endpoints."""
        if not self.running:
            return
        
        logger.info("Stopping Health Monitor...")
        
        # Cancel all monitoring tasks
        for endpoint_id, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping monitoring for endpoint {endpoint_id}: {str(e)}")
        
        self.monitoring_tasks.clear()
        self.running = False
        
        logger.info("Health Monitor stopped")
    
    async def add_endpoint(self, endpoint: ConnectionEndpoint):
        """Add endpoint to health monitoring."""
        if endpoint.id not in self.monitoring_tasks:
            await self._start_endpoint_monitoring(endpoint)
            logger.info(f"Added endpoint {endpoint.id} ({endpoint.name}) to health monitoring")
    
    async def remove_endpoint(self, endpoint_id: int):
        """Remove endpoint from health monitoring."""
        if endpoint_id in self.monitoring_tasks:
            self.monitoring_tasks[endpoint_id].cancel()
            try:
                await self.monitoring_tasks[endpoint_id]
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping monitoring for endpoint {endpoint_id}: {str(e)}")
            
            del self.monitoring_tasks[endpoint_id]
            logger.info(f"Removed endpoint {endpoint_id} from health monitoring")
    
    async def perform_health_check(self, endpoint_id: int) -> Optional[Dict[str, Any]]:
        """Perform immediate health check on an endpoint."""
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionEndpoint)
                .where(ConnectionEndpoint.id == endpoint_id)
            )
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                return None
            
            return await self._check_endpoint_health(endpoint)
    
    async def get_endpoint_health_history(self, endpoint_id: int, 
                                         hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history for an endpoint."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionHealth)
                .where(
                    and_(
                        ConnectionHealth.endpoint_id == endpoint_id,
                        ConnectionHealth.check_timestamp >= since
                    )
                )
                .order_by(desc(ConnectionHealth.check_timestamp))
                .limit(1000)  # Limit to prevent excessive data
            )
            health_records = result.scalars().all()
            
            return [
                {
                    "timestamp": record.check_timestamp,
                    "health_status": record.health_status.value,
                    "response_time_ms": record.response_time_ms,
                    "is_reachable": record.is_reachable,
                    "status_code": record.status_code,
                    "error_message": record.error_message,
                    "cpu_usage": record.cpu_usage,
                    "memory_usage": record.memory_usage,
                    "disk_usage": record.disk_usage,
                    "connection_count": record.connection_count
                }
                for record in health_records
            ]
    
    async def get_overall_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary for all endpoints."""
        async with get_async_session() as session:
            # Get current health status counts
            result = await session.execute(
                select(
                    ConnectionEndpoint.health_status,
                    ConnectionEndpoint.endpoint_type,
                    ConnectionEndpoint.id
                )
                .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
            )
            endpoints = result.all()
            
            # Aggregate health statistics
            health_summary = {
                "total_endpoints": len(endpoints),
                "healthy_endpoints": 0,
                "degraded_endpoints": 0,
                "unhealthy_endpoints": 0,
                "unknown_endpoints": 0,
                "by_type": {
                    "enterprise": {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0},
                    "cloud": {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0}
                },
                "monitoring_tasks": len(self.monitoring_tasks),
                "last_updated": datetime.utcnow()
            }
            
            for endpoint in endpoints:
                health_status = endpoint.health_status
                endpoint_type = endpoint.endpoint_type.value
                
                # Update type-specific counts
                health_summary["by_type"][endpoint_type]["total"] += 1
                
                # Update overall and type-specific health counts
                if health_status == HealthStatus.HEALTHY:
                    health_summary["healthy_endpoints"] += 1
                    health_summary["by_type"][endpoint_type]["healthy"] += 1
                elif health_status == HealthStatus.DEGRADED:
                    health_summary["degraded_endpoints"] += 1
                    health_summary["by_type"][endpoint_type]["degraded"] += 1
                elif health_status == HealthStatus.UNHEALTHY:
                    health_summary["unhealthy_endpoints"] += 1
                    health_summary["by_type"][endpoint_type]["unhealthy"] += 1
                else:  # UNKNOWN
                    health_summary["unknown_endpoints"] += 1
            
            # Calculate health percentages
            if health_summary["total_endpoints"] > 0:
                health_summary["health_percentage"] = round(
                    (health_summary["healthy_endpoints"] / health_summary["total_endpoints"]) * 100, 2
                )
            else:
                health_summary["health_percentage"] = 0.0
            
            return health_summary
    
    async def _start_endpoint_monitoring(self, endpoint: ConnectionEndpoint):
        """Start health monitoring task for an endpoint."""
        if endpoint.id in self.monitoring_tasks:
            return
        
        task = asyncio.create_task(
            self._monitor_endpoint_health(endpoint),
            name=f"health_monitor_{endpoint.id}"
        )
        self.monitoring_tasks[endpoint.id] = task
    
    async def _monitor_endpoint_health(self, endpoint: ConnectionEndpoint):
        """Continuously monitor health of a single endpoint."""
        logger.debug(f"Starting health monitoring for endpoint {endpoint.id} ({endpoint.name})")
        
        while self.running:
            try:
                # Perform health check
                health_result = await self._check_endpoint_health(endpoint)
                
                # Store health check result
                await self._store_health_result(endpoint.id, health_result)
                
                # Update endpoint health status in database
                await self._update_endpoint_health_status(endpoint.id, health_result)
                
                # Update connection pool manager
                await self.connection_pool_manager.update_endpoint_health(
                    endpoint.id, health_result["health_status"]
                )
                
                # Cache health status in Redis for quick access
                await self._cache_health_status(endpoint.id, health_result)
                
                # Wait for next check
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                logger.debug(f"Health monitoring cancelled for endpoint {endpoint.id}")
                break
            except Exception as e:
                logger.error(f"Error monitoring endpoint {endpoint.id}: {str(e)}")
                # Wait before retrying on error
                await asyncio.sleep(min(self.health_check_interval, 30))
    
    async def _check_endpoint_health(self, endpoint: ConnectionEndpoint) -> Dict[str, Any]:
        """Perform health check on a single endpoint."""
        start_time = time.time()
        health_result = {
            "endpoint_id": endpoint.id,
            "health_status": HealthStatus.UNKNOWN,
            "response_time_ms": None,
            "is_reachable": False,
            "status_code": None,
            "error_message": None,
            "check_details": {},
            "cpu_usage": None,
            "memory_usage": None,
            "disk_usage": None,
            "connection_count": None
        }
        
        try:
            # Create timeout for health check
            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)
            
            # Prepare authentication headers
            headers = {}
            if endpoint.auth_token:
                headers["Authorization"] = f"Bearer {endpoint.auth_token}"
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # Health check endpoint - try common Splunk health endpoints
                health_endpoints = [
                    "/services/server/health-config",  # Splunk health endpoint
                    "/services/server/info",           # Splunk server info
                    "/health",                         # Common health endpoint
                    "/api/health",                     # API health endpoint
                    "/"                                # Root endpoint as fallback
                ]
                
                check_successful = False
                
                for health_path in health_endpoints:
                    try:
                        url = f"{endpoint.base_url}{health_path}"
                        async with session.get(url) as response:
                            response_time = (time.time() - start_time) * 1000
                            health_result["response_time_ms"] = round(response_time, 2)
                            health_result["status_code"] = response.status
                            health_result["is_reachable"] = True
                            
                            # Try to get response content for additional details
                            try:
                                content = await response.text()
                                health_result["check_details"]["response_content"] = content[:1000]  # Limit content
                            except:
                                pass
                            
                            # Determine health status based on response
                            if response.status == 200:
                                health_result["health_status"] = HealthStatus.HEALTHY
                                check_successful = True
                                break
                            elif 200 <= response.status < 400:
                                health_result["health_status"] = HealthStatus.HEALTHY
                                check_successful = True
                                break
                            elif 400 <= response.status < 500:
                                # Client errors might still indicate the server is responsive
                                health_result["health_status"] = HealthStatus.DEGRADED
                                health_result["error_message"] = f"HTTP {response.status}"
                                check_successful = True
                                break
                            else:
                                # Server errors indicate unhealthy state
                                health_result["health_status"] = HealthStatus.UNHEALTHY
                                health_result["error_message"] = f"HTTP {response.status}"
                                # Continue to try other endpoints
                    
                    except asyncio.TimeoutError:
                        health_result["error_message"] = "Health check timeout"
                        continue
                    except Exception as endpoint_error:
                        health_result["error_message"] = str(endpoint_error)
                        continue
                
                if not check_successful:
                    health_result["health_status"] = HealthStatus.UNHEALTHY
                    if not health_result["error_message"]:
                        health_result["error_message"] = "All health check endpoints failed"
        
        except asyncio.TimeoutError:
            health_result["health_status"] = HealthStatus.UNHEALTHY
            health_result["error_message"] = "Connection timeout"
        except Exception as e:
            health_result["health_status"] = HealthStatus.UNHEALTHY
            health_result["error_message"] = str(e)
            logger.debug(f"Health check failed for endpoint {endpoint.id}: {str(e)}")
        
        # If no response time was recorded, calculate elapsed time
        if health_result["response_time_ms"] is None:
            health_result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return health_result
    
    async def _store_health_result(self, endpoint_id: int, health_result: Dict[str, Any]):
        """Store health check result in database."""
        try:
            async with get_async_session() as session:
                health_record = ConnectionHealth(
                    endpoint_id=endpoint_id,
                    health_status=health_result["health_status"],
                    response_time_ms=health_result["response_time_ms"],
                    is_reachable=health_result["is_reachable"],
                    status_code=health_result["status_code"],
                    error_message=health_result["error_message"],
                    check_details=health_result["check_details"],
                    cpu_usage=health_result["cpu_usage"],
                    memory_usage=health_result["memory_usage"],
                    disk_usage=health_result["disk_usage"],
                    connection_count=health_result["connection_count"],
                    check_timestamp=datetime.utcnow()
                )
                
                session.add(health_record)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store health result for endpoint {endpoint_id}: {str(e)}")
    
    async def _update_endpoint_health_status(self, endpoint_id: int, health_result: Dict[str, Any]):
        """Update endpoint health status in database."""
        try:
            async with get_async_session() as session:
                # Update endpoint health status and consecutive failures
                health_status = health_result["health_status"]
                
                # Get current endpoint data
                result = await session.execute(
                    select(ConnectionEndpoint)
                    .where(ConnectionEndpoint.id == endpoint_id)
                )
                endpoint = result.scalar_one_or_none()
                
                if endpoint:
                    # Update consecutive failures
                    if health_status == HealthStatus.HEALTHY:
                        consecutive_failures = 0
                    else:
                        consecutive_failures = endpoint.consecutive_failures + 1
                    
                    # Update endpoint
                    await session.execute(
                        update(ConnectionEndpoint)
                        .where(ConnectionEndpoint.id == endpoint_id)
                        .values(
                            health_status=health_status,
                            last_health_check=datetime.utcnow(),
                            consecutive_failures=consecutive_failures
                        )
                    )
                    
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update endpoint health status for {endpoint_id}: {str(e)}")
    
    async def _cache_health_status(self, endpoint_id: int, health_result: Dict[str, Any]):
        """Cache health status in Redis for quick access."""
        if not self._redis:
            return
        
        try:
            cache_key = f"endpoint_health:{endpoint_id}"
            cache_data = {
                "health_status": health_result["health_status"].value,
                "response_time_ms": health_result["response_time_ms"],
                "is_reachable": health_result["is_reachable"],
                "last_check": datetime.utcnow().isoformat(),
                "error_message": health_result["error_message"]
            }
            
            # Cache for 2x the health check interval
            ttl = self.health_check_interval * 2
            await self._redis.setex(
                cache_key, 
                ttl, 
                str(cache_data)
            )
            
        except Exception as e:
            logger.debug(f"Failed to cache health status for endpoint {endpoint_id}: {str(e)}")