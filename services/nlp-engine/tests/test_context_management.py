"""
Tests for context management system
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.context import (
    ConversationManager,
    ContextService,
    MemoryStore,
    ConversationMemory,
    QueryMemory,
    ConversationContext,
    QueryContext,
    ContextPreferences,
    ConversationState,
    MessageType
)


@pytest.fixture
async def memory_store():
    """Create a mock memory store for testing"""
    store = MemoryStore()
    # Mock Redis connection
    store.redis_client = AsyncMock()
    store.redis_client.ping.return_value = True
    store.redis_client.setex.return_value = True
    store.redis_client.get.return_value = None
    store.redis_client.sadd.return_value = True
    store.redis_client.expire.return_value = True
    store.redis_client.smembers.return_value = []
    store.redis_client.lpush.return_value = True
    store.redis_client.ltrim.return_value = True
    store.redis_client.lrange.return_value = []
    store.redis_client.delete.return_value = True
    store.redis_client.srem.return_value = True
    store.redis_client.keys.return_value = []
    store.redis_client.info.return_value = {"used_memory_human": "1MB", "used_memory_peak_human": "2MB"}
    return store


@pytest.fixture
async def conversation_manager(memory_store):
    """Create conversation manager with mock memory store"""
    return ConversationManager(memory_store)


@pytest.fixture
async def context_service(conversation_manager, memory_store):
    """Create context service with mock dependencies"""
    return ContextService(conversation_manager, memory_store)


class TestMemoryStore:
    """Test memory store functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, memory_store):
        """Test Redis health check"""
        # Test healthy connection
        health = await memory_store.health_check()
        assert health is True
        
        # Test failed connection
        memory_store.redis_client.ping.side_effect = Exception("Connection failed")
        health = await memory_store.health_check()
        assert health is False
    
    @pytest.mark.asyncio
    async def test_store_conversation(self, memory_store):
        """Test storing conversation memory"""
        memory = ConversationMemory(
            conversation_id="conv-123",
            user_id="user-456",
            messages=[],
            context_variables={"test": "value"},
            preferences={"format": "json"},
            metadata={"source": "test"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = await memory_store.store_conversation(memory)
        assert result is True
        memory_store.redis_client.setex.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_conversation(self, memory_store):
        """Test retrieving conversation memory"""
        # Test existing conversation
        test_data = {
            "conversation_id": "conv-123",
            "user_id": "user-456",
            "messages": [],
            "context_variables": {"test": "value"},
            "preferences": {"format": "json"},
            "metadata": {"source": "test"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        import json
        memory_store.redis_client.get.return_value = json.dumps(test_data)
        
        memory = await memory_store.get_conversation("conv-123")
        assert memory is not None
        assert memory.conversation_id == "conv-123"
        assert memory.user_id == "user-456"
        
        # Test non-existing conversation
        memory_store.redis_client.get.return_value = None
        memory = await memory_store.get_conversation("non-existent")
        assert memory is None
    
    @pytest.mark.asyncio
    async def test_store_query(self, memory_store):
        """Test storing query memory"""
        query_memory = QueryMemory(
            query_id="query-123",
            conversation_id="conv-123",
            user_id="user-456",
            original_query="test query",
            processed_query="test query",
            spl_query="search index=test",
            intent="SEARCH_EVENTS",
            entities={},
            confidence_score=0.8,
            context_used={},
            timestamp=datetime.utcnow()
        )
        
        result = await memory_store.store_query(query_memory)
        assert result is True
        memory_store.redis_client.setex.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_message_to_conversation(self, memory_store):
        """Test adding message to conversation"""
        # Setup existing conversation
        test_data = {
            "conversation_id": "conv-123",
            "user_id": "user-456",
            "messages": [{"id": "msg-1", "content": "hello"}],
            "context_variables": {"test": "value"},
            "preferences": {"format": "json"},
            "metadata": {"source": "test"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        import json
        memory_store.redis_client.get.return_value = json.dumps(test_data)
        
        message = {"id": "msg-2", "content": "world"}
        result = await memory_store.add_message_to_conversation("conv-123", message)
        assert result is True


class TestConversationManager:
    """Test conversation manager functionality"""
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_manager):
        """Test creating a new conversation"""
        context = await conversation_manager.create_conversation(
            user_id="user-123",
            title="Test Conversation"
        )
        
        assert context.user_id == "user-123"
        assert context.title == "Test Conversation"
        assert context.state == ConversationState.ACTIVE
        assert context.message_count == 0
        assert context.query_count == 0
    
    @pytest.mark.asyncio
    async def test_add_message(self, conversation_manager):
        """Test adding message to conversation"""
        # Setup mock conversation
        conversation_manager.memory_store.get_conversation.return_value = ConversationMemory(
            conversation_id="conv-123",
            user_id="user-456",
            messages=[],
            context_variables={"query_count": 0},
            preferences={},
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        conversation_manager.memory_store.add_message_to_conversation.return_value = True
        
        result = await conversation_manager.add_message(
            conversation_id="conv-123",
            message_type=MessageType.USER_QUERY,
            content="test message"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_build_query_context(self, conversation_manager):
        """Test building query context"""
        # Setup mock conversation
        conversation_manager.get_conversation.return_value = ConversationContext(
            conversation_id="conv-123",
            user_id="user-456",
            state=ConversationState.ACTIVE,
            title="Test",
            summary=None,
            current_topic="security"
        )
        
        conversation_manager.memory_store.get_recent_queries.return_value = [
            QueryMemory(
                query_id="q1",
                conversation_id="conv-123",
                user_id="user-456",
                original_query="previous query",
                processed_query="previous query",
                spl_query="search index=security",
                intent="SEARCH_EVENTS",
                entities={"FIELD_NAME": ["host"], "INDEX": ["security"]},
                confidence_score=0.8,
                context_used={},
                timestamp=datetime.utcnow()
            )
        ]
        
        context = await conversation_manager.build_query_context(
            conversation_id="conv-123",
            user_query="show me the same data for today"
        )
        
        assert context.conversation_id == "conv-123"
        assert context.user_id == "user-456"
        assert context.original_query == "show me the same data for today"
        assert context.conversation_topic == "security"
        assert "host" in context.referenced_fields
        assert "security" in context.referenced_indexes
    
    @pytest.mark.asyncio
    async def test_end_conversation(self, conversation_manager):
        """Test ending a conversation"""
        conversation_manager.update_conversation_context.return_value = True
        
        result = await conversation_manager.end_conversation("conv-123")
        assert result is True


class TestContextService:
    """Test context service functionality"""
    
    @pytest.mark.asyncio
    async def test_process_contextual_query(self, context_service):
        """Test processing contextual query"""
        # Mock dependencies
        with patch('app.context.context_service.nlp_service') as mock_nlp:
            # Setup mocks
            mock_query_context = QueryContext(
                query_id="query-123",
                conversation_id="conv-123",
                user_id="user-456",
                original_query="show me errors from yesterday",
                previous_queries=["show me logs"],
                referenced_fields=["error_level"],
                referenced_indexes=["main"]
            )
            
            context_service.conversation_manager.build_query_context.return_value = mock_query_context
            context_service.conversation_manager.store_query_result.return_value = True
            context_service._get_conversation_history.return_value = []
            
            mock_nlp.translate_to_spl.return_value = MagicMock(
                spl_query="search index=main earliest=-1d@d latest=-0d@d error_level=error",
                confidence_score=0.85,
                explanation="Searching for errors from yesterday",
                processing_time=1.2
            )
            
            preferences = ContextPreferences(
                include_history=True,
                max_context_queries=5,
                suggest_follow_ups=True
            )
            
            result = await context_service.process_contextual_query(
                conversation_id="conv-123",
                user_query="show me errors from yesterday",
                preferences=preferences
            )
            
            assert result.spl_query == "search index=main earliest=-1d@d latest=-0d@d error_level=error"
            assert result.confidence_score == 0.85
            assert result.explanation == "Searching for errors from yesterday"
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_enhance_query_with_context(self, context_service):
        """Test query enhancement with context"""
        query_context = QueryContext(
            query_id="query-123",
            conversation_id="conv-123",
            user_id="user-456",
            original_query="show me data",
            referenced_fields=["host", "source"],
            referenced_indexes=["security"],
            relative_time_references=True,
            time_context={"has_relative_references": True}
        )
        
        preferences = ContextPreferences(include_history=True)
        
        enhanced_query, context_info = await context_service._enhance_query_with_context(
            query_context, preferences
        )
        
        assert "host" in enhanced_query or "common_fields" in context_info
        assert "sources" in context_info
        assert len(context_info["sources"]) > 0
    
    def test_resolve_references(self, context_service):
        """Test reference resolution"""
        query_context = QueryContext(
            query_id="query-123",
            conversation_id="conv-123",
            user_id="user-456",
            original_query="show me this field data",
            referenced_fields=["error_count"],
            referenced_indexes=["main"]
        )
        
        preferences = ContextPreferences(auto_resolve_references=True)
        
        query = "show me this field data"
        resolved_query, resolved_refs = asyncio.run(
            context_service._resolve_references(query, query_context, preferences)
        )
        
        # Should resolve "this field" to specific field name
        assert "error_count" in resolved_query or "field_reference" in resolved_refs
    
    def test_calculate_context_confidence(self, context_service):
        """Test context confidence calculation"""
        query_context = QueryContext(
            query_id="query-123",
            conversation_id="conv-123",
            user_id="user-456",
            original_query="test query",
            confidence=0.8,
            previous_queries=["prev1", "prev2"]
        )
        
        context_info = {
            "sources": ["previous_queries", "field_context"],
            "enhancements": ["added_field_context"]
        }
        
        resolved_refs = {"field_reference": "host"}
        
        confidence = context_service._calculate_context_confidence(
            query_context, context_info, resolved_refs
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0  # Should have some confidence


class TestContextPreferences:
    """Test context preferences"""
    
    def test_default_preferences(self):
        """Test default preference values"""
        prefs = ContextPreferences()
        
        assert prefs.include_history is True
        assert prefs.max_context_queries == 5
        assert prefs.prefer_recent_context is True
        assert prefs.auto_resolve_references is True
        assert prefs.context_sensitivity == "medium"
        assert prefs.include_explanations is True
        assert prefs.suggest_follow_ups is True
    
    def test_custom_preferences(self):
        """Test custom preference values"""
        prefs = ContextPreferences(
            include_history=False,
            max_context_queries=10,
            context_sensitivity="high",
            suggest_follow_ups=False
        )
        
        assert prefs.include_history is False
        assert prefs.max_context_queries == 10
        assert prefs.context_sensitivity == "high"
        assert prefs.suggest_follow_ups is False


# Integration Tests
class TestContextIntegration:
    """Integration tests for context management"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, conversation_manager, context_service):
        """Test complete conversation flow"""
        # Create conversation
        context = await conversation_manager.create_conversation(
            user_id="user-123",
            title="Security Analysis"
        )
        
        # Add first query
        await conversation_manager.add_message(
            conversation_id=context.conversation_id,
            message_type=MessageType.USER_QUERY,
            content="show me failed logins"
        )
        
        # Add second contextual query
        await conversation_manager.add_message(
            conversation_id=context.conversation_id,
            message_type=MessageType.USER_QUERY,
            content="show me the same data for yesterday"
        )
        
        # Build context for second query
        query_context = await conversation_manager.build_query_context(
            conversation_id=context.conversation_id,
            user_query="show me the same data for yesterday"
        )
        
        assert query_context.conversation_id == context.conversation_id
        assert query_context.relative_time_references is True
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, memory_store):
        """Test memory persistence across operations"""
        # Store conversation
        memory = ConversationMemory(
            conversation_id="conv-persist",
            user_id="user-persist",
            messages=[{"id": "msg-1", "content": "hello"}],
            context_variables={"topic": "security"},
            preferences={"format": "detailed"},
            metadata={"session": "sess-123"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await memory_store.store_conversation(memory)
        
        # Add message
        new_message = {"id": "msg-2", "content": "world"}
        await memory_store.add_message_to_conversation(
            "conv-persist", 
            new_message,
            {"last_message": "world"}
        )
        
        # Verify persistence through mocked calls
        memory_store.redis_client.setex.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])