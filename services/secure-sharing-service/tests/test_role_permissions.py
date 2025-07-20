"""
Test suite for role-based permission system.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.role_permission_service import (
    role_permission_service, RolePermissionError, InsufficientPermissionError
)
from app.models.sharing_models import (
    ShareRole, ShareOperation, PermissionScope, ShareType,
    CreateRolePermissionRequest, RolePermissionCheck
)
from app.core.database import ShareRolePermissions, ShareRoleDefinitions


class TestRolePermissionService:
    """Test cases for role permission service."""

    @pytest.fixture
    async def mock_db(self):
        """Mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.refresh = AsyncMock()
        db.add = AsyncMock()
        return db

    @pytest.fixture
    def sample_permission_request(self):
        """Sample permission request for testing."""
        return CreateRolePermissionRequest(
            user_id="test-user-123",
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            scope_id="reports",
            resource_types=[ShareType.REPORT],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )

    @pytest.fixture
    def mock_role_definition(self):
        """Mock role definition."""
        return ShareRoleDefinitions(
            definition_id=uuid4(),
            role=ShareRole.CREATOR,
            display_name="Creator",
            description="Create and manage own shares",
            default_operations=[
                ShareOperation.CREATE.value,
                ShareOperation.READ.value,
                ShareOperation.UPDATE.value,
                ShareOperation.DELETE.value
            ],
            allowed_scopes=[
                PermissionScope.RESOURCE.value,
                PermissionScope.SHARE.value
            ],
            priority=60,
            is_system_role=True,
            is_assignable=True,
            created_by="admin"
        )

    @pytest.fixture
    def mock_user_permission(self):
        """Mock user permission."""
        return ShareRolePermissions(
            permission_id=uuid4(),
            user_id="test-user-123",
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            scope_id="reports",
            resource_types=[ShareType.REPORT.value],
            operations=[
                ShareOperation.CREATE.value,
                ShareOperation.READ.value,
                ShareOperation.UPDATE.value,
                ShareOperation.DELETE.value
            ],
            active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            created_by="admin"
        )

    async def test_initialize_default_roles(self, mock_db):
        """Test default role initialization."""
        # Mock existing role check
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        await role_permission_service.initialize_default_roles("admin-user", mock_db)
        
        # Verify role definitions were added
        assert mock_db.add.call_count == len(role_permission_service.DEFAULT_ROLE_PERMISSIONS)
        mock_db.commit.assert_called_once()

    async def test_assign_role_permission_success(self, mock_db, sample_permission_request, mock_role_definition):
        """Test successful role permission assignment."""
        # Mock permission check (admin has permission)
        with patch.object(role_permission_service, 'check_permission') as mock_check:
            mock_check.return_value = RolePermissionCheck(
                user_id="admin-user",
                operation=ShareOperation.MANAGE_PERMISSIONS,
                scope=PermissionScope.RESOURCE_TYPE,
                has_permission=True,
                granted_by_role=ShareRole.ADMIN,
                reason="Admin role"
            )
            
            # Mock role definition lookup
            with patch.object(role_permission_service, '_get_role_definition') as mock_get_role:
                mock_get_role.return_value = mock_role_definition
                
                # Mock existing permission check (no existing permission)
                mock_db.execute.return_value.scalar_one_or_none.return_value = None
                
                # Mock audit logging
                with patch.object(role_permission_service, '_log_permission_audit') as mock_audit:
                    result = await role_permission_service.assign_role_permission(
                        sample_permission_request, "admin-user", mock_db
                    )
                    
                    # Verify result
                    assert result.user_id == "test-user-123"
                    assert result.role == ShareRole.CREATOR
                    assert result.scope == PermissionScope.RESOURCE_TYPE
                    
                    # Verify database operations
                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called_once()
                    mock_audit.assert_called_once()

    async def test_assign_role_permission_insufficient_permissions(self, mock_db, sample_permission_request):
        """Test role assignment with insufficient permissions."""
        # Mock permission check (user lacks permission)
        with patch.object(role_permission_service, 'check_permission') as mock_check:
            mock_check.return_value = RolePermissionCheck(
                user_id="regular-user",
                operation=ShareOperation.MANAGE_PERMISSIONS,
                scope=PermissionScope.RESOURCE_TYPE,
                has_permission=False,
                reason="No permissions"
            )
            
            with pytest.raises(InsufficientPermissionError):
                await role_permission_service.assign_role_permission(
                    sample_permission_request, "regular-user", mock_db
                )

    async def test_check_permission_with_matching_role(self, mock_db, mock_user_permission):
        """Test permission check with matching role."""
        # Mock database query returning user permission
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_user_permission]
        
        # Mock audit logging
        with patch.object(role_permission_service, '_log_permission_audit') as mock_audit:
            result = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.CREATE,
                PermissionScope.RESOURCE_TYPE,
                resource_type=ShareType.REPORT,
                db=mock_db
            )
            
            # Verify permission granted
            assert result.has_permission is True
            assert result.granted_by_role == ShareRole.CREATOR
            assert result.user_id == "test-user-123"
            
            # Verify audit log
            mock_audit.assert_called_once()

    async def test_check_permission_no_matching_role(self, mock_db):
        """Test permission check with no matching role."""
        # Mock database query returning no permissions
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        # Mock audit logging
        with patch.object(role_permission_service, '_log_permission_audit') as mock_audit:
            result = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.CREATE,
                PermissionScope.RESOURCE_TYPE,
                resource_type=ShareType.REPORT,
                db=mock_db
            )
            
            # Verify permission denied
            assert result.has_permission is False
            assert result.granted_by_role is None
            assert "No matching permissions" in result.reason
            
            # Verify audit log
            mock_audit.assert_called_once()

    async def test_permission_scope_hierarchy(self, mock_db):
        """Test permission scope hierarchy (global > resource_type > resource > share)."""
        # Test global permission allows all scopes
        global_permission = ShareRolePermissions(
            permission_id=uuid4(),
            user_id="admin-user",
            role=ShareRole.ADMIN,
            scope=PermissionScope.GLOBAL,
            scope_id=None,
            operations=[ShareOperation.READ.value],
            active=True,
            created_by="system"
        )
        
        # Mock database query
        mock_db.execute.return_value.scalars.return_value.all.return_value = [global_permission]
        
        with patch.object(role_permission_service, '_log_permission_audit'):
            # Test access to specific share
            result = await role_permission_service.check_permission(
                "admin-user",
                ShareOperation.READ,
                PermissionScope.SHARE,
                scope_id="share-123",
                db=mock_db
            )
            
            assert result.has_permission is True
            assert result.granted_by_role == ShareRole.ADMIN

    async def test_get_user_permissions(self, mock_db, mock_user_permission):
        """Test getting user permissions."""
        # Mock database query
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_user_permission]
        
        result = await role_permission_service.get_user_permissions("test-user-123", db=mock_db)
        
        # Verify result structure
        assert result.user_id == "test-user-123"
        assert len(result.permissions) == 1
        assert result.permissions[0].role == ShareRole.CREATOR
        
        # Verify effective operations
        assert PermissionScope.RESOURCE_TYPE.value in result.effective_operations
        operations = result.effective_operations[PermissionScope.RESOURCE_TYPE.value]
        assert ShareOperation.CREATE.value in operations
        assert ShareOperation.READ.value in operations

    async def test_revoke_role_permission(self, mock_db, mock_user_permission):
        """Test role permission revocation."""
        permission_id = mock_user_permission.permission_id
        
        # Mock permission lookup
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user_permission
        
        # Mock permission check for revocation
        with patch.object(role_permission_service, 'check_permission') as mock_check:
            mock_check.return_value = RolePermissionCheck(
                user_id="admin-user",
                operation=ShareOperation.MANAGE_PERMISSIONS,
                scope=PermissionScope.RESOURCE_TYPE,
                has_permission=True,
                granted_by_role=ShareRole.ADMIN,
                reason="Admin role"
            )
            
            result = await role_permission_service.revoke_role_permission(
                permission_id, "admin-user", mock_db
            )
            
            # Verify permission was deactivated
            assert result is True
            assert mock_user_permission.active is False
            mock_db.commit.assert_called_once()

    async def test_permission_expiration(self, mock_db):
        """Test that expired permissions are not considered."""
        # Create expired permission
        expired_permission = ShareRolePermissions(
            permission_id=uuid4(),
            user_id="test-user-123",
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            scope_id="reports",
            operations=[ShareOperation.CREATE.value],
            active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            created_by="admin"
        )
        
        # Mock database query returning expired permission
        mock_db.execute.return_value.scalars.return_value.all.return_value = [expired_permission]
        
        with patch.object(role_permission_service, '_log_permission_audit'):
            result = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.CREATE,
                PermissionScope.RESOURCE_TYPE,
                db=mock_db
            )
            
            # Should deny permission due to expiration
            assert result.has_permission is False

    async def test_get_permission_matrix(self):
        """Test permission matrix generation."""
        matrix = await role_permission_service.get_permission_matrix()
        
        # Verify all roles are included
        roles = [item.role for item in matrix]
        assert ShareRole.ADMIN in roles
        assert ShareRole.MANAGER in roles
        assert ShareRole.CREATOR in roles
        assert ShareRole.MEMBER in roles
        assert ShareRole.VIEWER in roles
        
        # Verify admin has all permissions
        admin_item = next(item for item in matrix if item.role == ShareRole.ADMIN)
        assert admin_item.permissions[ShareOperation.MANAGE_PERMISSIONS][PermissionScope.GLOBAL] is True
        
        # Verify viewer has limited permissions
        viewer_item = next(item for item in matrix if item.role == ShareRole.VIEWER)
        assert viewer_item.permissions[ShareOperation.READ][PermissionScope.SHARE] is True
        assert viewer_item.permissions[ShareOperation.CREATE][PermissionScope.GLOBAL] is False

    async def test_role_priority_handling(self, mock_db):
        """Test that higher priority roles take precedence."""
        # User has both VIEWER and ADMIN roles
        viewer_permission = ShareRolePermissions(
            permission_id=uuid4(),
            user_id="test-user-123",
            role=ShareRole.VIEWER,  # Lower priority
            scope=PermissionScope.GLOBAL,
            operations=[ShareOperation.READ.value],
            active=True,
            created_by="admin"
        )
        
        admin_permission = ShareRolePermissions(
            permission_id=uuid4(),
            user_id="test-user-123",
            role=ShareRole.ADMIN,  # Higher priority
            scope=PermissionScope.GLOBAL,
            operations=[op.value for op in ShareOperation],
            active=True,
            created_by="admin"
        )
        
        # Mock database query returning both permissions
        mock_db.execute.return_value.scalars.return_value.all.return_value = [viewer_permission, admin_permission]
        
        with patch.object(role_permission_service, '_log_permission_audit'):
            result = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.MANAGE_PERMISSIONS,
                PermissionScope.GLOBAL,
                db=mock_db
            )
            
            # Should grant permission based on ADMIN role (higher priority)
            assert result.has_permission is True
            assert result.granted_by_role == ShareRole.ADMIN

    async def test_resource_type_filtering(self, mock_db):
        """Test resource type filtering in permissions."""
        # Permission limited to REPORT resource type
        permission = ShareRolePermissions(
            permission_id=uuid4(),
            user_id="test-user-123",
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            resource_types=[ShareType.REPORT.value],
            operations=[ShareOperation.CREATE.value],
            active=True,
            created_by="admin"
        )
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = [permission]
        
        with patch.object(role_permission_service, '_log_permission_audit'):
            # Test access to REPORT - should be allowed
            result1 = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.CREATE,
                PermissionScope.RESOURCE_TYPE,
                resource_type=ShareType.REPORT,
                db=mock_db
            )
            assert result1.has_permission is True
            
            # Test access to DASHBOARD - should be denied
            result2 = await role_permission_service.check_permission(
                "test-user-123",
                ShareOperation.CREATE,
                PermissionScope.RESOURCE_TYPE,
                resource_type=ShareType.DASHBOARD,
                db=mock_db
            )
            assert result2.has_permission is False