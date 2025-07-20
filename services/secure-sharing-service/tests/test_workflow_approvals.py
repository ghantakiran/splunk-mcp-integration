"""
Tests for workflow approval functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.sharing_models import (
    CreateApprovalWorkflowRequest, CreateApprovalRequestRequest, ApprovalActionRequest,
    CreateShareRequest, ApprovalTrigger, ApprovalLevel, ApprovalAction, WorkflowStatus,
    ShareType, SharePermission, AccessMethod, ExpirationPolicy
)
from app.services.workflow_approval_service import workflow_approval_service
from app.core.database import ShareApprovalWorkflow, ShareApprovalRequest, ShareApprovalAction


class TestWorkflowApprovalService:
    """Test suite for workflow approval service functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_workflow_request(self):
        """Create sample workflow creation request."""
        return CreateApprovalWorkflowRequest(
            name="Test Security Review Workflow",
            description="Security review for sensitive data shares",
            triggers=[ApprovalTrigger.SENSITIVE_DATA, ApprovalTrigger.SECURITY_REVIEW],
            approval_level=ApprovalLevel.SINGLE,
            required_approvers=["security_admin", "data_owner"],
            expires_after=72,
            require_reason=True,
            notify_approvers=True,
            tags=["security", "data-protection"]
        )

    @pytest.fixture
    def sample_share_request(self):
        """Create sample share request."""
        return CreateShareRequest(
            resource_type=ShareType.REPORT,
            resource_id=uuid4(),
            resource_name="Sensitive Security Report",
            permissions=[SharePermission.VIEW, SharePermission.DOWNLOAD],
            access_method=AccessMethod.LINK,
            requires_authentication=True,
            expiration_policy=ExpirationPolicy.AFTER_TIME,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            description="Contains sensitive security data"
        )

    @pytest.fixture
    def sample_approval_request(self, sample_share_request):
        """Create sample approval request."""
        return CreateApprovalRequestRequest(
            share_request=sample_share_request,
            workflow_id=uuid4(),
            justification="Need to share security findings with stakeholders",
            priority="high",
            business_case="Required for incident response",
            risk_assessment="Medium risk - contains sensitive data"
        )

    @pytest.mark.asyncio
    async def test_create_workflow(self, sample_workflow_request, mock_db):
        """Test workflow creation."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_permission_service:
                # Mock permission check
                mock_permission_check = AsyncMock()
                mock_permission_check.has_permission = True
                mock_permission_service.check_permission.return_value = mock_permission_check

                # Mock database operations
                mock_workflow = MagicMock()
                mock_workflow.workflow_id = uuid4()
                mock_workflow.name = sample_workflow_request.name
                mock_workflow.is_active = True
                mock_workflow.triggers = [trigger.value for trigger in sample_workflow_request.triggers]
                mock_workflow.created_at = datetime.now(timezone.utc)
                mock_workflow.updated_at = datetime.now(timezone.utc)

                mock_db.add = MagicMock()
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                # Mock refresh to set workflow attributes
                def mock_refresh_side_effect(record):
                    for attr, value in vars(mock_workflow).items():
                        if not attr.startswith('_'):
                            setattr(record, attr, value)

                mock_db.refresh.side_effect = mock_refresh_side_effect

                # Test workflow creation
                result = await workflow_approval_service.create_workflow(
                    sample_workflow_request, "admin_user", mock_db
                )

                # Verify database operations
                assert mock_db.add.called
                assert mock_db.commit.call_count >= 1
                assert mock_db.refresh.called

                # Verify result
                assert result.name == sample_workflow_request.name
                assert len(result.triggers) == len(sample_workflow_request.triggers)
                assert result.approval_level == sample_workflow_request.approval_level

    @pytest.mark.asyncio
    async def test_create_workflow_insufficient_permissions(self, sample_workflow_request, mock_db):
        """Test workflow creation with insufficient permissions."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_permission_service:
                # Mock permission check failure
                mock_permission_check = AsyncMock()
                mock_permission_check.has_permission = False
                mock_permission_service.check_permission.return_value = mock_permission_check

                # Test workflow creation should fail
                with pytest.raises(Exception) as exc_info:
                    await workflow_approval_service.create_workflow(
                        sample_workflow_request, "regular_user", mock_db
                    )

                assert "Insufficient permissions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_approval_request(self, sample_approval_request, mock_db):
        """Test approval request creation."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Mock workflow lookup
            mock_workflow = MagicMock()
            mock_workflow.workflow_id = sample_approval_request.workflow_id
            mock_workflow.is_active = True
            mock_workflow.auto_approve_after = None
            mock_workflow.expires_after = 72
            mock_workflow.required_approvers = ["security_admin", "data_owner"]
            mock_workflow.optional_approvers = None
            mock_workflow.approval_level = ApprovalLevel.SINGLE
            mock_workflow.allow_self_approval = False
            mock_workflow.total_requests = 0
            mock_workflow.pending_requests = 0

            workflow_result = AsyncMock()
            workflow_result.scalar_one_or_none.return_value = mock_workflow

            # Mock approval request creation
            mock_approval_request = MagicMock()
            mock_approval_request.request_id = uuid4()
            mock_approval_request.workflow_id = sample_approval_request.workflow_id
            mock_approval_request.status = WorkflowStatus.PENDING
            mock_approval_request.current_approvers = ["security_admin", "data_owner"]
            mock_approval_request.created_at = datetime.now(timezone.utc)
            mock_approval_request.updated_at = datetime.now(timezone.utc)

            mock_db.execute.return_value = workflow_result
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock refresh to set approval request attributes
            def mock_refresh_side_effect(record):
                for attr, value in vars(mock_approval_request).items():
                    if not attr.startswith('_'):
                        setattr(record, attr, value)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            # Mock notification sending
            with patch.object(workflow_approval_service, '_send_approval_notifications'):
                # Test approval request creation
                result = await workflow_approval_service.create_approval_request(
                    sample_approval_request, "requester_user", mock_db
                )

                # Verify database operations
                assert mock_db.add.called
                assert mock_db.commit.call_count >= 1
                assert mock_db.refresh.called

                # Verify result
                assert result.workflow_id == sample_approval_request.workflow_id
                assert result.status == WorkflowStatus.PENDING
                assert len(result.current_approvers) > 0

    @pytest.mark.asyncio
    async def test_take_approval_action_approve(self, mock_db):
        """Test taking approval action - approve."""
        request_id = uuid4()
        
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Mock approval request lookup
            mock_approval_request = MagicMock()
            mock_approval_request.request_id = request_id
            mock_approval_request.status = WorkflowStatus.PENDING
            mock_approval_request.current_approvers = ["security_admin", "data_owner"]
            mock_approval_request.pending_approvals = ["security_admin", "data_owner"]
            mock_approval_request.completed_approvals = []
            mock_approval_request.created_at = datetime.now(timezone.utc) - timedelta(hours=1)

            # Mock workflow
            mock_workflow = MagicMock()
            mock_workflow.approval_level = ApprovalLevel.SINGLE
            mock_workflow.required_approvers = ["security_admin", "data_owner"]
            mock_workflow.pending_requests = 1
            mock_workflow.approved_requests = 0

            mock_approval_request.workflow = mock_workflow

            request_result = AsyncMock()
            request_result.scalar_one_or_none.return_value = mock_approval_request

            mock_db.execute.return_value = request_result
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock action creation
            mock_action = MagicMock()
            mock_action.action_id = uuid4()
            mock_action.request_id = request_id
            mock_action.approver_id = "security_admin"
            mock_action.action = ApprovalAction.APPROVE
            mock_action.reason = "Security review passed"
            mock_action.status = "completed"
            mock_action.taken_at = datetime.now(timezone.utc)

            def mock_refresh_side_effect(record):
                if hasattr(record, 'action_id'):  # It's an action
                    for attr, value in vars(mock_action).items():
                        if not attr.startswith('_'):
                            setattr(record, attr, value)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            # Mock share creation after approval
            with patch.object(workflow_approval_service, '_create_approved_share') as mock_create_share:
                mock_share_response = MagicMock()
                mock_share_response.share_id = uuid4()
                mock_create_share.return_value = mock_share_response

                # Mock notification sending
                with patch.object(workflow_approval_service, '_send_approval_notifications'):
                    # Create action request
                    action_request = ApprovalActionRequest(
                        action=ApprovalAction.APPROVE,
                        reason="Security review passed"
                    )

                    # Test approval action
                    result = await workflow_approval_service.take_action(
                        request_id, action_request, "security_admin", mock_db
                    )

                    # Verify database operations
                    assert mock_db.add.called
                    assert mock_db.commit.call_count >= 1

                    # Verify result
                    assert result.action == ApprovalAction.APPROVE
                    assert result.approver_id == "security_admin"
                    assert result.reason == "Security review passed"

    @pytest.mark.asyncio
    async def test_take_approval_action_reject(self, mock_db):
        """Test taking approval action - reject."""
        request_id = uuid4()
        
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Mock approval request lookup
            mock_approval_request = MagicMock()
            mock_approval_request.request_id = request_id
            mock_approval_request.status = WorkflowStatus.PENDING
            mock_approval_request.current_approvers = ["security_admin"]
            mock_approval_request.pending_approvals = ["security_admin"]
            mock_approval_request.completed_approvals = []

            # Mock workflow
            mock_workflow = MagicMock()
            mock_workflow.pending_requests = 1
            mock_workflow.rejected_requests = 0

            mock_approval_request.workflow = mock_workflow

            request_result = AsyncMock()
            request_result.scalar_one_or_none.return_value = mock_approval_request

            mock_db.execute.return_value = request_result
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock action creation
            mock_action = MagicMock()
            mock_action.action_id = uuid4()
            mock_action.request_id = request_id
            mock_action.approver_id = "security_admin"
            mock_action.action = ApprovalAction.REJECT
            mock_action.reason = "Security concerns identified"
            mock_action.status = "completed"
            mock_action.taken_at = datetime.now(timezone.utc)

            def mock_refresh_side_effect(record):
                if hasattr(record, 'action_id'):  # It's an action
                    for attr, value in vars(mock_action).items():
                        if not attr.startswith('_'):
                            setattr(record, attr, value)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            # Mock notification sending
            with patch.object(workflow_approval_service, '_send_approval_notifications'):
                # Create action request
                action_request = ApprovalActionRequest(
                    action=ApprovalAction.REJECT,
                    reason="Security concerns identified"
                )

                # Test rejection action
                result = await workflow_approval_service.take_action(
                    request_id, action_request, "security_admin", mock_db
                )

                # Verify result
                assert result.action == ApprovalAction.REJECT
                assert result.approver_id == "security_admin"
                assert result.reason == "Security concerns identified"

                # Verify request status is updated to rejected
                assert mock_approval_request.status == WorkflowStatus.REJECTED

    @pytest.mark.asyncio
    async def test_take_approval_action_unauthorized(self, mock_db):
        """Test taking approval action without authorization."""
        request_id = uuid4()
        
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Mock approval request lookup
            mock_approval_request = MagicMock()
            mock_approval_request.request_id = request_id
            mock_approval_request.status = WorkflowStatus.PENDING
            mock_approval_request.current_approvers = ["security_admin"]

            mock_workflow = MagicMock()
            mock_approval_request.workflow = mock_workflow

            request_result = AsyncMock()
            request_result.scalar_one_or_none.return_value = mock_approval_request

            mock_db.execute.return_value = request_result

            # Create action request
            action_request = ApprovalActionRequest(
                action=ApprovalAction.APPROVE,
                reason="Unauthorized approval attempt"
            )

            # Test unauthorized action should fail
            with pytest.raises(Exception) as exc_info:
                await workflow_approval_service.take_action(
                    request_id, action_request, "unauthorized_user", mock_db
                )

            assert "not authorized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_workflows(self, mock_db):
        """Test listing workflows."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Mock workflow data
            mock_workflows = [
                MagicMock(
                    workflow_id=uuid4(),
                    name="Security Review",
                    is_active=True,
                    triggers=["sensitive_data"],
                    created_at=datetime.now(timezone.utc)
                ),
                MagicMock(
                    workflow_id=uuid4(),
                    name="Manager Approval",
                    is_active=True,
                    triggers=["manager_approval"],
                    created_at=datetime.now(timezone.utc)
                )
            ]

            # Mock database queries
            mock_db.execute.side_effect = [
                # Count query
                AsyncMock(scalar=lambda: len(mock_workflows)),
                # Main query
                AsyncMock(scalars=lambda: AsyncMock(all=lambda: mock_workflows))
            ]

            # Mock permission checks
            with patch.object(workflow_approval_service, '_check_workflow_access_permission'):
                from app.models.sharing_models import ApprovalWorkflowListRequest
                
                request = ApprovalWorkflowListRequest(
                    limit=50,
                    offset=0,
                    sort_by="created_at",
                    sort_order="desc"
                )

                result = await workflow_approval_service.list_workflows(request, "test_user", mock_db)

                # Verify results
                assert result["total"] == len(mock_workflows)
                assert len(result["items"]) == len(mock_workflows)
                assert result["has_more"] == False

    @pytest.mark.asyncio
    async def test_approval_statistics(self, mock_db):
        """Test getting approval statistics."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_permission_service:
                # Mock permission check
                mock_permission_check = AsyncMock()
                mock_permission_check.has_permission = True
                mock_permission_service.check_permission.return_value = mock_permission_check

                # Mock database queries for statistics
                mock_db.execute.side_effect = [
                    # Total workflows
                    AsyncMock(scalar=lambda: 5),
                    # Active workflows
                    AsyncMock(scalar=lambda: 4),
                    # Request statistics
                    AsyncMock(first=lambda: MagicMock(
                        total=25, pending=5, approved=15, rejected=3, expired=2
                    )),
                    # Average approval time
                    AsyncMock(scalar=lambda: 2.5),
                    # Median approval time
                    AsyncMock(scalar=lambda: 2.0)
                ]

                result = await workflow_approval_service.get_approval_statistics(
                    "admin_user", db=mock_db
                )

                # Verify statistics
                assert result.total_workflows == 5
                assert result.active_workflows == 4
                assert result.total_requests == 25
                assert result.pending_requests == 5
                assert result.approved_requests == 15
                assert result.rejected_requests == 3
                assert result.average_approval_time_hours == 2.5

    def test_is_approval_complete_single(self):
        """Test approval completion logic for single approval."""
        # Mock objects
        mock_request = MagicMock()
        mock_request.completed_approvals = [
            {"action": "approve", "approver_id": "user1"}
        ]
        
        mock_workflow = MagicMock()
        mock_workflow.approval_level = ApprovalLevel.SINGLE
        mock_workflow.required_approvers = ["user1", "user2"]

        # Test single approval
        result = workflow_approval_service._is_approval_complete(mock_request, mock_workflow)
        assert result == True

    def test_is_approval_complete_unanimous(self):
        """Test approval completion logic for unanimous approval."""
        # Mock objects
        mock_request = MagicMock()
        mock_request.completed_approvals = [
            {"action": "approve", "approver_id": "user1"},
            {"action": "approve", "approver_id": "user2"}
        ]
        
        mock_workflow = MagicMock()
        mock_workflow.approval_level = ApprovalLevel.UNANIMOUS
        mock_workflow.required_approvers = ["user1", "user2"]

        # Test unanimous approval (complete)
        result = workflow_approval_service._is_approval_complete(mock_request, mock_workflow)
        assert result == True

        # Test unanimous approval (incomplete)
        mock_request.completed_approvals = [
            {"action": "approve", "approver_id": "user1"}
        ]
        result = workflow_approval_service._is_approval_complete(mock_request, mock_workflow)
        assert result == False

    def test_is_approval_complete_majority(self):
        """Test approval completion logic for majority approval."""
        # Mock objects
        mock_request = MagicMock()
        mock_request.completed_approvals = [
            {"action": "approve", "approver_id": "user1"},
            {"action": "approve", "approver_id": "user2"}
        ]
        
        mock_workflow = MagicMock()
        mock_workflow.approval_level = ApprovalLevel.MAJORITY
        mock_workflow.required_approvers = ["user1", "user2", "user3"]
        mock_workflow.optional_approvers = None

        # Test majority approval (complete with 2 out of 3)
        result = workflow_approval_service._is_approval_complete(mock_request, mock_workflow)
        assert result == True

        # Test majority approval (incomplete with 1 out of 3)
        mock_request.completed_approvals = [
            {"action": "approve", "approver_id": "user1"}
        ]
        result = workflow_approval_service._is_approval_complete(mock_request, mock_workflow)
        assert result == False


class TestWorkflowApprovalAPI:
    """Test suite for workflow approval API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_workflow_approval_endpoints_require_auth(self, client):
        """Test that workflow approval endpoints require authentication."""
        endpoints = [
            "/api/v1/workflow-approvals/workflows",
            "/api/v1/workflow-approvals/requests",
            "/api/v1/workflow-approvals/statistics"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should require authentication
            assert response.status_code in [401, 403, 422]

    def test_workflow_approval_health_endpoint(self, client):
        """Test workflow approval health endpoint."""
        with patch('app.api.v1.endpoints.workflow_approvals.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.return_value = AsyncMock()
            
            response = client.get("/api/v1/workflow-approvals/health")
            
            # Health endpoint should be accessible without auth
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "workflow-approvals"

    def test_workflow_approval_capabilities_endpoint(self, client):
        """Test workflow approval capabilities endpoint."""
        response = client.get("/api/v1/workflow-approvals/capabilities")
        
        # Capabilities endpoint should be accessible without auth
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "workflow-approvals"
        assert "features" in data
        assert "supported_approval_levels" in data
        assert "supported_triggers" in data
        assert "supported_actions" in data

    @pytest.mark.asyncio
    async def test_workflow_approval_error_handling(self):
        """Test workflow approval error handling."""
        with patch('app.services.workflow_approval_service.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.side_effect = Exception("Database error")
            
            with pytest.raises(Exception):
                from app.models.sharing_models import ApprovalWorkflowListRequest
                request = ApprovalWorkflowListRequest()
                await workflow_approval_service.list_workflows(request, "test_user", mock_db)

    def test_workflow_approval_input_validation(self, client):
        """Test input validation for workflow approval endpoints."""
        # Test invalid workflow ID format
        response = client.get(
            "/api/v1/workflow-approvals/workflows/invalid-uuid",
            headers={"Authorization": "Bearer fake-token"}
        )
        assert response.status_code in [400, 422]

        # Test invalid action format
        response = client.post(
            "/api/v1/workflow-approvals/requests/123e4567-e89b-12d3-a456-426614174000/actions",
            headers={"Authorization": "Bearer fake-token"},
            json={
                "action": "invalid_action",
                "reason": "Test reason"
            }
        )
        assert response.status_code in [400, 422]


class TestWorkflowApprovalIntegration:
    """Integration tests for workflow approval functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_approval_workflow(self, mock_db):
        """Test complete approval workflow from creation to approval."""
        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            # Test 1: Create a workflow
            workflow_request = CreateApprovalWorkflowRequest(
                name="Integration Test Workflow",
                triggers=[ApprovalTrigger.SENSITIVE_DATA],
                approval_level=ApprovalLevel.SINGLE,
                required_approvers=["integration_approver"]
            )

            with patch('app.services.role_permission_service.role_permission_service') as mock_permission_service:
                mock_permission_check = AsyncMock()
                mock_permission_check.has_permission = True
                mock_permission_service.check_permission.return_value = mock_permission_check

                # Mock workflow creation
                mock_workflow = MagicMock()
                mock_workflow.workflow_id = uuid4()
                mock_workflow.name = workflow_request.name
                mock_workflow.is_active = True
                mock_workflow.triggers = [trigger.value for trigger in workflow_request.triggers]
                mock_workflow.created_at = datetime.now(timezone.utc)
                mock_workflow.updated_at = datetime.now(timezone.utc)

                mock_db.add = MagicMock()
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                def mock_refresh_side_effect(record):
                    for attr, value in vars(mock_workflow).items():
                        if not attr.startswith('_'):
                            setattr(record, attr, value)

                mock_db.refresh.side_effect = mock_refresh_side_effect

                created_workflow = await workflow_approval_service.create_workflow(
                    workflow_request, "integration_admin", mock_db
                )

                # Verify workflow creation
                assert created_workflow.name == workflow_request.name
                assert created_workflow.workflow_id == mock_workflow.workflow_id

    @pytest.mark.asyncio
    async def test_approval_workflow_performance(self, mock_db):
        """Test approval workflow performance with multiple requests."""
        # Create multiple mock approval requests
        large_request_set = []
        for i in range(100):
            request = MagicMock()
            request.request_id = uuid4()
            request.status = WorkflowStatus.PENDING
            request.current_approvers = [f"approver_{i % 10}"]
            request.created_at = datetime.now(timezone.utc) - timedelta(seconds=i)
            large_request_set.append(request)

        with patch('app.services.workflow_approval_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service') as mock_permission_service:
                mock_permission_check = AsyncMock()
                mock_permission_check.has_permission = True
                mock_permission_service.check_permission.return_value = mock_permission_check

                # Mock database to return large dataset
                mock_db.execute.side_effect = [
                    # Count query
                    AsyncMock(scalar=lambda: len(large_request_set)),
                    # Main query (limited)
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: large_request_set[:50]))
                ]

                # This should complete without performance issues
                from app.models.sharing_models import ApprovalRequestListRequest
                request = ApprovalRequestListRequest(limit=50)
                result = await workflow_approval_service.list_approval_requests(request, "performance_user", mock_db)

                assert result["total"] == 100
                assert len(result["items"]) == 50
                assert result["has_more"] == True