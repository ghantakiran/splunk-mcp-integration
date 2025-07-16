"""
Alert-related data models.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
import uuid

Base = declarative_base()


class AlertStatus(str, Enum):
    """Alert rule status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class IncidentStatus(str, Enum):
    """Alert incident status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class IncidentSeverity(str, Enum):
    """Alert incident severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ConditionType(str, Enum):
    """Alert condition types."""
    THRESHOLD = "threshold"
    STATISTICAL = "statistical"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"


class AlertRule(Base):
    """Alert rule database model."""
    
    __tablename__ = "alert_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # User and ownership
    created_by = Column(String(255), nullable=False, index=True)
    organization_id = Column(String(255), index=True)
    
    # Rule configuration
    spl_query = Column(Text, nullable=False)
    conditions = Column(JSON, nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="active")
    
    # Scheduling
    is_continuous = Column(Boolean, default=False)
    evaluation_interval = Column(Integer, default=300)  # seconds
    schedule_cron = Column(String(255))  # for scheduled alerts
    
    # Thresholds and conditions
    threshold_value = Column(Float)
    threshold_operator = Column(String(10))  # >, <, >=, <=, ==, !=
    time_window = Column(Integer, default=300)  # seconds
    
    # Alert behavior
    max_incidents_per_hour = Column(Integer, default=10)
    suppression_window = Column(Integer, default=300)  # seconds
    auto_resolve_timeout = Column(Integer)  # seconds, null = manual only
    
    # Metadata
    tags = Column(JSON, default=lambda: [])
    metadata = Column(JSON, default=lambda: {})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_evaluated_at = Column(DateTime)
    last_triggered_at = Column(DateTime)
    
    # Relationships
    incidents = relationship("AlertIncident", back_populates="rule", cascade="all, delete-orphan")
    conditions_rel = relationship("AlertCondition", back_populates="rule", cascade="all, delete-orphan")


class AlertCondition(Base):
    """Alert condition database model."""
    
    __tablename__ = "alert_conditions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, ForeignKey("alert_rules.id"), nullable=False, index=True)
    
    # Condition details
    condition_type = Column(String(20), nullable=False)
    field_name = Column(String(255))
    operator = Column(String(20))
    value = Column(String(255))
    
    # Statistical conditions
    aggregation_function = Column(String(50))  # count, avg, sum, max, min, stddev
    aggregation_field = Column(String(255))
    
    # Pattern conditions
    pattern = Column(Text)
    pattern_type = Column(String(50))  # regex, contains, starts_with, ends_with
    
    # Time-based conditions
    time_field = Column(String(255))
    time_operator = Column(String(20))
    time_value = Column(String(255))
    
    # Metadata
    metadata = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    rule = relationship("AlertRule", back_populates="conditions_rel")


class AlertIncident(Base):
    """Alert incident database model."""
    
    __tablename__ = "alert_incidents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, ForeignKey("alert_rules.id"), nullable=False, index=True)
    
    # Incident details
    status = Column(String(20), nullable=False, default="open")
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Trigger information
    trigger_value = Column(Float)
    trigger_data = Column(JSON)  # Raw data that triggered the alert
    trigger_query_result = Column(JSON)  # SPL query result
    
    # People and assignment
    assigned_to = Column(String(255), index=True)
    acknowledged_by = Column(String(255))
    resolved_by = Column(String(255))
    
    # Timing
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Resolution
    resolution_notes = Column(Text)
    resolution_time_minutes = Column(Float)
    
    # Correlation and grouping
    correlation_group_id = Column(String(255), index=True)
    parent_incident_id = Column(String, ForeignKey("alert_incidents.id"))
    
    # Escalation tracking
    escalation_level = Column(Integer, default=0)
    escalated_at = Column(DateTime)
    escalated_to = Column(String(255))
    
    # Suppression
    is_suppressed = Column(Boolean, default=False)
    suppression_reason = Column(Text)
    suppressed_until = Column(DateTime)
    
    # Metadata
    tags = Column(JSON, default=lambda: [])
    metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    rule = relationship("AlertRule", back_populates="incidents")
    child_incidents = relationship("AlertIncident", backref="parent_incident", remote_side=[id])


# Pydantic models for API

