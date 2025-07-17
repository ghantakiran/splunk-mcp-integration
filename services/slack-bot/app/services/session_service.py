"""
Session service for managing user conversation sessions.
"""

import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncpg
import redis.asyncio as redis

from ..core.config import settings
from ..core.logging import get_logger, LogContext
from ..models.slack_models import UserSession, QueryResult

logger = get_logger(__name__)

class SessionService:
    """Service for managing user conversation sessions."""
    
    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.session_timeout = timedelta(hours=1)  # Sessions expire after 1 hour of inactivity
        
    async def initialize(self):
        """Initialize database connections."""
        try:
            # Initialize PostgreSQL connection pool
            self.db_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Initialize Redis for session caching
            self.redis_client = redis.from_url(
                settings.redis_url,
                socket_timeout=settings.redis_timeout,
                decode_responses=True
            )
            
            # Test connections
            async with self.db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            await self.redis_client.ping()
            
            logger.info("Session service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize session service: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def get_or_create_session(self, user_id: str, channel_id: str) -> UserSession:
        """Get existing session or create a new one."""
        with LogContext(user_id=user_id, channel_id=channel_id):
            try:
                # Check for existing active session
                session = await self._get_active_session(user_id, channel_id)
                
                if session:
                    # Update last activity
                    session.last_activity = datetime.utcnow()
                    await self._cache_session(session)
                    return session
                
                # Create new session
                session_id = str(uuid.uuid4())
                session = UserSession(
                    id=session_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    started_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    history=[],
                    context={},
                    preferences={},
                    is_active=True
                )
                
                # Save to database
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO user_sessions 
                        (id, user_id, channel_id, started_at, last_activity, history, context, preferences, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        session.id,
                        session.user_id,
                        session.channel_id,
                        session.started_at,
                        session.last_activity,
                        json.dumps(session.history),
                        json.dumps(session.context),
                        json.dumps(session.preferences),
                        session.is_active
                    )
                
                # Cache the session
                await self._cache_session(session)
                
                logger.info("New session created", session_id=session_id)
                return session
                
            except Exception as e:
                logger.error(f"Error getting/creating session: {str(e)}")
                # Return minimal session as fallback
                return UserSession(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    channel_id=channel_id
                )
    
    async def update_session(self, session_id: str, query: str, response: Dict[str, Any]) -> bool:
        """Update session with new interaction."""
        with LogContext(session_id=session_id):
            try:
                # Get session from cache or database
                session = await self._get_session_by_id(session_id)
                if not session:
                    logger.warning("Session not found for update")
                    return False
                
                # Add interaction to history
                interaction = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query": query,
                    "response": {
                        "success": response.get("success", False),
                        "spl_query": response.get("data", {}).get("spl_query"),
                        "results_count": len(response.get("data", {}).get("data", [])),
                        "execution_time": response.get("data", {}).get("execution_time"),
                        "confidence_score": response.get("data", {}).get("confidence_score"),
                        "error": response.get("error")
                    }
                }
                
                session.history.append(interaction)
                session.last_activity = datetime.utcnow()
                
                # Limit history size
                if len(session.history) > 50:
                    session.history = session.history[-50:]
                
                # Update database
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE user_sessions 
                        SET history = $2, last_activity = $3
                        WHERE id = $1
                        """,
                        session_id,
                        json.dumps(session.history),
                        session.last_activity
                    )
                
                # Update cache
                await self._cache_session(session)
                
                logger.info("Session updated", query_length=len(query))
                return True
                
            except Exception as e:
                logger.error(f"Error updating session: {str(e)}")
                return False
    
    async def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get session conversation history."""
        try:
            session = await self._get_session_by_id(session_id)
            if not session:
                return []
            
            # Return recent history
            return session.history[-limit:] if session.history else []
            
        except Exception as e:
            logger.error(f"Error getting session history: {str(e)}")
            return []
    
    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[UserSession]:
        """Get recent sessions for a user."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, channel_id, started_at, last_activity, 
                           history, context, preferences, is_active
                    FROM user_sessions 
                    WHERE user_id = $1 
                    ORDER BY last_activity DESC 
                    LIMIT $2
                    """,
                    user_id, limit
                )
                
                sessions = []
                for row in rows:
                    session_data = dict(row)
                    session_data["history"] = json.loads(session_data["history"] or "[]")
                    session_data["context"] = json.loads(session_data["context"] or "{}")
                    session_data["preferences"] = json.loads(session_data["preferences"] or "{}")
                    sessions.append(UserSession(**session_data))
                
                return sessions
                
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    async def close_session(self, session_id: str) -> bool:
        """Close/deactivate a session."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_sessions 
                    SET is_active = FALSE, last_activity = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    session_id
                )
            
            # Remove from cache
            await self.redis_client.delete(f"session:{session_id}")
            
            logger.info("Session closed", session_id=session_id)
            return True
            
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions."""
        try:
            cutoff_time = datetime.utcnow() - self.session_timeout
            
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE user_sessions 
                    SET is_active = FALSE 
                    WHERE is_active = TRUE AND last_activity < $1
                    """,
                    cutoff_time
                )
                
                # Extract the number of updated rows
                updated_count = int(result.split()[-1]) if result.startswith("UPDATE") else 0
                
                if updated_count > 0:
                    logger.info(f"Cleaned up {updated_count} expired sessions")
                
                return updated_count
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            return 0
    
    async def _get_active_session(self, user_id: str, channel_id: str) -> Optional[UserSession]:
        """Get active session for user in channel."""
        try:
            # Check cache first
            cache_key = f"active_session:{user_id}:{channel_id}"
            cached_session_id = await self.redis_client.get(cache_key)
            
            if cached_session_id:
                session = await self._get_session_by_id(cached_session_id)
                if session and session.is_active:
                    # Check if session is still valid (not expired)
                    if datetime.utcnow() - session.last_activity < self.session_timeout:
                        return session
            
            # Get from database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, channel_id, started_at, last_activity,
                           history, context, preferences, is_active
                    FROM user_sessions 
                    WHERE user_id = $1 AND channel_id = $2 AND is_active = TRUE
                    AND last_activity > $3
                    ORDER BY last_activity DESC 
                    LIMIT 1
                    """,
                    user_id, channel_id, datetime.utcnow() - self.session_timeout
                )
                
                if row:
                    session_data = dict(row)
                    session_data["history"] = json.loads(session_data["history"] or "[]")
                    session_data["context"] = json.loads(session_data["context"] or "{}")
                    session_data["preferences"] = json.loads(session_data["preferences"] or "{}")
                    
                    session = UserSession(**session_data)
                    
                    # Cache the active session reference
                    await self.redis_client.setex(cache_key, 3600, session.id)
                    
                    return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting active session: {str(e)}")
            return None
    
    async def _get_session_by_id(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID from cache or database."""
        try:
            # Check cache first
            cache_key = f"session:{session_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                session_data = json.loads(cached_data)
                return UserSession(**session_data)
            
            # Get from database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, channel_id, started_at, last_activity,
                           history, context, preferences, is_active
                    FROM user_sessions WHERE id = $1
                    """,
                    session_id
                )
                
                if row:
                    session_data = dict(row)
                    session_data["history"] = json.loads(session_data["history"] or "[]")
                    session_data["context"] = json.loads(session_data["context"] or "{}")
                    session_data["preferences"] = json.loads(session_data["preferences"] or "{}")
                    
                    session = UserSession(**session_data)
                    
                    # Cache the session
                    await self._cache_session(session)
                    
                    return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session by ID: {str(e)}")
            return None
    
    async def _cache_session(self, session: UserSession):
        """Cache session data."""
        try:
            cache_key = f"session:{session.id}"
            session_data = session.model_dump()
            
            # Convert datetime objects to strings
            for key, value in session_data.items():
                if isinstance(value, datetime):
                    session_data[key] = value.isoformat()
            
            await self.redis_client.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps(session_data)
            )
            
            # Also cache the active session reference
            if session.is_active:
                active_key = f"active_session:{session.user_id}:{session.channel_id}"
                await self.redis_client.setex(active_key, 3600, session.id)
            
        except Exception as e:
            logger.debug(f"Failed to cache session: {str(e)}")