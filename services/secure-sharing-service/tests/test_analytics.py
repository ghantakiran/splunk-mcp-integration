"""
Tests for analytics functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.sharing_models import (
    ShareType, SharePermission, ShareStatus, AccessMethod, ExpirationPolicy
)
from app.services.analytics_service import analytics_service
from app.services.metrics_collector import metrics_collector
from app.core.database import SharedResource, ShareAccessLog, ShareMetrics


class TestAnalyticsService:
    """Test suite for analytics service functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_shares(self):
        """Create sample shares for testing."""
        base_time = datetime.now(timezone.utc)
        
        return [
            SharedResource(
                share_id=uuid4(),
                resource_type=ShareType.REPORT,
                resource_id=uuid4(),
                resource_name="Test Report 1",
                share_token="token1",
                permissions=["view", "download"],
                access_method=AccessMethod.LINK,
                requires_authentication=True,
                expiration_policy=ExpirationPolicy.AFTER_TIME,
                expires_at=base_time + timedelta(days=7),
                status=ShareStatus.ACTIVE,
                total_views=150,
                total_downloads=25,
                unique_viewers=45,
                created_by="user1",
                created_at=base_time - timedelta(days=5)
            ),
            SharedResource(
                share_id=uuid4(),
                resource_type=ShareType.DASHBOARD,
                resource_id=uuid4(),
                resource_name="Test Dashboard 1",
                share_token="token2",
                permissions=["view"],
                access_method=AccessMethod.LINK,
                requires_authentication=False,
                expiration_policy=ExpirationPolicy.AFTER_VIEWS,
                max_views=1000,
                status=ShareStatus.ACTIVE,
                total_views=75,
                total_downloads=0,
                unique_viewers=30,
                created_by="user2",
                created_at=base_time - timedelta(days=3)
            ),
            SharedResource(
                share_id=uuid4(),
                resource_type=ShareType.CHART,
                resource_id=uuid4(),
                resource_name="Expired Chart",
                share_token="token3",
                permissions=["view"],
                access_method=AccessMethod.LINK,
                requires_authentication=True,
                expiration_policy=ExpirationPolicy.AFTER_TIME,
                expires_at=base_time - timedelta(days=1),
                status=ShareStatus.EXPIRED,
                total_views=20,
                total_downloads=5,
                unique_viewers=10,
                created_by="user1",
                created_at=base_time - timedelta(days=10)
            )
        ]

    @pytest.fixture
    def sample_access_logs(self, sample_shares):
        """Create sample access logs for testing."""
        base_time = datetime.now(timezone.utc)
        logs = []
        
        for i, share in enumerate(sample_shares):
            # Create various access logs for each share
            for j in range(10):
                logs.append(ShareAccessLog(
                    log_id=uuid4(),
                    share_id=share.share_id,
                    accessed_at=base_time - timedelta(hours=j),
                    user_email=f"user{j}@example.com",
                    ip_address=f"192.168.1.{j + 1}",
                    user_agent=f"TestAgent/{j + 1}.0",
                    action="view",
                    success=True,
                    session_duration=30.0 + j,
                    country="US",
                    device_type="desktop"
                ))
        
        return logs

    @pytest.mark.asyncio
    async def test_get_share_analytics_basic(self, sample_shares, mock_db):
        """Test basic share analytics calculation."""
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch.object(analytics_service, '_calculate_views_in_period', return_value=200):
                # Mock database queries
                mock_db.execute.side_effect = [
                    # Permission check
                    AsyncMock(scalar_one_or_none=lambda: None),
                    # Shares query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_shares))
                ]

                analytics = await analytics_service.get_share_analytics(
                    user_id="test_user",
                    start_date=datetime.now(timezone.utc) - timedelta(days=30),
                    end_date=datetime.now(timezone.utc)
                )

                assert analytics.total_shares == 3
                assert analytics.active_shares == 2
                assert analytics.expired_shares == 1
                assert analytics.total_views_all_shares == 245  # Sum of all views
                assert analytics.total_downloads_all_shares == 30  # Sum of all downloads
                assert analytics.average_views_per_share == 245 / 3

    @pytest.mark.asyncio
    async def test_get_share_analytics_breakdown(self, sample_shares, mock_db):
        """Test analytics breakdown calculations."""
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch.object(analytics_service, '_calculate_views_in_period', return_value=200):
                # Mock database queries
                mock_db.execute.side_effect = [
                    # Permission check
                    AsyncMock(scalar_one_or_none=lambda: None),
                    # Shares query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_shares))
                ]

                analytics = await analytics_service.get_share_analytics(
                    user_id="test_user"
                )

                # Test type breakdown
                expected_type_breakdown = {"report": 1, "dashboard": 1, "chart": 1}
                assert analytics.shares_by_type == expected_type_breakdown

                # Test permission breakdown
                expected_permission_breakdown = {"view": 3, "download": 1}
                assert analytics.shares_by_permission == expected_permission_breakdown

                # Test access method breakdown
                expected_access_breakdown = {"link": 3}
                assert analytics.shares_by_access_method == expected_access_breakdown

    @pytest.mark.asyncio
    async def test_get_share_stats_detailed(self, sample_shares, sample_access_logs, mock_db):
        """Test detailed share statistics calculation."""
        share = sample_shares[0]
        relevant_logs = [log for log in sample_access_logs if log.share_id == share.share_id]
        
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            # Mock database queries
            mock_db.execute.side_effect = [
                # Get share
                AsyncMock(scalar_one_or_none=lambda: share),
                # Permission check
                AsyncMock(has_permission=True),
                # Get access logs
                AsyncMock(scalars=lambda: AsyncMock(all=lambda: relevant_logs))
            ]

            stats = await analytics_service.get_share_stats(
                share_id=share.share_id,
                user_id="test_user",
                period_days=30
            )

            assert stats.share_id == share.share_id
            assert stats.total_views == share.total_views
            assert stats.total_downloads == share.total_downloads
            assert stats.unique_viewers == share.unique_viewers
            assert len(stats.daily_views) > 0
            assert stats.average_session_duration is not None
            assert isinstance(stats.device_types, dict)

    @pytest.mark.asyncio
    async def test_get_access_logs_pagination(self, sample_shares, sample_access_logs, mock_db):
        """Test access logs retrieval with pagination."""
        share = sample_shares[0]
        relevant_logs = [log for log in sample_access_logs if log.share_id == share.share_id]
        
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            # Mock database queries
            mock_db.execute.side_effect = [
                # Get share
                AsyncMock(scalar_one_or_none=lambda: share),
                # Permission check
                AsyncMock(has_permission=True),
                # Count query
                AsyncMock(scalar=lambda: len(relevant_logs)),
                # Logs query
                AsyncMock(scalars=lambda: AsyncMock(all=lambda: relevant_logs[:5]))
            ]

            logs, total = await analytics_service.get_access_logs(
                share_id=share.share_id,
                user_id="test_user",
                limit=5,
                offset=0
            )

            assert len(logs) == 5
            assert total == len(relevant_logs)
            assert all(isinstance(log.log_id, type(uuid4())) for log in logs)

    @pytest.mark.asyncio
    async def test_generate_metrics_aggregation(self, sample_shares, sample_access_logs, mock_db):
        """Test metrics aggregation generation."""
        test_date = datetime.now(timezone.utc)
        
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            # Mock database queries
            mock_db.execute.side_effect = [
                # Get all shares
                AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_shares)),
                # For each share, get access logs
                *[AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_access_logs[:5])) for _ in sample_shares],
                # Check existing metrics (return None for each share)
                *[AsyncMock(scalar_one_or_none=lambda: None) for _ in sample_shares]
            ]

            # Test aggregation
            await analytics_service.generate_metrics_aggregation(
                period_type="day",
                date=test_date,
                db=mock_db
            )

            # Verify that metrics were added to the session
            assert mock_db.add.call_count == len(sample_shares)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_analytics_permission_filtering(self, sample_shares, mock_db):
        """Test that analytics respects user permissions."""
        # Test with user who can only see their own shares
        user_shares = [s for s in sample_shares if s.created_by == "user1"]
        
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch.object(analytics_service, '_calculate_views_in_period', return_value=100):
                # Mock permission check to return False (no global permissions)
                mock_db.execute.side_effect = [
                    # Permission check - no global access
                    AsyncMock(scalar_one_or_none=lambda: None),
                    # User's shares query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: user_shares))
                ]

                analytics = await analytics_service.get_share_analytics(
                    user_id="user1"
                )

                # Should only see user1's shares
                assert analytics.total_shares == len(user_shares)
                assert analytics.total_views_all_shares == sum(s.total_views for s in user_shares)

    def test_calculate_daily_views(self, sample_access_logs):
        """Test daily views calculation."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        daily_views = analytics_service._calculate_daily_views(
            sample_access_logs, start_date, end_date
        )
        
        assert len(daily_views) == 8  # 7 days + today
        assert all("date" in day and "views" in day for day in daily_views)
        assert sum(day["views"] for day in daily_views) <= len(sample_access_logs)

    def test_device_type_detection(self):
        """Test device type detection from user agents."""
        test_cases = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0", True, False, False),  # Desktop
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) Mobile/15E148", False, True, False),  # Mobile
            ("Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) Mobile/15E148", False, False, True),  # Tablet
            ("Unknown Agent", False, False, False)  # Unknown
        ]
        
        for user_agent, is_desktop, is_mobile, is_tablet in test_cases:
            assert analytics_service._is_desktop(user_agent) == is_desktop
            assert analytics_service._is_mobile(user_agent) == is_mobile
            assert analytics_service._is_tablet(user_agent) == is_tablet

    def test_period_boundaries_calculation(self):
        """Test period boundary calculations."""
        test_date = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        
        # Test hour boundaries
        start, end = analytics_service._get_period_boundaries(test_date, "hour")
        assert start == datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        
        # Test day boundaries
        start, end = analytics_service._get_period_boundaries(test_date, "day")
        assert start == datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)
        
        # Test week boundaries (assuming Monday is start of week)
        start, end = analytics_service._get_period_boundaries(test_date, "week")
        assert start.weekday() == 0  # Monday
        assert (end - start).days == 7
        
        # Test month boundaries
        start, end = analytics_service._get_period_boundaries(test_date, "month")
        assert start == datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2024, 7, 1, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_invalid_period_type(self):
        """Test error handling for invalid period types."""
        with pytest.raises(ValueError, match="Invalid period type"):
            analytics_service._get_period_boundaries(datetime.now(timezone.utc), "invalid")

    @pytest.mark.asyncio
    async def test_analytics_with_empty_data(self, mock_db):
        """Test analytics with no shares."""
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            # Mock empty results
            mock_db.execute.side_effect = [
                # Permission check
                AsyncMock(scalar_one_or_none=lambda: None),
                # Empty shares query
                AsyncMock(scalars=lambda: AsyncMock(all=lambda: []))
            ]

            analytics = await analytics_service.get_share_analytics(
                user_id="test_user"
            )

            assert analytics.total_shares == 0
            assert analytics.active_shares == 0
            assert analytics.expired_shares == 0
            assert analytics.total_views_all_shares == 0
            assert analytics.average_views_per_share == 0
            assert len(analytics.most_viewed_shares) == 0


class TestMetricsCollector:
    """Test suite for metrics collector functionality."""

    @pytest.fixture
    def collector(self):
        """Create metrics collector instance."""
        return metrics_collector

    @pytest.mark.asyncio
    async def test_collect_share_interaction_metrics(self, collector):
        """Test interaction metrics collection."""
        with patch('app.services.metrics_collector.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            await collector.collect_share_interaction_metrics(
                share_id="test-share-id",
                action="view",
                user_email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
                session_duration=45.5
            )
            
            # Should not raise any exceptions
            # In a real implementation, this would verify metrics storage

    @pytest.mark.asyncio
    async def test_get_real_time_metrics(self, collector):
        """Test real-time metrics retrieval."""
        with patch('app.services.metrics_collector.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            mock_db.execute.return_value = AsyncMock(scalar=lambda: 5)
            
            metrics = await collector.get_real_time_metrics("test-share-id")
            
            assert "timestamp" in metrics
            assert "share_id" in metrics
            assert "recent_activity" in metrics
            assert metrics["share_id"] == "test-share-id"

    @pytest.mark.asyncio
    async def test_update_share_real_time_metrics(self, collector):
        """Test share-specific metrics updates."""
        mock_share = MagicMock()
        mock_share.share_id = uuid4()
        
        with patch('app.services.metrics_collector.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Mock database results
            mock_db.execute.side_effect = [
                AsyncMock(scalar=lambda: 100),  # Total views
                AsyncMock(scalar=lambda: 25),   # Total downloads
                AsyncMock(scalar=lambda: 30),   # Unique viewers (email)
                AsyncMock(scalar_one_or_none=lambda: mock_share)  # Share object
            ]
            
            await collector._update_share_real_time_metrics(mock_share.share_id, mock_db)
            
            # Verify that share metrics were updated
            assert mock_share.total_views == 100
            assert mock_share.total_downloads == 25
            assert mock_share.unique_viewers == 30

    def test_collector_lifecycle(self, collector):
        """Test collector start/stop lifecycle."""
        assert not collector.is_running
        
        # Test stop when not running
        collector.stop_collection()  # Should not raise
        
        # Test configuration
        assert collector.collection_interval > 0
        assert collector.aggregation_interval > 0


class TestAnalyticsAPI:
    """Test suite for analytics API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_analytics_endpoints_require_auth(self, client):
        """Test that analytics endpoints require authentication."""
        endpoints = [
            "/api/v1/analytics/overview",
            "/api/v1/analytics/shares/test-id/stats",
            "/api/v1/analytics/shares/test-id/access-logs",
            "/api/v1/analytics/metrics/summary",
            "/api/v1/analytics/dashboard"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should require authentication
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_analytics_error_handling(self):
        """Test analytics error handling."""
        with patch('app.services.analytics_service.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.side_effect = Exception("Database error")
            
            with pytest.raises(Exception):
                await analytics_service.get_share_analytics(
                    user_id="test_user"
                )

    def test_analytics_input_validation(self, client):
        """Test input validation for analytics endpoints."""
        # Test invalid UUID
        response = client.get(
            "/api/v1/analytics/shares/invalid-uuid/stats",
            headers={"Authorization": "Bearer fake-token"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_analytics_permission_checks(self, sample_shares, mock_db):
        """Test that analytics properly checks permissions."""
        # Test insufficient permissions
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch('app.services.role_permission_service.role_permission_service.check_permission') as mock_check:
                mock_check.return_value = AsyncMock(has_permission=False)
                
                with pytest.raises(ValueError, match="Insufficient permissions"):
                    await analytics_service.get_share_stats(
                        share_id=sample_shares[0].share_id,
                        user_id="unauthorized_user"
                    )


class TestAnalyticsModels:
    """Test suite for analytics data models."""

    def test_share_analytics_response_model(self):
        """Test ShareAnalyticsResponse model validation."""
        from app.models.sharing_models import ShareAnalyticsResponse
        
        data = {
            "total_shares": 10,
            "active_shares": 8,
            "expired_shares": 2,
            "shares_by_type": {"report": 5, "dashboard": 3, "chart": 2},
            "shares_by_permission": {"view": 10, "download": 6},
            "shares_by_access_method": {"link": 8, "email_invite": 2},
            "total_views_all_shares": 1000,
            "total_downloads_all_shares": 200,
            "average_views_per_share": 100.0,
            "most_viewed_shares": [],
            "shares_created_this_week": 3,
            "shares_created_this_month": 10,
            "views_this_week": 150,
            "views_this_month": 500
        }
        
        response = ShareAnalyticsResponse(**data)
        assert response.total_shares == 10
        assert response.average_views_per_share == 100.0
        assert isinstance(response.shares_by_type, dict)

    def test_share_stats_response_model(self):
        """Test ShareStatsResponse model validation."""
        from app.models.sharing_models import ShareStatsResponse
        
        data = {
            "share_id": uuid4(),
            "total_views": 100,
            "total_downloads": 25,
            "unique_viewers": 30,
            "daily_views": [{"date": "2024-01-01", "views": 10}],
            "top_referrers": [{"referrer": "google.com", "count": 5}],
            "geographic_distribution": [{"country": "US", "count": 20}],
            "device_types": {"desktop": 15, "mobile": 10, "tablet": 5},
            "access_timeline": [],
            "average_session_duration": 45.5,
            "bounce_rate": 25.0,
            "conversion_rate": 10.0
        }
        
        response = ShareStatsResponse(**data)
        assert response.total_views == 100
        assert response.bounce_rate == 25.0
        assert len(response.daily_views) == 1

    def test_access_log_entry_model(self):
        """Test AccessLogEntry model validation."""
        from app.models.sharing_models import AccessLogEntry
        
        data = {
            "log_id": uuid4(),
            "share_id": uuid4(),
            "accessed_at": datetime.now(timezone.utc),
            "user_email": "test@example.com",
            "ip_address": "192.168.1.1",
            "user_agent": "TestAgent/1.0",
            "referrer": "https://example.com",
            "action": "view",
            "success": True,
            "error_message": None,
            "session_duration": 30.0,
            "metadata": {"key": "value"}
        }
        
        entry = AccessLogEntry(**data)
        assert entry.action == "view"
        assert entry.success is True
        assert entry.session_duration == 30.0


class TestAnalyticsIntegration:
    """Integration tests for analytics functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_analytics_workflow(self, sample_shares, sample_access_logs, mock_db):
        """Test complete analytics workflow from data to insights."""
        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch.object(analytics_service, '_calculate_views_in_period', return_value=250):
                # Mock all database interactions
                mock_db.execute.side_effect = [
                    # Permission check
                    AsyncMock(scalar_one_or_none=lambda: None),
                    # Shares query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: sample_shares)),
                    # Views calculation queries
                    AsyncMock(scalar=lambda: 100),  # Week views
                    AsyncMock(scalar=lambda: 200)   # Month views
                ]

                # Get analytics
                analytics = await analytics_service.get_share_analytics(
                    user_id="test_user",
                    start_date=datetime.now(timezone.utc) - timedelta(days=30),
                    end_date=datetime.now(timezone.utc)
                )

                # Verify complete analytics data
                assert analytics.total_shares > 0
                assert analytics.total_views_all_shares > 0
                assert len(analytics.most_viewed_shares) > 0
                assert isinstance(analytics.shares_by_type, dict)
                assert isinstance(analytics.shares_by_permission, dict)

                # Test detailed stats for one share
                share = sample_shares[0]
                relevant_logs = [log for log in sample_access_logs if log.share_id == share.share_id]
                
                mock_db.execute.side_effect = [
                    # Get share
                    AsyncMock(scalar_one_or_none=lambda: share),
                    # Permission check
                    AsyncMock(has_permission=True),
                    # Get access logs
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: relevant_logs))
                ]

                stats = await analytics_service.get_share_stats(
                    share_id=share.share_id,
                    user_id="test_user"
                )

                assert stats.share_id == share.share_id
                assert len(stats.daily_views) > 0
                assert stats.total_views == share.total_views

    @pytest.mark.asyncio
    async def test_analytics_performance_with_large_dataset(self, mock_db):
        """Test analytics performance with large datasets."""
        # Create a large number of mock shares
        large_share_set = []
        for i in range(1000):
            share = SharedResource(
                share_id=uuid4(),
                resource_type=ShareType.REPORT,
                resource_id=uuid4(),
                resource_name=f"Share {i}",
                share_token=f"token{i}",
                permissions=["view"],
                access_method=AccessMethod.LINK,
                requires_authentication=True,
                status=ShareStatus.ACTIVE,
                total_views=i * 2,
                total_downloads=i,
                unique_viewers=i,
                created_by="performance_user",
                created_at=datetime.now(timezone.utc) - timedelta(days=i % 30)
            )
            large_share_set.append(share)

        with patch('app.services.analytics_service.get_database', return_value=mock_db):
            with patch.object(analytics_service, '_calculate_views_in_period', return_value=50000):
                # Mock database to return large dataset
                mock_db.execute.side_effect = [
                    # Permission check
                    AsyncMock(scalar_one_or_none=lambda: None),
                    # Large shares query
                    AsyncMock(scalars=lambda: AsyncMock(all=lambda: large_share_set))
                ]

                # This should complete without performance issues
                analytics = await analytics_service.get_share_analytics(
                    user_id="performance_user"
                )

                assert analytics.total_shares == 1000
                assert analytics.total_views_all_shares > 0
                assert len(analytics.most_viewed_shares) <= 10  # Should be limited