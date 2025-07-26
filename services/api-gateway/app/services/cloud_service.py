"""
Cloud service for managing Splunk Cloud instances
Integrates with the Cloud Connection Manager service
"""

import aiohttp
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
from urllib.parse import urljoin

from app.core.config import settings
from app.core.logging import get_logger
from app.models.cloud import (
    CloudInstanceCreate,
    CloudInstanceUpdate,
    CloudInstanceResponse,
    CloudInstanceWithHealth,
    CloudConnectionRequest,
    CloudConnectionResponse,
    CloudHealthCheck,
    CloudMetrics,
    EndpointType,
    InstanceStatus,
    HealthStatus
)

logger = get_logger(__name__)


class CloudService:
    """Service for managing Splunk Cloud instances through Cloud Connection Manager"""
    
    def __init__(self):
        self.connection_manager_url = getattr(settings, 'cloud_connection_manager_url', 'http://cloud-connection-manager:8018')
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Cloud Connection Manager"""
        url = urljoin(self.connection_manager_url, endpoint)
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                request_kwargs = {
                    'url': url,
                    'headers': {'Content-Type': 'application/json'}
                }
                
                if data:
                    request_kwargs['json'] = data
                if params:
                    request_kwargs['params'] = params
                
                async with session.request(method, **request_kwargs) as response:
                    if response.status == 404:
                        return None
                    
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(
                "Cloud Connection Manager request failed",
                url=url,
                method=method,
                error=str(e)
            )
            raise Exception(f"Failed to communicate with Cloud Connection Manager: {str(e)}")
        except Exception as e:
            logger.error(
                "Unexpected error in Cloud Connection Manager request",
                url=url,
                method=method,
                error=str(e)
            )
            raise
    
    async def create_instance(
        self, 
        instance_data: CloudInstanceCreate, 
        created_by: int
    ) -> CloudInstanceResponse:
        """Create a new cloud instance in Connection Manager"""
        try:
            # Prepare request data for Connection Manager
            request_data = {
                "name": instance_data.name,
                "endpoint_type": instance_data.endpoint_type.value,
                "host": instance_data.host,
                "port": instance_data.port,
                "scheme": instance_data.scheme,
                "tenant_id": instance_data.tenant_id,
                "priority": instance_data.priority,
                "weight": instance_data.weight,
                "max_connections": instance_data.max_connections,
                "timeout": instance_data.timeout,
                "auth_token": instance_data.auth_token,
                "username": instance_data.username,
                "password": instance_data.password,
                "tags": instance_data.tags or {},
                "description": instance_data.description,
                "created_by": created_by
            }
            
            response = await self._make_request(
                'POST',
                '/api/v1/connections/endpoints',
                data=request_data
            )
            
            if not response:
                raise Exception("Failed to create cloud instance")
            
            # Convert response to our model format
            instance_data = response.get('data', response)
            return CloudInstanceResponse(
                id=instance_data['id'],
                name=instance_data['name'],
                description=instance_data.get('description'),
                endpoint_type=EndpointType(instance_data['endpoint_type']),
                host=instance_data['host'],
                port=instance_data['port'],
                scheme=instance_data['scheme'],
                tenant_id=instance_data.get('tenant_id'),
                priority=instance_data['priority'],
                weight=instance_data['weight'],
                max_connections=instance_data['max_connections'],
                timeout=instance_data['timeout'],
                tags=instance_data.get('tags', {}),
                status=InstanceStatus(instance_data.get('status', 'active')),
                created_at=datetime.fromisoformat(instance_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(instance_data['updated_at'].replace('Z', '+00:00')) if instance_data.get('updated_at') else None,
                created_by=instance_data['created_by'],
                updated_by=instance_data.get('updated_by')
            )
            
        except Exception as e:
            logger.error("Failed to create cloud instance", error=str(e), created_by=created_by)
            raise
    
    async def list_instances(
        self,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        include_health: bool = True,
        user_id: int = None
    ) -> List[CloudInstanceWithHealth]:
        """List cloud instances with optional filtering"""
        try:
            params = {
                'limit': limit,
                'offset': offset
            }
            
            if tenant_id:
                params['tenant_id'] = tenant_id
            if status:
                params['status'] = status
            
            response = await self._make_request(
                'GET',
                '/api/v1/connections/endpoints',
                params=params
            )
            
            if not response:
                return []
            
            instances_data = response.get('data', [])
            instances = []
            
            for instance_data in instances_data:
                # Create base instance
                instance = CloudInstanceResponse(
                    id=instance_data['id'],
                    name=instance_data['name'],
                    description=instance_data.get('description'),
                    endpoint_type=EndpointType(instance_data['endpoint_type']),
                    host=instance_data['host'],
                    port=instance_data['port'],
                    scheme=instance_data['scheme'],
                    tenant_id=instance_data.get('tenant_id'),
                    priority=instance_data['priority'],
                    weight=instance_data['weight'],
                    max_connections=instance_data['max_connections'],
                    timeout=instance_data['timeout'],
                    tags=instance_data.get('tags', {}),
                    status=InstanceStatus(instance_data.get('status', 'active')),
                    created_at=datetime.fromisoformat(instance_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(instance_data['updated_at'].replace('Z', '+00:00')) if instance_data.get('updated_at') else None,
                    created_by=instance_data['created_by'],
                    updated_by=instance_data.get('updated_by')
                )
                
                # Add health information if requested
                health = None
                if include_health:
                    health = await self._get_health_for_instance(instance_data['id'])
                
                instances.append(CloudInstanceWithHealth(
                    **instance.dict(),
                    health=health
                ))
            
            return instances
            
        except Exception as e:
            logger.error("Failed to list cloud instances", error=str(e), user_id=user_id)
            raise
    
    async def get_instance(
        self,
        instance_id: int,
        include_metrics: bool = False,
        user_id: int = None
    ) -> Optional[CloudInstanceWithHealth]:
        """Get detailed information about a specific cloud instance"""
        try:
            response = await self._make_request(
                'GET',
                f'/api/v1/connections/endpoints/{instance_id}'
            )
            
            if not response:
                return None
            
            instance_data = response.get('data', response)
            
            # Create base instance
            instance = CloudInstanceResponse(
                id=instance_data['id'],
                name=instance_data['name'],
                description=instance_data.get('description'),
                endpoint_type=EndpointType(instance_data['endpoint_type']),
                host=instance_data['host'],
                port=instance_data['port'],
                scheme=instance_data['scheme'],
                tenant_id=instance_data.get('tenant_id'),
                priority=instance_data['priority'],
                weight=instance_data['weight'],
                max_connections=instance_data['max_connections'],
                timeout=instance_data['timeout'],
                tags=instance_data.get('tags', {}),
                status=InstanceStatus(instance_data.get('status', 'active')),
                created_at=datetime.fromisoformat(instance_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(instance_data['updated_at'].replace('Z', '+00:00')) if instance_data.get('updated_at') else None,
                created_by=instance_data['created_by'],
                updated_by=instance_data.get('updated_by')
            )
            
            # Get health information
            health = await self._get_health_for_instance(instance_id)
            
            return CloudInstanceWithHealth(
                **instance.dict(),
                health=health
            )
            
        except Exception as e:
            logger.error("Failed to get cloud instance", instance_id=instance_id, error=str(e), user_id=user_id)
            raise
    
    async def update_instance(
        self,
        instance_id: int,
        instance_data: CloudInstanceUpdate,
        updated_by: int
    ) -> Optional[CloudInstanceResponse]:
        """Update a cloud instance configuration"""
        try:
            # Prepare update data
            update_data = {}
            
            if instance_data.name is not None:
                update_data['name'] = instance_data.name
            if instance_data.description is not None:
                update_data['description'] = instance_data.description
            if instance_data.priority is not None:
                update_data['priority'] = instance_data.priority
            if instance_data.weight is not None:
                update_data['weight'] = instance_data.weight
            if instance_data.max_connections is not None:
                update_data['max_connections'] = instance_data.max_connections
            if instance_data.timeout is not None:
                update_data['timeout'] = instance_data.timeout
            if instance_data.status is not None:
                update_data['status'] = instance_data.status.value
            if instance_data.tags is not None:
                update_data['tags'] = instance_data.tags
            if instance_data.auth_token is not None:
                update_data['auth_token'] = instance_data.auth_token
            if instance_data.username is not None:
                update_data['username'] = instance_data.username
            if instance_data.password is not None:
                update_data['password'] = instance_data.password
            
            update_data['updated_by'] = updated_by
            
            response = await self._make_request(
                'PUT',
                f'/api/v1/connections/endpoints/{instance_id}',
                data=update_data
            )
            
            if not response:
                return None
            
            instance_data = response.get('data', response)
            return CloudInstanceResponse(
                id=instance_data['id'],
                name=instance_data['name'],
                description=instance_data.get('description'),
                endpoint_type=EndpointType(instance_data['endpoint_type']),
                host=instance_data['host'],
                port=instance_data['port'],
                scheme=instance_data['scheme'],
                tenant_id=instance_data.get('tenant_id'),
                priority=instance_data['priority'],
                weight=instance_data['weight'],
                max_connections=instance_data['max_connections'],
                timeout=instance_data['timeout'],
                tags=instance_data.get('tags', {}),
                status=InstanceStatus(instance_data.get('status', 'active')),
                created_at=datetime.fromisoformat(instance_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(instance_data['updated_at'].replace('Z', '+00:00')) if instance_data.get('updated_at') else None,
                created_by=instance_data['created_by'],
                updated_by=instance_data.get('updated_by')
            )
            
        except Exception as e:
            logger.error("Failed to update cloud instance", instance_id=instance_id, error=str(e), updated_by=updated_by)
            raise
    
    async def delete_instance(
        self,
        instance_id: int,
        force: bool = False,
        deleted_by: int = None
    ) -> bool:
        """Delete a cloud instance"""
        try:
            params = {}
            if force:
                params['force'] = 'true'
            
            response = await self._make_request(
                'DELETE',
                f'/api/v1/connections/endpoints/{instance_id}',
                params=params
            )
            
            return response is not None
            
        except Exception as e:
            if "404" in str(e):
                return False
            logger.error("Failed to delete cloud instance", instance_id=instance_id, error=str(e), deleted_by=deleted_by)
            raise
    
    async def get_optimal_connection(
        self,
        tenant_id: Optional[str] = None,
        endpoint_type: Optional[EndpointType] = None,
        session_id: Optional[str] = None,
        lb_config_name: str = "default",
        user_id: int = None
    ) -> Optional[CloudConnectionResponse]:
        """Get optimal cloud connection from Connection Manager"""
        try:
            params = {
                'lb_config_name': lb_config_name
            }
            
            if tenant_id:
                params['tenant_id'] = tenant_id
            if endpoint_type:
                params['endpoint_type'] = endpoint_type.value
            if session_id:
                params['session_id'] = session_id
            
            response = await self._make_request(
                'GET',
                '/api/v1/connections/optimal',
                params=params
            )
            
            if not response:
                return None
            
            connection_data = response.get('data', response)
            
            return CloudConnectionResponse(
                endpoint_id=connection_data['endpoint_id'],
                host=connection_data['host'],
                port=connection_data['port'],
                scheme=connection_data['scheme'],
                tenant_id=connection_data.get('tenant_id'),
                session_token=connection_data.get('session_token', 'default'),
                expires_at=datetime.utcnow() + timedelta(hours=1),  # Default 1 hour
                load_balancer_algorithm=connection_data.get('algorithm', 'round_robin'),
                connection_metadata=connection_data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error("Failed to get optimal connection", error=str(e), user_id=user_id)
            raise
    
    async def get_instance_health(
        self,
        instance_id: int,
        hours: int = 24
    ) -> Optional[CloudHealthCheck]:
        """Get health information for a cloud instance"""
        return await self._get_health_for_instance(instance_id, hours)
    
    async def _get_health_for_instance(
        self,
        instance_id: int,
        hours: int = 24
    ) -> Optional[CloudHealthCheck]:
        """Internal method to get health information"""
        try:
            params = {'hours': hours}
            
            response = await self._make_request(
                'GET',
                f'/api/v1/connections/endpoints/{instance_id}/health',
                params=params
            )
            
            if not response:
                return None
            
            health_data = response.get('data', response)
            
            return CloudHealthCheck(
                instance_id=instance_id,
                status=HealthStatus(health_data.get('status', 'unknown')),
                response_time_ms=health_data.get('response_time_ms', 0),
                status_code=health_data.get('status_code'),
                error_message=health_data.get('error_message'),
                checked_at=datetime.fromisoformat(health_data.get('checked_at', datetime.utcnow().isoformat()).replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error("Failed to get instance health", instance_id=instance_id, error=str(e))
            return None
    
    async def trigger_health_check(
        self,
        instance_id: int,
        triggered_by: int = None
    ) -> Optional[CloudHealthCheck]:
        """Trigger an immediate health check for a cloud instance"""
        try:
            response = await self._make_request(
                'POST',
                f'/api/v1/connections/endpoints/{instance_id}/health-check'
            )
            
            if not response:
                return None
            
            health_data = response.get('data', response)
            
            return CloudHealthCheck(
                instance_id=instance_id,
                status=HealthStatus(health_data.get('status', 'unknown')),
                response_time_ms=health_data.get('response_time_ms', 0),
                status_code=health_data.get('status_code'),
                error_message=health_data.get('error_message'),
                checked_at=datetime.fromisoformat(health_data.get('checked_at', datetime.utcnow().isoformat()).replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error("Failed to trigger health check", instance_id=instance_id, error=str(e), triggered_by=triggered_by)
            raise
    
    async def get_instance_metrics(
        self,
        instance_id: int,
        hours: int = 24
    ) -> Optional[CloudMetrics]:
        """Get performance metrics for a cloud instance"""
        try:
            params = {'hours': hours}
            
            response = await self._make_request(
                'GET',
                f'/api/v1/connections/endpoints/{instance_id}/metrics',
                params=params
            )
            
            if not response:
                return None
            
            metrics_data = response.get('data', response)
            
            return CloudMetrics(
                instance_id=instance_id,
                time_range_hours=hours,
                total_requests=metrics_data.get('total_requests', 0),
                successful_requests=metrics_data.get('successful_requests', 0),
                failed_requests=metrics_data.get('failed_requests', 0),
                avg_response_time_ms=metrics_data.get('avg_response_time_ms', 0),
                min_response_time_ms=metrics_data.get('min_response_time_ms', 0),
                max_response_time_ms=metrics_data.get('max_response_time_ms', 0),
                uptime_percentage=metrics_data.get('uptime_percentage', 0),
                performance_history=[]  # Would parse from metrics_data if available
            )
            
        except Exception as e:
            logger.error("Failed to get instance metrics", instance_id=instance_id, error=str(e))
            return None
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary for all cloud instances"""
        try:
            response = await self._make_request(
                'GET',
                '/api/v1/health/endpoints'
            )
            
            if not response:
                return {
                    "total_instances": 0,
                    "healthy_instances": 0,
                    "degraded_instances": 0,
                    "unhealthy_instances": 0,
                    "avg_response_time_ms": 0,
                    "last_updated": datetime.utcnow()
                }
            
            summary_data = response.get('data', response)
            
            return {
                "total_instances": summary_data.get('total_endpoints', 0),
                "healthy_instances": summary_data.get('healthy_endpoints', 0),
                "degraded_instances": summary_data.get('degraded_endpoints', 0),
                "unhealthy_instances": summary_data.get('unhealthy_endpoints', 0),
                "avg_response_time_ms": summary_data.get('avg_response_time_ms', 0),
                "health_percentage": summary_data.get('health_percentage', 0),
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Failed to get health summary", error=str(e))
            raise