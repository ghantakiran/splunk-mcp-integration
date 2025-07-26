"""
Database models for Cloud Connection Manager Service.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, validator, Field

from app.core.database import Base


# Enums
class EndpointType(PyEnum):
    """Endpoint type enumeration."""
    ENTERPRISE = "enterprise"
    CLOUD = "cloud"


class EndpointStatus(PyEnum):
    """Endpoint status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


class HealthStatus(PyEnum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalancerAlgorithm(PyEnum):
    """Load balancer algorithm enumeration."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


# SQLAlchemy Models
class ConnectionEndpoint(Base):
    """Connection endpoint model for Splunk instances."""
    
    __tablename__ = "connection_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    endpoint_type = Column(Enum(EndpointType), nullable=False, index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    scheme = Column(String(10), nullable=False, default="https")
    base_url = Column(String(512), nullable=False)
    
    # Authentication details
    tenant_id = Column(String(255), nullable=True, index=True)  # For Cloud instances
    auth_token = Column(Text, nullable=True)  # Encrypted auth token
    username = Column(String(255), nullable=True)
    password = Column(Text, nullable=True)  # Encrypted password
    
    # Configuration
    priority = Column(Integer, default=100)  # Higher value = higher priority
    weight = Column(Integer, default=100)  # For weighted load balancing
    max_connections = Column(Integer, default=50)
    timeout = Column(Integer, default=30)  # Request timeout in seconds
    
    # Status and health
    status = Column(Enum(EndpointStatus), default=EndpointStatus.ACTIVE, index=True)
    health_status = Column(Enum(HealthStatus), default=HealthStatus.UNKNOWN, index=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=dict)  # Key-value tags for grouping/filtering
    metadata = Column(JSON, default=dict)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    pools = relationship("ConnectionPool", back_populates="endpoint", cascade="all, delete-orphan")
    health_records = relationship("ConnectionHealth", back_populates="endpoint", cascade="all, delete-orphan")
    metrics = relationship("ConnectionMetrics", back_populates="endpoint", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_endpoint_type_status", "endpoint_type", "status"),
        Index("idx_endpoint_health_status", "health_status"),
        Index("idx_endpoint_tenant", "tenant_id"),
        UniqueConstraint("host", "port", "tenant_id", name="uq_endpoint_host_port_tenant"),
        CheckConstraint("port > 0 AND port <= 65535", name="ck_endpoint_port_range"),
        CheckConstraint("priority >= 0", name="ck_endpoint_priority_positive"),
        CheckConstraint("weight > 0", name="ck_endpoint_weight_positive"),
        CheckConstraint("max_connections > 0", name="ck_endpoint_max_connections_positive"),
        CheckConstraint("timeout > 0", name="ck_endpoint_timeout_positive"),
    )


class ConnectionPool(Base):
    """Connection pool model for managing connections to endpoints."""
    
    __tablename__ = "connection_pools"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("connection_endpoints.id"), nullable=False, index=True)
    pool_name = Column(String(255), nullable=False, index=True)
    
    # Pool configuration
    min_size = Column(Integer, default=5)
    max_size = Column(Integer, default=50)
    current_size = Column(Integer, default=0)
    active_connections = Column(Integer, default=0)
    idle_connections = Column(Integer, default=0)
    
    # Pool behavior
    idle_timeout = Column(Integer, default=300)  # 5 minutes
    max_lifetime = Column(Integer, default=3600)  # 1 hour
    validation_query = Column(String(255), default="SELECT 1")
    validate_on_borrow = Column(Boolean, default=True)
    validate_on_return = Column(Boolean, default=False)
    
    # Pool status
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Statistics
    total_connections_created = Column(Integer, default=0)
    total_connections_destroyed = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    total_successful_requests = Column(Integer, default=0)
    total_failed_requests = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    endpoint = relationship("ConnectionEndpoint", back_populates="pools")
    
    # Indexes
    __table_args__ = (
        Index("idx_pool_endpoint_active", "endpoint_id", "is_active"),
        Index("idx_pool_last_activity", "last_activity"),
        UniqueConstraint("endpoint_id", "pool_name", name="uq_pool_endpoint_name"),
        CheckConstraint("min_size >= 0", name="ck_pool_min_size_positive"),
        CheckConstraint("max_size > 0", name="ck_pool_max_size_positive"),
        CheckConstraint("max_size >= min_size", name="ck_pool_max_ge_min_size"),
        CheckConstraint("current_size >= 0", name="ck_pool_current_size_positive"),
        CheckConstraint("active_connections >= 0", name="ck_pool_active_connections_positive"),
        CheckConstraint("idle_connections >= 0", name="ck_pool_idle_connections_positive"),
    )


class ConnectionHealth(Base):
    """Connection health monitoring model."""
    
    __tablename__ = "connection_health"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("connection_endpoints.id"), nullable=False, index=True)
    
    # Health check details
    check_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    health_status = Column(Enum(HealthStatus), nullable=False, index=True)
    response_time_ms = Column(Float, nullable=True)
    
    # Check results
    is_reachable = Column(Boolean, default=False)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    check_details = Column(JSON, default=dict)  # Additional check results
    
    # Performance metrics
    cpu_usage = Column(Float, nullable=True)  # CPU usage percentage
    memory_usage = Column(Float, nullable=True)  # Memory usage percentage
    disk_usage = Column(Float, nullable=True)  # Disk usage percentage
    connection_count = Column(Integer, nullable=True)  # Active connections
    
    # Relationships
    endpoint = relationship("ConnectionEndpoint", back_populates="health_records")
    
    # Indexes
    __table_args__ = (
        Index("idx_health_endpoint_timestamp", "endpoint_id", "check_timestamp"),
        Index("idx_health_status_timestamp", "health_status", "check_timestamp"),
        Index("idx_health_response_time", "response_time_ms"),
    )


class LoadBalancerConfig(Base):
    """Load balancer configuration model."""
    
    __tablename__ = "load_balancer_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    algorithm = Column(Enum(LoadBalancerAlgorithm), nullable=False)
    
    # Configuration parameters
    health_check_interval = Column(Integer, default=30)  # seconds
    health_check_timeout = Column(Integer, default=10)  # seconds
    failover_timeout = Column(Integer, default=30)  # seconds
    
    # Circuit breaker configuration
    circuit_breaker_enabled = Column(Boolean, default=True)
    circuit_breaker_failure_threshold = Column(Integer, default=5)
    circuit_breaker_timeout = Column(Integer, default=60)  # seconds
    circuit_breaker_half_open_max_calls = Column(Integer, default=3)
    
    # Load balancer behavior
    sticky_sessions = Column(Boolean, default=False)
    session_affinity_timeout = Column(Integer, default=3600)  # 1 hour
    retry_attempts = Column(Integer, default=3)
    retry_delay = Column(Float, default=1.0)  # seconds
    
    # Target endpoint filters
    endpoint_types = Column(JSON, default=list)  # Filter by endpoint types
    endpoint_tags = Column(JSON, default=dict)  # Filter by endpoint tags
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    failover_logs = relationship("FailoverLog", back_populates="config", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_lb_config_algorithm", "algorithm"),
        Index("idx_lb_config_active", "is_active"),
        CheckConstraint("health_check_interval > 0", name="ck_lb_health_check_interval"),
        CheckConstraint("health_check_timeout > 0", name="ck_lb_health_check_timeout"),
        CheckConstraint("failover_timeout > 0", name="ck_lb_failover_timeout"),
        CheckConstraint("circuit_breaker_failure_threshold > 0", name="ck_lb_cb_failure_threshold"),
        CheckConstraint("circuit_breaker_timeout > 0", name="ck_lb_cb_timeout"),
        CheckConstraint("retry_attempts >= 0", name="ck_lb_retry_attempts"),
        CheckConstraint("retry_delay >= 0", name="ck_lb_retry_delay"),
    )


class FailoverLog(Base):
    """Failover event logging model."""
    
    __tablename__ = "failover_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("load_balancer_configs.id"), nullable=False, index=True)
    
    # Failover details
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # failover, recovery, circuit_breaker_open, etc.
    source_endpoint_id = Column(Integer, ForeignKey("connection_endpoints.id"), nullable=True, index=True)
    target_endpoint_id = Column(Integer, ForeignKey("connection_endpoints.id"), nullable=True, index=True)
    
    # Event context
    reason = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Additional details
    request_details = Column(JSON, default=dict)
    system_metrics = Column(JSON, default=dict)
    
    # Relationships
    config = relationship("LoadBalancerConfig", back_populates="failover_logs")
    source_endpoint = relationship("ConnectionEndpoint", foreign_keys=[source_endpoint_id])
    target_endpoint = relationship("ConnectionEndpoint", foreign_keys=[target_endpoint_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_failover_config_timestamp", "config_id", "event_timestamp"),
        Index("idx_failover_event_type", "event_type"),
        Index("idx_failover_endpoints", "source_endpoint_id", "target_endpoint_id"),
    )


class ConnectionMetrics(Base):
    """Connection metrics and performance data model."""
    
    __tablename__ = "connection_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("connection_endpoints.id"), nullable=False, index=True)
    
    # Time-based metrics
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    interval_minutes = Column(Integer, default=1, index=True)  # Aggregation interval
    
    # Request metrics
    request_count = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    timeout_requests = Column(Integer, default=0)
    
    # Response time metrics
    avg_response_time_ms = Column(Float, nullable=True)
    min_response_time_ms = Column(Float, nullable=True)
    max_response_time_ms = Column(Float, nullable=True)
    p95_response_time_ms = Column(Float, nullable=True)
    p99_response_time_ms = Column(Float, nullable=True)
    
    # Connection metrics
    active_connections = Column(Integer, default=0)
    peak_connections = Column(Integer, default=0)
    connection_pool_usage = Column(Float, nullable=True)  # Percentage
    
    # Error metrics
    error_rate = Column(Float, default=0.0)  # Percentage
    timeout_rate = Column(Float, default=0.0)  # Percentage
    circuit_breaker_trips = Column(Integer, default=0)
    
    # Resource utilization
    cpu_usage = Column(Float, nullable=True)  # Percentage
    memory_usage = Column(Float, nullable=True)  # Percentage
    network_bytes_in = Column(Integer, nullable=True)
    network_bytes_out = Column(Integer, nullable=True)
    
    # Relationships
    endpoint = relationship("ConnectionEndpoint", back_populates="metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_metrics_endpoint_timestamp", "endpoint_id", "timestamp"),
        Index("idx_metrics_interval", "interval_minutes"),
        Index("idx_metrics_timestamp_interval", "timestamp", "interval_minutes"),
        Index("idx_metrics_error_rate", "error_rate"),
        Index("idx_metrics_response_time", "avg_response_time_ms"),
        UniqueConstraint("endpoint_id", "timestamp", "interval_minutes", name="uq_metrics_endpoint_time_interval"),
    )


# Pydantic Models for API
class EndpointBase(BaseModel):
    """Base endpoint model."""
    name: str = Field(..., min_length=1, max_length=255)
    endpoint_type: EndpointType
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    scheme: str = Field(default="https", regex="^(http|https)$")
    tenant_id: Optional[str] = Field(None, max_length=255)
    priority: int = Field(default=100, ge=0)
    weight: int = Field(default=100, gt=0)
    max_connections: int = Field(default=50, gt=0)
    timeout: int = Field(default=30, gt=0)
    description: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("base_url", pre=True, always=True)
    def set_base_url(cls, v, values):
        """Set base URL from scheme, host, and port."""
        scheme = values.get("scheme", "https")
        host = values.get("host", "")
        port = values.get("port", 443)
        return f"{scheme}://{host}:{port}"


class EndpointCreate(EndpointBase):
    """Endpoint creation model."""
    auth_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class EndpointUpdate(BaseModel):
    """Endpoint update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    priority: Optional[int] = Field(None, ge=0)
    weight: Optional[int] = Field(None, gt=0)
    max_connections: Optional[int] = Field(None, gt=0)
    timeout: Optional[int] = Field(None, gt=0)
    status: Optional[EndpointStatus] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    auth_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class EndpointResponse(EndpointBase):
    """Endpoint response model."""
    id: int
    base_url: str
    status: EndpointStatus
    health_status: HealthStatus
    last_health_check: Optional[datetime]
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PoolConfigCreate(BaseModel):
    """Pool configuration creation model."""
    pool_name: str = Field(..., min_length=1, max_length=255)
    min_size: int = Field(default=5, ge=0)
    max_size: int = Field(default=50, gt=0)
    idle_timeout: int = Field(default=300, gt=0)
    max_lifetime: int = Field(default=3600, gt=0)
    validation_query: str = Field(default="SELECT 1", max_length=255)
    validate_on_borrow: bool = Field(default=True)
    validate_on_return: bool = Field(default=False)
    
    @validator("max_size")
    def validate_max_size(cls, v, values):
        """Validate max_size is greater than min_size."""
        min_size = values.get("min_size", 0)
        if v <= min_size:
            raise ValueError("max_size must be greater than min_size")
        return v


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    endpoint_id: int
    health_status: HealthStatus
    response_time_ms: Optional[float]
    is_reachable: bool
    status_code: Optional[int]
    error_message: Optional[str]
    check_timestamp: datetime
    check_details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class LoadBalancerConfigCreate(BaseModel):
    """Load balancer configuration creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    algorithm: LoadBalancerAlgorithm
    health_check_interval: int = Field(default=30, gt=0)
    health_check_timeout: int = Field(default=10, gt=0)
    failover_timeout: int = Field(default=30, gt=0)
    circuit_breaker_enabled: bool = Field(default=True)
    circuit_breaker_failure_threshold: int = Field(default=5, gt=0)
    circuit_breaker_timeout: int = Field(default=60, gt=0)
    sticky_sessions: bool = Field(default=False)
    retry_attempts: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    endpoint_types: List[EndpointType] = Field(default_factory=list)
    endpoint_tags: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class MetricsResponse(BaseModel):
    """Metrics response model."""
    endpoint_id: int
    timestamp: datetime
    interval_minutes: int
    request_count: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    avg_response_time_ms: Optional[float]
    active_connections: int
    connection_pool_usage: Optional[float]
    
    class Config:
        from_attributes = True