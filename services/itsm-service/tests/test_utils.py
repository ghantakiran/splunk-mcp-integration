"""
Tests for ITSM Service utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status

from app.utils.auth import verify_jwt_token, get_current_user, create_jwt_token
from app.utils.dependencies import get_database, get_redis, get_current_user_context
from app.models.itsm_models import ITSMUser, UserRole


class TestAuthUtilities:
    """Test authentication utilities."""
    
    def test_create_jwt_token(self):
        """Test JWT token creation."""
        user_data = {
            "user_id": "user-123",
            "username": "testuser",
            "roles": ["user", "admin"]
        }
        
        # Mock the JWT secret
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token content
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            decoded = jwt.decode(token, 'test-secret', algorithms=['HS256'])
        
        assert decoded["user_id"] == "user-123"
        assert decoded["username"] == "testuser"
        assert decoded["roles"] == ["user", "admin"]
        assert "exp" in decoded
        assert "iat" in decoded
    
    def test_create_jwt_token_with_expiration(self):
        """Test JWT token creation with custom expiration."""
        user_data = {"user_id": "user-123"}
        expires_delta = timedelta(hours=2)
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data, expires_delta)
            decoded = jwt.decode(token, 'test-secret', algorithms=['HS256'])
        
        exp_time = datetime.fromtimestamp(decoded["exp"])
        iat_time = datetime.fromtimestamp(decoded["iat"])
        
        # Should be approximately 2 hours difference
        time_diff = exp_time - iat_time
        assert abs(time_diff.total_seconds() - 7200) < 60  # Within 1 minute tolerance
    
    def test_verify_jwt_token_valid(self):
        """Test verifying a valid JWT token."""
        user_data = {
            "user_id": "user-123",
            "username": "testuser",
            "roles": ["user"]
        }
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
            decoded_data = verify_jwt_token(token)
        
        assert decoded_data["user_id"] == "user-123"
        assert decoded_data["username"] == "testuser"
        assert decoded_data["roles"] == ["user"]
    
    def test_verify_jwt_token_invalid_signature(self):
        """Test verifying JWT token with invalid signature."""
        # Create token with one secret
        user_data = {"user_id": "user-123"}
        with patch('app.utils.auth.JWT_SECRET_KEY', 'secret1'):
            token = create_jwt_token(user_data)
        
        # Try to verify with different secret
        with patch('app.utils.auth.JWT_SECRET_KEY', 'secret2'):
            with pytest.raises(HTTPException) as exc_info:
                verify_jwt_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
    
    def test_verify_jwt_token_expired(self):
        """Test verifying an expired JWT token."""
        user_data = {"user_id": "user-123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data, expires_delta)
            
            with pytest.raises(HTTPException) as exc_info:
                verify_jwt_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token expired" in str(exc_info.value.detail)
    
    def test_verify_jwt_token_malformed(self):
        """Test verifying a malformed JWT token."""
        malformed_token = "not.a.valid.jwt.token"
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            with pytest.raises(HTTPException) as exc_info:
                verify_jwt_token(malformed_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        # Mock database
        mock_db = AsyncMock()
        mock_user_record = {
            "id": "user-123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        mock_db.fetchrow.return_value = mock_user_record
        
        user_data = {
            "user_id": "user-123",
            "username": "testuser",
            "roles": ["user"]
        }
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
            user = await get_current_user(token, mock_db)
        
        assert isinstance(user, ITSMUser)
        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        
        mock_db.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        """Test getting current user when user not found in database."""
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # User not found
        
        user_data = {"user_id": "user-123"}
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self):
        """Test getting current user when user is inactive."""
        mock_db = AsyncMock()
        mock_user_record = {
            "id": "user-123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "is_active": False,  # Inactive user
            "created_at": datetime.utcnow()
        }
        mock_db.fetchrow.return_value = mock_user_record
        
        user_data = {"user_id": "user-123"}
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "User account is inactive" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_database_error(self):
        """Test getting current user when database error occurs."""
        mock_db = AsyncMock()
        mock_db.fetchrow.side_effect = Exception("Database connection error")
        
        user_data = {"user_id": "user-123"}
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            token = create_jwt_token(user_data)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database error" in str(exc_info.value.detail)


class TestDependencies:
    """Test dependency injection utilities."""
    
    @pytest.mark.asyncio
    async def test_get_database_success(self):
        """Test getting database connection successfully."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        with patch('app.utils.dependencies.get_db_pool', return_value=mock_pool):
            async with get_database() as db:
                assert db == mock_conn
        
        mock_pool.acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_database_connection_error(self):
        """Test getting database connection when error occurs."""
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("Connection pool exhausted")
        
        with patch('app.utils.dependencies.get_db_pool', return_value=mock_pool):
            with pytest.raises(HTTPException) as exc_info:
                async with get_database() as db:
                    pass
        
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Database connection error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_redis_success(self):
        """Test getting Redis connection successfully."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        
        with patch('app.utils.dependencies.get_redis_client', return_value=mock_redis):
            redis_client = await get_redis()
            assert redis_client == mock_redis
        
        mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_redis_connection_error(self):
        """Test getting Redis connection when error occurs."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        with patch('app.utils.dependencies.get_redis_client', return_value=mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await get_redis()
        
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Redis connection error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_context_success(self):
        """Test getting current user context successfully."""
        mock_user = ITSMUser(
            id="user-123",
            username="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        mock_db = AsyncMock()
        mock_context_record = {
            "user_id": "user-123",
            "permissions": ["read", "write", "admin"],
            "accessible_integrations": ["servicenow-1", "jira-1"],
            "preferences": {"theme": "dark", "notifications": True}
        }
        mock_db.fetchrow.return_value = mock_context_record
        
        context = await get_current_user_context(mock_user, mock_db)
        
        assert context["user_id"] == "user-123"
        assert context["role"] == "admin"
        assert "admin" in context["permissions"]
        assert "servicenow-1" in context["accessible_integrations"]
        assert context["preferences"]["theme"] == "dark"
        
        mock_db.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_current_user_context_not_found(self):
        """Test getting user context when context not found."""
        mock_user = ITSMUser(
            id="user-123",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        mock_db = AsyncMock()
        mock_db.fetchrow.return_value = None  # Context not found
        
        context = await get_current_user_context(mock_user, mock_db)
        
        # Should return default context
        assert context["user_id"] == "user-123"
        assert context["role"] == "user"
        assert context["permissions"] == ["read"]  # Default permissions
        assert context["accessible_integrations"] == []
        assert context["preferences"] == {}
    
    @pytest.mark.asyncio
    async def test_get_current_user_context_database_error(self):
        """Test getting user context when database error occurs."""
        mock_user = ITSMUser(
            id="user-123",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        mock_db = AsyncMock()
        mock_db.fetchrow.side_effect = Exception("Database query failed")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_context(mock_user, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to get user context" in str(exc_info.value.detail)


class TestRoleBasedPermissions:
    """Test role-based permission utilities."""
    
    def test_admin_permissions(self):
        """Test admin role permissions."""
        from app.utils.auth import get_role_permissions
        
        permissions = get_role_permissions(UserRole.ADMIN)
        
        expected_permissions = [
            "read", "write", "delete", "admin",
            "integration:create", "integration:update", "integration:delete",
            "workflow:create", "workflow:update", "workflow:delete",
            "user:manage", "system:configure"
        ]
        
        for permission in expected_permissions:
            assert permission in permissions
    
    def test_manager_permissions(self):
        """Test manager role permissions."""
        from app.utils.auth import get_role_permissions
        
        permissions = get_role_permissions(UserRole.MANAGER)
        
        expected_permissions = [
            "read", "write", "delete",
            "integration:create", "integration:update",
            "workflow:create", "workflow:update"
        ]
        
        for permission in expected_permissions:
            assert permission in permissions
        
        # Should not have admin permissions
        assert "admin" not in permissions
        assert "user:manage" not in permissions
        assert "system:configure" not in permissions
    
    def test_analyst_permissions(self):
        """Test analyst role permissions."""
        from app.utils.auth import get_role_permissions
        
        permissions = get_role_permissions(UserRole.ANALYST)
        
        expected_permissions = ["read", "write", "workflow:create"]
        
        for permission in expected_permissions:
            assert permission in permissions
        
        # Should not have delete or admin permissions
        assert "delete" not in permissions
        assert "admin" not in permissions
        assert "integration:create" not in permissions
    
    def test_user_permissions(self):
        """Test user role permissions."""
        from app.utils.auth import get_role_permissions
        
        permissions = get_role_permissions(UserRole.USER)
        
        expected_permissions = ["read"]
        
        assert permissions == expected_permissions
        
        # Should not have write or admin permissions
        assert "write" not in permissions
        assert "delete" not in permissions
        assert "admin" not in permissions
    
    def test_viewer_permissions(self):
        """Test viewer role permissions."""
        from app.utils.auth import get_role_permissions
        
        permissions = get_role_permissions(UserRole.VIEWER)
        
        expected_permissions = ["read"]
        
        assert permissions == expected_permissions
        
        # Should only have read permissions
        assert "write" not in permissions
        assert "delete" not in permissions


class TestPermissionChecking:
    """Test permission checking utilities."""
    
    def test_has_permission_success(self):
        """Test permission checking when user has permission."""
        from app.utils.auth import has_permission
        
        user_permissions = ["read", "write", "integration:create"]
        
        assert has_permission(user_permissions, "read") is True
        assert has_permission(user_permissions, "write") is True
        assert has_permission(user_permissions, "integration:create") is True
    
    def test_has_permission_failure(self):
        """Test permission checking when user lacks permission."""
        from app.utils.auth import has_permission
        
        user_permissions = ["read", "write"]
        
        assert has_permission(user_permissions, "delete") is False
        assert has_permission(user_permissions, "admin") is False
        assert has_permission(user_permissions, "integration:create") is False
    
    def test_require_permission_success(self):
        """Test permission requirement when user has permission."""
        from app.utils.auth import require_permission
        
        user_permissions = ["read", "write", "admin"]
        
        # Should not raise exception
        require_permission(user_permissions, "read")
        require_permission(user_permissions, "write")
        require_permission(user_permissions, "admin")
    
    def test_require_permission_failure(self):
        """Test permission requirement when user lacks permission."""
        from app.utils.auth import require_permission
        
        user_permissions = ["read"]
        
        with pytest.raises(HTTPException) as exc_info:
            require_permission(user_permissions, "write")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in str(exc_info.value.detail)
        
        with pytest.raises(HTTPException) as exc_info:
            require_permission(user_permissions, "admin")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_require_any_permission_success(self):
        """Test requiring any of multiple permissions when user has one."""
        from app.utils.auth import require_any_permission
        
        user_permissions = ["read", "write"]
        required_permissions = ["write", "admin"]  # User has write
        
        # Should not raise exception
        require_any_permission(user_permissions, required_permissions)
    
    def test_require_any_permission_failure(self):
        """Test requiring any of multiple permissions when user has none."""
        from app.utils.auth import require_any_permission
        
        user_permissions = ["read"]
        required_permissions = ["write", "admin", "delete"]  # User has none
        
        with pytest.raises(HTTPException) as exc_info:
            require_any_permission(user_permissions, required_permissions)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in str(exc_info.value.detail)
    
    def test_require_all_permissions_success(self):
        """Test requiring all permissions when user has all."""
        from app.utils.auth import require_all_permissions
        
        user_permissions = ["read", "write", "delete", "admin"]
        required_permissions = ["read", "write", "delete"]  # User has all
        
        # Should not raise exception
        require_all_permissions(user_permissions, required_permissions)
    
    def test_require_all_permissions_failure(self):
        """Test requiring all permissions when user lacks some."""
        from app.utils.auth import require_all_permissions
        
        user_permissions = ["read", "write"]
        required_permissions = ["read", "write", "delete"]  # User lacks delete
        
        with pytest.raises(HTTPException) as exc_info:
            require_all_permissions(user_permissions, required_permissions)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in str(exc_info.value.detail)


class TestTokenUtilities:
    """Test token utility functions."""
    
    def test_extract_token_from_bearer(self):
        """Test extracting token from Bearer authorization header."""
        from app.utils.auth import extract_token_from_header
        
        # Valid Bearer token
        auth_header = "Bearer eyJhbGciOiJIUzI1NiJ9.test.token"
        token = extract_token_from_header(auth_header)
        assert token == "eyJhbGciOiJIUzI1NiJ9.test.token"
        
        # Invalid format
        with pytest.raises(HTTPException) as exc_info:
            extract_token_from_header("InvalidHeader")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Missing token
        with pytest.raises(HTTPException) as exc_info:
            extract_token_from_header("Bearer")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Empty header
        with pytest.raises(HTTPException) as exc_info:
            extract_token_from_header("")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_functionality(self):
        """Test refresh token creation and validation."""
        from app.utils.auth import create_refresh_token, verify_refresh_token
        
        user_data = {"user_id": "user-123", "username": "testuser"}
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            refresh_token = create_refresh_token(user_data)
            decoded_data = verify_refresh_token(refresh_token)
        
        assert decoded_data["user_id"] == "user-123"
        assert decoded_data["username"] == "testuser"
        assert decoded_data["token_type"] == "refresh"
    
    def test_access_token_from_refresh_token(self):
        """Test creating access token from refresh token."""
        from app.utils.auth import (
            create_refresh_token, verify_refresh_token, 
            create_access_token_from_refresh
        )
        
        user_data = {"user_id": "user-123", "username": "testuser"}
        
        with patch('app.utils.auth.JWT_SECRET_KEY', 'test-secret'):
            refresh_token = create_refresh_token(user_data)
            access_token = create_access_token_from_refresh(refresh_token)
            
            # Verify the new access token
            access_data = verify_jwt_token(access_token)
        
        assert access_data["user_id"] == "user-123"
        assert access_data["username"] == "testuser"
        assert access_data.get("token_type") != "refresh"  # Should be access token


if __name__ == "__main__":
    pytest.main([__file__])