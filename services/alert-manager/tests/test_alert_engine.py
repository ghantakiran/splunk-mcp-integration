"""
Tests for Alert Engine functionality.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services.alert_engine import AlertEngine
from app.models.alert import NaturalLanguageAlertRequest, IncidentSeverity


@pytest.fixture
def alert_engine():
    """Create AlertEngine instance for testing."""
    return AlertEngine()


@pytest.fixture
def sample_nl_request():
    """Sample natural language alert request."""
    return NaturalLanguageAlertRequest(
        description="Alert me when CPU usage exceeds 80% for 5 minutes",
        severity=IncidentSeverity.HIGH,
        tags=["performance", "cpu"],
        additional_context={"environment": "production"}
    )


class TestAlertEngine:
    """Test cases for AlertEngine."""
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_threshold(self, alert_engine):
        """Test parsing natural language with threshold condition."""
        description = "Alert me when CPU usage exceeds 80% for 5 minutes"
        
        parsed = await alert_engine._parse_natural_language(description)
        
        assert parsed["threshold_value"] == 80.0
        assert parsed["threshold_operator"] == ">"
        assert parsed["time_window"] == 300  # 5 minutes in seconds
        assert len(parsed["conditions"]) > 0
        assert any(
            condition["field_name"] == "cpu_usage" 
            for condition in parsed["conditions"]
        )
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_statistical(self, alert_engine):
        """Test parsing natural language with statistical condition."""
        description = "Alert me when average response time exceeds 2 seconds"
        
        parsed = await alert_engine._parse_natural_language(description)
        
        assert parsed["threshold_value"] == 2.0
        assert any(
            condition["condition_type"] == "statistical" 
            for condition in parsed["conditions"]
        )
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_pattern(self, alert_engine):
        """Test parsing natural language with pattern condition."""
        description = "Alert me when log level contains 'ERROR'"
        
        parsed = await alert_engine._parse_natural_language(description)
        
        assert any(
            condition["condition_type"] == "pattern" 
            for condition in parsed["conditions"]
        )
    
    def test_extract_operator_and_value(self, alert_engine):
        """Test operator and value extraction."""
        operator, value = alert_engine._extract_operator_and_value(
            "cpu usage exceeds 80%", "80%"
        )
        
        assert operator == ">"
        assert value == 0.8  # 80% converted to decimal
    
    def test_generate_alert_name(self, alert_engine):
        """Test alert name generation."""
        description = "Alert me when CPU usage exceeds 80% for 5 minutes"
        name = alert_engine._generate_alert_name(description)
        
        assert "cpu usage exceeds" in name.lower()
        assert len(name) > 0
    
    @pytest.mark.asyncio
    @patch('app.services.alert_engine.httpx.AsyncClient')
    async def test_generate_spl_query_success(self, mock_client, alert_engine):
        """Test SPL query generation with successful NLP service response."""
        # Mock NLP service response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "spl_query": "search index=main | where cpu_usage > 80"
        }
        mock_response.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        parsed_alert = {
            "conditions": [{"field_name": "cpu_usage", "operator": ">", "value": "80"}]
        }
        
        spl_query = await alert_engine._generate_spl_query(parsed_alert, {})
        
        assert "cpu_usage > 80" in spl_query
    
    @pytest.mark.asyncio
    @patch('app.services.alert_engine.httpx.AsyncClient')
    async def test_generate_spl_query_fallback(self, mock_client, alert_engine):
        """Test SPL query generation with fallback when NLP service fails."""
        # Mock NLP service failure
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Service unavailable")
        
        parsed_alert = {
            "conditions": [{"field_name": "cpu_usage", "operator": ">", "value": "80"}]
        }
        
        spl_query = await alert_engine._generate_spl_query(parsed_alert, {})
        
        assert "search index=main" in spl_query
        assert "cpu_usage > 80" in spl_query
    
    @pytest.mark.asyncio
    async def test_create_alert_from_natural_language(
        self, alert_engine, sample_nl_request
    ):
        """Test creating alert from natural language."""
        with patch.object(alert_engine, '_generate_spl_query') as mock_spl:
            mock_spl.return_value = "search index=main | where cpu_usage > 80"
            
            result = await alert_engine.create_alert_from_natural_language(
                request=sample_nl_request,
                user_id="test_user",
                organization_id="test_org"
            )
            
            assert result.name
            assert result.description == sample_nl_request.description
            assert result.severity == sample_nl_request.severity
            assert result.tags == sample_nl_request.tags
            assert result.spl_query == "search index=main | where cpu_usage > 80"
    
    @pytest.mark.asyncio
    async def test_check_alert_conditions_threshold_exceeded(self, alert_engine):
        """Test alert condition checking when threshold is exceeded."""
        from app.models.alert import AlertRule
        
        # Create mock rule
        rule = AlertRule(
            id="test_rule",
            name="Test Rule",
            threshold_value=80.0,
            threshold_operator=">",
            spl_query="search index=main"
        )
        
        # Mock query result with value exceeding threshold
        query_result = {
            "results": [{"value": 85.5}],
            "summary": {"max_value": 85.5}
        }
        
        result = await alert_engine._check_alert_conditions(rule, query_result)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_alert_conditions_threshold_not_exceeded(self, alert_engine):
        """Test alert condition checking when threshold is not exceeded."""
        from app.models.alert import AlertRule
        
        # Create mock rule
        rule = AlertRule(
            id="test_rule",
            name="Test Rule",
            threshold_value=80.0,
            threshold_operator=">",
            spl_query="search index=main"
        )
        
        # Mock query result with value below threshold
        query_result = {
            "results": [{"value": 75.0}],
            "summary": {"max_value": 75.0}
        }
        
        result = await alert_engine._check_alert_conditions(rule, query_result)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_spl_query(self, alert_engine):
        """Test SPL query execution (mock implementation)."""
        query_result = await alert_engine._execute_spl_query("search index=main")
        
        assert "results" in query_result
        assert "count" in query_result
        assert "summary" in query_result
        assert isinstance(query_result["results"], list)


if __name__ == "__main__":
    pytest.main([__file__])