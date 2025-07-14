"""
Conversation manager for handling conversation flow and context
"""

import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .memory_store import MemoryStore, ConversationMemory, QueryMemory, memory_store
from ..core.logging import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class ConversationState(str, Enum):
    """Conversation states"""
    ACTIVE = "active"
    IDLE = "idle"
    ENDED = "ended"
    ARCHIVED = "archived"


class MessageType(str, Enum):
    """Message types in conversation"""
    USER_QUERY = "user_query"
    ASSISTANT_RESPONSE = "assistant_response"
    SYSTEM_MESSAGE = "system_message"
    CLARIFICATION_REQUEST = "clarification_request"
    FOLLOW_UP_QUESTION = "follow_up_question"
    ERROR_MESSAGE = "error_message"


@dataclass
class ConversationContext:
    """Context for an entire conversation"""
    conversation_id: str
    user_id: str
    state: ConversationState
    title: Optional[str]
    summary: Optional[str]
    
    # Context variables
    current_topic: Optional[str] = None
    current_index: Optional[str] = None
    current_sourcetype: Optional[str] = None
    current_time_range: Optional[Dict[str, Any]] = None
    
    # User preferences
    preferred_chart_type: Optional[str] = None
    preferred_aggregation: Optional[str] = None
    output_format: str = "auto"
    
    # Conversation metadata
    message_count: int = 0
    query_count: int = 0
    last_activity: Optional[datetime] = None
    
    # Session information
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


@dataclass
class QueryContext:
    """Context for a specific query within a conversation"""
    query_id: str
    conversation_id: str
    user_id: str
    
    # Query information
    original_query: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    
    # Context from conversation
    previous_queries: List[str] = None
    conversation_topic: Optional[str] = None
    referenced_fields: List[str] = None
    referenced_indexes: List[str] = None
    
    # Temporal context
    relative_time_references: bool = False
    time_context: Optional[Dict[str, Any]] = None
    
    # Processing metadata
    processing_hints: Dict[str, Any] = None
    clarification_needed: bool = False
    follow_up_suggestions: List[str] = None


