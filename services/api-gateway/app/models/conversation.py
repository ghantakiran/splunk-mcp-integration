"""
Conversation and Message models for chat functionality
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class MessageType(enum.Enum):
    """Message type enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(BaseModel):
    """Conversation model for chat sessions"""
    
    __tablename__ = "conversations"
    __table_args__ = {"schema": "chat"}
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Conversation metadata
    title = Column(String(255), nullable=True)
    context = Column(JSONB, nullable=False, default={}, server_default='{}')
    metadata = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Status
    is_active = Column("is_active", nullable=False, default=True, server_default='true')
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Message.created_at"
    )
    
    queries = relationship(
        "Query",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title='{self.title}', user_id={self.user_id})>"
    
    @property
    def message_count(self) -> int:
        """Get total number of messages in conversation"""
        return self.messages.count()
    
    @property
    def last_message(self) -> Optional["Message"]:
        """Get the last message in conversation"""
        return self.messages.order_by("Message.created_at desc").first()
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get context value by key"""
        if self.context and key in self.context:
            return self.context[key]
        return default
    
    def set_context_value(self, key: str, value: Any) -> None:
        """Set context value"""
        context_dict = dict(self.context) if self.context else {}
        context_dict[key] = value
        self.context = context_dict
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update multiple context values"""
        context_dict = dict(self.context) if self.context else {}
        context_dict.update(updates)
        self.context = context_dict
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        if self.metadata and key in self.metadata:
            return self.metadata[key]
        return default
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        metadata_dict = dict(self.metadata) if self.metadata else {}
        metadata_dict[key] = value
        self.metadata = metadata_dict
    
    def generate_title(self) -> str:
        """Generate conversation title from first user message"""
        first_user_message = self.messages.filter_by(message_type=MessageType.USER).first()
        if first_user_message and first_user_message.content:
            # Take first 50 characters and add ellipsis if longer
            content = first_user_message.content.strip()
            if len(content) > 50:
                return content[:47] + "..."
            return content
        return "New Conversation"
    
    def get_recent_messages(self, limit: int = 10) -> List["Message"]:
        """Get recent messages from conversation"""
        return list(self.messages.order_by("Message.created_at desc").limit(limit))
    
    def archive(self) -> None:
        """Archive conversation (mark as inactive)"""
        self.is_active = False
        self.set_metadata_value("archived_at", self.updated_at.isoformat())


class Message(BaseModel):
    """Message model for chat messages"""
    
    __tablename__ = "messages"
    __table_args__ = {"schema": "chat"}
    
    # Foreign keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat.conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Message data
    message_type = Column(
        SQLEnum(MessageType),
        nullable=False,
        default=MessageType.USER,
        index=True
    )
    
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Message threading
    parent_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat.messages.id"),
        nullable=True
    )
    
    # Message status
    edited_at = Column("edited_at", nullable=True)
    is_deleted = Column("is_deleted", nullable=False, default=False, server_default='false')
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")
    parent_message = relationship("Message", remote_side="Message.id")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, type={self.message_type}, conversation_id={self.conversation_id})>"
    
    @property
    def is_user_message(self) -> bool:
        """Check if message is from user"""
        return self.message_type == MessageType.USER
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant"""
        return self.message_type == MessageType.ASSISTANT
    
    @property
    def is_system_message(self) -> bool:
        """Check if message is system message"""
        return self.message_type == MessageType.SYSTEM
    
    @property
    def content_preview(self) -> str:
        """Get preview of message content"""
        if not self.content:
            return ""
        
        content = self.content.strip()
        if len(content) > 100:
            return content[:97] + "..."
        return content
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        if self.metadata and key in self.metadata:
            return self.metadata[key]
        return default
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        metadata_dict = dict(self.metadata) if self.metadata else {}
        metadata_dict[key] = value
        self.metadata = metadata_dict
    
    def mark_edited(self) -> None:
        """Mark message as edited"""
        from datetime import datetime
        self.edited_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete message"""
        self.is_deleted = True
        self.content = "[Message deleted]"
        self.set_metadata_value("deleted_at", self.updated_at.isoformat())
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        
        # Add computed fields
        data['content_preview'] = self.content_preview
        data['is_user_message'] = self.is_user_message
        data['is_assistant_message'] = self.is_assistant_message
        data['is_system_message'] = self.is_system_message
        
        if not include_metadata:
            data.pop('metadata', None)
        
        return data