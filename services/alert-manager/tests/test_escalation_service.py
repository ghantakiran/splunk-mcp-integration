"""
Tests for Escalation Service.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.escalation_service import EscalationService
from app.models.escalation import EscalationRule, EscalationRuleCreate
from app.models.alert import AlertIncident, IncidentStatus


@pytest.fixture
def escalation_service():
    """Create EscalationService instance for testing."""
    return EscalationService()


@pytest.fixture
def sample_escalation_rule():
    """Sample escalation rule for testing."""
    return EscalationRule(
        id="escalation-rule-123",
        name="Standard Escalation",
        description="Standard escalation workflow",
        alert_rule_id="alert-rule-123",
        escalation_levels=[
            {
                "level": 1,
                "delay_minutes": 0,
                "notification_channels": ["email-channel-123"],
                "assignees": ["oncall@test.com"],
                "conditions": {"severity": ["high", "critical"]}
            },
            {
                "level": 2,
                "delay_minutes": 15,
                "notification_channels": ["slack-channel-123"],
                "assignees": ["manager@test.com"],
                "conditions": {"status": "open", "age_minutes": 15}
            },
            {
                "level": 3,
                "delay_minutes": 30,
                "notification_channels": ["teams-channel-123"],
                "assignees": ["director@test.com"],
                "conditions": {"status": "open", "age_minutes": 30}
            }
        ],
        max_escalations=3,
        auto_resolve=True,
        auto_resolve_timeout=3600,
        is_active=True,
        created_by="test-user-123",
        organization_id="test-org-123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_incident():
    """Sample alert incident for testing."""
    return AlertIncident(
        id="incident-123",
        rule_id="alert-rule-123",
        status=IncidentStatus.OPEN.value,
        severity="high",
        title="High Severity Alert",
        description="Critical issue detected",
        triggered_at=datetime.utcnow() - timedelta(minutes=20),
        escalation_level=0,
        last_escalated_at=None,
        notification_sent=False
    )


class TestEscalationService:
    """Test suite for EscalationService class."""
    
    def test_escalation_service_initialization(self, escalation_service):
        """Test EscalationService initialization."""
        assert escalation_service.logger is not None
        assert escalation_service.check_interval == 60  # Default check interval
        assert escalation_service.max_concurrent_escalations == 50
    
    @pytest.mark.asyncio
    async def test_create_escalation_rule_success(self, escalation_service):
        """Test successful escalation rule creation."""
        rule_data = EscalationRuleCreate(
            name="Test Escalation",
            description="Test escalation rule",
            alert_rule_id="alert-rule-456",
            escalation_levels=[
                {
                    "level": 1,
                    "delay_minutes": 0,
                    "notification_channels": ["channel-123"],
                    "assignees": ["user@test.com"]
                }
            ],
            max_escalations=2,
            auto_resolve=True,
            auto_resolve_timeout=1800
        )
        user_id = "test-user-123"
        
        with patch.object(escalation_service, '_validate_escalation_rule') as mock_validate, \
             patch.object(escalation_service, '_save_escalation_rule') as mock_save:
            
            mock_validate.return_value = None
            mock_save.return_value = EscalationRule(
                id="new-escalation-123",
                name=rule_data.name,
                description=rule_data.description,
                alert_rule_id=rule_data.alert_rule_id,
                escalation_levels=rule_data.escalation_levels,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            result = await escalation_service.create_escalation_rule(rule_data, user_id)
            
            assert result.name == rule_data.name
            assert result.alert_rule_id == rule_data.alert_rule_id
            assert result.created_by == user_id
            mock_validate.assert_called_once()
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_escalation_rule_validation_error(self, escalation_service):
        """Test escalation rule creation with validation error."""
        rule_data = EscalationRuleCreate(
            name="Invalid Rule",
            alert_rule_id="nonexistent-rule",
            escalation_levels=[],  # Empty levels should fail validation
            max_escalations=0
        )
        user_id = "test-user-123"
        
        with patch.object(escalation_service, '_validate_escalation_rule') as mock_validate:
            mock_validate.side_effect = ValueError("Escalation levels cannot be empty")
            
            with pytest.raises(ValueError, match="Escalation levels cannot be empty"):
                await escalation_service.create_escalation_rule(rule_data, user_id)
    
    @pytest.mark.asyncio
    async def test_evaluate_escalation_success(self, escalation_service, sample_escalation_rule, sample_incident):
        """Test successful escalation evaluation."""
        # Mock incident that should be escalated (age > 15 minutes, level 0)
        sample_incident.escalation_level = 0
        sample_incident.triggered_at = datetime.utcnow() - timedelta(minutes=20)
        
        with patch.object(escalation_service, '_get_escalation_rule') as mock_get_rule, \
             patch.object(escalation_service, '_should_escalate') as mock_should, \
             patch.object(escalation_service, '_perform_escalation') as mock_perform:
            
            mock_get_rule.return_value = sample_escalation_rule
            mock_should.return_value = True
            mock_perform.return_value = True
            
            result = await escalation_service.evaluate_escalation(sample_incident)
            
            assert result["escalated"] is True
            assert result["new_level"] == 1
            mock_get_rule.assert_called_once()
            mock_should.assert_called_once()
            mock_perform.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_escalation_no_rule(self, escalation_service, sample_incident):
        """Test escalation evaluation with no escalation rule."""
        with patch.object(escalation_service, '_get_escalation_rule') as mock_get_rule:
            mock_get_rule.return_value = None
            
            result = await escalation_service.evaluate_escalation(sample_incident)
            
            assert result["escalated"] is False
            assert result["reason"] == "no_escalation_rule"
    
    @pytest.mark.asyncio
    async def test_evaluate_escalation_should_not_escalate(self, escalation_service, sample_escalation_rule, sample_incident):
        """Test escalation evaluation when incident should not be escalated."""
        # Recent incident that shouldn't be escalated yet
        sample_incident.triggered_at = datetime.utcnow() - timedelta(minutes=5)
        
        with patch.object(escalation_service, '_get_escalation_rule') as mock_get_rule, \
             patch.object(escalation_service, '_should_escalate') as mock_should:
            
            mock_get_rule.return_value = sample_escalation_rule
            mock_should.return_value = False
            
            result = await escalation_service.evaluate_escalation(sample_incident)
            
            assert result["escalated"] is False
            assert result["reason"] == "conditions_not_met"
    
    @pytest.mark.asyncio
    async def test_escalate_incident_success(self, escalation_service, sample_incident):
        """Test successful incident escalation."""
        target_level = 2
        escalation_config = {
            "level": 2,
            "delay_minutes": 15,
            "notification_channels": ["slack-channel-123"],
            "assignees": ["manager@test.com"]
        }
        
        with patch.object(escalation_service, '_send_escalation_notifications') as mock_notify, \
             patch.object(escalation_service, '_update_incident_escalation') as mock_update, \
             patch.object(escalation_service, '_log_escalation') as mock_log:
            
            mock_notify.return_value = True
            mock_update.return_value = None
            mock_log.return_value = None
            
            result = await escalation_service.escalate_incident(
                sample_incident, target_level, escalation_config
            )
            
            assert result is True
            mock_notify.assert_called_once()
            mock_update.assert_called_once()
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_escalate_incident_notification_failure(self, escalation_service, sample_incident):
        """Test incident escalation with notification failure."""
        target_level = 2
        escalation_config = {
            "level": 2,
            "notification_channels": ["invalid-channel"],
            "assignees": ["manager@test.com"]
        }
        
        with patch.object(escalation_service, '_send_escalation_notifications') as mock_notify:
            mock_notify.side_effect = Exception("Notification failed")
            
            result = await escalation_service.escalate_incident(
                sample_incident, target_level, escalation_config
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_escalation_rule_success(self, escalation_service, sample_escalation_rule):
        """Test successful escalation rule testing."""
        test_incident = AlertIncident(
            id="test-incident",
            rule_id=sample_escalation_rule.alert_rule_id,
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Test Alert",
            triggered_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        with patch.object(escalation_service, '_simulate_escalation') as mock_simulate:
            mock_simulate.return_value = {
                "test_successful": True,
                "escalation_path": [
                    {"level": 1, "delay": 0, "triggered": True},
                    {"level": 2, "delay": 15, "triggered": True},
                    {"level": 3, "delay": 30, "triggered": True}
                ],
                "notifications_sent": 3,
                "total_delay": 45
            }
            
            result = await escalation_service.test_escalation_rule(
                sample_escalation_rule, test_incident
            )
            
            assert result["test_successful"] is True
            assert len(result["escalation_path"]) == 3
            assert result["notifications_sent"] == 3
            mock_simulate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_escalation_history_success(self, escalation_service):
        """Test successful escalation history retrieval."""
        incident_id = "incident-123"
        
        mock_history = [
            {
                "id": "esc-1",
                "incident_id": incident_id,
                "from_level": 0,
                "to_level": 1,
                "escalated_at": datetime.utcnow() - timedelta(minutes=30),
                "reason": "timeout"
            },
            {
                "id": "esc-2",
                "incident_id": incident_id,
                "from_level": 1,
                "to_level": 2,
                "escalated_at": datetime.utcnow() - timedelta(minutes=15),
                "reason": "manual"
            }
        ]
        
        with patch.object(escalation_service, '_get_escalation_history_from_db') as mock_get:
            mock_get.return_value = mock_history
            
            result = await escalation_service.get_escalation_history(incident_id)
            
            assert len(result) == 2
            assert result[0]["to_level"] == 1
            assert result[1]["to_level"] == 2
            mock_get.assert_called_once_with(incident_id)


class TestEscalationServiceHelperMethods:
    """Test suite for EscalationService helper methods."""
    
    @pytest.fixture
    def escalation_service(self):
        """Create EscalationService instance."""
        return EscalationService()
    
    def test_should_escalate_time_based_true(self, escalation_service, sample_incident):
        """Test time-based escalation condition - should escalate."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 10,
            "conditions": {"age_minutes": 15}
        }
        
        # Incident is 20 minutes old, should escalate
        sample_incident.triggered_at = datetime.utcnow() - timedelta(minutes=20)
        sample_incident.escalation_level = 0
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is True
    
    def test_should_escalate_time_based_false(self, escalation_service, sample_incident):
        """Test time-based escalation condition - should not escalate."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 10,
            "conditions": {"age_minutes": 15}
        }
        
        # Incident is only 5 minutes old, should not escalate
        sample_incident.triggered_at = datetime.utcnow() - timedelta(minutes=5)
        sample_incident.escalation_level = 0
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is False
    
    def test_should_escalate_severity_condition_true(self, escalation_service, sample_incident):
        """Test severity-based escalation condition - should escalate."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 0,
            "conditions": {"severity": ["high", "critical"]}
        }
        
        sample_incident.severity = "high"
        sample_incident.escalation_level = 0
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is True
    
    def test_should_escalate_severity_condition_false(self, escalation_service, sample_incident):
        """Test severity-based escalation condition - should not escalate."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 0,
            "conditions": {"severity": ["critical"]}
        }
        
        sample_incident.severity = "medium"  # Not in the escalation condition
        sample_incident.escalation_level = 0
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is False
    
    def test_should_escalate_status_condition(self, escalation_service, sample_incident):
        """Test status-based escalation condition."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 0,
            "conditions": {"status": "open"}
        }
        
        # Open incident should escalate
        sample_incident.status = IncidentStatus.OPEN.value
        sample_incident.escalation_level = 0
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is True
        
        # Resolved incident should not escalate
        sample_incident.status = IncidentStatus.RESOLVED.value
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is False
    
    def test_should_escalate_max_level_reached(self, escalation_service, sample_incident):
        """Test escalation when max level is already reached."""
        escalation_config = {
            "level": 2,
            "delay_minutes": 0,
            "conditions": {"age_minutes": 0}
        }
        
        # Incident already at level 2, should not escalate further
        sample_incident.escalation_level = 2
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is False
    
    def test_should_escalate_already_escalated_recently(self, escalation_service, sample_incident):
        """Test escalation when already escalated recently."""
        escalation_config = {
            "level": 1,
            "delay_minutes": 15,
            "conditions": {"age_minutes": 0}
        }
        
        # Last escalated 5 minutes ago, should wait longer
        sample_incident.escalation_level = 0
        sample_incident.last_escalated_at = datetime.utcnow() - timedelta(minutes=5)
        
        result = escalation_service._should_escalate(sample_incident, escalation_config)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_escalation_notifications_success(self, escalation_service):
        """Test successful escalation notification sending."""
        incident = AlertIncident(
            id="incident-123",
            title="Test Alert",
            description="Test description",
            severity="high"
        )
        
        escalation_config = {
            "level": 2,
            "notification_channels": ["email-123", "slack-456"],
            "assignees": ["manager@test.com", "director@test.com"]
        }
        
        with patch.object(escalation_service, '_send_notification_to_channel') as mock_send:
            mock_send.return_value = True
            
            result = await escalation_service._send_escalation_notifications(
                incident, escalation_config
            )
            
            assert result is True
            # Should call notification for each channel
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_escalation_notifications_partial_failure(self, escalation_service):
        """Test escalation notification with partial failures."""
        incident = AlertIncident(
            id="incident-123",
            title="Test Alert",
            severity="high"
        )
        
        escalation_config = {
            "level": 2,
            "notification_channels": ["email-123", "slack-456"],
            "assignees": ["manager@test.com"]
        }
        
        with patch.object(escalation_service, '_send_notification_to_channel') as mock_send:
            # First call succeeds, second fails
            mock_send.side_effect = [True, False]
            
            result = await escalation_service._send_escalation_notifications(
                incident, escalation_config
            )
            
            # Should return True if at least one notification succeeds
            assert result is True
            assert mock_send.call_count == 2
    
    def test_validate_escalation_rule_success(self, escalation_service):
        """Test successful escalation rule validation."""
        rule_data = EscalationRuleCreate(
            name="Valid Rule",
            alert_rule_id="alert-rule-123",
            escalation_levels=[
                {
                    "level": 1,
                    "delay_minutes": 0,
                    "notification_channels": ["channel-123"],
                    "assignees": ["user@test.com"]
                }
            ],
            max_escalations=3
        )
        
        # Should not raise any exception
        escalation_service._validate_escalation_rule(rule_data)
    
    def test_validate_escalation_rule_empty_levels(self, escalation_service):
        """Test escalation rule validation with empty levels."""
        rule_data = EscalationRuleCreate(
            name="Invalid Rule",
            alert_rule_id="alert-rule-123",
            escalation_levels=[],  # Empty levels
            max_escalations=3
        )
        
        with pytest.raises(ValueError, match="Escalation levels cannot be empty"):
            escalation_service._validate_escalation_rule(rule_data)
    
    def test_validate_escalation_rule_invalid_level_sequence(self, escalation_service):
        """Test escalation rule validation with invalid level sequence."""
        rule_data = EscalationRuleCreate(
            name="Invalid Rule",
            alert_rule_id="alert-rule-123",
            escalation_levels=[
                {
                    "level": 1,
                    "delay_minutes": 0,
                    "notification_channels": ["channel-123"],
                    "assignees": ["user@test.com"]
                },
                {
                    "level": 3,  # Should be 2, not 3
                    "delay_minutes": 15,
                    "notification_channels": ["channel-456"],
                    "assignees": ["manager@test.com"]
                }
            ],
            max_escalations=3
        )
        
        with pytest.raises(ValueError, match="Escalation levels must be sequential"):
            escalation_service._validate_escalation_rule(rule_data)
    
    def test_validate_escalation_rule_invalid_delay_sequence(self, escalation_service):
        """Test escalation rule validation with invalid delay sequence."""
        rule_data = EscalationRuleCreate(
            name="Invalid Rule",
            alert_rule_id="alert-rule-123",
            escalation_levels=[
                {
                    "level": 1,
                    "delay_minutes": 15,  # Higher delay than level 2
                    "notification_channels": ["channel-123"],
                    "assignees": ["user@test.com"]
                },
                {
                    "level": 2,
                    "delay_minutes": 5,  # Lower delay than level 1
                    "notification_channels": ["channel-456"],
                    "assignees": ["manager@test.com"]
                }
            ],
            max_escalations=3
        )
        
        with pytest.raises(ValueError, match="Escalation delays must be increasing"):
            escalation_service._validate_escalation_rule(rule_data)


