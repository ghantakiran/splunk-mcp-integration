"""
Escalation-related data models.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
import uuid

Base = declarative_base()


class EscalationTrigger(str, Enum):
    """Escalation trigger types."""
    TIME_BASED = "time_based"
    SEVERITY_BASED = "severity_based"
    NO_ACKNOWLEDGMENT = "no_acknowledgment"
    NO_RESOLUTION = "no_resolution"
    INCIDENT_COUNT = "incident_count"
    CUSTOM_CONDITION = "custom_condition"


class EscalationAction(str, Enum):
    """Escalation action types."""
    NOTIFY = "notify"
    REASSIGN = "reassign"
    INCREASE_SEVERITY = "increase_severity"
    CREATE_TICKET = "create_ticket"
    CALL_WEBHOOK = "call_webhook"
    RUN_AUTOMATION = "run_automation"


class EscalationStatus(str, Enum):
    """Escalation status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class EscalationRule(Base):
    """Escalation rule database model."""
    
    __tablename__ = "escalation_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Owner information
    created_by = Column(String(255), nullable=False, index=True)
    organization_id = Column(String(255), index=True)
    
    # Rule configuration
    status = Column(String(20), nullable=False, default="active")
    priority = Column(Integer, default=100)  # Lower number = higher priority
    
    # Trigger conditions
    trigger_type = Column(String(50), nullable=False)
    trigger_conditions = Column(JSON, nullable=False)
    
    # Filters - which incidents this rule applies to
    severity_filter = Column(JSON)  # List of severities
    tag_filter = Column(JSON)  # Tags that must match
    alert_rule_filter = Column(JSON)  # Specific alert rules
    time_filter = Column(JSON)  # Time-based filters
    
    # Actions to take when escalated
    actions = Column(JSON, nullable=False)
    
    # Escalation timing
    delay_minutes = Column(Integer, default=15)  # Initial delay before escalation
    repeat_interval_minutes = Column(Integer)  # Repeat escalation interval
    max_escalations = Column(Integer, default=3)
    
    # Business hours consideration
    respect_business_hours = Column(Boolean, default=False)
    business_hours_config = Column(JSON)  # Business hours configuration
    
    # Metadata
    tags = Column(JSON, default=lambda: [])
    metadata = Column(JSON, default=lambda: {})
    
    # Statistics
    total_escalations = Column(Integer, default=0)
    successful_escalations = Column(Integer, default=0)
    last_triggered_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    escalation_levels = relationship("EscalationLevel", back_populates="rule", cascade="all, delete-orphan")


class EscalationLevel(Base):
    """Escalation level database model."""
    
    __tablename__ = "escalation_levels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, ForeignKey("escalation_rules.id"), nullable=False, index=True)
    
    # Level configuration
    level = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    name = Column(String(255), nullable=False)
    
    # Timing for this level
    delay_minutes = Column(Integer, nullable=False)
    timeout_minutes = Column(Integer)  # Max time to wait at this level
    
    # Actions for this level
    actions = Column(JSON, nullable=False)
    
    # Notification targets
    notification_channels = Column(JSON)  # Channel IDs to notify
    assignees = Column(JSON)  # Users/groups to assign to
    
    # Conditions to advance to next level
    advance_conditions = Column(JSON)
    
    # Metadata
    metadata = Column(JSON, default=lambda: {})
    
    # Statistics
    total_escalations = Column(Integer, default=0)
    average_resolution_time = Column(Integer)  # Minutes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    rule = relationship("EscalationRule", back_populates="escalation_levels")


class EscalationHistory(Base):
    """Escalation history tracking."""
    
    __tablename__ = "escalation_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, ForeignKey("escalation_rules.id"), nullable=False, index=True)
    level_id = Column(String, ForeignKey("escalation_levels.id"), index=True)
    
    # Escalation details
    escalation_level = Column(Integer, nullable=False)
    trigger_type = Column(String(50), nullable=False)
    trigger_reason = Column(Text)
    
    # Actions taken
    actions_executed = Column(JSON)
    notifications_sent = Column(JSON)
    
    # People involved
    escalated_by = Column(String(255))  # System or user ID
    escalated_to = Column(String(255))  # User/group escalated to
    
    # Timing
    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    success = Column(Boolean)
    error_message = Column(Text)
    response_data = Column(JSON)
    
    # Metadata
    metadata = Column(JSON, default=lambda: {})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Pydantic models for API

