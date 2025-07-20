"""
Tests for Alert Correlation Engine.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.correlation_engine import CorrelationEngine, CorrelationGroup
from app.models.alert import AlertIncident, IncidentStatus


@pytest.fixture
def correlation_engine():
    """Create CorrelationEngine instance for testing."""
    return CorrelationEngine()


@pytest.fixture
def sample_incidents():
    """Create sample alert incidents for testing."""
    base_time = datetime.utcnow()
    
    incidents = []
    for i in range(5):
        incident = AlertIncident(
            id=f"incident-{i+1}",
            rule_id=f"rule-{(i % 2) + 1}",  # Alternate between rule-1 and rule-2
            status=IncidentStatus.OPEN.value,
            severity="high" if i < 2 else "medium",
            title=f"Server {i+1} Alert",
            description=f"Issue detected on server-{i+1}",
            triggered_at=base_time - timedelta(minutes=i*3),
            trigger_data=[{
                "host": f"server-{i+1}",
                "cpu_usage": 80 + (i * 2),
                "_time": (base_time - timedelta(minutes=i*3)).isoformat()
            }],
            affected_entities=[f"server-{i+1}"],
            metadata={"source": "monitoring", "region": "us-west" if i < 3 else "us-east"}
        )
        incidents.append(incident)
    
    return incidents


@pytest.fixture
def sample_correlation_group(sample_incidents):
    """Create sample correlation group."""
    return CorrelationGroup(
        id="group-123",
        incidents=sample_incidents[:3],  # First 3 incidents
        correlation_type="time_window",
        correlation_score=0.85,
        created_at=datetime.utcnow() - timedelta(minutes=15),
        last_updated=datetime.utcnow() - timedelta(minutes=5)
    )


class TestCorrelationEngine:
    """Test suite for CorrelationEngine class."""
    
    def test_correlation_engine_initialization(self, correlation_engine):
        """Test CorrelationEngine initialization."""
        assert correlation_engine.logger is not None
        assert len(correlation_engine.correlation_strategies) == 4
        assert correlation_engine.active_groups == {}
        assert correlation_engine.time_window_minutes == 15
        assert correlation_engine.max_group_size == 20
        assert correlation_engine.min_correlation_score == 0.5
    
    @pytest.mark.asyncio
    async def test_correlate_incident_new_group(self, correlation_engine, sample_incidents):
        """Test correlating incident when no existing groups match."""
        incident = sample_incidents[0]
        
        # Mock methods
        with patch.object(correlation_engine, '_find_best_correlation_group') as mock_find, \
             patch.object(correlation_engine, '_create_correlation_group') as mock_create:
            
            mock_find.return_value = None  # No existing group
            mock_create.return_value = "new-group-123"
            
            result = await correlation_engine.correlate_incident(incident)
            
            assert result == "new-group-123"
            mock_find.assert_called_once_with(incident)
            mock_create.assert_called_once_with(incident)
    
    @pytest.mark.asyncio
    async def test_correlate_incident_existing_group(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test correlating incident with existing group."""
        incident = sample_incidents[3]  # New incident
        
        # Add sample group to active groups
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        with patch.object(correlation_engine, '_find_best_correlation_group') as mock_find:
            mock_find.return_value = sample_correlation_group
            
            result = await correlation_engine.correlate_incident(incident)
            
            assert result == "group-123"
            assert len(sample_correlation_group.incidents) == 4  # Original 3 + 1 new
            assert incident in sample_correlation_group.incidents
            mock_find.assert_called_once_with(incident)
    
    @pytest.mark.asyncio
    async def test_correlate_incident_error_handling(self, correlation_engine, sample_incidents):
        """Test correlation with error handling."""
        incident = sample_incidents[0]
        
        with patch.object(correlation_engine, '_find_best_correlation_group') as mock_find:
            mock_find.side_effect = Exception("Correlation error")
            
            result = await correlation_engine.correlate_incident(incident)
            
            assert result is None  # Should return None on error
    
    @pytest.mark.asyncio
    async def test_find_best_correlation_group_success(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test finding best correlation group successfully."""
        incident = sample_incidents[3]
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        with patch.object(correlation_engine, '_is_group_expired') as mock_expired, \
             patch.object(correlation_engine, '_calculate_correlation_score') as mock_score:
            
            mock_expired.return_value = False
            mock_score.return_value = 0.75  # Above min threshold
            
            result = await correlation_engine._find_best_correlation_group(incident)
            
            assert result == sample_correlation_group
            mock_expired.assert_called_once_with(sample_correlation_group)
            mock_score.assert_called_once_with(incident, sample_correlation_group)
    
    @pytest.mark.asyncio
    async def test_find_best_correlation_group_expired_group(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test finding correlation group with expired group."""
        incident = sample_incidents[3]
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        with patch.object(correlation_engine, '_is_group_expired') as mock_expired:
            mock_expired.return_value = True  # Group is expired
            
            result = await correlation_engine._find_best_correlation_group(incident)
            
            assert result is None
            mock_expired.assert_called_once_with(sample_correlation_group)
    
    @pytest.mark.asyncio
    async def test_find_best_correlation_group_low_score(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test finding correlation group with low correlation score."""
        incident = sample_incidents[3]
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        with patch.object(correlation_engine, '_is_group_expired') as mock_expired, \
             patch.object(correlation_engine, '_calculate_correlation_score') as mock_score:
            
            mock_expired.return_value = False
            mock_score.return_value = 0.3  # Below min threshold (0.5)
            
            result = await correlation_engine._find_best_correlation_group(incident)
            
            assert result is None
            mock_score.assert_called_once_with(incident, sample_correlation_group)
    
    @pytest.mark.asyncio
    async def test_calculate_correlation_score(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test correlation score calculation."""
        incident = sample_incidents[3]
        
        with patch.object(correlation_engine, '_correlate_by_source') as mock_source, \
             patch.object(correlation_engine, '_correlate_by_time_window') as mock_time, \
             patch.object(correlation_engine, '_correlate_by_pattern') as mock_pattern, \
             patch.object(correlation_engine, '_correlate_by_root_cause') as mock_root:
            
            # Mock different strategy scores
            mock_source.return_value = 0.8
            mock_time.return_value = 0.6
            mock_pattern.return_value = 0.4
            mock_root.return_value = 0.9
            
            score = await correlation_engine._calculate_correlation_score(incident, sample_correlation_group)
            
            # Should return the highest score
            assert score == 0.9
            
            # All strategies should be called
            mock_source.assert_called_once_with(incident, sample_correlation_group)
            mock_time.assert_called_once_with(incident, sample_correlation_group)
            mock_pattern.assert_called_once_with(incident, sample_correlation_group)
            mock_root.assert_called_once_with(incident, sample_correlation_group)
    
    @pytest.mark.asyncio
    async def test_create_correlation_group(self, correlation_engine, sample_incidents):
        """Test creating new correlation group."""
        incident = sample_incidents[0]
        
        group_id = await correlation_engine._create_correlation_group(incident)
        
        assert group_id is not None
        assert group_id in correlation_engine.active_groups
        
        group = correlation_engine.active_groups[group_id]
        assert len(group.incidents) == 1
        assert group.incidents[0] == incident
        assert group.correlation_type == "new"
        assert group.correlation_score == 1.0
    
    def test_is_group_expired_not_expired(self, correlation_engine, sample_correlation_group):
        """Test group expiration check - not expired."""
        # Group was last updated 5 minutes ago, within window
        result = correlation_engine._is_group_expired(sample_correlation_group)
        assert result is False
    
    def test_is_group_expired_expired(self, correlation_engine, sample_correlation_group):
        """Test group expiration check - expired."""
        # Modify group to be older than time window
        sample_correlation_group.last_updated = datetime.utcnow() - timedelta(minutes=30)
        
        result = correlation_engine._is_group_expired(sample_correlation_group)
        assert result is True


class TestCorrelationStrategies:
    """Test suite for correlation strategies."""
    
    @pytest.fixture
    def correlation_engine(self):
        """Create CorrelationEngine instance."""
        return CorrelationEngine()
    
    def test_correlate_by_source_same_rule(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test source correlation with same rule ID."""
        # Create incident with same rule ID as group incidents
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",  # Same as sample_correlation_group incidents
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=datetime.utcnow()
        )
        
        score = correlation_engine._correlate_by_source(incident, sample_correlation_group)
        assert score == 1.0  # Perfect match for same rule
    
    def test_correlate_by_source_different_rule(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test source correlation with different rule ID."""
        # Create incident with different rule ID
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-999",  # Different from group incidents
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=datetime.utcnow()
        )
        
        score = correlation_engine._correlate_by_source(incident, sample_correlation_group)
        assert score == 0.0  # No match for different rule
    
    def test_correlate_by_time_window_within_window(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test time window correlation within window."""
        # Create incident within time window
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=recent_time
        )
        
        score = correlation_engine._correlate_by_time_window(incident, sample_correlation_group)
        assert score > 0.5  # Should have reasonable correlation within window
    
    def test_correlate_by_time_window_outside_window(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test time window correlation outside window."""
        # Create incident outside time window
        old_time = datetime.utcnow() - timedelta(hours=2)
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=old_time
        )
        
        score = correlation_engine._correlate_by_time_window(incident, sample_correlation_group)
        assert score == 0.0  # No correlation outside window
    
    def test_correlate_by_pattern_matching_entities(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test pattern correlation with matching entities."""
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Server 1 Alert",  # Similar pattern to group incidents
            description="Issue detected on server-1",
            triggered_at=datetime.utcnow(),
            affected_entities=["server-1"]  # Matches entities in group
        )
        
        score = correlation_engine._correlate_by_pattern(incident, sample_correlation_group)
        assert score > 0.0  # Should have some correlation
    
    def test_correlate_by_pattern_no_matching_entities(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test pattern correlation with no matching entities."""
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Database Alert",  # Different pattern
            description="Database connection error",
            triggered_at=datetime.utcnow(),
            affected_entities=["database-1"]  # No overlap with group
        )
        
        score = correlation_engine._correlate_by_pattern(incident, sample_correlation_group)
        assert score == 0.0  # No pattern correlation
    
    def test_correlate_by_root_cause_same_metadata(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test root cause correlation with same metadata."""
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=datetime.utcnow(),
            metadata={"source": "monitoring", "region": "us-west"}  # Matches group metadata
        )
        
        score = correlation_engine._correlate_by_root_cause(incident, sample_correlation_group)
        assert score > 0.0  # Should have correlation based on metadata
    
    def test_correlate_by_root_cause_different_metadata(self, correlation_engine, sample_incidents, sample_correlation_group):
        """Test root cause correlation with different metadata."""
        incident = AlertIncident(
            id="test-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            description="Test description",
            triggered_at=datetime.utcnow(),
            metadata={"source": "application", "region": "eu-west"}  # Different metadata
        )
        
        score = correlation_engine._correlate_by_root_cause(incident, sample_correlation_group)
        assert score == 0.0  # No correlation with different metadata


class TestCorrelationGroupManagement:
    """Test suite for correlation group management."""
    
    @pytest.fixture
    def correlation_engine(self):
        """Create CorrelationEngine instance."""
        return CorrelationEngine()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_groups(self, correlation_engine, sample_correlation_group):
        """Test cleanup of expired correlation groups."""
        # Add expired group
        expired_group = CorrelationGroup(
            id="expired-group",
            incidents=[],
            correlation_type="time_window",
            correlation_score=0.5,
            created_at=datetime.utcnow() - timedelta(hours=2),
            last_updated=datetime.utcnow() - timedelta(hours=1)
        )
        
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        correlation_engine.active_groups["expired-group"] = expired_group
        
        cleaned_count = await correlation_engine.cleanup_expired_groups()
        
        assert cleaned_count == 1
        assert "expired-group" not in correlation_engine.active_groups
        assert "group-123" in correlation_engine.active_groups
    
    @pytest.mark.asyncio
    async def test_get_correlation_groups(self, correlation_engine, sample_correlation_group):
        """Test getting correlation groups."""
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        groups = await correlation_engine.get_correlation_groups()
        
        assert len(groups) == 1
        assert groups[0] == sample_correlation_group
    
    @pytest.mark.asyncio
    async def test_get_correlation_groups_by_type(self, correlation_engine, sample_correlation_group):
        """Test getting correlation groups by type."""
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        groups = await correlation_engine.get_correlation_groups(correlation_type="time_window")
        
        assert len(groups) == 1
        assert groups[0].correlation_type == "time_window"
    
    @pytest.mark.asyncio
    async def test_get_correlation_analytics(self, correlation_engine, sample_correlation_group):
        """Test getting correlation analytics."""
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        
        analytics = await correlation_engine.get_correlation_analytics()
        
        assert "total_groups" in analytics
        assert "active_groups" in analytics
        assert "avg_group_size" in analytics
        assert "correlation_types" in analytics
        assert analytics["total_groups"] == 1
    
    @pytest.mark.asyncio
    async def test_update_correlation_group(self, correlation_engine, sample_correlation_group, sample_incidents):
        """Test updating correlation group."""
        correlation_engine.active_groups["group-123"] = sample_correlation_group
        new_incident = sample_incidents[4]
        
        result = await correlation_engine.update_correlation_group("group-123", new_incident)
        
        assert result is True
        assert new_incident in sample_correlation_group.incidents
        assert len(sample_correlation_group.incidents) == 4  # Original 3 + 1 new
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_correlation_group(self, correlation_engine, sample_incidents):
        """Test updating non-existent correlation group."""
        new_incident = sample_incidents[0]
        
        result = await correlation_engine.update_correlation_group("nonexistent", new_incident)
        
        assert result is False


class TestCorrelationPerformance:
    """Test suite for correlation performance."""
    
    @pytest.fixture
    def correlation_engine(self):
        """Create CorrelationEngine instance."""
        return CorrelationEngine()
    
    @pytest.mark.asyncio
    async def test_correlation_with_many_groups(self, correlation_engine):
        """Test correlation performance with many groups."""
        # Create many correlation groups
        for i in range(50):
            group = CorrelationGroup(
                id=f"group-{i}",
                incidents=[],
                correlation_type="time_window",
                correlation_score=0.5,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            correlation_engine.active_groups[f"group-{i}"] = group
        
        # Create test incident
        incident = AlertIncident(
            id="performance-test",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Performance Test",
            description="Test incident",
            triggered_at=datetime.utcnow()
        )
        
        import time
        start_time = time.time()
        
        result = await correlation_engine.correlate_incident(incident)
        
        end_time = time.time()
        correlation_time = end_time - start_time
        
        # Correlation should complete in reasonable time (< 1 second)
        assert correlation_time < 1.0
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_correlation_with_large_groups(self, correlation_engine):
        """Test correlation with large incident groups."""
        # Create group with many incidents
        incidents = []
        for i in range(15):  # Near max group size
            incident = AlertIncident(
                id=f"incident-{i}",
                rule_id="rule-1",
                status=IncidentStatus.OPEN.value,
                severity="medium",
                title=f"Alert {i}",
                description=f"Test incident {i}",
                triggered_at=datetime.utcnow() - timedelta(minutes=i)
            )
            incidents.append(incident)
        
        large_group = CorrelationGroup(
            id="large-group",
            incidents=incidents,
            correlation_type="pattern",
            correlation_score=0.8,
            created_at=datetime.utcnow() - timedelta(minutes=30),
            last_updated=datetime.utcnow()
        )
        
        correlation_engine.active_groups["large-group"] = large_group
        
        # Test with new incident
        new_incident = AlertIncident(
            id="new-incident",
            rule_id="rule-1",
            status=IncidentStatus.OPEN.value,
            severity="medium",
            title="New Alert",
            description="New test incident",
            triggered_at=datetime.utcnow()
        )
        
        result = await correlation_engine.correlate_incident(new_incident)
        
        # Should either add to existing group or create new one
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])