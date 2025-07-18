"""
Webhook-related data models for the Webhook Service.
"""

import enum
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator, HttpUrl
import uuid

Base = declarative_base()


class WebhookStatus(enum.Enum):
    """Webhook endpoint status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    FAILED = "failed"


class EventType(enum.Enum):
    """Webhook event type enumeration."""
    QUERY_COMPLETED = "query.completed"
    ALERT_TRIGGERED = "alert.triggered"
    DASHBOARD_CREATED = "dashboard.created"
    REPORT_GENERATED = "report.generated"
    ERROR_OCCURRED = "error.occurred"
    SYSTEM_STATUS_CHANGED = "system.status_changed"
    USER_ACTION = "user.action"
    DATA_UPDATED = "data.updated"


class DeliveryStatus(enum.Enum):
    """Webhook delivery status enumeration."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class WebhookMethod(enum.Enum):
    """HTTP method enumeration for webhooks."""
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"


# SQLAlchemy Models
class WebhookEndpoint(Base):
    """Webhook endpoint database model."""
    __tablename__ = "webhook_endpoints"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    url = Column(String(2048), nullable=False)
    method = Column(Enum(WebhookMethod), nullable=False, default=WebhookMethod.POST)
    headers = Column(JSON, default=dict)
    secret = Column(String(255))
    status = Column(Enum(WebhookStatus), nullable=False, default=WebhookStatus.ACTIVE)
    
    # Event filtering
    event_types = Column(JSON, default=list)  # List of event types to subscribe to
    event_filters = Column(JSON, default=dict)  # Additional filtering criteria
    
    # Configuration
    timeout = Column(Integer, default=30)
    retry_attempts = Column(Integer, default=3)
    retry_delay = Column(Integer, default=300)  # seconds
    
    # Metrics
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    last_delivery_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("WebhookEvent", back_populates="endpoint")
    deliveries = relationship("WebhookDelivery", back_populates="endpoint")
    logs = relationship("WebhookLog", back_populates="endpoint")


class WebhookEvent(Base):
    """Webhook event database model."""
    __tablename__ = "webhook_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    source = Column(String(255), nullable=False)  # Which service generated the event
    
    # Event data
    payload = Column(JSON, nullable=False)
    metadata = Column(JSON, default=dict)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="events")
    deliveries = relationship("WebhookDelivery", back_populates="event")


class WebhookDelivery(Base):
    """Webhook delivery database model."""
    __tablename__ = "webhook_deliveries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id"), nullable=False)
    event_id = Column(String(36), ForeignKey("webhook_events.id"), nullable=False)
    
    # Delivery details
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)
    attempt_number = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    
    # HTTP details
    http_status = Column(Integer)
    response_body = Column(Text)
    response_headers = Column(JSON, default=dict)
    error_message = Column(Text)
    
    # Timing
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    attempted_at = Column(DateTime)
    completed_at = Column(DateTime)
    response_time = Column(Float)  # milliseconds
    
    # Retry logic
    next_retry_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")
    event = relationship("WebhookEvent", back_populates="deliveries")


class WebhookSubscription(Base):
    """Webhook subscription database model."""
    __tablename__ = "webhook_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    
    # Subscription configuration
    active = Column(Boolean, default=True)
    filters = Column(JSON, default=dict)  # Additional filtering criteria
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookLog(Base):
    """Webhook activity log database model."""
    __tablename__ = "webhook_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    
    # Log details
    action = Column(String(255), nullable=False)  # created, updated, deleted, delivered, failed
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="logs")


class WebhookMetric(Base):
    """Webhook metrics database model."""
    __tablename__ = "webhook_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id"), nullable=False)
    
    # Metric details
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram
    tags = Column(JSON, default=dict)
    
    # Time bucket
    timestamp = Column(DateTime, default=datetime.utcnow)
    time_bucket = Column(String(20), nullable=False)  # hour, day, week, month
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API
class WebhookEndpointCreate(BaseModel):
    """Pydantic model for creating webhook endpoints."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    url: HttpUrl
    method: WebhookMethod = WebhookMethod.POST
    headers: Dict[str, str] = Field(default_factory=dict)
    secret: Optional[str] = Field(None, min_length=8, max_length=255)
    event_types: List[EventType] = Field(default_factory=list)
    event_filters: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=300, ge=0, le=3600)
    
    @validator("headers")
    def validate_headers(cls, v):
        """Validate webhook headers."""
        if not isinstance(v, dict):
            raise ValueError("Headers must be a dictionary")
        
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Header keys and values must be strings")
        
        return v
    
    @validator("event_filters")
    def validate_event_filters(cls, v):
        """Validate event filters."""
        if not isinstance(v, dict):
            raise ValueError("Event filters must be a dictionary")
        return v


class WebhookEndpointUpdate(BaseModel):
    """Pydantic model for updating webhook endpoints."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    url: Optional[HttpUrl] = None
    method: Optional[WebhookMethod] = None
    headers: Optional[Dict[str, str]] = None
    secret: Optional[str] = Field(None, min_length=8, max_length=255)
    status: Optional[WebhookStatus] = None
    event_types: Optional[List[EventType]] = None
    event_filters: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    retry_delay: Optional[int] = Field(None, ge=0, le=3600)


class WebhookEndpointResponse(BaseModel):
    """Pydantic model for webhook endpoint responses."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    url: str
    method: WebhookMethod
    headers: Dict[str, str]
    status: WebhookStatus
    event_types: List[EventType]
    event_filters: Dict[str, Any]
    timeout: int
    retry_attempts: int
    retry_delay: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookEventCreate(BaseModel):
    """Pydantic model for creating webhook events."""
    event_type: EventType
    source: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("payload")
    def validate_payload(cls, v):
        """Validate event payload."""
        if not isinstance(v, dict):
            raise ValueError("Payload must be a dictionary")
        return v


class WebhookEventResponse(BaseModel):
    """Pydantic model for webhook event responses."""
    id: str
    endpoint_id: str
    event_type: EventType
    source: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    processed: bool
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Pydantic model for webhook delivery responses."""
    id: str
    endpoint_id: str
    event_id: str
    status: DeliveryStatus
    attempt_number: int
    max_attempts: int
    http_status: Optional[int]
    response_body: Optional[str]
    response_headers: Dict[str, Any]
    error_message: Optional[str]
    scheduled_at: datetime
    attempted_at: Optional[datetime]
    completed_at: Optional[datetime]
    response_time: Optional[float]
    next_retry_at: Optional[datetime]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookAnalytics(BaseModel):
    """Pydantic model for webhook analytics."""
    total_endpoints: int
    active_endpoints: int
    total_events: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_response_time: float
    events_by_type: Dict[str, int]
    deliveries_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]