"""
Connection Pool Manager Service for dynamic endpoint routing and load balancing.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.redis_client import get_redis_client
from app.models.connection_models import (
    ConnectionEndpoint, ConnectionPool, LoadBalancerConfig, 
    EndpointType, EndpointStatus, HealthStatus, LoadBalancerAlgorithm
)

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Manages connection pools and load balancing for Splunk instances."""
    
    def __init__(self):
        self.pools: Dict[int, aiohttp.ClientSession] = {}
        self.load_balancer_state: Dict[str, Any] = {}
        self.circuit_breakers: Dict[int, Dict[str, Any]] = {}
        self.session_affinity: Dict[str, int] = {}  # session_id -> endpoint_id
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the connection pool manager."""
        if self._initialized:
            return
            
        logger.info("Initializing Connection Pool Manager...")
        
        try:
            # Initialize Redis client
            self.redis = await get_redis_client()
            
            # Load existing endpoints and create pools
            async with get_async_session() as session:
                result = await session.execute(
                    select(ConnectionEndpoint)
                    .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
                    .options(selectinload(ConnectionEndpoint.pools))
                )
                endpoints = result.scalars().all()
                
                for endpoint in endpoints:
                    await self._create_connection_pool(endpoint)
                    self._initialize_circuit_breaker(endpoint.id)
                    
            # Load load balancer configurations
            await self._load_load_balancer_configs()
            
            self._initialized = True
            logger.info(f"Connection Pool Manager initialized with {len(self.pools)} pools")
            
        except Exception as e:
            logger.error(f"Failed to initialize Connection Pool Manager: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup connection pools and resources."""
        logger.info("Cleaning up Connection Pool Manager...")
        
        async with self._lock:
            # Close all connection pools
            for endpoint_id, session in self.pools.items():
                try:
                    await session.close()
                    logger.debug(f"Closed connection pool for endpoint {endpoint_id}")
                except Exception as e:
                    logger.error(f"Error closing pool for endpoint {endpoint_id}: {str(e)}")
            
            self.pools.clear()
            self.circuit_breakers.clear()
            self.session_affinity.clear()
            self.load_balancer_state.clear()
            
        logger.info("Connection Pool Manager cleanup complete")
    
    async def get_connection(self, endpoint_type: Optional[EndpointType] = None, 
                           tenant_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           lb_config_name: str = "default") -> Tuple[int, aiohttp.ClientSession]:
        """
        Get an optimal connection based on load balancing configuration.
        
        Args:
            endpoint_type: Filter by endpoint type (enterprise/cloud)
            tenant_id: Filter by tenant ID for cloud instances
            session_id: Session ID for sticky sessions
            lb_config_name: Load balancer configuration name
            
        Returns:
            Tuple of (endpoint_id, client_session)
        """
        if not self._initialized:
            await self.initialize()
        
        async with self._lock:
            # Get load balancer configuration
            lb_config = self.load_balancer_state.get(lb_config_name)
            if not lb_config:
                lb_config = self.load_balancer_state.get("default")
            
            if not lb_config:
                raise ValueError(f"Load balancer configuration '{lb_config_name}' not found")
            
            # Handle sticky sessions
            if lb_config.get("sticky_sessions") and session_id:
                if session_id in self.session_affinity:
                    endpoint_id = self.session_affinity[session_id]
                    if endpoint_id in self.pools and self._is_endpoint_healthy(endpoint_id):
                        return endpoint_id, self.pools[endpoint_id]
            
            # Get eligible endpoints
            eligible_endpoints = await self._get_eligible_endpoints(
                endpoint_type, tenant_id, lb_config
            )
            
            if not eligible_endpoints:
                raise RuntimeError("No healthy endpoints available")
            
            # Apply load balancing algorithm
            algorithm = lb_config.get("algorithm", LoadBalancerAlgorithm.ROUND_ROBIN)
            endpoint_id = await self._apply_load_balancing_algorithm(
                algorithm, eligible_endpoints, lb_config_name
            )
            
            # Update session affinity if enabled
            if lb_config.get("sticky_sessions") and session_id:
                self.session_affinity[session_id] = endpoint_id
                # Set expiration for session affinity
                timeout = lb_config.get("session_affinity_timeout", 3600)
                asyncio.create_task(self._expire_session_affinity(session_id, timeout))
            
            return endpoint_id, self.pools[endpoint_id]
    
    async def add_endpoint(self, endpoint: ConnectionEndpoint) -> bool:
        """Add a new endpoint and create its connection pool."""
        try:
            async with self._lock:
                await self._create_connection_pool(endpoint)
                self._initialize_circuit_breaker(endpoint.id)
                
            logger.info(f"Added endpoint {endpoint.id} ({endpoint.name}) to connection pool")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add endpoint {endpoint.id}: {str(e)}")
            return False
    
    async def remove_endpoint(self, endpoint_id: int) -> bool:
        """Remove an endpoint and close its connection pool."""
        try:
            async with self._lock:
                if endpoint_id in self.pools:
                    await self.pools[endpoint_id].close()
                    del self.pools[endpoint_id]
                
                if endpoint_id in self.circuit_breakers:
                    del self.circuit_breakers[endpoint_id]
                
                # Remove from session affinity
                self.session_affinity = {
                    session_id: eid for session_id, eid in self.session_affinity.items() 
                    if eid != endpoint_id
                }
                
            logger.info(f"Removed endpoint {endpoint_id} from connection pool")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove endpoint {endpoint_id}: {str(e)}")
            return False
    
    async def update_endpoint_health(self, endpoint_id: int, health_status: HealthStatus):
        """Update endpoint health status and manage circuit breaker."""
        if endpoint_id not in self.circuit_breakers:
            return
        
        circuit_breaker = self.circuit_breakers[endpoint_id]
        current_time = time.time()
        
        if health_status == HealthStatus.HEALTHY:
            # Reset circuit breaker on successful health check
            circuit_breaker.update({
                "failure_count": 0,
                "last_failure_time": None,
                "state": "closed"
            })
        else:
            # Increment failure count
            circuit_breaker["failure_count"] += 1
            circuit_breaker["last_failure_time"] = current_time
            
            # Check if circuit breaker should open
            threshold = circuit_breaker.get("failure_threshold", 5)
            if circuit_breaker["failure_count"] >= threshold:
                circuit_breaker["state"] = "open"
                circuit_breaker["open_time"] = current_time
                logger.warning(f"Circuit breaker opened for endpoint {endpoint_id}")
    
    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "total_pools": len(self.pools),
            "pools": {},
            "circuit_breakers": {},
            "session_affinity_count": len(self.session_affinity)
        }
        
        # Get pool details from database
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionPool, ConnectionEndpoint)
                .join(ConnectionEndpoint)
                .where(ConnectionEndpoint.status == EndpointStatus.ACTIVE)
            )
            pool_data = result.all()
            
            for pool, endpoint in pool_data:
                stats["pools"][endpoint.id] = {
                    "endpoint_name": endpoint.name,
                    "endpoint_type": endpoint.endpoint_type.value,
                    "pool_name": pool.pool_name,
                    "current_size": pool.current_size,
                    "active_connections": pool.active_connections,
                    "idle_connections": pool.idle_connections,
                    "total_requests": pool.total_requests,
                    "successful_requests": pool.total_successful_requests,
                    "failed_requests": pool.total_failed_requests,
                    "success_rate": (
                        pool.total_successful_requests / pool.total_requests * 100
                        if pool.total_requests > 0 else 0
                    )
                }
        
        # Add circuit breaker states
        for endpoint_id, cb_state in self.circuit_breakers.items():
            stats["circuit_breakers"][endpoint_id] = {
                "state": cb_state.get("state", "closed"),
                "failure_count": cb_state.get("failure_count", 0),
                "last_failure_time": cb_state.get("last_failure_time")
            }
        
        return stats
    
    async def _create_connection_pool(self, endpoint: ConnectionEndpoint):
        """Create a connection pool for an endpoint."""
        timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
        connector = aiohttp.TCPConnector(
            limit=endpoint.max_connections,
            limit_per_host=endpoint.max_connections,
            keepalive_timeout=300,
            enable_cleanup_closed=True
        )
        
        # Create headers for authentication
        headers = {}
        if endpoint.auth_token:
            headers["Authorization"] = f"Bearer {endpoint.auth_token}"
        elif endpoint.username and endpoint.password:
            # Basic auth would be handled by aiohttp.BasicAuth
            pass
        
        session = aiohttp.ClientSession(
            base_url=endpoint.base_url,
            timeout=timeout,
            connector=connector,
            headers=headers
        )
        
        self.pools[endpoint.id] = session
        logger.debug(f"Created connection pool for endpoint {endpoint.id} ({endpoint.name})")
    
    def _initialize_circuit_breaker(self, endpoint_id: int):
        """Initialize circuit breaker for an endpoint."""
        self.circuit_breakers[endpoint_id] = {
            "state": "closed",  # closed, open, half-open
            "failure_count": 0,
            "failure_threshold": 5,
            "timeout": 60,  # seconds
            "last_failure_time": None,
            "open_time": None
        }
    
    async def _load_load_balancer_configs(self):
        """Load load balancer configurations from database."""
        async with get_async_session() as session:
            result = await session.execute(
                select(LoadBalancerConfig)
                .where(LoadBalancerConfig.is_active == True)
            )
            configs = result.scalars().all()
            
            for config in configs:
                self.load_balancer_state[config.name] = {
                    "algorithm": config.algorithm,
                    "health_check_interval": config.health_check_interval,
                    "health_check_timeout": config.health_check_timeout,
                    "failover_timeout": config.failover_timeout,
                    "circuit_breaker_enabled": config.circuit_breaker_enabled,
                    "circuit_breaker_failure_threshold": config.circuit_breaker_failure_threshold,
                    "circuit_breaker_timeout": config.circuit_breaker_timeout,
                    "sticky_sessions": config.sticky_sessions,
                    "session_affinity_timeout": config.session_affinity_timeout,
                    "retry_attempts": config.retry_attempts,
                    "retry_delay": config.retry_delay,
                    "endpoint_types": config.endpoint_types,
                    "endpoint_tags": config.endpoint_tags,
                    "round_robin_index": 0  # For round-robin algorithm
                }
            
            # Ensure default configuration exists
            if "default" not in self.load_balancer_state:
                self.load_balancer_state["default"] = {
                    "algorithm": LoadBalancerAlgorithm.ROUND_ROBIN,
                    "health_check_interval": 30,
                    "health_check_timeout": 10,
                    "failover_timeout": 30,
                    "circuit_breaker_enabled": True,
                    "circuit_breaker_failure_threshold": 5,
                    "circuit_breaker_timeout": 60,
                    "sticky_sessions": False,
                    "session_affinity_timeout": 3600,
                    "retry_attempts": 3,
                    "retry_delay": 1.0,
                    "endpoint_types": [],
                    "endpoint_tags": {},
                    "round_robin_index": 0
                }
    
    async def _get_eligible_endpoints(self, endpoint_type: Optional[EndpointType], 
                                    tenant_id: Optional[str],
                                    lb_config: Dict[str, Any]) -> List[int]:
        """Get list of eligible endpoint IDs based on filters and health."""
        async with get_async_session() as session:
            # Build query with filters
            query = select(ConnectionEndpoint.id).where(
                and_(
                    ConnectionEndpoint.status == EndpointStatus.ACTIVE,
                    ConnectionEndpoint.health_status.in_([HealthStatus.HEALTHY, HealthStatus.DEGRADED])
                )
            )
            
            # Apply endpoint type filter
            if endpoint_type:
                query = query.where(ConnectionEndpoint.endpoint_type == endpoint_type)
            elif lb_config.get("endpoint_types"):
                query = query.where(ConnectionEndpoint.endpoint_type.in_(lb_config["endpoint_types"]))
            
            # Apply tenant filter for cloud instances
            if tenant_id:
                query = query.where(ConnectionEndpoint.tenant_id == tenant_id)
            
            # Apply tag filters
            endpoint_tags = lb_config.get("endpoint_tags", {})
            for tag_key, tag_value in endpoint_tags.items():
                query = query.where(ConnectionEndpoint.tags[tag_key].astext == str(tag_value))
            
            result = await session.execute(query)
            endpoint_ids = result.scalars().all()
            
            # Filter out endpoints with open circuit breakers
            if lb_config.get("circuit_breaker_enabled", True):
                eligible_endpoints = []
                current_time = time.time()
                
                for endpoint_id in endpoint_ids:
                    if endpoint_id not in self.circuit_breakers:
                        eligible_endpoints.append(endpoint_id)
                        continue
                    
                    cb_state = self.circuit_breakers[endpoint_id]
                    if cb_state["state"] == "closed":
                        eligible_endpoints.append(endpoint_id)
                    elif cb_state["state"] == "open":
                        # Check if circuit breaker should transition to half-open
                        open_time = cb_state.get("open_time", 0)
                        timeout = cb_state.get("timeout", 60)
                        if current_time - open_time >= timeout:
                            cb_state["state"] = "half-open"
                            eligible_endpoints.append(endpoint_id)
                    elif cb_state["state"] == "half-open":
                        eligible_endpoints.append(endpoint_id)
                
                return eligible_endpoints
            
            return list(endpoint_ids)
    
    async def _apply_load_balancing_algorithm(self, algorithm: LoadBalancerAlgorithm,
                                            endpoints: List[int],
                                            config_name: str) -> int:
        """Apply load balancing algorithm to select an endpoint."""
        if not endpoints:
            raise RuntimeError("No endpoints available for load balancing")
        
        if algorithm == LoadBalancerAlgorithm.ROUND_ROBIN:
            return await self._round_robin_selection(endpoints, config_name)
        elif algorithm == LoadBalancerAlgorithm.LEAST_CONNECTIONS:
            return await self._least_connections_selection(endpoints)
        elif algorithm == LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_selection(endpoints)
        elif algorithm == LoadBalancerAlgorithm.RANDOM:
            return random.choice(endpoints)
        else:
            # Default to round-robin
            return await self._round_robin_selection(endpoints, config_name)
    
    async def _round_robin_selection(self, endpoints: List[int], config_name: str) -> int:
        """Round-robin endpoint selection."""
        config = self.load_balancer_state[config_name]
        index = config.get("round_robin_index", 0)
        
        selected_endpoint = endpoints[index % len(endpoints)]
        config["round_robin_index"] = (index + 1) % len(endpoints)
        
        return selected_endpoint
    
    async def _least_connections_selection(self, endpoints: List[int]) -> int:
        """Select endpoint with least active connections."""
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionPool.endpoint_id, ConnectionPool.active_connections)
                .where(ConnectionPool.endpoint_id.in_(endpoints))
                .order_by(ConnectionPool.active_connections.asc())
            )
            pool_data = result.first()
            
            if pool_data:
                return pool_data.endpoint_id
            
            # Fallback to random selection if no pool data
            return random.choice(endpoints)
    
    async def _weighted_round_robin_selection(self, endpoints: List[int]) -> int:
        """Weighted round-robin selection based on endpoint weights."""
        async with get_async_session() as session:
            result = await session.execute(
                select(ConnectionEndpoint.id, ConnectionEndpoint.weight)
                .where(ConnectionEndpoint.id.in_(endpoints))
            )
            endpoint_weights = {row.id: row.weight for row in result.all()}
            
            # Create weighted list
            weighted_endpoints = []
            for endpoint_id in endpoints:
                weight = endpoint_weights.get(endpoint_id, 100)
                weighted_endpoints.extend([endpoint_id] * weight)
            
            if weighted_endpoints:
                return random.choice(weighted_endpoints)
            
            # Fallback to random selection
            return random.choice(endpoints)
    
    def _is_endpoint_healthy(self, endpoint_id: int) -> bool:
        """Check if an endpoint is healthy based on circuit breaker state."""
        if endpoint_id not in self.circuit_breakers:
            return True
        
        cb_state = self.circuit_breakers[endpoint_id]
        return cb_state.get("state", "closed") != "open"
    
    async def _expire_session_affinity(self, session_id: str, timeout: int):
        """Expire session affinity after timeout."""
        await asyncio.sleep(timeout)
        if session_id in self.session_affinity:
            del self.session_affinity[session_id]