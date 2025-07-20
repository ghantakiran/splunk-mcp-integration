"""
Tests for Slack Bot services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.services.splunk_service import SplunkService
from app.models.slack_models import UserSession


class TestUserService:
    """Test suite for UserService."""
    
    @pytest.fixture
    def user_service(self):
        """Create UserService instance."""
        service = UserService()
        service.db = AsyncMock()
        service.cache = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_get_user_context_cached(self, user_service):
        """Test getting user context from cache."""
        # Setup
        user_id = "U123456789"
        cached_context = {
            "user_id": user_id,
            "roles": ["user"],
            "accessible_indexes": ["*"]
        }
        user_service.cache.get.return_value = cached_context
        
        # Execute
        result = await user_service.get_user_context(user_id)
        
        # Verify
        assert result == cached_context
        user_service.cache.get.assert_called_once_with(f"user_context:{user_id}")
        user_service.db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_context_from_db(self, user_service):
        """Test getting user context from database."""
        # Setup
        user_id = "U123456789"
        user_service.cache.get.return_value = None  # Not in cache
        
        # Mock database result
        db_result = MagicMock()
        db_result.fetchone.return_value = {
            "slack_user_id": user_id,
            "roles": ["user", "analyst"],
            "accessible_indexes": ["main", "security"],
            "preferences": {"timezone": "UTC"}
        }
        user_service.db.execute.return_value = db_result
        
        # Execute
        result = await user_service.get_user_context(user_id)
        
        # Verify
        assert result["user_id"] == user_id
        assert result["roles"] == ["user", "analyst"]
        assert result["accessible_indexes"] == ["main", "security"]
        user_service.cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_context_not_found(self, user_service):
        """Test getting user context when user not found."""
        # Setup
        user_id = "U999999999"
        user_service.cache.get.return_value = None
        
        db_result = MagicMock()
        db_result.fetchone.return_value = None
        user_service.db.execute.return_value = db_result
        
        # Execute
        result = await user_service.get_user_context(user_id)
        
        # Verify - should return default context
        assert result["user_id"] == user_id
        assert result["roles"] == ["guest"]
        assert result["accessible_indexes"] == []
    
    @pytest.mark.asyncio
    async def test_create_or_update_user(self, user_service):
        """Test creating or updating user."""
        # Setup
        user_data = {
            "slack_user_id": "U123456789",
            "team_id": "T123456789",
            "real_name": "Test User",
            "email": "test@example.com"
        }
        
        # Execute
        await user_service.create_or_update_user(user_data)
        
        # Verify
        user_service.db.execute.assert_called()
        # Should invalidate cache
        user_service.cache.delete.assert_called_with(f"user_context:{user_data['slack_user_id']}")
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, user_service):
        """Test getting user information."""
        # Setup
        user_id = "U123456789"
        user_service.cache.get.return_value = None
        
        db_result = MagicMock()
        db_result.fetchone.return_value = {
            "slack_user_id": user_id,
            "real_name": "Test User",
            "email": "test@example.com",
            "access_level": "standard",
            "last_active": datetime.utcnow()
        }
        user_service.db.execute.return_value = db_result
        
        # Execute
        result = await user_service.get_user_info(user_id)
        
        # Verify
        assert result["real_name"] == "Test User"
        assert result["access_level"] == "standard"
    
    @pytest.mark.asyncio
    async def test_update_user_activity(self, user_service):
        """Test updating user activity."""
        # Setup
        user_id = "U123456789"
        activity_data = {
            "last_query": "show me errors",
            "query_count": 5
        }
        
        # Execute
        await user_service.update_user_activity(user_id, activity_data)
        
        # Verify
        user_service.db.execute.assert_called()


class TestSessionService:
    """Test suite for SessionService."""
    
    @pytest.fixture
    def session_service(self):
        """Create SessionService instance."""
        service = SessionService()
        service.db = AsyncMock()
        service.cache = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_existing(self, session_service):
        """Test getting existing session."""
        # Setup
        user_id = "U123456789"
        channel_id = "C123456789"
        
        existing_session = UserSession(
            id="session-123",
            user_id=user_id,
            channel_id=channel_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            context={"last_query": "show me status"}
        )
        
        db_result = MagicMock()
        db_result.fetchone.return_value = {
            "id": existing_session.id,
            "user_id": user_id,
            "channel_id": channel_id,
            "created_at": existing_session.created_at,
            "last_active": existing_session.last_active,
            "context": existing_session.context
        }
        session_service.db.execute.return_value = db_result
        
        # Execute
        result = await session_service.get_or_create_session(user_id, channel_id)
        
        # Verify
        assert result.id == existing_session.id
        assert result.user_id == user_id
        assert result.channel_id == channel_id
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_new(self, session_service):
        """Test creating new session."""
        # Setup
        user_id = "U123456789"
        channel_id = "C123456789"
        
        # No existing session
        db_result_fetch = MagicMock()
        db_result_fetch.fetchone.return_value = None
        
        # Mock session creation
        db_result_insert = MagicMock()
        db_result_insert.fetchone.return_value = {"id": "new-session-123"}
        
        session_service.db.execute.side_effect = [db_result_fetch, db_result_insert]
        
        # Execute
        result = await session_service.get_or_create_session(user_id, channel_id)
        
        # Verify
        assert result.id == "new-session-123"
        assert result.user_id == user_id
        assert result.channel_id == channel_id
        assert session_service.db.execute.call_count == 2  # SELECT then INSERT
    
    @pytest.mark.asyncio
    async def test_update_session_context(self, session_service):
        """Test updating session context."""
        # Setup
        session_id = "session-123"
        context_update = {
            "last_query": "show me errors",
            "query_count": 3
        }
        
        # Execute
        await session_service.update_session_context(session_id, context_update)
        
        # Verify
        session_service.db.execute.assert_called()
        # Should invalidate cache
        session_service.cache.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_message_to_history(self, session_service):
        """Test adding message to session history."""
        # Setup
        session_id = "session-123"
        message = {
            "user_id": "U123456789",
            "text": "show me status",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Execute
        await session_service.add_message_to_history(session_id, message)
        
        # Verify
        session_service.db.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_session_history(self, session_service):
        """Test getting session history."""
        # Setup
        session_id = "session-123"
        limit = 10
        
        db_result = MagicMock()
        db_result.fetchall.return_value = [
            {
                "user_id": "U123456789",
                "text": "show me status",
                "timestamp": datetime.utcnow()
            }
        ]
        session_service.db.execute.return_value = db_result
        
        # Execute
        result = await session_service.get_session_history(session_id, limit)
        
        # Verify
        assert len(result) == 1
        assert result[0]["text"] == "show me status"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service):
        """Test cleaning up expired sessions."""
        # Setup
        expiry_hours = 24
        
        db_result = MagicMock()
        db_result.rowcount = 5  # 5 sessions deleted
        session_service.db.execute.return_value = db_result
        
        # Execute
        count = await session_service.cleanup_expired_sessions(expiry_hours)
        
        # Verify
        assert count == 5
        session_service.db.execute.assert_called()


class TestSplunkService:
    """Test suite for SplunkService."""
    
    @pytest.fixture
    def splunk_service(self):
        """Create SplunkService instance."""
        service = SplunkService()
        service.nlp_client = AsyncMock()
        service.viz_client = AsyncMock()
        service.api_client = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, splunk_service):
        """Test successful query processing."""
        # Setup
        query = "show me errors from last hour"
        user_context = {
            "user_id": "U123456789",
            "accessible_indexes": ["main"]
        }
        
        # Mock NLP response
        nlp_response = AsyncMock()
        nlp_response.json.return_value = {
            "success": True,
            "spl_query": "search index=main error | head 100",
            "confidence": 0.9
        }
        nlp_response.raise_for_status = AsyncMock()
        splunk_service.nlp_client.post.return_value = nlp_response
        
        # Mock API Gateway response
        api_response = AsyncMock()
        api_response.json.return_value = {
            "success": True,
            "data": [{"count": 5, "severity": "high"}],
            "execution_time": 1.2
        }
        api_response.raise_for_status = AsyncMock()
        splunk_service.api_client.post.return_value = api_response
        
        # Execute
        result = await splunk_service.process_query(query, user_context)
        
        # Verify
        assert result["success"] is True
        assert "spl_query" in result["data"]
        assert "execution_time" in result["data"]
        splunk_service.nlp_client.post.assert_called_once()
        splunk_service.api_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_nlp_failure(self, splunk_service):
        """Test query processing with NLP failure."""
        # Setup
        query = "show me errors"
        user_context = {"user_id": "U123456789"}
        
        # Mock NLP failure
        splunk_service.nlp_client.post.side_effect = Exception("NLP service unavailable")
        
        # Execute
        result = await splunk_service.process_query(query, user_context)
        
        # Verify
        assert result["success"] is False
        assert "error" in result
        assert "NLP service unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, splunk_service):
        """Test getting system status."""
        # Setup
        status_response = AsyncMock()
        status_response.json.return_value = {
            "status": "healthy",
            "services": {
                "nlp_engine": {"status": "healthy", "response_time": 50},
                "api_gateway": {"status": "healthy", "response_time": 30}
            }
        }
        status_response.raise_for_status = AsyncMock()
        splunk_service.api_client.get.return_value = status_response
        
        # Execute
        result = await splunk_service.get_system_status()
        
        # Verify
        assert result["status"] == "healthy"
        assert "services" in result
        splunk_service.api_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_visualization(self, splunk_service):
        """Test creating visualization."""
        # Setup
        viz_request = {
            "chart_type": "line",
            "data": [{"x": 1, "y": 10}],
            "title": "Test Chart"
        }
        
        viz_response = AsyncMock()
        viz_response.json.return_value = {
            "success": True,
            "image_url": "http://example.com/chart.png",
            "chart_id": "chart-123"
        }
        viz_response.raise_for_status = AsyncMock()
        splunk_service.viz_client.post.return_value = viz_response
        
        # Execute
        result = await splunk_service.create_visualization(viz_request)
        
        # Verify
        assert result["success"] is True
        assert "image_url" in result
        splunk_service.viz_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_spl_query(self, splunk_service):
        """Test SPL query validation."""
        # Setup
        spl_query = "search index=main | stats count"
        
        validation_response = AsyncMock()
        validation_response.json.return_value = {
            "valid": True,
            "syntax_errors": [],
            "performance_score": 0.8
        }
        validation_response.raise_for_status = AsyncMock()
        splunk_service.api_client.post.return_value = validation_response
        
        # Execute
        result = await splunk_service.validate_spl_query(spl_query)
        
        # Verify
        assert result["valid"] is True
        assert result["performance_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_get_available_indexes(self, splunk_service):
        """Test getting available indexes."""
        # Setup
        user_context = {"user_id": "U123456789"}
        
        indexes_response = AsyncMock()
        indexes_response.json.return_value = {
            "indexes": ["main", "security", "web"]
        }
        indexes_response.raise_for_status = AsyncMock()
        splunk_service.api_client.get.return_value = indexes_response
        
        # Execute
        result = await splunk_service.get_available_indexes(user_context)
        
        # Verify
        assert "main" in result
        assert "security" in result
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_service_health_check(self, splunk_service):
        """Test service health check."""
        # Setup - all services healthy
        health_response = AsyncMock()
        health_response.json.return_value = {"status": "healthy"}
        health_response.raise_for_status = AsyncMock()
        
        splunk_service.nlp_client.get.return_value = health_response
        splunk_service.viz_client.get.return_value = health_response
        splunk_service.api_client.get.return_value = health_response
        
        # Execute
        result = await splunk_service.health_check()
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_service_health_check_failure(self, splunk_service):
        """Test service health check with failure."""
        # Setup - one service failing
        splunk_service.nlp_client.get.side_effect = Exception("Service down")
        
        # Execute
        result = await splunk_service.health_check()
        
        # Verify
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])