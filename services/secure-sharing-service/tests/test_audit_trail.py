"""
Tests for audit trail functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.sharing_models import (
    AuditEventType, AuditEventSeverity, AuditEventCategory, ShareType, ShareOperation, 
    PermissionScope, CreateAuditEventRequest, AuditTrailQuery, AuditTrailEvent
)
from app.services.audit_trail_service import audit_trail_service
from app.core.database import ShareAuditTrail


class TestAuditTrailService:
    """Test suite for audit trail service functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_audit_event_request(self):
        """Create sample audit event request."""
        return CreateAuditEventRequest(
            event_type=AuditEventType.SHARE_CREATED,
            category=AuditEventCategory.SHARE_MANAGEMENT,
            severity=AuditEventSeverity.LOW,
            title="Share Created",
            description="User created a new share for dashboard resource",
            user_id="test_user",
            share_id=uuid4(),
            resource_id=uuid4(),
            resource_type=ShareType.DASHBOARD,
            operation=ShareOperation.CREATE,
            context={"action": "share_creation", "source": "web_ui"},
            correlation_id="test-correlation-123"
        )

    @pytest.fixture
    def sample_audit_records(self):
        """Create sample audit records for testing."""
        base_time = datetime.now(timezone.utc)
        
        return [
            ShareAuditTrail(
                event_id=uuid4(),
                event_type=AuditEventType.SHARE_CREATED,
                category=AuditEventCategory.SHARE_MANAGEMENT,
                severity=AuditEventSeverity.LOW,
                title="Share Created",
                description="User created a new share",
                timestamp=base_time - timedelta(hours=1),
                user_id="user1",
                ip_address="192.168.1.1",
                share_id=uuid4(),
                resource_type=ShareType.REPORT,
                operation=ShareOperation.CREATE,
                authorization_granted=True,
                service_name="secure-sharing-service",
                correlation_id="corr-1"
            ),
            ShareAuditTrail(
                event_id=uuid4(),
                event_type=AuditEventType.PERMISSION_DENIED,
                category=AuditEventCategory.SECURITY,
                severity=AuditEventSeverity.HIGH,
                title="Permission Denied",
                description="User attempted unauthorized access",
                timestamp=base_time - timedelta(minutes=30),
                user_id="user2",
                ip_address="192.168.1.2",
                share_id=uuid4(),
                operation=ShareOperation.READ,
                authorization_granted=False,
                service_name="secure-sharing-service",
                correlation_id="corr-2"
            ),
            ShareAuditTrail(
                event_id=uuid4(),
                event_type=AuditEventType.SECURITY_VIOLATION,
                category=AuditEventCategory.SECURITY,
                severity=AuditEventSeverity.CRITICAL,
                title="Security Violation",
                description="Multiple failed login attempts detected",
                timestamp=base_time - timedelta(minutes=15),
                user_id="user3",
                ip_address="192.168.1.3",
                authorization_granted=False,
                service_name="secure-sharing-service",
                context={"failed_attempts": 5, "time_window": "5 minutes"},
                correlation_id="corr-3"
            )
        ]

    @pytest.mark.asyncio
    async def test_log_event_basic(self, sample_audit_event_request, mock_db):
        """Test basic event logging functionality."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            # Mock database operations
            mock_audit_record = MagicMock()
            mock_audit_record.event_id = uuid4()
            mock_audit_record.event_type = sample_audit_event_request.event_type
            mock_audit_record.title = sample_audit_event_request.title
            mock_audit_record.timestamp = datetime.now(timezone.utc)
            
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Mock refresh to set the audit record attributes
            def mock_refresh_side_effect(record):
                for attr, value in vars(mock_audit_record).items():
                    if not attr.startswith('_'):
                        setattr(record, attr, value)
            
            mock_db.refresh.side_effect = mock_refresh_side_effect

            # Test event logging
            result = await audit_trail_service.log_event(sample_audit_event_request, mock_db)

            # Verify database operations
            assert mock_db.add.called
            assert mock_db.commit.call_count >= 1
            assert mock_db.refresh.called

            # Verify result
            assert result.event_type == sample_audit_event_request.event_type
            assert result.title == sample_audit_event_request.title

    @pytest.mark.asyncio
    async def test_log_share_event_simplified(self, mock_db):
        """Test simplified share event logging."""
        share_id = uuid4()
        
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, 'log_event') as mock_log_event:
                mock_log_event.return_value = AsyncMock()
                
                await audit_trail_service.log_share_event(
                    event_type=AuditEventType.SHARE_UPDATED,
                    title="Share Updated",
                    description="User updated share settings",
                    share_id=share_id,
                    user_id="test_user",
                    operation=ShareOperation.UPDATE,
                    severity=AuditEventSeverity.MEDIUM
                )

                # Verify log_event was called with correct parameters
                mock_log_event.assert_called_once()
                call_args = mock_log_event.call_args[0][0]
                
                assert call_args.event_type == AuditEventType.SHARE_UPDATED
                assert call_args.category == AuditEventCategory.SHARE_MANAGEMENT
                assert call_args.severity == AuditEventSeverity.MEDIUM
                assert call_args.share_id == share_id

    @pytest.mark.asyncio
    async def test_log_permission_event(self, mock_db):
        """Test permission event logging."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, 'log_event') as mock_log_event:
                mock_log_event.return_value = AsyncMock()
                
                await audit_trail_service.log_permission_event(
                    event_type=AuditEventType.PERMISSION_GRANTED,
                    title="Permission Granted",
                    description="User granted view permission",
                    user_id="test_user",
                    operation=ShareOperation.READ,
                    scope=PermissionScope.SHARE,
                    authorization_granted=True
                )

                # Verify log_event was called
                mock_log_event.assert_called_once()
                call_args = mock_log_event.call_args[0][0]
                
                assert call_args.event_type == AuditEventType.PERMISSION_GRANTED
                assert call_args.category == AuditEventCategory.PERMISSION_MANAGEMENT
                assert call_args.operation == ShareOperation.READ
                assert call_args.authorization_granted == True

    @pytest.mark.asyncio
    async def test_log_security_event(self, mock_db):
        """Test security event logging."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, 'log_event') as mock_log_event:
                mock_log_event.return_value = AsyncMock()
                
                await audit_trail_service.log_security_event(
                    event_type=AuditEventType.SECURITY_VIOLATION,
                    title="Suspicious Activity",
                    description="Multiple failed login attempts",
                    severity=AuditEventSeverity.CRITICAL,
                    user_id="suspicious_user",
                    ip_address="192.168.1.100"
                )

                # Verify log_event was called
                mock_log_event.assert_called_once()
                call_args = mock_log_event.call_args[0][0]
                
                assert call_args.event_type == AuditEventType.SECURITY_VIOLATION
                assert call_args.category == AuditEventCategory.SECURITY
                assert call_args.severity == AuditEventSeverity.CRITICAL
                assert call_args.authorization_granted == False

    @pytest.mark.asyncio
    async def test_query_events_basic(self, sample_audit_records, mock_db):
        """Test basic event querying."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                # Mock database query results
                mock_db.execute.side_effect = [
                    # Count query
                    AsyncMock(scalar=lambda: len(sample_audit_records)),
                    # Main query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_audit_records))
                ]

                query = AuditTrailQuery(
                    limit=50,
                    offset=0,
                    sort_by="timestamp",
                    sort_order="desc"
                )

                result = await audit_trail_service.query_events(query, "test_user", mock_db)

                # Verify results
                assert result.total_count == len(sample_audit_records)
                assert result.filtered_count == len(sample_audit_records)
                assert len(result.events) == len(sample_audit_records)
                assert result.has_more == False

    @pytest.mark.asyncio
    async def test_query_events_with_filters(self, sample_audit_records, mock_db):
        """Test event querying with comprehensive filters."""
        filtered_records = [r for r in sample_audit_records if r.category == AuditEventCategory.SECURITY]
        
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                # Mock database query results
                mock_db.execute.side_effect = [
                    # Count query
                    AsyncMock(scalar=lambda: len(filtered_records)),
                    # Main query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: filtered_records))
                ]

                query = AuditTrailQuery(
                    categories=[AuditEventCategory.SECURITY],
                    severities=[AuditEventSeverity.HIGH, AuditEventSeverity.CRITICAL],
                    start_time=datetime.now(timezone.utc) - timedelta(days=1),
                    end_time=datetime.now(timezone.utc),
                    limit=25,
                    offset=0
                )

                result = await audit_trail_service.query_events(query, "test_user", mock_db)

                # Verify filtered results
                assert result.total_count == len(filtered_records)
                assert result.limit == 25

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, sample_audit_records, mock_db):
        """Test getting specific event by ID."""
        target_record = sample_audit_records[0]
        
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                # Mock database query
                mock_db.execute.return_value = AsyncMock(scalar_one_or_none=lambda: target_record)

                result = await audit_trail_service.get_event_by_id(target_record.event_id, "test_user", mock_db)

                # Verify result
                assert result is not None
                assert result.event_id == target_record.event_id
                assert result.event_type == target_record.event_type

    @pytest.mark.asyncio
    async def test_get_event_by_id_not_found(self, mock_db):
        """Test getting non-existent event by ID."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                # Mock database query returning None
                mock_db.execute.return_value = AsyncMock(scalar_one_or_none=lambda: None)

                result = await audit_trail_service.get_event_by_id(uuid4(), "test_user", mock_db)

                # Verify result is None
                assert result is None

    @pytest.mark.asyncio
    async def test_get_statistics(self, mock_db):
        """Test getting audit trail statistics."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                with patch.object(audit_trail_service, '_detect_suspicious_activity', return_value=[]):
                    with patch.object(audit_trail_service, '_check_retention_compliance', return_value={}):
                        # Mock all database queries for statistics
                        mock_db.execute.side_effect = [
                            # Total events
                            AsyncMock(scalar=lambda: 100),
                            # Event count by type
                            AsyncMock(fetchall=lambda: [(AuditEventType.SHARE_CREATED, 50), (AuditEventType.SHARE_ACCESSED, 30)]),
                            # Event count by category
                            AsyncMock(fetchall=lambda: [(AuditEventCategory.SHARE_MANAGEMENT, 80), (AuditEventCategory.SECURITY, 20)]),
                            # Event count by severity
                            AsyncMock(fetchall=lambda: [(AuditEventSeverity.LOW, 60), (AuditEventSeverity.HIGH, 40)]),
                            # Hourly events
                            AsyncMock(fetchall=lambda: []),
                            # Daily events
                            AsyncMock(fetchall=lambda: []),
                            # Top users
                            AsyncMock(fetchall=lambda: [("user1", 25), ("user2", 15)]),
                            # Unique users
                            AsyncMock(scalar=lambda: 10),
                            # Most accessed shares
                            AsyncMock(fetchall=lambda: [(uuid4(), 10), (uuid4(), 8)]),
                            # Resource type activity
                            AsyncMock(fetchall=lambda: [(ShareType.REPORT, 40), (ShareType.DASHBOARD, 30)]),
                            # Security events
                            AsyncMock(scalar=lambda: 5),
                            # Failed authorization
                            AsyncMock(scalar=lambda: 3),
                            # Peak hours
                            AsyncMock(fetchall=lambda: [(9, 15), (14, 12)]),
                        ]

                        result = await audit_trail_service.get_statistics(
                            start_time=datetime.now(timezone.utc) - timedelta(days=30),
                            end_time=datetime.now(timezone.utc),
                            user_id="test_user",
                            db=mock_db
                        )

                        # Verify statistics
                        assert result.total_events == 100
                        assert AuditEventType.SHARE_CREATED in result.event_count_by_type
                        assert AuditEventCategory.SHARE_MANAGEMENT in result.event_count_by_category
                        assert len(result.top_active_users) > 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_events(self, mock_db):
        """Test cleanup of expired audit events."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            # Mock queries for cleanup
            mock_db.execute.side_effect = [
                # Count expired events
                AsyncMock(scalar=lambda: 1000),
                # Get batch of expired IDs
                AsyncMock(fetchall=lambda: [(uuid4(),) for _ in range(100)]),
                # Delete batch result
                AsyncMock(rowcount=100),
                # Next batch (empty)
                AsyncMock(fetchall=lambda: [])
            ]
            
            result = await audit_trail_service.cleanup_expired_events(batch_size=100, db=mock_db)

            # Verify cleanup results
            assert result["total_expired"] == 1000
            assert result["deleted_count"] == 100
            assert result["batches_processed"] == 1
            assert result["cleanup_completed"] == True

    @pytest.mark.asyncio
    async def test_permission_checks(self, mock_db):
        """Test audit trail permission checking."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            from app.services.role_permission_service import role_permission_service
            
            with patch.object(role_permission_service, 'check_permission') as mock_permission_check:
                # Test case 1: User has global permissions
                mock_permission_check.return_value = AsyncMock(has_permission=True)
                
                filters = []
                await audit_trail_service._check_audit_access_permission("admin_user", filters, mock_db)
                
                # Should not add user filter
                assert len(filters) == 0

                # Test case 2: User has no global permissions
                mock_permission_check.return_value = AsyncMock(has_permission=False)
                
                filters = []
                await audit_trail_service._check_audit_access_permission("regular_user", filters, mock_db)
                
                # Should add user filter
                assert len(filters) == 1

    def test_convert_to_response_model(self, sample_audit_records):
        """Test conversion from database model to response model."""
        audit_record = sample_audit_records[0]
        
        result = audit_trail_service._convert_to_response_model(audit_record)
        
        # Verify conversion
        assert isinstance(result, AuditTrailEvent)
        assert result.event_id == audit_record.event_id
        assert result.event_type == audit_record.event_type
        assert result.title == audit_record.title
        assert result.user_id == audit_record.user_id