class AlertConditionCreate(BaseModel):
    """Alert condition creation model."""
    condition_type: ConditionType
    field_name: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[str] = None
    aggregation_function: Optional[str] = None
    aggregation_field: Optional[str] = None
    pattern: Optional[str] = None
    pattern_type: Optional[str] = None
    time_field: Optional[str] = None
    time_operator: Optional[str] = None
    time_value: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertConditionResponse(BaseModel):
    """Alert condition response model."""
    id: str
    rule_id: str
    condition_type: str
    field_name: Optional[str]
    operator: Optional[str]
    value: Optional[str]
    aggregation_function: Optional[str]
    aggregation_field: Optional[str]
    pattern: Optional[str]
    pattern_type: Optional[str]
    time_field: Optional[str]
    time_operator: Optional[str]
    time_value: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertRuleCreate(BaseModel):
    """Alert rule creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    spl_query: str = Field(..., min_length=1)
    conditions: List[AlertConditionCreate] = Field(default_factory=list)
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    
    # Scheduling
    is_continuous: bool = False
    evaluation_interval: int = Field(default=300, ge=60, le=3600)
    schedule_cron: Optional[str] = None
    
    # Thresholds
    threshold_value: Optional[float] = None
    threshold_operator: Optional[str] = None
    time_window: int = Field(default=300, ge=60)
    
    # Behavior
    max_incidents_per_hour: int = Field(default=10, ge=1, le=100)
    suppression_window: int = Field(default=300, ge=0)
    auto_resolve_timeout: Optional[int] = Field(default=None, ge=300)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertRuleUpdate(BaseModel):
    """Alert rule update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    spl_query: Optional[str] = Field(None, min_length=1)
    severity: Optional[IncidentSeverity] = None
    status: Optional[AlertStatus] = None
    
    # Scheduling
    is_continuous: Optional[bool] = None
    evaluation_interval: Optional[int] = Field(None, ge=60, le=3600)
    schedule_cron: Optional[str] = None
    
    # Thresholds
    threshold_value: Optional[float] = None
    threshold_operator: Optional[str] = None
    time_window: Optional[int] = Field(None, ge=60)
    
    # Behavior
    max_incidents_per_hour: Optional[int] = Field(None, ge=1, le=100)
    suppression_window: Optional[int] = Field(None, ge=0)
    auto_resolve_timeout: Optional[int] = Field(None, ge=300)
    
    # Metadata
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertRuleResponse(BaseModel):
    """Alert rule response model."""
    id: str
    name: str
    description: Optional[str]
    created_by: str
    organization_id: Optional[str]
    
    spl_query: str
    conditions: List[AlertConditionResponse]
    severity: str
    status: str
    
    # Scheduling
    is_continuous: bool
    evaluation_interval: int
    schedule_cron: Optional[str]
    
    # Thresholds
    threshold_value: Optional[float]
    threshold_operator: Optional[str]
    time_window: int
    
    # Behavior
    max_incidents_per_hour: int
    suppression_window: int
    auto_resolve_timeout: Optional[int]
    
    # Metadata
    tags: List[str]
    metadata: Dict[str, Any]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_evaluated_at: Optional[datetime]
    last_triggered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AlertIncidentCreate(BaseModel):
    """Alert incident creation model."""
    rule_id: str
    severity: IncidentSeverity
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    trigger_value: Optional[float] = None
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    trigger_query_result: Dict[str, Any] = Field(default_factory=dict)
    correlation_group_id: Optional[str] = None
    parent_incident_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertIncidentUpdate(BaseModel):
    """Alert incident update model."""
    status: Optional[IncidentStatus] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertIncidentResponse(BaseModel):
    """Alert incident response model."""
    id: str
    rule_id: str
    status: str
    severity: str
    title: str
    description: Optional[str]
    
    trigger_value: Optional[float]
    trigger_data: Dict[str, Any]
    trigger_query_result: Dict[str, Any]
    
    assigned_to: Optional[str]
    acknowledged_by: Optional[str]
    resolved_by: Optional[str]
    
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    resolution_notes: Optional[str]
    resolution_time_minutes: Optional[float]
    
    correlation_group_id: Optional[str]
    parent_incident_id: Optional[str]
    
    escalation_level: int
    escalated_at: Optional[datetime]
    escalated_to: Optional[str]
    
    is_suppressed: bool
    suppression_reason: Optional[str]
    suppressed_until: Optional[datetime]
    
    tags: List[str]
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class NaturalLanguageAlertRequest(BaseModel):
    """Natural language alert creation request."""
    description: str = Field(..., min_length=10, max_length=1000)
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    tags: List[str] = Field(default_factory=list)
    additional_context: Dict[str, Any] = Field(default_factory=dict)


class AlertTestRequest(BaseModel):
    """Alert rule test request."""
    rule_id: str
    test_data: Optional[Dict[str, Any]] = None
    dry_run: bool = True


class AlertTestResponse(BaseModel):
    """Alert rule test response."""
    rule_id: str
    test_passed: bool
    would_trigger: bool
    trigger_value: Optional[float]
    evaluation_result: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)