class TestEscalationServiceIntegration:
    """Test suite for EscalationService integration scenarios."""
    
    @pytest.fixture
    def escalation_service(self):
        """Create EscalationService instance."""
        return EscalationService()
    
    @pytest.mark.asyncio
    async def test_full_escalation_workflow(self, escalation_service, sample_escalation_rule):
        """Test complete escalation workflow from creation to execution."""
        # Create a new incident
        incident = AlertIncident(
            id="workflow-incident",
            rule_id=sample_escalation_rule.alert_rule_id,
            status=IncidentStatus.OPEN.value,
            severity="high",
            title="Workflow Test Alert",
            triggered_at=datetime.utcnow() - timedelta(minutes=25),
            escalation_level=0
        )
        
        with patch.object(escalation_service, '_get_escalation_rule') as mock_get_rule, \
             patch.object(escalation_service, '_send_escalation_notifications') as mock_notify, \
             patch.object(escalation_service, '_update_incident_escalation') as mock_update, \
             patch.object(escalation_service, '_log_escalation') as mock_log:
            
            mock_get_rule.return_value = sample_escalation_rule
            mock_notify.return_value = True
            mock_update.return_value = None
            mock_log.return_value = None
            
            # Should escalate from level 0 to level 2 (25 minutes old)
            result = await escalation_service.evaluate_escalation(incident)
            
            assert result["escalated"] is True
            assert result["new_level"] == 2  # Should skip to appropriate level
            mock_notify.assert_called()
            mock_update.assert_called()
    
    @pytest.mark.asyncio
    async def test_escalation_with_auto_resolve(self, escalation_service):
        """Test escalation with auto-resolve functionality."""
        # Create escalation rule with auto-resolve
        escalation_rule = EscalationRule(
            id="auto-resolve-rule",
            name="Auto Resolve Rule",
            alert_rule_id="alert-rule-456",
            escalation_levels=[
                {
                    "level": 1,
                    "delay_minutes": 0,
                    "notification_channels": ["email-123"],
                    "assignees": ["oncall@test.com"]
                }
            ],
            max_escalations=1,
            auto_resolve=True,
            auto_resolve_timeout=1800,  # 30 minutes
            is_active=True
        )
        
        # Create old incident that should be auto-resolved
        incident = AlertIncident(
            id="auto-resolve-incident",
            rule_id="alert-rule-456",
            status=IncidentStatus.OPEN.value,
            severity="medium",
            triggered_at=datetime.utcnow() - timedelta(minutes=45),  # 45 minutes old
            escalation_level=1
        )
        
        with patch.object(escalation_service, '_get_escalation_rule') as mock_get_rule, \
             patch.object(escalation_service, '_auto_resolve_incident') as mock_resolve:
            
            mock_get_rule.return_value = escalation_rule
            mock_resolve.return_value = True
            
            result = await escalation_service.evaluate_escalation(incident)
            
            assert result["auto_resolved"] is True
            mock_resolve.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])