"""
Base model class with common fields and utilities
"""

from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy import Column, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func
import uuid

from ..db.base import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now()
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    is_deleted = Column(Boolean, nullable=False, default=False, server_default='false')
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class BaseModel(Base, TimestampMixin):
    """Base model class with common functionality"""
    
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[set] = None) -> None:
        """Update model instance from dictionary"""
        exclude = exclude or set()
        exclude.update({'id', 'created_at'})  # Always exclude these fields
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get table name for the model"""
        return cls.__tablename__
    
    @classmethod
    def get_primary_key_column(cls):
        """Get primary key column"""
        return cls.id
    
    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<{self.__class__.__name__}(id={self.id})>"


class AuditMixin:
    """Mixin for audit trail fields"""
    
    @declared_attr
    def created_by_id(cls):
        return Column(UUID(as_uuid=True), nullable=True)
    
    @declared_attr
    def updated_by_id(cls):
        return Column(UUID(as_uuid=True), nullable=True)
    
    @declared_attr
    def version(cls):
        return Column('version', type_=int, nullable=False, default=1)


class BaseModelWithSoftDelete(BaseModel, SoftDeleteMixin):
    """Base model with soft delete capability"""
    
    __abstract__ = True
    
    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = func.now()
    
    def restore(self):
        """Restore soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class BaseModelWithAudit(BaseModel, AuditMixin):
    """Base model with audit trail"""
    
    __abstract__ = True
    
    def increment_version(self):
        """Increment version for optimistic locking"""
        self.version += 1