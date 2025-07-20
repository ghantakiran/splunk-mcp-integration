"""
Test suite for role permissions API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.main import app
from app.models.sharing_models import (
    ShareRole, ShareOperation, PermissionScope, ShareType,
    RolePermissionResponse, RolePermissionCheck, UserRolePermissionsResponse
)


class TestRolePermissionsAPI:
    """Test cases for role permissions API endpoints."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def mock_user_context(self):
        """Mock user context from JWT."""
        return {
            "sub": "test-user-123",
            "user_id": "test-user-123",
            "email": "test@example.com"
        }

    @pytest.fixture
    def sample_permission_response(self):
        """Sample permission response."""
        return RolePermissionResponse(
            permission_id=uuid4(),
            user_id="target-user-456",
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            scope_id="reports",
            resource_types=[ShareType.REPORT],
            operations=[ShareOperation.CREATE, ShareOperation.READ, ShareOperation.UPDATE],
            active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            created_by="test-user-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_assign_role_permission_success(self, client, auth_headers, mock_user_context, sample_permission_response):
        """Test successful role permission assignment."""
        request_data = {
            "user_id": "target-user-456",
            "role": "creator",
            "scope": "resource_type",
            "scope_id": "reports",
            "resource_types": ["report"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.assign_role_permission.return_value = sample_permission_response
                        
                        response = client.post(
                            "/api/v1/permissions/assign",
                            json=request_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 201
                        data = response.json()
                        assert data["user_id"] == "target-user-456"
                        assert data["role"] == "creator"
                        assert data["scope"] == "resource_type"

    def test_assign_role_permission_insufficient_permissions(self, client, auth_headers, mock_user_context):
        """Test role assignment with insufficient permissions."""
        request_data = {
            "user_id": "target-user-456",
            "role": "admin",
            "scope": "global"
        }

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        from app.services.role_permission_service import InsufficientPermissionError
                        mock_rps.assign_role_permission.side_effect = InsufficientPermissionError(
                            "Insufficient permissions to assign admin role"
                        )
                        
                        response = client.post(
                            "/api/v1/permissions/assign",
                            json=request_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 403
                        assert "Insufficient permissions" in response.json()["detail"]

    def test_get_user_permissions_own(self, client, auth_headers, mock_user_context):
        """Test getting user's own permissions."""
        user_permissions = UserRolePermissionsResponse(
            user_id="test-user-123",
            permissions=[],
            effective_operations={
                "global": ["read"],
                "resource_type": ["create", "read", "update"],
                "resource": [],
                "share": []
            },
            can_create_shares=True,
            can_manage_permissions=False,
            can_view_analytics=False
        )

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.get_user_permissions.return_value = user_permissions
                        
                        response = client.get(
                            "/api/v1/permissions/user/test-user-123",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["user_id"] == "test-user-123"
                        assert data["can_create_shares"] is True
                        assert "resource_type" in data["effective_operations"]

    def test_get_user_permissions_other_user_admin(self, client, auth_headers, mock_user_context):
        """Test admin getting other user's permissions."""
        user_permissions = UserRolePermissionsResponse(
            user_id="other-user-456",
            permissions=[],
            effective_operations={},
            can_create_shares=False,
            can_manage_permissions=False,
            can_view_analytics=False
        )

        admin_permission_check = RolePermissionCheck(
            user_id="test-user-123",
            operation=ShareOperation.MANAGE_PERMISSIONS,
            scope=PermissionScope.GLOBAL,
            has_permission=True,
            granted_by_role=ShareRole.ADMIN,
            reason="Admin role"
        )

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.check_permission.return_value = admin_permission_check
                        mock_rps.get_user_permissions.return_value = user_permissions
                        
                        response = client.get(
                            "/api/v1/permissions/user/other-user-456",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["user_id"] == "other-user-456"

    def test_get_user_permissions_other_user_forbidden(self, client, auth_headers, mock_user_context):
        """Test non-admin trying to get other user's permissions."""
        permission_check = RolePermissionCheck(
            user_id="test-user-123",
            operation=ShareOperation.MANAGE_PERMISSIONS,
            scope=PermissionScope.GLOBAL,
            has_permission=False,
            reason="No admin permissions"
        )

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.check_permission.return_value = permission_check
                        
                        response = client.get(
                            "/api/v1/permissions/user/other-user-456",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 403
                        assert "Insufficient permissions" in response.json()["detail"]

    def test_check_permission_endpoint(self, client, auth_headers, mock_user_context):
        """Test permission check endpoint."""
        permission_result = RolePermissionCheck(
            user_id="test-user-123",
            operation=ShareOperation.CREATE,
            scope=PermissionScope.RESOURCE_TYPE,
            resource_type=ShareType.REPORT,
            has_permission=True,
            granted_by_role=ShareRole.CREATOR,
            granted_by_permission_id=uuid4(),
            reason="Creator role allows creation"
        )

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.check_permission.return_value = permission_result
                        
                        response = client.post(
                            "/api/v1/permissions/check",
                            params={
                                "user_id": "test-user-123",
                                "operation": "create",
                                "scope": "resource_type",
                                "resource_type": "report"
                            },
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["has_permission"] is True
                        assert data["granted_by_role"] == "creator"

    def test_revoke_role_permission(self, client, auth_headers, mock_user_context):
        """Test role permission revocation."""
        permission_id = uuid4()

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        mock_rps.revoke_role_permission.return_value = True
                        
                        response = client.delete(
                            f"/api/v1/permissions/{permission_id}",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 204

    def test_revoke_role_permission_not_found(self, client, auth_headers, mock_user_context):
        """Test revoking non-existent permission."""
        permission_id = uuid4()

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        from app.services.role_permission_service import RolePermissionError
                        mock_rps.revoke_role_permission.side_effect = RolePermissionError("Permission not found")
                        
                        response = client.delete(
                            f"/api/v1/permissions/{permission_id}",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 404
                        assert "Permission not found" in response.json()["detail"]

    def test_get_permission_matrix(self, client, auth_headers, mock_user_context):
        """Test getting permission matrix."""
        from app.models.sharing_models import SharePermissionMatrix
        
        matrix = [
            SharePermissionMatrix(
                role=ShareRole.ADMIN,
                permissions={
                    ShareOperation.CREATE: {
                        PermissionScope.GLOBAL: True,
                        PermissionScope.RESOURCE_TYPE: True,
                        PermissionScope.RESOURCE: True,
                        PermissionScope.SHARE: True
                    }
                },
                description="Full access to all operations",
                typical_use_cases=["System administrators"]
            )
        ]

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.utils.rate_limiter.rate_limit'):
                with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                    mock_rps.get_permission_matrix.return_value = matrix
                    
                    response = client.get(
                        "/api/v1/permissions/matrix",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data) == 1
                    assert data[0]["role"] == "admin"
                    assert data[0]["description"] == "Full access to all operations"

    def test_initialize_default_roles(self, client, auth_headers, mock_user_context):
        """Test default role initialization."""
        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        # Mock admin permission check
                        mock_rps.check_permission.return_value = RolePermissionCheck(
                            user_id="test-user-123",
                            operation=ShareOperation.MANAGE_PERMISSIONS,
                            scope=PermissionScope.GLOBAL,
                            has_permission=True,
                            granted_by_role=ShareRole.ADMIN,
                            reason="Admin role"
                        )
                        mock_rps.initialize_default_roles.return_value = None
                        
                        response = client.post(
                            "/api/v1/permissions/initialize",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "initialized successfully" in data["message"]

    def test_bulk_assign_roles(self, client, auth_headers, mock_user_context):
        """Test bulk role assignment."""
        from app.models.sharing_models import BulkRoleOperation
        
        request_data = {
            "operation": "assign",
            "user_ids": ["user1", "user2", "user3"],
            "role": "creator",
            "scope": "resource_type",
            "scope_id": "reports"
        }

        bulk_result = BulkRoleOperation(
            operation="assign",
            user_ids=["user1", "user2", "user3"],
            role=ShareRole.CREATOR,
            scope=PermissionScope.RESOURCE_TYPE,
            scope_id="reports",
            successful_operations=3,
            failed_operations=0,
            errors=[]
        )

        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit'):
                    with patch('app.services.role_permission_service.role_permission_service') as mock_rps:
                        # Mock permission check for bulk operations
                        mock_rps.check_permission.return_value = RolePermissionCheck(
                            user_id="test-user-123",
                            operation=ShareOperation.MANAGE_PERMISSIONS,
                            scope=PermissionScope.RESOURCE_TYPE,
                            has_permission=True,
                            granted_by_role=ShareRole.ADMIN,
                            reason="Admin role"
                        )
                        
                        # Mock successful assignments
                        mock_rps.assign_role_permission.return_value = AsyncMock()
                        
                        response = client.post(
                            "/api/v1/permissions/bulk-assign",
                            json=request_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["successful_operations"] == 3
                        assert data["failed_operations"] == 0

    def test_get_available_roles(self, client, auth_headers, mock_user_context):
        """Test getting available roles."""
        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.utils.rate_limiter.rate_limit'):
                response = client.get(
                    "/api/v1/permissions/roles",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 5  # All five roles
                
                # Check that all roles are present
                role_names = [role["role"] for role in data]
                assert "admin" in role_names
                assert "manager" in role_names
                assert "creator" in role_names
                assert "member" in role_names
                assert "viewer" in role_names
                
                # Check role structure
                admin_role = next(role for role in data if role["role"] == "admin")
                assert admin_role["priority"] == 100
                assert "Full access" in admin_role["description"]
                assert len(admin_role["operations"]) > 0
                assert len(admin_role["scopes"]) > 0

    def test_unauthorized_request(self, client):
        """Test request without authentication."""
        response = client.get("/api/v1/permissions/roles")
        assert response.status_code == 401

    def test_invalid_user_context(self, client, auth_headers):
        """Test request with invalid user context."""
        invalid_context = {}  # Missing user ID
        
        with patch('app.utils.auth.get_current_user', return_value=invalid_context):
            response = client.get(
                "/api/v1/permissions/roles",
                headers=auth_headers
            )
            # Should handle gracefully or return 401
            assert response.status_code in [401, 422]

    def test_rate_limiting(self, client, auth_headers, mock_user_context):
        """Test rate limiting on endpoints."""
        with patch('app.utils.auth.get_current_user', return_value=mock_user_context):
            with patch('app.core.database.get_database'):
                with patch('app.utils.rate_limiter.rate_limit') as mock_rate_limit:
                    from fastapi import HTTPException
                    mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")
                    
                    response = client.get(
                        "/api/v1/permissions/user/test-user-123",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 429
                    assert "Rate limit exceeded" in response.json()["detail"]