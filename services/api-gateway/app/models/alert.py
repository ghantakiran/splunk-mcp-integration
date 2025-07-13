"""
Alert Rule and Alert Incident models for alert management
"""

from typing import Dict, Any
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class AlertSeverity(enum.Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(enum.Enum):
    """Alert incident status"""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertRule(BaseModel):
    """Alert rule model for alert definitions"""
    
    __tablename__ = "alert_rules"
    __table_args__ = {"schema": "alerts"}
    
    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spl.queries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Alert metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Alert configuration
    conditions = Column(JSONB, nullable=False, default={}, server_default='{}')
    notification_config = Column(JSONB, nullable=False, default={}, server_default='{}')
    schedule_config = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, server_default='true')
    
    # Tracking
    last_triggered = Column("last_triggered", nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alert_rules")
    query = relationship("Query")
    incidents = relationship(
        "AlertIncident",
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name='{self.name}', active={self.is_active})>"


class AlertIncident(BaseModel):
    """Alert incident model for triggered alerts"""
    
    __tablename__ = "alert_incidents"
    __table_args__ = {"schema": "alerts"}
    
    # Foreign keys
    alert_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alerts.alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Incident data
    severity = Column(
        SQLEnum(AlertSeverity),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        index=True
    )
    
    status = Column(
        SQLEnum(AlertStatus),
        nullable=False,
        default=AlertStatus.OPEN,
        index=True
    )
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Incident metadata
    trigger_data = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Status timestamps
    acknowledged_at = Column("acknowledged_at", nullable=True)
    resolved_at = Column("resolved_at", nullable=True)
    
    # Relationships
    alert_rule = relationship("AlertRule", back_populates="incidents")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    def __repr__(self) -> str:
        return f"<AlertIncident(id={self.id}, severity={self.severity}, status={self.status})>"