class TestAuditTrailAPI:
    """Test suite for audit trail API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_audit_trail_endpoints_require_auth(self, client):
        """Test that audit trail endpoints require authentication."""
        endpoints = [
            "/api/v1/audit-trail/events",
            "/api/v1/audit-trail/statistics",
            "/api/v1/audit-trail/events/share/123e4567-e89b-12d3-a456-426614174000",
            "/api/v1/audit-trail/events/user/test_user",
            "/api/v1/audit-trail/security/events"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should require authentication
            assert response.status_code in [401, 403, 422]

    def test_audit_trail_health_endpoint(self, client):
        """Test audit trail health endpoint."""
        with patch('app.api.v1.endpoints.audit_trail.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.return_value = AsyncMock()
            
            response = client.get("/api/v1/audit-trail/health")
            
            # Health endpoint should be accessible without auth
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "audit-trail"

    def test_audit_trail_capabilities_endpoint(self, client):
        """Test audit trail capabilities endpoint."""
        response = client.get("/api/v1/audit-trail/capabilities")
        
        # Capabilities endpoint should be accessible without auth
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "audit-trail"
        assert "features" in data
        assert "supported_event_types" in data
        assert "limits" in data

    @pytest.mark.asyncio
    async def test_audit_trail_error_handling(self):
        """Test audit trail error handling."""
        with patch('app.services.audit_trail_service.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.side_effect = Exception("Database error")
            
            with pytest.raises(Exception):
                query = AuditTrailQuery()
                await audit_trail_service.query_events(query, "test_user", mock_db)

    def test_audit_trail_input_validation(self, client):
        """Test input validation for audit trail endpoints."""
        # Test invalid event ID format
        response = client.get(
            "/api/v1/audit-trail/events/invalid-uuid",
            headers={"Authorization": "Bearer fake-token"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_audit_trail_rate_limiting_integration(self):
        """Test that audit trail respects rate limiting."""
        # This would test the actual rate limiting integration
        # In a real scenario, you'd make multiple requests and verify rate limiting
        pass

    @pytest.mark.asyncio
    async def test_suspicious_activity_detection(self, mock_db):
        """Test suspicious activity detection."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            # Mock suspicious activity queries
            mock_db.execute.side_effect = [
                # Failed auth by IP
                AsyncMock(fetchall=lambda: [("192.168.1.100", 10, 3)]),
                # Critical events count
                AsyncMock(scalar=lambda: 2)
            ]

            start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            end_time = datetime.now(timezone.utc)
            
            result = await audit_trail_service._detect_suspicious_activity(start_time, end_time, mock_db)

            # Verify suspicious activity detection
            assert len(result) >= 1
            assert any(indicator["type"] == "multiple_failed_auth" for indicator in result)

    @pytest.mark.asyncio
    async def test_retention_compliance_check(self, mock_db):
        """Test retention policy compliance checking."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            # Mock retention compliance queries
            mock_db.execute.side_effect = [
                # Overdue events count
                AsyncMock(scalar=lambda: 50),
                # Total events count
                AsyncMock(scalar=lambda: 1000)
            ]

            result = await audit_trail_service._check_retention_compliance(mock_db)

            # Verify compliance check
            assert "total_events" in result
            assert "overdue_events" in result
            assert "compliance_percentage" in result
            assert result["compliance_percentage"] == 95.0  # (1000-50)/1000 * 100


class TestAuditTrailIntegration:
    """Integration tests for audit trail functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_audit_workflow(self, sample_audit_records, mock_db):
        """Test complete audit workflow from logging to querying."""
        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            # Test 1: Log an event
            request = CreateAuditEventRequest(
                event_type=AuditEventType.SHARE_CREATED,
                category=AuditEventCategory.SHARE_MANAGEMENT,
                severity=AuditEventSeverity.LOW,
                title="Integration Test Share Created",
                description="Testing end-to-end audit trail workflow",
                user_id="integration_test_user"
            )

            with patch.object(audit_trail_service, '_convert_to_response_model') as mock_convert:
                mock_convert.return_value = AuditTrailEvent(
                    event_id=uuid4(),
                    event_type=request.event_type,
                    category=request.category,
                    severity=request.severity,
                    title=request.title,
                    description=request.description,
                    timestamp=datetime.now(timezone.utc),
                    user_id=request.user_id,
                    service_name="secure-sharing-service"
                )
                
                mock_db.add = MagicMock()
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                logged_event = await audit_trail_service.log_event(request, mock_db)

                # Verify event was logged
                assert logged_event.event_type == request.event_type
                assert logged_event.user_id == request.user_id

            # Test 2: Query the logged events
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                mock_db.execute.side_effect = [
                    # Count query
                    AsyncMock(scalar=lambda: 1),
                    # Main query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: [sample_audit_records[0]]))
                ]

                query = AuditTrailQuery(
                    user_ids=["integration_test_user"],
                    limit=10
                )

                query_result = await audit_trail_service.query_events(query, "integration_test_user", mock_db)

                # Verify query results
                assert query_result.total_count == 1
                assert len(query_result.events) == 1

    @pytest.mark.asyncio
    async def test_audit_trail_performance_with_large_dataset(self, mock_db):
        """Test audit trail performance with large datasets."""
        # Create a large number of mock records
        large_record_set = []
        for i in range(1000):
            record = ShareAuditTrail(
                event_id=uuid4(),
                event_type=AuditEventType.SHARE_ACCESSED,
                category=AuditEventCategory.SHARE_MANAGEMENT,
                severity=AuditEventSeverity.LOW,
                title=f"Performance Test Event {i}",
                description=f"Testing performance with event {i}",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=i),
                user_id=f"performance_user_{i % 100}",
                service_name="secure-sharing-service"
            )
            large_record_set.append(record)

        with patch('app.services.audit_trail_service.get_database', return_value=mock_db):
            with patch.object(audit_trail_service, '_check_audit_access_permission'):
                # Mock database to return large dataset
                mock_db.execute.side_effect = [
                    # Count query
                    AsyncMock(scalar=lambda: len(large_record_set)),
                    # Main query (limited)
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: large_record_set[:100]))
                ]

                # This should complete without performance issues
                query = AuditTrailQuery(limit=100)
                result = await audit_trail_service.query_events(query, "performance_user", mock_db)

                assert result.total_count == 1000
                assert len(result.events) == 100
                assert result.has_more == True