"""
User service for managing Teams users and their Splunk access.
"""

import asyncio
from typing import Dict, List, Any, Optional
import asyncpg
import redis.asyncio as redis
from datetime import datetime, timedelta

from ..core.config import settings
from ..core.logging import get_logger, LogContext
from ..models.teams_models import TeamsUser, UserContext

logger = get_logger(__name__)

class UserService:
    """Service for managing users and their access context."""
    
    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        
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
            
            # Initialize Redis for caching
            self.redis_client = redis.from_url(
                settings.redis_url,
                socket_timeout=settings.redis_timeout,
                decode_responses=True
            )
            
            # Test connections
            async with self.db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            await self.redis_client.ping()
            
            logger.info("User service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize user service: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def get_or_create_user(self, teams_user_data: Dict[str, Any]) -> TeamsUser:
        """Get or create a user from Teams user data."""
        with LogContext(user_id=teams_user_data.get("id")):
            try:
                user_id = teams_user_data["id"]
                
                # Check cache first
                cached_user = await self._get_cached_user(user_id)
                if cached_user:
                    return cached_user
                
                # Get from database
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, name, email, aad_object_id, tenant_id, 
                               conversation_type, is_admin, is_bot, 
                               created_at, updated_at
                        FROM teams_users WHERE id = $1
                        """,
                        user_id
                    )
                    
                    if row:
                        user = TeamsUser(**dict(row))
                        
                        # Update user info if needed
                        if self._should_update_user(user, teams_user_data):
                            user = await self._update_user(conn, user_id, teams_user_data)
                    else:
                        # Create new user
                        user = await self._create_user(conn, teams_user_data)
                    
                    # Cache the user
                    await self._cache_user(user)
                    
                    return user
                    
            except Exception as e:
                logger.error(f"Error getting/creating user: {str(e)}")
                # Return minimal user object as fallback
                return TeamsUser(
                    id=teams_user_data.get("id", "unknown"),
                    name=teams_user_data.get("name", "Unknown User"),
                    tenant_id=teams_user_data.get("tenant_id", "unknown")
                )
    
    async def get_user_context(self, user_id: str) -> UserContext:
        """Get user's Splunk access context."""
        with LogContext(user_id=user_id):
            try:
                # Check cache first
                cache_key = f"user_context:{user_id}"
                cached_context = await self.redis_client.get(cache_key)
                
                if cached_context:
                    import json
                    context_data = json.loads(cached_context)
                    return UserContext(**context_data)
                
                # Get from database
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT uc.user_id, uc.roles, uc.permissions, uc.accessible_indexes,
                               uc.preferences, uc.access_level
                        FROM user_contexts uc
                        WHERE uc.user_id = $1
                        """,
                        user_id
                    )
                    
                    if row:
                        context = UserContext(
                            user_id=row["user_id"],
                            roles=row["roles"] or [],
                            permissions=row["permissions"] or {},
                            accessible_indexes=row["accessible_indexes"] or [],
                            preferences=row["preferences"] or {},
                            access_level=row["access_level"] or "standard"
                        )
                    else:
                        # Create default context for new user
                        context = await self._create_default_user_context(conn, user_id)
                    
                    # Cache the context
                    await self._cache_user_context(context)
                    
                    return context
                    
            except Exception as e:
                logger.error(f"Error getting user context: {str(e)}")
                # Return default context as fallback
                return UserContext(
                    user_id=user_id,
                    roles=["user"],
                    accessible_indexes=["*"],
                    access_level="standard"
                )
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information for display."""
        try:
            context = await self.get_user_context(user_id)
            
            # Get Teams user info
            async with self.db_pool.acquire() as conn:
                user_row = await conn.fetchrow(
                    "SELECT name, email, aad_object_id FROM teams_users WHERE id = $1",
                    user_id
                )
            
            user_info = {
                "user_id": context.user_id,
                "access_level": context.access_level,
                "roles": context.roles,
                "accessible_indexes": context.accessible_indexes,
                "permissions": context.permissions
            }
            
            if user_row:
                user_info.update({
                    "name": user_row["name"],
                    "email": user_row["email"],
                    "aad_object_id": user_row["aad_object_id"]
                })
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {
                "user_id": user_id,
                "access_level": "standard",
                "roles": ["user"],
                "accessible_indexes": [],
                "permissions": {}
            }
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        with LogContext(user_id=user_id):
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE user_contexts 
                        SET preferences = $2, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = $1
                        """,
                        user_id, preferences
                    )
                    
                    # Invalidate cache
                    await self.redis_client.delete(f"user_context:{user_id}")
                    
                    logger.info("User preferences updated", preferences_count=len(preferences))
                    return True
                    
            except Exception as e:
                logger.error(f"Error updating user preferences: {str(e)}")
                return False
    
    async def get_user_by_aad_object_id(self, aad_object_id: str) -> Optional[TeamsUser]:
        """Get user by Azure AD object ID."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, name, email, aad_object_id, tenant_id, 
                           conversation_type, is_admin, is_bot, 
                           created_at, updated_at
                    FROM teams_users WHERE aad_object_id = $1
                    """,
                    aad_object_id
                )
                
                if row:
                    return TeamsUser(**dict(row))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by AAD object ID: {str(e)}")
            return None
    
    async def get_users_in_tenant(self, tenant_id: str, limit: int = 100) -> List[TeamsUser]:
        """Get users in a specific tenant."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, name, email, aad_object_id, tenant_id, 
                           conversation_type, is_admin, is_bot, 
                           created_at, updated_at
                    FROM teams_users 
                    WHERE tenant_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                    """,
                    tenant_id, limit
                )
                
                return [TeamsUser(**dict(row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting users in tenant: {str(e)}")
            return []
    
    async def _get_cached_user(self, user_id: str) -> Optional[TeamsUser]:
        """Get user from cache."""
        try:
            cache_key = f"teams_user:{user_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                import json
                user_data = json.loads(cached_data)
                return TeamsUser(**user_data)
                
        except Exception as e:
            logger.debug(f"Cache miss for user {user_id}: {str(e)}")
        
        return None
    
    async def _cache_user(self, user: TeamsUser):
        """Cache user data."""
        try:
            cache_key = f"teams_user:{user.id}"
            user_data = user.model_dump()
            
            # Convert datetime objects to strings
            for key, value in user_data.items():
                if isinstance(value, datetime):
                    user_data[key] = value.isoformat()
            
            import json
            await self.redis_client.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps(user_data)
            )
            
        except Exception as e:
            logger.debug(f"Failed to cache user: {str(e)}")
    
    async def _cache_user_context(self, context: UserContext):
        """Cache user context."""
        try:
            cache_key = f"user_context:{context.user_id}"
            context_data = context.model_dump()
            
            import json
            await self.redis_client.setex(
                cache_key,
                1800,  # 30 minutes TTL
                json.dumps(context_data)
            )
            
        except Exception as e:
            logger.debug(f"Failed to cache user context: {str(e)}")
    
    def _should_update_user(self, user: TeamsUser, teams_data: Dict[str, Any]) -> bool:
        """Check if user data should be updated."""
        # Update if basic info has changed or it's been more than a day
        if user.updated_at < datetime.utcnow() - timedelta(hours=24):
            return True
        
        # Check if key fields have changed
        fields_to_check = ["name", "email"]
        for field in fields_to_check:
            if teams_data.get(field) != getattr(user, field, None):
                return True
        
        return False
    
    async def _update_user(self, conn: asyncpg.Connection, user_id: str, teams_data: Dict[str, Any]) -> TeamsUser:
        """Update existing user."""
        await conn.execute(
            """
            UPDATE teams_users 
            SET name = $2, email = $3, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            user_id,
            teams_data.get("name"),
            teams_data.get("email")
        )
        
        # Get updated user
        row = await conn.fetchrow(
            "SELECT * FROM teams_users WHERE id = $1",
            user_id
        )
        
        logger.info("Teams user updated", user_id=user_id)
        return TeamsUser(**dict(row))
    
    async def _create_user(self, conn: asyncpg.Connection, teams_data: Dict[str, Any]) -> TeamsUser:
        """Create new user."""
        user_id = teams_data["id"]
        
        await conn.execute(
            """
            INSERT INTO teams_users 
            (id, name, email, aad_object_id, tenant_id, conversation_type, is_admin, is_bot)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            user_id,
            teams_data.get("name"),
            teams_data.get("email"),
            teams_data.get("aad_object_id"),
            teams_data.get("tenant_id"),
            teams_data.get("conversation_type", "personal"),
            False,  # is_admin
            False   # is_bot
        )
        
        # Get created user
        row = await conn.fetchrow(
            "SELECT * FROM teams_users WHERE id = $1",
            user_id
        )
        
        logger.info("Teams user created", user_id=user_id)
        return TeamsUser(**dict(row))
    
    async def _create_default_user_context(self, conn: asyncpg.Connection, user_id: str) -> UserContext:
        """Create default user context."""
        default_context = UserContext(
            user_id=user_id,
            roles=["user"],
            permissions={"read": True, "search": True},
            accessible_indexes=["*"],  # All indexes by default
            preferences={
                "theme": "teams",
                "max_results": 50,
                "chart_type": "auto"
            },
            access_level="standard"
        )
        
        await conn.execute(
            """
            INSERT INTO user_contexts 
            (user_id, roles, permissions, accessible_indexes, preferences, access_level)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            default_context.roles,
            default_context.permissions,
            default_context.accessible_indexes,
            default_context.preferences,
            default_context.access_level
        )
        
        logger.info("Default user context created", user_id=user_id)
        return default_context