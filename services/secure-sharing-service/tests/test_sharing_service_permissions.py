"""
Test suite for sharing service with role-based permissions integration.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.sharing_service import (
    SharingService, ShareSecurityError, ShareNotFoundError
)
from app.models.sharing_models import (
    CreateShareRequest, UpdateShareRequest, ShareListRequest,
    ShareType, SharePermission, AccessMethod, ExpirationPolicy,
    ShareRole, ShareOperation, PermissionScope, RolePermissionCheck
)
from app.core.database import SharedResource


class TestSharingServicePermissions:
    """Test cases for sharing service with role-based permissions."""

    @pytest.fixture
    def sharing_service(self):
        """Sharing service instance."""
        return SharingService()

    @pytest.fixture
    async def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.refresh = AsyncMock()
        db.add = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def sample_create_request(self):
        """Sample share creation request."""
        return CreateShareRequest(
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Test Report",
            permissions=[SharePermission.VIEW, SharePermission.DOWNLOAD],
            access_method=AccessMethod.LINK,
            requires_authentication=True,
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def sample_share(self):
        """Sample shared resource."""
        return SharedResource(
            share_id=uuid4(),
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Test Report",
            share_token="test-token-123",
            permissions=[SharePermission.VIEW.value],
            access_method=AccessMethod.LINK,
            requires_authentication=True,
            expiration_policy=ExpirationPolicy.NEVER,
            created_by="test-user-123"
        )

    async def test_create_share_with_permission(self, sharing_service, mock_db, sample_create_request):
        """Test share creation with sufficient permissions."""
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - user has permission
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="test-user-123",
                    operation=ShareOperation.CREATE,
                    scope=PermissionScope.RESOURCE_TYPE,
                    has_permission=True,
                    granted_by_role=ShareRole.CREATOR,
                    reason="Creator role allows creation"
                )
                
                # Mock token uniqueness check
                mock_db.execute.return_value.scalar_one_or_none.return_value = None
                
                result = await sharing_service.create_share(sample_create_request, "test-user-123", mock_db)
                
                # Verify share was created
                assert result.resource_type == ShareType.REPORT
                assert result.resource_name == "Test Report"
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()

    async def test_create_share_without_permission(self, sharing_service, mock_db, sample_create_request):
        """Test share creation without sufficient permissions."""
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - user lacks permission
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="test-user-123",
                    operation=ShareOperation.CREATE,
                    scope=PermissionScope.RESOURCE_TYPE,
                    has_permission=False,
                    reason="No permissions to create shares"
                )
                
                with pytest.raises(ShareSecurityError) as exc_info:
                    await sharing_service.create_share(sample_create_request, "test-user-123", mock_db)
                
                assert "Insufficient permissions" in str(exc_info.value)
                mock_db.rollback.assert_called_once()

    async def test_update_share_as_creator(self, sharing_service, mock_db, sample_share):
        """Test share update by the original creator."""
        update_request = UpdateShareRequest(
            resource_name="Updated Report Name",
            description="Updated description"
        )
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Creator updates their own share - should succeed without explicit permission check
                result = await sharing_service.update_share(
                    sample_share.share_id, update_request, "test-user-123", mock_db
                )
                
                assert result.resource_name == "Updated Report Name"
                mock_db.commit.assert_called_once()
                # Permission service should not be called for creator updating own share
                mock_rps.check_permission.assert_not_called()

    async def test_update_share_with_permission(self, sharing_service, mock_db, sample_share):
        """Test share update by non-creator with permissions."""
        update_request = UpdateShareRequest(
            resource_name="Updated Report Name"
        )
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - user has share-level update permission
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="other-user",
                    operation=ShareOperation.UPDATE,
                    scope=PermissionScope.SHARE,
                    has_permission=True,
                    granted_by_role=ShareRole.MANAGER,
                    reason="Manager role allows updates"
                )
                
                result = await sharing_service.update_share(
                    sample_share.share_id, update_request, "other-user", mock_db
                )
                
                assert result.resource_name == "Updated Report Name"
                mock_db.commit.assert_called_once()
                mock_rps.check_permission.assert_called_once()

    async def test_update_share_without_permission(self, sharing_service, mock_db, sample_share):
        """Test share update by non-creator without permissions."""
        update_request = UpdateShareRequest(
            resource_name="Updated Report Name"
        )
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - user lacks permission
                mock_rps.check_permission.side_effect = [
                    RolePermissionCheck(
                        user_id="other-user",
                        operation=ShareOperation.UPDATE,
                        scope=PermissionScope.SHARE,
                        has_permission=False,
                        reason="No share-level permissions"
                    ),
                    RolePermissionCheck(
                        user_id="other-user",
                        operation=ShareOperation.UPDATE,
                        scope=PermissionScope.RESOURCE,
                        has_permission=False,
                        reason="No resource-level permissions"
                    )
                ]
                
                with pytest.raises(ShareSecurityError) as exc_info:
                    await sharing_service.update_share(
                        sample_share.share_id, update_request, "other-user", mock_db
                    )
                
                assert "Insufficient permissions" in str(exc_info.value)
                mock_db.rollback.assert_called_once()

    async def test_delete_share_as_creator(self, sharing_service, mock_db, sample_share):
        """Test share deletion by the original creator."""
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                result = await sharing_service.delete_share(
                    sample_share.share_id, "test-user-123", mock_db
                )
                
                assert result is True
                mock_db.delete.assert_called_once_with(sample_share)
                mock_db.commit.assert_called_once()
                # Permission service should not be called for creator deleting own share
                mock_rps.check_permission.assert_not_called()

    async def test_delete_share_with_admin_permission(self, sharing_service, mock_db, sample_share):
        """Test share deletion by admin user."""
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - admin has global delete permission
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="admin-user",
                    operation=ShareOperation.DELETE,
                    scope=PermissionScope.SHARE,
                    has_permission=True,
                    granted_by_role=ShareRole.ADMIN,
                    reason="Admin role allows all operations"
                )
                
                result = await sharing_service.delete_share(
                    sample_share.share_id, "admin-user", mock_db
                )
                
                assert result is True
                mock_db.delete.assert_called_once_with(sample_share)
                mock_db.commit.assert_called_once()

    async def test_list_shares_global_permission(self, sharing_service, mock_db):
        """Test listing shares with global read permissions."""
        request = ShareListRequest(limit=10, offset=0)
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock global permission check - admin can see all shares
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="admin-user",
                    operation=ShareOperation.READ,
                    scope=PermissionScope.GLOBAL,
                    has_permission=True,
                    granted_by_role=ShareRole.ADMIN,
                    reason="Admin role allows global access"
                )
                
                # Mock database queries
                mock_db.execute.side_effect = [
                    MagicMock(scalar=MagicMock(return_value=5)),  # Count query
                    MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))  # Main query
                ]
                
                result = await sharing_service.list_shares(request, "admin-user", mock_db)
                
                assert result["total"] == 5
                # Should query all shares, not filtered by created_by
                call_args = mock_db.execute.call_args_list
                # The first call should be for count, second for actual query
                assert len(call_args) >= 2

    async def test_list_shares_resource_type_permission(self, sharing_service, mock_db):
        """Test listing shares with resource type permissions."""
        request = ShareListRequest(resource_type=ShareType.REPORT, limit=10, offset=0)
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission checks
                mock_rps.check_permission.side_effect = [
                    # Global permission check - denied
                    RolePermissionCheck(
                        user_id="user-123",
                        operation=ShareOperation.READ,
                        scope=PermissionScope.GLOBAL,
                        has_permission=False,
                        reason="No global permissions"
                    ),
                    # Resource type permission check - allowed
                    RolePermissionCheck(
                        user_id="user-123",
                        operation=ShareOperation.READ,
                        scope=PermissionScope.RESOURCE_TYPE,
                        has_permission=True,
                        granted_by_role=ShareRole.CREATOR,
                        reason="Creator role allows access to reports"
                    )
                ]
                
                # Mock database queries
                mock_db.execute.side_effect = [
                    MagicMock(scalar=MagicMock(return_value=3)),  # Count query
                    MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))  # Main query
                ]
                
                result = await sharing_service.list_shares(request, "user-123", mock_db)
                
                assert result["total"] == 3
                # Should check both global and resource-type permissions
                assert mock_rps.check_permission.call_count == 2

    async def test_list_shares_own_only(self, sharing_service, mock_db):
        """Test listing shares when user can only see their own."""
        request = ShareListRequest(limit=10, offset=0)
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission check - no special permissions
                mock_rps.check_permission.return_value = RolePermissionCheck(
                    user_id="user-123",
                    operation=ShareOperation.READ,
                    scope=PermissionScope.GLOBAL,
                    has_permission=False,
                    reason="No global permissions"
                )
                
                # Mock database queries
                mock_db.execute.side_effect = [
                    MagicMock(scalar=MagicMock(return_value=2)),  # Count query
                    MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))  # Main query
                ]
                
                result = await sharing_service.list_shares(request, "user-123", mock_db)
                
                assert result["total"] == 2
                # Should only check global permissions
                assert mock_rps.check_permission.call_count == 1

    async def test_share_not_found_error(self, sharing_service, mock_db):
        """Test share not found error in update/delete operations."""
        update_request = UpdateShareRequest(resource_name="Updated")
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup returning None
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            with pytest.raises(ShareNotFoundError):
                await sharing_service.update_share(uuid4(), update_request, "user-123", mock_db)
            
            with pytest.raises(ShareNotFoundError):
                await sharing_service.delete_share(uuid4(), "user-123", mock_db)

    async def test_permission_hierarchy_in_update(self, sharing_service, mock_db, sample_share):
        """Test permission hierarchy in update operations."""
        update_request = UpdateShareRequest(resource_name="Updated")
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            # Mock share lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_share
            
            with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                # Mock permission checks - share-level denied, resource-level allowed
                mock_rps.check_permission.side_effect = [
                    RolePermissionCheck(
                        user_id="manager-user",
                        operation=ShareOperation.UPDATE,
                        scope=PermissionScope.SHARE,
                        has_permission=False,
                        reason="No share-level permissions"
                    ),
                    RolePermissionCheck(
                        user_id="manager-user",
                        operation=ShareOperation.UPDATE,
                        scope=PermissionScope.RESOURCE,
                        has_permission=True,
                        granted_by_role=ShareRole.MANAGER,
                        reason="Manager role allows resource-level updates"
                    )
                ]
                
                result = await sharing_service.update_share(
                    sample_share.share_id, update_request, "manager-user", mock_db
                )
                
                assert result.resource_name == "Updated"
                mock_db.commit.assert_called_once()
                # Should check both share and resource level permissions
                assert mock_rps.check_permission.call_count == 2