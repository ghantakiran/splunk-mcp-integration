"""
Database base configuration and imports
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData

# Create base class for all models
Base = declarative_base()

# Naming convention for constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Set up metadata with naming convention
Base.metadata.naming_convention = naming_convention

# Import all models here to ensure they are registered with SQLAlchemy
# This is important for Alembic to detect all models during migrations
from ..models.user import User
from ..models.conversation import Conversation, Message
from ..models.query import Query, QueryResult
from ..models.dashboard import Dashboard, Chart
from ..models.alert import AlertRule, AlertIncident
from ..models.audit import ActivityLog, SecurityEvent

# Export all models
__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message", 
    "Query",
    "QueryResult",
    "Dashboard",
    "Chart",
    "AlertRule",
    "AlertIncident",
    "ActivityLog",
    "SecurityEvent"
]