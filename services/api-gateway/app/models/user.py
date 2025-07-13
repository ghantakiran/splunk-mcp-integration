"""
User model for authentication and user management
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import Column, String, Boolean, ARRAY, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class User(BaseModel):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
    
    # Core user fields
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, nullable=False, default=True, server_default='true')
    is_verified = Column(Boolean, nullable=False, default=False, server_default='false')
    is_superuser = Column(Boolean, nullable=False, default=False, server_default='false')
    
    # Splunk integration
    splunk_user_id = Column(String(255), nullable=True, index=True)
    
    # Role-based access control
    roles = Column(ARRAY(String), nullable=False, default=[], server_default='{}')
    permissions = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # User preferences
    preferences = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Session tracking
    last_login = Column("last_login", nullable=True)
    login_count = Column("login_count", default=0, server_default='0')
    
    # Profile metadata
    timezone = Column(String(50), nullable=True, default='UTC')
    language = Column(String(10), nullable=True, default='en')
    
    # Relationships
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    queries = relationship(
        "Query",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    dashboards = relationship(
        "Dashboard", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    alert_rules = relationship(
        "AlertRule",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    activity_logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    security_events = relationship(
        "SecurityEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return self.full_name if self.full_name != self.username else self.username
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        # Check direct permissions
        if permission in self.permissions:
            return self.permissions[permission]
        
        # Check role-based permissions
        # This would typically integrate with a more complex RBAC system
        if self.is_superuser:
            return True
        
        if "admin" in self.roles:
            return True
        
        return False
    
    def add_role(self, role: str) -> None:
        """Add role to user"""
        if role not in self.roles:
            roles_list = list(self.roles) if self.roles else []
            roles_list.append(role)
            self.roles = roles_list
    
    def remove_role(self, role: str) -> None:
        """Remove role from user"""
        if self.roles and role in self.roles:
            roles_list = list(self.roles)
            roles_list.remove(role)
            self.roles = roles_list
    
    def set_permission(self, permission: str, value: bool) -> None:
        """Set a specific permission"""
        permissions_dict = dict(self.permissions) if self.permissions else {}
        permissions_dict[permission] = value
        self.permissions = permissions_dict
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference value"""
        if self.preferences and key in self.preferences:
            return self.preferences[key]
        return default
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference value"""
        preferences_dict = dict(self.preferences) if self.preferences else {}
        preferences_dict[key] = value
        self.preferences = preferences_dict
    
    def update_last_login(self) -> None:
        """Update last login timestamp and increment login count"""
        self.last_login = datetime.utcnow()
        self.login_count = (self.login_count or 0) + 1
    
    def get_accessible_indexes(self) -> List[str]:
        """Get list of Splunk indexes user can access"""
        # This would integrate with Splunk RBAC
        if self.has_permission("splunk:all_indexes"):
            return ["*"]
        
        # Get from permissions or role configuration
        indexes = self.get_preference("accessible_indexes", [])
        return indexes if isinstance(indexes, list) else []
    
    def can_access_index(self, index_name: str) -> bool:
        """Check if user can access specific Splunk index"""
        accessible_indexes = self.get_accessible_indexes()
        return "*" in accessible_indexes or index_name in accessible_indexes
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with option to exclude sensitive data"""
        data = super().to_dict()
        
        if not include_sensitive:
            # Remove sensitive fields
            data.pop('password_hash', None)
            
            # Filter sensitive preferences
            if data.get('preferences'):
                filtered_prefs = {
                    k: v for k, v in data['preferences'].items() 
                    if not k.startswith('_') and k not in ['api_keys', 'tokens']
                }
                data['preferences'] = filtered_prefs
        
        # Add computed fields
        data['full_name'] = self.full_name
        data['display_name'] = self.display_name
        
        return data