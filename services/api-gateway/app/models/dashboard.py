"""
Dashboard and Chart models for visualization
"""

from typing import Dict, Any, List
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class Dashboard(BaseModel):
    """Dashboard model for visualization management"""
    
    __tablename__ = "dashboards"
    __table_args__ = {"schema": "viz"}
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Dashboard metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Dashboard configuration
    layout = Column(JSONB, nullable=False, default={}, server_default='{}')
    panels = Column(JSONB, nullable=False, default=[], server_default='[]')
    
    # Access control
    permissions = Column(JSONB, nullable=False, default={}, server_default='{}')
    is_public = Column(Boolean, nullable=False, default=False, server_default='false')
    is_template = Column(Boolean, nullable=False, default=False, server_default='false')
    
    # Organization
    tags = Column(ARRAY(String), nullable=False, default=[], server_default='{}')
    
    # Usage tracking
    last_accessed = Column("last_accessed", nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="dashboards")
    charts = relationship(
        "Chart",
        back_populates="dashboard",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Dashboard(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class Chart(BaseModel):
    """Chart model for individual visualizations"""
    
    __tablename__ = "charts"
    __table_args__ = {"schema": "viz"}
    
    # Foreign keys
    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("viz.dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spl.queries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Chart metadata
    title = Column(String(255), nullable=False)
    chart_type = Column(String(100), nullable=False)
    
    # Chart configuration
    configuration = Column(JSONB, nullable=False, default={}, server_default='{}')
    data_source = Column(JSONB, nullable=False, default={}, server_default='{}')
    position = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Relationships
    dashboard = relationship("Dashboard", back_populates="charts")
    query = relationship("Query")
    
    def __repr__(self) -> str:
        return f"<Chart(id={self.id}, title='{self.title}', type='{self.chart_type}')>"