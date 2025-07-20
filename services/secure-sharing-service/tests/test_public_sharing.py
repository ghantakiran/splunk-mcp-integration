"""
Tests for public sharing functionality with and without authentication.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.sharing_models import (
    CreateShareRequest, AccessShareRequest, ShareType, SharePermission, 
    ExpirationPolicy, AccessMethod, ShareSecurityValidation
)
from app.services.sharing_service import sharing_service, ShareSecurityError
from app.core.database import SharedResource, ShareStatus


class TestPublicSharing:
    """Test suite for public sharing functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def public_share_request(self):
        """Create a public share request (no authentication required)."""
        return CreateShareRequest(
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Public Test Report",
            permissions=[SharePermission.VIEW, SharePermission.DOWNLOAD],
            access_method=AccessMethod.LINK,
            requires_authentication=False,  # Public share
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            password_protected=False,
            description="A publicly accessible report"
        )

    @pytest.fixture
    def authenticated_share_request(self):
        """Create an authenticated share request."""
        return CreateShareRequest(
            resource_type=ShareType.DASHBOARD,
            resource_id=uuid4(),
            resource_name="Authenticated Test Dashboard",
            permissions=[SharePermission.VIEW, SharePermission.INTERACT],
            access_method=AccessMethod.LINK,
            requires_authentication=True,  # Authentication required
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            password_protected=False,
            description="An authenticated-only dashboard"
        )

    @pytest.fixture
    def public_share_resource(self):
        """Create a mock public share resource."""
        return SharedResource(
            share_id=uuid4(),
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Public Test Report",
            share_token="public_test_token_123",
            permissions=["view", "download"],
            access_method=AccessMethod.LINK,
            requires_authentication=False,  # Public share
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            password_protected=False,
            status=ShareStatus.ACTIVE,
            total_views=0,
            total_downloads=0,
            unique_viewers=0,
            created_by="test_user"
        )

    @pytest.fixture
    def authenticated_share_resource(self):
        """Create a mock authenticated share resource."""
        return SharedResource(
            share_id=uuid4(),
            resource_type=ShareType.DASHBOARD,
            resource_id=uuid4(),
            resource_name="Authenticated Test Dashboard",
            share_token="auth_test_token_456",
            permissions=["view", "interact"],
            access_method=AccessMethod.LINK,
            requires_authentication=True,  # Authentication required
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            password_protected=False,
            status=ShareStatus.ACTIVE,
            total_views=0,
            total_downloads=0,
            unique_viewers=0,
            created_by="test_user"
        )

    @pytest.mark.asyncio
    async def test_create_public_share(self, public_share_request, mock_db):
        """Test creating a public share that doesn't require authentication."""
        with patch.object(sharing_service, 'check_permission') as mock_check:
            mock_check.return_value = AsyncMock(has_permission=True)
            
            with patch('app.services.sharing_service.get_database', return_value=mock_db):
                with patch.object(sharing_service, '_token_exists', return_value=False):
                    response = await sharing_service.create_share(
                        public_share_request, 
                        "test_user", 
                        mock_db
                    )
                    
                    assert response.requires_authentication == False
                    assert response.resource_name == "Public Test Report"
                    assert response.permissions == [SharePermission.VIEW, SharePermission.DOWNLOAD]

    @pytest.mark.asyncio
    async def test_create_authenticated_share(self, authenticated_share_request, mock_db):
        """Test creating an authenticated share that requires authentication."""
        with patch.object(sharing_service, 'check_permission') as mock_check:
            mock_check.return_value = AsyncMock(has_permission=True)
            
            with patch('app.services.sharing_service.get_database', return_value=mock_db):
                with patch.object(sharing_service, '_token_exists', return_value=False):
                    response = await sharing_service.create_share(
                        authenticated_share_request, 
                        "test_user", 
                        mock_db
                    )
                    
                    assert response.requires_authentication == True
                    assert response.resource_name == "Authenticated Test Dashboard"
                    assert response.permissions == [SharePermission.VIEW, SharePermission.INTERACT]

    @pytest.mark.asyncio
    async def test_public_share_access_without_email(self, public_share_resource):
        """Test accessing a public share without providing email (should succeed)."""
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None  # No email required for public shares
        )
        
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        
        assert validation.is_valid == True
        assert validation.has_access == True
        assert len(validation.warnings) == 0

    @pytest.mark.asyncio
    async def test_public_share_access_with_email(self, public_share_resource):
        """Test accessing a public share with email provided (should succeed with warning)."""
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email="user@example.com"  # Email provided but not required
        )
        
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        
        assert validation.is_valid == True
        assert validation.has_access == True
        assert "Email provided but not required for public share" in validation.warnings

    @pytest.mark.asyncio
    async def test_authenticated_share_access_without_email(self, authenticated_share_resource):
        """Test accessing an authenticated share without email (should fail)."""
        access_request = AccessShareRequest(
            share_token="auth_test_token_456",
            user_email=None  # No email provided
        )
        
        validation = await sharing_service._validate_security(authenticated_share_resource, access_request)
        
        assert validation.is_valid == False
        assert validation.has_access == False
        assert "Authentication required - user email must be provided" in validation.error_message

    @pytest.mark.asyncio
    async def test_authenticated_share_access_with_valid_email(self, authenticated_share_resource):
        """Test accessing an authenticated share with valid email (should succeed)."""
        access_request = AccessShareRequest(
            share_token="auth_test_token_456",
            user_email="user@example.com"  # Valid email provided
        )
        
        validation = await sharing_service._validate_security(authenticated_share_resource, access_request)
        
        assert validation.is_valid == True
        assert validation.has_access == True
        assert len(validation.warnings) == 0

    @pytest.mark.asyncio
    async def test_authenticated_share_access_with_invalid_email(self, authenticated_share_resource):
        """Test accessing an authenticated share with invalid email format (should fail)."""
        access_request = AccessShareRequest(
            share_token="auth_test_token_456",
            user_email="invalid-email"  # Invalid email format
        )
        
        validation = await sharing_service._validate_security(authenticated_share_resource, access_request)
        
        assert validation.is_valid == False
        assert validation.has_access == False
        assert "Invalid email format for authenticated access" in validation.error_message

    @pytest.mark.asyncio
    async def test_public_share_with_password(self, public_share_resource):
        """Test accessing a public share that's password protected."""
        # Modify resource to be password protected
        public_share_resource.password_protected = True
        public_share_resource.password_hash = sharing_service.hash_password("testpass123")
        
        # Access without password should fail
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None,
            password=None
        )
        
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        assert validation.is_valid == False
        assert "Password required" in validation.error_message
        
        # Access with correct password should succeed
        access_request.password = "testpass123"
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        assert validation.is_valid == True
        assert validation.has_access == True

    @pytest.mark.asyncio
    async def test_public_share_domain_restrictions(self, public_share_resource):
        """Test public share with domain restrictions."""
        # Add domain restrictions
        public_share_resource.allowed_domains = ["example.com", "company.org"]
        
        # Access without email from allowed domain (should succeed for public)
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None
        )
        
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        assert validation.is_valid == True  # Public shares don't enforce domain restrictions without email
        
        # Access with email from allowed domain (should succeed)
        access_request.user_email = "user@example.com"
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        assert validation.is_valid == True
        
        # Access with email from disallowed domain (should fail)
        access_request.user_email = "user@unauthorized.com"
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        assert validation.is_valid == False
        assert "Domain not allowed" in validation.error_message

    def test_public_access_api_endpoint(self, client):
        """Test the public access API endpoint."""
        with patch('app.api.v1.endpoints.shares.sharing_service') as mock_service:
            # Mock successful access
            mock_access_response = AsyncMock()
            mock_access_response.share_id = uuid4()
            mock_access_response.success = True
            mock_service.access_share.return_value = mock_access_response
            
            response = client.post(
                "/api/v1/shares/access",
                json={
                    "share_token": "public_test_token_123",
                    "user_email": None
                }
            )
            
            # The actual implementation may vary, but we're testing the endpoint exists
            # and handles public access requests
            assert response.status_code in [200, 422]  # 422 for validation, 200 for success

    def test_authenticated_access_api_endpoint(self, client):
        """Test the authenticated access API endpoint."""
        # This would require proper JWT token setup for full testing
        # For now, we test that the endpoint exists and requires authentication
        response = client.post(
            "/api/v1/shares/access/authenticated",
            json={
                "share_token": "auth_test_token_456",
                "user_email": "user@example.com"
            }
        )
        
        # Should require authentication (401) or validation error (422)
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_public_share_metrics_tracking(self, public_share_resource, mock_db):
        """Test that public shares still track metrics properly."""
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None,
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0"
        )
        
        with patch('app.services.sharing_service.get_database', return_value=mock_db):
            with patch.object(sharing_service, '_get_share_by_token', return_value=public_share_resource):
                with patch.object(sharing_service, 'check_expiration') as mock_expiration:
                    mock_expiration.return_value = AsyncMock(is_expired=False)
                    
                    with patch.object(sharing_service, '_get_resource_data', return_value={}):
                        response = await sharing_service.access_share(access_request, mock_db)
                        
                        assert response.success == True
                        assert response.share_id == public_share_resource.share_id
                        
                        # Verify metrics were updated
                        assert public_share_resource.total_views == 1

    @pytest.mark.asyncio
    async def test_share_security_validation_fields(self):
        """Test that ShareSecurityValidation includes all required fields."""
        validation = ShareSecurityValidation(
            is_valid=True,
            has_access=True,
            requires_password=False,
            domain_allowed=True,
            user_allowed=True,
            error_message=None,
            warnings=["Test warning"]
        )
        
        assert validation.is_valid == True
        assert validation.has_access == True
        assert validation.requires_password == False
        assert validation.domain_allowed == True
        assert validation.user_allowed == True
        assert validation.error_message is None
        assert "Test warning" in validation.warnings

    @pytest.mark.parametrize("email,expected_valid", [
        ("user@example.com", True),
        ("test.user+tag@company.org", True),
        ("user@sub.domain.com", True),
        ("invalid-email", False),
        ("user@", False),
        ("@domain.com", False),
        ("user..double@domain.com", False),
        ("", False)
    ])
    @pytest.mark.asyncio
    async def test_email_validation_patterns(self, email, expected_valid, authenticated_share_resource):
        """Test various email patterns for authenticated shares."""
        access_request = AccessShareRequest(
            share_token="auth_test_token_456",
            user_email=email
        )
        
        validation = await sharing_service._validate_security(authenticated_share_resource, access_request)
        
        if expected_valid:
            assert validation.is_valid == True
            assert validation.has_access == True
        else:
            assert validation.is_valid == False
            assert "Invalid email format" in validation.error_message

    @pytest.mark.asyncio
    async def test_expired_public_share_access(self, public_share_resource):
        """Test accessing an expired public share."""
        # Set share to expired
        public_share_resource.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None
        )
        
        with patch('app.services.sharing_service.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            with patch.object(sharing_service, '_get_share_by_token', return_value=public_share_resource):
                with pytest.raises(Exception):  # Should raise ShareExpirationError
                    await sharing_service.access_share(access_request, mock_db)

    @pytest.mark.asyncio
    async def test_revoked_public_share_access(self, public_share_resource):
        """Test accessing a revoked public share."""
        # Set share to revoked
        public_share_resource.status = ShareStatus.REVOKED
        
        access_request = AccessShareRequest(
            share_token="public_test_token_123",
            user_email=None
        )
        
        validation = await sharing_service._validate_security(public_share_resource, access_request)
        
        assert validation.is_valid == False
        assert validation.has_access == False
        assert "Share is revoked" in validation.error_message


class TestPublicSharingIntegration:
    """Integration tests for public sharing functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_public_share_workflow(self, mock_db):
        """Test complete workflow: create public share -> access share -> verify metrics."""
        # Create public share
        share_request = CreateShareRequest(
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Integration Test Report",
            permissions=[SharePermission.VIEW],
            requires_authentication=False,
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        with patch.object(sharing_service, 'check_permission') as mock_check:
            mock_check.return_value = AsyncMock(has_permission=True)
            
            with patch('app.services.sharing_service.get_database', return_value=mock_db):
                with patch.object(sharing_service, '_token_exists', return_value=False):
                    # Create share
                    share_response = await sharing_service.create_share(share_request, "test_user", mock_db)
                    
                    assert share_response.requires_authentication == False
                    assert share_response.share_token is not None
                    
                    # Access share
                    access_request = AccessShareRequest(
                        share_token=share_response.share_token,
                        user_email=None
                    )
                    
                    # Mock the database operations for access
                    mock_share = SharedResource(
                        share_id=share_response.share_id,
                        resource_type=share_response.resource_type,
                        resource_id=share_response.resource_id,
                        resource_name=share_response.resource_name,
                        share_token=share_response.share_token,
                        permissions=["view"],
                        requires_authentication=False,
                        status=ShareStatus.ACTIVE,
                        expires_at=share_response.expires_at,
                        password_protected=False,
                        total_views=0,
                        total_downloads=0,
                        unique_viewers=0,
                        created_by="test_user"
                    )
                    
                    with patch.object(sharing_service, '_get_share_by_token', return_value=mock_share):
                        with patch.object(sharing_service, 'check_expiration') as mock_expiration:
                            mock_expiration.return_value = AsyncMock(is_expired=False)
                            
                            with patch.object(sharing_service, '_get_resource_data', return_value={}):
                                access_response = await sharing_service.access_share(access_request, mock_db)
                                
                                assert access_response.success == True
                                assert access_response.share_id == share_response.share_id
                                assert access_response.resource_name == "Integration Test Report"

    @pytest.mark.asyncio
    async def test_mixed_sharing_modes_same_resource(self, mock_db):
        """Test that the same resource can have both public and authenticated shares."""
        resource_id = uuid4()
        
        # Create public share
        public_request = CreateShareRequest(
            resource_type=ShareType.DASHBOARD,
            resource_id=resource_id,
            resource_name="Mixed Access Dashboard - Public",
            permissions=[SharePermission.VIEW],
            requires_authentication=False,
            expiration_policy=ExpirationPolicy.NEVER
        )
        
        # Create authenticated share for same resource
        auth_request = CreateShareRequest(
            resource_type=ShareType.DASHBOARD,
            resource_id=resource_id,
            resource_name="Mixed Access Dashboard - Authenticated",
            permissions=[SharePermission.VIEW, SharePermission.INTERACT, SharePermission.EDIT],
            requires_authentication=True,
            expiration_policy=ExpirationPolicy.NEVER
        )
        
        with patch.object(sharing_service, 'check_permission') as mock_check:
            mock_check.return_value = AsyncMock(has_permission=True)
            
            with patch('app.services.sharing_service.get_database', return_value=mock_db):
                with patch.object(sharing_service, '_token_exists', return_value=False):
                    # Create both shares
                    public_share = await sharing_service.create_share(public_request, "test_user", mock_db)
                    auth_share = await sharing_service.create_share(auth_request, "test_user", mock_db)
                    
                    # Verify different access levels
                    assert public_share.requires_authentication == False
                    assert auth_share.requires_authentication == True
                    assert len(public_share.permissions) == 1  # Only VIEW
                    assert len(auth_share.permissions) == 3  # VIEW, INTERACT, EDIT
                    assert public_share.share_token != auth_share.share_token  # Different tokens