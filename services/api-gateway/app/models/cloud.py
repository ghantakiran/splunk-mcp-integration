"""
Cloud instance models for API requests and responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class EndpointType(str, Enum):
    """Cloud endpoint types"""
    CLOUD = "cloud"
    ENTERPRISE = "enterprise"


class InstanceStatus(str, Enum):
    """Cloud instance status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    UNHEALTHY = "unhealthy"


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalancerAlgorithm(str, Enum):
    """Load balancer algorithms"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


class CloudInstanceBase(BaseModel):
    """Base cloud instance model"""
    name: str = Field(..., min_length=1, max_length=255, description="Instance name")
    description: Optional[str] = Field(None, max_length=1000, description="Instance description")
    endpoint_type: EndpointType = Field(..., description="Endpoint type (cloud/enterprise)")
    host: str = Field(..., min_length=1, max_length=255, description="Instance hostname or IP")
    port: int = Field(default=443, ge=1, le=65535, description="Instance port")
    scheme: str = Field(default="https", regex="^https?$", description="Connection scheme")
    tenant_id: Optional[str] = Field(None, max_length=100, description="Tenant identifier")
    priority: int = Field(default=100, ge=0, le=1000, description="Instance priority")
    weight: int = Field(default=100, ge=1, le=1000, description="Load balancing weight")
    max_connections: int = Field(default=50, ge=1, le=1000, description="Maximum connections")
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout in seconds")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Instance tags")


class CloudInstanceCreate(CloudInstanceBase):
    """Cloud instance creation model"""
    auth_token: Optional[str] = Field(None, description="Authentication token")
    username: Optional[str] = Field(None, max_length=100, description="Username for basic auth")
    password: Optional[str] = Field(None, max_length=255, description="Password for basic auth")
    
    @validator("auth_token", "username", "password")
    def validate_auth_methods(cls, v, values):
        """Ensure at least one authentication method is provided"""
        auth_token = values.get("auth_token") or v if hasattr(v, "__name__") and v.__name__ == "auth_token" else values.get("auth_token")
        username = values.get("username") or v if hasattr(v, "__name__") and v.__name__ == "username" else values.get("username")
        password = values.get("password") or v if hasattr(v, "__name__") and v.__name__ == "password" else values.get("password")
        
        if not any([auth_token, (username and password)]):
            raise ValueError("Either auth_token or username/password must be provided")
        return v


class CloudInstanceUpdate(BaseModel):
    """Cloud instance update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=0, le=1000)
    weight: Optional[int] = Field(None, ge=1, le=1000)
    max_connections: Optional[int] = Field(None, ge=1, le=1000)
    timeout: Optional[int] = Field(None, ge=1, le=300)
    status: Optional[InstanceStatus] = None
    tags: Optional[Dict[str, str]] = None
    auth_token: Optional[str] = None
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)