class ConversationManager:
    """Manages conversation flow and context"""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.logger = get_logger(__name__)
        
        # Configuration
        self.max_context_length = settings.max_context_length or 8192
        self.conversation_timeout = settings.conversation_timeout or 1800  # 30 minutes
        self.max_follow_up_depth = 5
        self.context_window_size = 10  # Number of previous messages to consider
    
    async def create_conversation(
        self, 
        user_id: str,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        try:
            # Create conversation context
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                state=ConversationState.ACTIVE,
                title=title or "New Conversation",
                summary=None,
                session_id=session_id,
                last_activity=datetime.utcnow()
            )
            
            # Create memory record
            memory = ConversationMemory(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=[],
                context_variables={
                    "state": context.state.value,
                    "title": context.title,
                    "created_at": datetime.utcnow().isoformat()
                },
                preferences={
                    "output_format": context.output_format,
                    "preferred_chart_type": context.preferred_chart_type,
                    "preferred_aggregation": context.preferred_aggregation
                },
                metadata=metadata or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=self.conversation_timeout)
            )
            
            # Store in memory
            success = await self.memory_store.store_conversation(memory)
            if not success:
                raise Exception("Failed to store conversation in memory")
            
            self.logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context"""
        try:
            memory = await self.memory_store.get_conversation(conversation_id)
            if not memory:
                return None
            
            # Convert memory to context
            context = ConversationContext(
                conversation_id=memory.conversation_id,
                user_id=memory.user_id,
                state=ConversationState(memory.context_variables.get("state", "active")),
                title=memory.context_variables.get("title"),
                summary=memory.context_variables.get("summary"),
                current_topic=memory.context_variables.get("current_topic"),
                current_index=memory.context_variables.get("current_index"),
                current_sourcetype=memory.context_variables.get("current_sourcetype"),
                current_time_range=memory.context_variables.get("current_time_range"),
                preferred_chart_type=memory.preferences.get("preferred_chart_type"),
                preferred_aggregation=memory.preferences.get("preferred_aggregation"),
                output_format=memory.preferences.get("output_format", "auto"),
                message_count=len(memory.messages),
                query_count=memory.context_variables.get("query_count", 0),
                last_activity=memory.updated_at,
                session_id=memory.context_variables.get("session_id"),
                user_agent=memory.metadata.get("user_agent"),
                ip_address=memory.metadata.get("ip_address")
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None
    
    async def add_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a message to the conversation"""
        try:
            message = {
                "id": str(uuid.uuid4()),
                "type": message_type.value,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update context based on message
            context_updates = {}
            
            if message_type == MessageType.USER_QUERY:
                context_updates["query_count"] = await self._increment_query_count(conversation_id)
                context_updates["last_user_query"] = content
            
            # Add to memory
            success = await self.memory_store.add_message_to_conversation(
                conversation_id, 
                message, 
                context_updates
            )
            
            if success:
                self.logger.debug(f"Added {message_type.value} message to conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to add message to conversation: {e}")
            return False
    
    async def build_query_context(
        self,
        conversation_id: str,
        user_query: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None
    ) -> QueryContext:
        """Build context for a specific query"""
        try:
            query_id = str(uuid.uuid4())
            
            # Get conversation context
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Get recent queries for context
            recent_queries = await self.memory_store.get_recent_queries(
                conversation_id=conversation_id,
                limit=self.context_window_size
            )
            
            # Extract context from recent queries
            previous_queries = [q.original_query for q in recent_queries]
            referenced_fields = []
            referenced_indexes = []
            
            for query in recent_queries:
                if query.entities:
                    if "FIELD_NAME" in query.entities:
                        referenced_fields.extend(query.entities["FIELD_NAME"])
                    if "INDEX" in query.entities:
                        referenced_indexes.extend(query.entities["INDEX"])
            
            # Remove duplicates
            referenced_fields = list(set(referenced_fields))
            referenced_indexes = list(set(referenced_indexes))
            
            # Detect temporal context
            relative_time_references = self._has_relative_time_references(user_query)
            time_context = self._extract_time_context(user_query, conversation)
            
            # Build query context
            query_context = QueryContext(
                query_id=query_id,
                conversation_id=conversation_id,
                user_id=conversation.user_id,
                original_query=user_query,
                intent=intent,
                entities=entities,
                previous_queries=previous_queries,
                conversation_topic=conversation.current_topic,
                referenced_fields=referenced_fields,
                referenced_indexes=referenced_indexes,
                relative_time_references=relative_time_references,
                time_context=time_context,
                processing_hints={}
            )
            
            self.logger.debug(f"Built query context for {query_id}")
            return query_context
            
        except Exception as e:
            self.logger.error(f"Failed to build query context: {e}")
            raise
    
    async def update_conversation_context(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update conversation context variables"""
        try:
            memory = await self.memory_store.get_conversation(conversation_id)
            if not memory:
                return False
            
            # Update context variables
            memory.context_variables.update(updates)
            memory.updated_at = datetime.utcnow()
            
            # Store updated memory
            success = await self.memory_store.store_conversation(memory)
            
            if success:
                self.logger.debug(f"Updated context for conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation context: {e}")
            return False
    
    async def store_query_result(
        self,
        query_context: QueryContext,
        spl_query: str,
        confidence: float,
        execution_time: Optional[float] = None,
        result_summary: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store query result for future context"""
        try:
            query_memory = QueryMemory(
                query_id=query_context.query_id,
                conversation_id=query_context.conversation_id,
                user_id=query_context.user_id,
                original_query=query_context.original_query,
                processed_query=query_context.original_query,  # Could be modified version
                spl_query=spl_query,
                intent=query_context.intent or "unknown",
                entities=query_context.entities or {},
                confidence_score=confidence,
                execution_time=execution_time,
                result_summary=result_summary,
                context_used={
                    "previous_queries": query_context.previous_queries,
                    "conversation_topic": query_context.conversation_topic,
                    "referenced_fields": query_context.referenced_fields,
                    "time_context": query_context.time_context
                },
                timestamp=datetime.utcnow()
            )
            
            success = await self.memory_store.store_query(query_memory)
            
            if success:
                self.logger.debug(f"Stored query result for {query_context.query_id}")
                
                # Update conversation context with successful query info
                await self.update_conversation_context(
                    query_context.conversation_id,
                    {
                        "last_successful_query": query_context.original_query,
                        "last_query_time": datetime.utcnow().isoformat()
                    }
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to store query result: {e}")
            return False
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Generate a summary of the conversation"""
        try:
            memory = await self.memory_store.get_conversation(conversation_id)
            if not memory:
                return None
            
            # Simple summary generation (could be enhanced with AI)
            message_count = len(memory.messages)
            query_count = memory.context_variables.get("query_count", 0)
            
            if message_count == 0:
                return "Empty conversation"
            
            # Get topic from context
            topic = memory.context_variables.get("current_topic", "various topics")
            
            summary = f"Conversation with {message_count} messages and {query_count} queries about {topic}"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate conversation summary: {e}")
            return None
    
    async def end_conversation(self, conversation_id: str) -> bool:
        """End a conversation and archive it"""
        try:
            # Update state to ended
            success = await self.update_conversation_context(
                conversation_id,
                {
                    "state": ConversationState.ENDED.value,
                    "ended_at": datetime.utcnow().isoformat()
                }
            )
            
            if success:
                self.logger.info(f"Ended conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to end conversation: {e}")
            return False
    
    # Helper methods
    
    async def _increment_query_count(self, conversation_id: str) -> int:
        """Increment and return query count for conversation"""
        try:
            memory = await self.memory_store.get_conversation(conversation_id)
            if memory:
                current_count = memory.context_variables.get("query_count", 0)
                return current_count + 1
            return 1
        except:
            return 1
    
    def _has_relative_time_references(self, query: str) -> bool:
        """Check if query has relative time references"""
        relative_terms = [
            "last", "past", "recent", "today", "yesterday", "this week",
            "last week", "this month", "last month", "ago", "since",
            "before", "after", "now", "current"
        ]
        
        query_lower = query.lower()
        return any(term in query_lower for term in relative_terms)
    
    def _extract_time_context(
        self, 
        query: str, 
        conversation: ConversationContext
    ) -> Optional[Dict[str, Any]]:
        """Extract time context from query and conversation"""
        time_context = {}
        
        # Use conversation's current time range if available
        if conversation.current_time_range:
            time_context["conversation_time_range"] = conversation.current_time_range
        
        # Add query-specific time detection (simplified)
        if self._has_relative_time_references(query):
            time_context["has_relative_references"] = True
            time_context["reference_point"] = datetime.utcnow().isoformat()
        
        return time_context if time_context else None


# Global conversation manager instance
conversation_manager = ConversationManager(memory_store)