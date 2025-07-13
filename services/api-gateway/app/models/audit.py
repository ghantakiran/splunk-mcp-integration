"""
Audit and Security Event models for tracking and compliance
"""

from typing import Dict, Any
from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID, INET
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class SecurityEventSeverity(enum.Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class ActivityLog(BaseModel):
    """Activity log model for audit trail"""
    
    __tablename__ = "activity_logs"
    __table_args__ = {"schema": "audit"}
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Activity details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Activity metadata
    details = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    
    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"


class SecurityEvent(BaseModel):
    """Security event model for security monitoring"""
    
    __tablename__ = "security_events"
    __table_args__ = {"schema": "audit"}
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(
        SQLEnum(SecurityEventSeverity),
        nullable=False,
        default=SecurityEventSeverity.LOW,
        index=True
    )
    
    description = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Request context
    ip_address = Column(INET, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="security_events")
    
    def __repr__(self) -> str:
        return f"<SecurityEvent(id={self.id}, type='{self.event_type}', severity={self.severity})>"