class CloudInstanceResponse(CloudInstanceBase):
    """Cloud instance response model"""
    id: int = Field(..., description="Instance ID")
    status: InstanceStatus = Field(..., description="Instance status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: int = Field(..., description="Creator user ID")
    updated_by: Optional[int] = Field(None, description="Last updater user ID")
    
    class Config:
        from_attributes = True


class HealthMetrics(BaseModel):
    """Health check metrics"""
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    availability: float = Field(..., ge=0, le=1, description="Availability percentage")
    success_rate: float = Field(..., ge=0, le=1, description="Success rate percentage")
    error_count: int = Field(..., ge=0, description="Error count")
    last_error: Optional[str] = Field(None, description="Last error message")
    check_count: int = Field(..., ge=0, description="Total health checks performed")


class CloudHealthCheck(BaseModel):
    """Cloud instance health check result"""
    instance_id: int = Field(..., description="Instance ID")
    status: HealthStatus = Field(..., description="Health status")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    checked_at: datetime = Field(..., description="Health check timestamp")
    metrics: Optional[HealthMetrics] = Field(None, description="Historical health metrics")


class CloudInstanceWithHealth(CloudInstanceResponse):
    """Cloud instance with health information"""
    health: Optional[CloudHealthCheck] = Field(None, description="Current health status")
    health_history: Optional[List[CloudHealthCheck]] = Field(None, description="Recent health history")


class CloudConnectionRequest(BaseModel):
    """Request for optimal cloud connection"""
    tenant_id: Optional[str] = Field(None, max_length=100, description="Tenant identifier")
    endpoint_type: Optional[EndpointType] = Field(None, description="Preferred endpoint type")
    session_id: Optional[str] = Field(None, max_length=100, description="Session ID for sticky sessions")
    lb_config_name: str = Field(default="default", max_length=100, description="Load balancer configuration")
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional requirements")


class CloudConnectionResponse(BaseModel):
    """Optimal cloud connection response"""
    endpoint_id: int = Field(..., description="Selected endpoint ID")
    host: str = Field(..., description="Connection host")
    port: int = Field(..., description="Connection port")
    scheme: str = Field(..., description="Connection scheme")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    session_token: str = Field(..., description="Connection session token")
    expires_at: datetime = Field(..., description="Connection expiration time")
    load_balancer_algorithm: LoadBalancerAlgorithm = Field(..., description="Load balancer algorithm used")
    connection_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional connection metadata")


class PerformanceMetrics(BaseModel):
    """Performance metrics data"""
    timestamp: datetime = Field(..., description="Metric timestamp")
    requests_per_second: float = Field(..., ge=0, description="Requests per second")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time")
    error_rate: float = Field(..., ge=0, le=1, description="Error rate percentage")
    active_connections: int = Field(..., ge=0, description="Active connection count")
    throughput_mbps: float = Field(..., ge=0, description="Throughput in Mbps")


class CloudMetrics(BaseModel):
    """Cloud instance metrics"""
    instance_id: int = Field(..., description="Instance ID")
    time_range_hours: int = Field(..., description="Time range in hours")
    total_requests: int = Field(..., ge=0, description="Total requests processed")
    successful_requests: int = Field(..., ge=0, description="Successful requests")
    failed_requests: int = Field(..., ge=0, description="Failed requests")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time")
    min_response_time_ms: float = Field(..., ge=0, description="Minimum response time")
    max_response_time_ms: float = Field(..., ge=0, description="Maximum response time")
    uptime_percentage: float = Field(..., ge=0, le=1, description="Uptime percentage")
    performance_history: List[PerformanceMetrics] = Field(default_factory=list, description="Performance history")


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    algorithm: LoadBalancerAlgorithm = Field(..., description="Load balancing algorithm")
    health_check_interval: int = Field(default=30, ge=5, le=300, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, ge=1, le=60, description="Health check timeout in seconds")
    failover_timeout: int = Field(default=30, ge=5, le=300, description="Failover timeout in seconds")
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, le=100, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: int = Field(default=60, ge=10, le=600, description="Circuit breaker timeout in seconds")
    sticky_sessions: bool = Field(default=False, description="Enable sticky sessions")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="Retry delay in seconds")
    endpoint_types: List[EndpointType] = Field(default_factory=list, description="Supported endpoint types")
    endpoint_tags: Dict[str, str] = Field(default_factory=dict, description="Endpoint tag filters")


class LoadBalancerStats(BaseModel):
    """Load balancer statistics"""
    config_name: str = Field(..., description="Configuration name")
    total_requests: int = Field(..., ge=0, description="Total requests processed")
    successful_requests: int = Field(..., ge=0, description="Successful requests")
    failed_requests: int = Field(..., ge=0, description="Failed requests")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time")
    active_endpoints: int = Field(..., ge=0, description="Number of active endpoints")
    circuit_breaker_open: bool = Field(..., description="Circuit breaker status")
    last_failover: Optional[datetime] = Field(None, description="Last failover timestamp")
    endpoint_distribution: Dict[int, int] = Field(default_factory=dict, description="Request distribution by endpoint")


class FailoverEvent(BaseModel):
    """Failover event information"""
    id: int = Field(..., description="Event ID")
    config_id: int = Field(..., description="Load balancer configuration ID")
    from_endpoint_id: int = Field(..., description="Source endpoint ID")
    to_endpoint_id: int = Field(..., description="Target endpoint ID")
    event_type: str = Field(..., description="Event type (failover, recovery)")
    reason: str = Field(..., description="Failover reason")
    occurred_at: datetime = Field(..., description="Event timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")


class CloudInstanceSummary(BaseModel):
    """Summary statistics for cloud instances"""
    total_instances: int = Field(..., ge=0, description="Total number of instances")
    healthy_instances: int = Field(..., ge=0, description="Number of healthy instances")
    degraded_instances: int = Field(..., ge=0, description="Number of degraded instances")
    unhealthy_instances: int = Field(..., ge=0, description="Number of unhealthy instances")
    maintenance_instances: int = Field(..., ge=0, description="Number of instances in maintenance")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time across all instances")
    total_requests_last_hour: int = Field(..., ge=0, description="Total requests in the last hour")
    success_rate_last_hour: float = Field(..., ge=0, le=1, description="Success rate in the last hour")
    last_updated: datetime = Field(..., description="Last update timestamp")