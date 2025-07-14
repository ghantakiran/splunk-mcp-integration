"""
Memory store for conversation and query context management
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict

import redis.asyncio as redis
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationMemory:
    """Memory structure for conversation context"""
    conversation_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    context_variables: Dict[str, Any]
    preferences: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)


@dataclass
class QueryMemory:
    """Memory structure for query context"""
    query_id: str
    conversation_id: str
    user_id: str
    original_query: str
    processed_query: str
    spl_query: str
    intent: str
    entities: Dict[str, Any]
    confidence_score: float
    execution_time: Optional[float]
    result_summary: Optional[Dict[str, Any]]
    context_used: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryMemory":
        """Create from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class MemoryStore:
    """Redis-based memory store for conversation and query context"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.logger = get_logger(__name__)
        self._connection_lock = asyncio.Lock()
        
        # Memory configuration
        self.default_conversation_ttl = settings.conversation_timeout or 1800  # 30 minutes
        self.default_query_ttl = 86400  # 24 hours
        self.max_messages_per_conversation = 100
        self.max_queries_per_user = 1000
        
        # Key prefixes
        self.conversation_prefix = "conv:"
        self.query_prefix = "query:"
        self.user_prefix = "user:"
        self.session_prefix = "session:"
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection with lazy initialization"""
        if self.redis_client is None:
            async with self._connection_lock:
                if self.redis_client is None:
                    try:
                        self.redis_client = redis.from_url(
                            settings.redis_url,
                            password=settings.redis_password,
                            db=settings.redis_db,
                            max_connections=settings.redis_max_connections,
                            decode_responses=True
                        )
                        # Test connection
                        await self.redis_client.ping()
                        self.logger.info("Connected to Redis for memory storage")
                    except Exception as e:
                        self.logger.error(f"Failed to connect to Redis: {e}")
                        raise
        return self.redis_client
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
    
    # Conversation Memory Management
    
    async def store_conversation(self, memory: ConversationMemory, ttl: Optional[int] = None) -> bool:
        """Store conversation memory in Redis"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.conversation_prefix}{memory.conversation_id}"
            
            # Set TTL
            expiry = ttl or self.default_conversation_ttl
            
            # Store as JSON
            data = memory.to_dict()
            await redis_client.setex(key, expiry, json.dumps(data))
            
            # Update user conversation index
            user_conv_key = f"{self.user_prefix}{memory.user_id}:conversations"
            await redis_client.sadd(user_conv_key, memory.conversation_id)
            await redis_client.expire(user_conv_key, expiry)
            
            self.logger.debug(f"Stored conversation memory for {memory.conversation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store conversation memory: {e}")
            return False
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Retrieve conversation memory from Redis"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.conversation_prefix}{conversation_id}"
            
            data = await redis_client.get(key)
            if not data:
                return None
            
            memory_data = json.loads(data)
            memory = ConversationMemory.from_dict(memory_data)
            
            self.logger.debug(f"Retrieved conversation memory for {conversation_id}")
            return memory
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve conversation memory: {e}")
            return None
    
    async def update_conversation(self, memory: ConversationMemory) -> bool:
        """Update existing conversation memory"""
        memory.updated_at = datetime.utcnow()
        return await self.store_conversation(memory)
    
    async def add_message_to_conversation(
        self, 
        conversation_id: str, 
        message: Dict[str, Any],
        context_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a message to conversation and update context"""
        try:
            memory = await self.get_conversation(conversation_id)
            if not memory:
                self.logger.warning(f"Conversation {conversation_id} not found")
                return False
            
            # Add message with timestamp
            message["timestamp"] = datetime.utcnow().isoformat()
            memory.messages.append(message)
            
            # Trim messages if too many
            if len(memory.messages) > self.max_messages_per_conversation:
                memory.messages = memory.messages[-self.max_messages_per_conversation:]
            
            # Update context variables
            if context_updates:
                memory.context_variables.update(context_updates)
            
            return await self.update_conversation(memory)
            
        except Exception as e:
            self.logger.error(f"Failed to add message to conversation: {e}")
            return False
    
    async def get_user_conversations(self, user_id: str, limit: int = 10) -> List[str]:
        """Get list of conversation IDs for a user"""
        try:
            redis_client = await self._get_redis()
            user_conv_key = f"{self.user_prefix}{user_id}:conversations"
            
            conversations = await redis_client.smembers(user_conv_key)
            return list(conversations)[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get user conversations: {e}")
            return []
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete conversation memory"""
        try:
            redis_client = await self._get_redis()
            
            # Delete conversation
            conv_key = f"{self.conversation_prefix}{conversation_id}"
            await redis_client.delete(conv_key)
            
            # Remove from user index
            user_conv_key = f"{self.user_prefix}{user_id}:conversations"
            await redis_client.srem(user_conv_key, conversation_id)
            
            self.logger.debug(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete conversation: {e}")
            return False
    
    # Query Memory Management
    
    async def store_query(self, memory: QueryMemory, ttl: Optional[int] = None) -> bool:
        """Store query memory in Redis"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.query_prefix}{memory.query_id}"
            
            # Set TTL
            expiry = ttl or self.default_query_ttl
            
            # Store as JSON
            data = memory.to_dict()
            await redis_client.setex(key, expiry, json.dumps(data))
            
            # Update user query index
            user_query_key = f"{self.user_prefix}{memory.user_id}:queries"
            await redis_client.lpush(user_query_key, memory.query_id)
            await redis_client.ltrim(user_query_key, 0, self.max_queries_per_user - 1)
            await redis_client.expire(user_query_key, expiry)
            
            # Update conversation query index
            conv_query_key = f"{self.conversation_prefix}{memory.conversation_id}:queries"
            await redis_client.lpush(conv_query_key, memory.query_id)
            await redis_client.expire(conv_query_key, expiry)
            
            self.logger.debug(f"Stored query memory for {memory.query_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store query memory: {e}")
            return False
    
    async def get_query(self, query_id: str) -> Optional[QueryMemory]:
        """Retrieve query memory from Redis"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.query_prefix}{query_id}"
            
            data = await redis_client.get(key)
            if not data:
                return None
            
            memory_data = json.loads(data)
            memory = QueryMemory.from_dict(memory_data)
            
            self.logger.debug(f"Retrieved query memory for {query_id}")
            return memory
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve query memory: {e}")
            return None
    
    async def get_recent_queries(
        self, 
        user_id: Optional[str] = None, 
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[QueryMemory]:
        """Get recent queries for user or conversation"""
        try:
            redis_client = await self._get_redis()
            
            if conversation_id:
                key = f"{self.conversation_prefix}{conversation_id}:queries"
            elif user_id:
                key = f"{self.user_prefix}{user_id}:queries"
            else:
                return []
            
            # Get recent query IDs
            query_ids = await redis_client.lrange(key, 0, limit - 1)
            
            # Fetch query memories
            queries = []
            for query_id in query_ids:
                query_memory = await self.get_query(query_id)
                if query_memory:
                    queries.append(query_memory)
            
            return queries
            
        except Exception as e:
            self.logger.error(f"Failed to get recent queries: {e}")
            return []
    
    # Context Variable Management
    
    async def set_context_variable(
        self, 
        conversation_id: str, 
        key: str, 
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a context variable for a conversation"""
        try:
            memory = await self.get_conversation(conversation_id)
            if not memory:
                return False
            
            memory.context_variables[key] = value
            return await self.update_conversation(memory)
            
        except Exception as e:
            self.logger.error(f"Failed to set context variable: {e}")
            return False
    
    async def get_context_variable(self, conversation_id: str, key: str) -> Any:
        """Get a context variable for a conversation"""
        try:
            memory = await self.get_conversation(conversation_id)
            if not memory:
                return None
            
            return memory.context_variables.get(key)
            
        except Exception as e:
            self.logger.error(f"Failed to get context variable: {e}")
            return None
    
    async def get_all_context_variables(self, conversation_id: str) -> Dict[str, Any]:
        """Get all context variables for a conversation"""
        try:
            memory = await self.get_conversation(conversation_id)
            if not memory:
                return {}
            
            return memory.context_variables.copy()
            
        except Exception as e:
            self.logger.error(f"Failed to get context variables: {e}")
            return {}
    
    # Session Management
    
    async def create_session(self, session_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Create a user session"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.session_prefix}{session_id}"
            
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "data": data
            }
            
            await redis_client.setex(key, self.default_conversation_ttl, json.dumps(session_data))
            
            self.logger.debug(f"Created session {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.session_prefix}{session_id}"
            
            data = await redis_client.get(key)
            if not data:
                return None
            
            return json.loads(data)
            
        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            redis_client = await self._get_redis()
            key = f"{self.session_prefix}{session_id}"
            
            await redis_client.delete(key)
            
            self.logger.debug(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete session: {e}")
            return False
    
    # Cleanup and Maintenance
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired conversations and queries"""
        try:
            redis_client = await self._get_redis()
            
            # This would typically be handled by Redis TTL
            # but we can implement additional cleanup logic here
            cleanup_stats = {
                "conversations_cleaned": 0,
                "queries_cleaned": 0,
                "sessions_cleaned": 0
            }
            
            # Implementation would scan for expired keys and clean up
            # For now, rely on Redis TTL
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired data: {e}")
            return {}
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            redis_client = await self._get_redis()
            
            # Count conversations
            conv_keys = await redis_client.keys(f"{self.conversation_prefix}*")
            conversation_count = len(conv_keys)
            
            # Count queries
            query_keys = await redis_client.keys(f"{self.query_prefix}*")
            query_count = len(query_keys)
            
            # Count sessions
            session_keys = await redis_client.keys(f"{self.session_prefix}*")
            session_count = len(session_keys)
            
            # Get Redis info
            redis_info = await redis_client.info("memory")
            
            return {
                "conversations": conversation_count,
                "queries": query_count,
                "sessions": session_count,
                "redis_memory_used": redis_info.get("used_memory_human", "N/A"),
                "redis_memory_peak": redis_info.get("used_memory_peak_human", "N/A")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {}


# Global memory store instance
memory_store = MemoryStore()