class EscalationLevelCreate(BaseModel):
    """Escalation level creation model."""
    level: int = Field(..., ge=1, le=10)
    name: str = Field(..., min_length=1, max_length=255)
    delay_minutes: int = Field(..., ge=0, le=10080)  # Max 1 week
    timeout_minutes: Optional[int] = Field(None, ge=1, le=10080)
    actions: List[Dict[str, Any]] = Field(..., min_items=1)
    notification_channels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    advance_conditions: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EscalationLevelResponse(BaseModel):
    """Escalation level response model."""
    id: str
    rule_id: str
    level: int
    name: str
    delay_minutes: int
    timeout_minutes: Optional[int]
    actions: List[Dict[str, Any]]
    notification_channels: List[str]
    assignees: List[str]
    advance_conditions: Dict[str, Any]
    metadata: Dict[str, Any]
    total_escalations: int
    average_resolution_time: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EscalationRuleCreate(BaseModel):
    """Escalation rule creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: int = Field(default=100, ge=1, le=1000)
    
    # Trigger configuration
    trigger_type: EscalationTrigger
    trigger_conditions: Dict[str, Any] = Field(..., min_items=1)
    
    # Filters
    severity_filter: Optional[List[str]] = None
    tag_filter: Optional[List[str]] = None
    alert_rule_filter: Optional[List[str]] = None
    time_filter: Optional[Dict[str, Any]] = None
    
    # Actions
    actions: List[Dict[str, Any]] = Field(..., min_items=1)
    
    # Timing
    delay_minutes: int = Field(default=15, ge=0, le=1440)  # Max 24 hours
    repeat_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_escalations: int = Field(default=3, ge=1, le=10)
    
    # Business hours
    respect_business_hours: bool = False
    business_hours_config: Optional[Dict[str, Any]] = None
    
    # Escalation levels
    escalation_levels: List[EscalationLevelCreate] = Field(default_factory=list)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EscalationRuleUpdate(BaseModel):
    """Escalation rule update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[EscalationStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    
    # Trigger configuration
    trigger_type: Optional[EscalationTrigger] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    
    # Filters
    severity_filter: Optional[List[str]] = None
    tag_filter: Optional[List[str]] = None
    alert_rule_filter: Optional[List[str]] = None
    time_filter: Optional[Dict[str, Any]] = None
    
    # Actions
    actions: Optional[List[Dict[str, Any]]] = None
    
    # Timing
    delay_minutes: Optional[int] = Field(None, ge=0, le=1440)
    repeat_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_escalations: Optional[int] = Field(None, ge=1, le=10)
    
    # Business hours
    respect_business_hours: Optional[bool] = None
    business_hours_config: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class EscalationRuleResponse(BaseModel):
    """Escalation rule response model."""
    id: str
    name: str
    description: Optional[str]
    created_by: str
    organization_id: Optional[str]
    status: str
    priority: int
    
    # Trigger configuration
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    
    # Filters
    severity_filter: Optional[List[str]]
    tag_filter: Optional[List[str]]
    alert_rule_filter: Optional[List[str]]
    time_filter: Optional[Dict[str, Any]]
    
    # Actions
    actions: List[Dict[str, Any]]
    
    # Timing
    delay_minutes: int
    repeat_interval_minutes: Optional[int]
    max_escalations: int
    
    # Business hours
    respect_business_hours: bool
    business_hours_config: Optional[Dict[str, Any]]
    
    # Escalation levels
    escalation_levels: List[EscalationLevelResponse]
    
    # Metadata
    tags: List[str]
    metadata: Dict[str, Any]
    
    # Statistics
    total_escalations: int
    successful_escalations: int
    last_triggered_at: Optional[datetime]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EscalationHistoryResponse(BaseModel):
    """Escalation history response model."""
    id: str
    incident_id: str
    rule_id: str
    level_id: Optional[str]
    escalation_level: int
    trigger_type: str
    trigger_reason: Optional[str]
    actions_executed: List[Dict[str, Any]]
    notifications_sent: List[Dict[str, Any]]
    escalated_by: Optional[str]
    escalated_to: Optional[str]
    scheduled_at: datetime
    executed_at: Optional[datetime]
    completed_at: Optional[datetime]
    success: Optional[bool]
    error_message: Optional[str]
    response_data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EscalationTestRequest(BaseModel):
    """Escalation rule test request."""
    rule_id: str
    test_incident_data: Dict[str, Any] = Field(default_factory=dict)
    test_level: Optional[int] = None
    dry_run: bool = True


class EscalationTestResponse(BaseModel):
    """Escalation rule test response."""
    rule_id: str
    would_escalate: bool
    matched_conditions: List[str]
    escalation_level: Optional[int]
    actions_to_execute: List[Dict[str, Any]]
    notifications_to_send: List[Dict[str, Any]]
    delay_minutes: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# Common escalation action models

class NotifyAction(BaseModel):
    """Notification escalation action."""
    action_type: str = "notify"
    channels: List[str] = Field(..., min_items=1)
    message_template: Optional[str] = None
    priority: str = "high"


class ReassignAction(BaseModel):
    """Reassignment escalation action."""
    action_type: str = "reassign"
    assignee: str = Field(..., min_length=1)
    notify_assignee: bool = True
    add_note: Optional[str] = None


class SeverityAction(BaseModel):
    """Severity increase escalation action."""
    action_type: str = "increase_severity"
    new_severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    add_note: Optional[str] = None


class WebhookAction(BaseModel):
    """Webhook escalation action."""
    action_type: str = "call_webhook"
    url: str = Field(..., min_length=1)
    method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH)$")
    headers: Dict[str, str] = Field(default_factory=dict)
    payload_template: Optional[str] = None
    timeout: int = Field(default=30, ge=1, le=300)


class TicketAction(BaseModel):
    """Ticket creation escalation action."""
    action_type: str = "create_ticket"
    system: str = Field(..., min_length=1)  # jira, servicenow, etc.
    project: str = Field(..., min_length=1)
    issue_type: str = Field(..., min_length=1)
    priority: Optional[str] = None
    assignee: Optional[str] = None
    template: Optional[str] = None