"""
Tests for AI Enhancement features including predictive analytics,
anomaly detection, and intelligent suggestions.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.ai.predictive_analytics import predictive_analytics
from app.ai.anomaly_detection import anomaly_detector
from app.ai.intelligent_suggestions import intelligent_suggestions

class TestPredictiveAnalytics:
    """Test cases for predictive analytics engine."""
    
    def setup_method(self):
        """Set up test data."""
        self.time_series_data = [
            {"_time": "2024-01-01T00:00:00Z", "value": 100},
            {"_time": "2024-01-01T01:00:00Z", "value": 105},
            {"_time": "2024-01-01T02:00:00Z", "value": 110},
            {"_time": "2024-01-01T03:00:00Z", "value": 115},
            {"_time": "2024-01-01T04:00:00Z", "value": 120},
            {"_time": "2024-01-01T05:00:00Z", "value": 125},
            {"_time": "2024-01-01T06:00:00Z", "value": 130},
            {"_time": "2024-01-01T07:00:00Z", "value": 135},
            {"_time": "2024-01-01T08:00:00Z", "value": 140},
            {"_time": "2024-01-01T09:00:00Z", "value": 145}
        ]
        
        self.resource_data = [
            {"timestamp": "2024-01-01T00:00:00Z", "usage": 45.5},
            {"timestamp": "2024-01-01T01:00:00Z", "usage": 50.2},
            {"timestamp": "2024-01-01T02:00:00Z", "usage": 48.8},
            {"timestamp": "2024-01-01T03:00:00Z", "usage": 52.1},
            {"timestamp": "2024-01-01T04:00:00Z", "usage": 47.9},
            {"timestamp": "2024-01-01T05:00:00Z", "usage": 51.3},
            {"timestamp": "2024-01-01T06:00:00Z", "usage": 49.7},
            {"timestamp": "2024-01-01T07:00:00Z", "usage": 53.2},
            {"timestamp": "2024-01-01T08:00:00Z", "usage": 48.5},
            {"timestamp": "2024-01-01T09:00:00Z", "usage": 50.8}
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_trends_increasing(self):
        """Test trend analysis with increasing data."""
        result = await predictive_analytics.analyze_trends(self.time_series_data)
        
        assert "error" not in result
        assert result["trend_type"] == "increasing"
        assert result["slope"] > 0
        assert result["r_squared"] > 0.8
        assert "moving_averages" in result
        assert "volatility" in result
        
    @pytest.mark.asyncio
    async def test_analyze_trends_empty_data(self):
        """Test trend analysis with empty data."""
        result = await predictive_analytics.analyze_trends([])
        
        assert "error" in result
        assert result["error"] == "No data provided for trend analysis"
    
    @pytest.mark.asyncio
    async def test_forecast_values_linear(self):
        """Test forecasting with linear model."""
        result = await predictive_analytics.forecast_values(
            self.time_series_data, 
            forecast_periods=5, 
            model_type="linear"
        )
        
        assert "error" not in result
        assert "forecasts" in result
        assert len(result["forecasts"]) == 5
        assert result["model_type"] == "linear"
        assert "model_performance" in result
        
        # Check forecast structure
        forecast = result["forecasts"][0]
        assert "time" in forecast
        assert "predicted_value" in forecast
        assert "upper_bound" in forecast
        assert "lower_bound" in forecast
        assert "confidence_level" in forecast
    
    @pytest.mark.asyncio
    async def test_forecast_values_random_forest(self):
        """Test forecasting with random forest model."""
        result = await predictive_analytics.forecast_values(
            self.time_series_data, 
            forecast_periods=3, 
            model_type="random_forest"
        )
        
        assert "error" not in result
        assert result["model_type"] == "random_forest"
        assert len(result["forecasts"]) == 3
    
    @pytest.mark.asyncio
    async def test_forecast_insufficient_data(self):
        """Test forecasting with insufficient data."""
        result = await predictive_analytics.forecast_values(
            self.time_series_data[:2], 
            forecast_periods=5
        )
        
        assert "error" in result
        assert "Insufficient data" in result["error"]
    
    @pytest.mark.asyncio
    async def test_detect_patterns(self):
        """Test pattern detection."""
        pattern_data = [{"value": i + np.random.normal(0, 0.1)} for i in range(20)]
        
        result = await predictive_analytics.detect_patterns(pattern_data)
        
        assert "error" not in result
        assert "patterns" in result
        assert "distribution" in result["patterns"]
        assert "outliers" in result["patterns"]
        assert "cyclic_patterns" in result["patterns"]
        assert "change_points" in result["patterns"]
        
        # Check distribution stats
        distribution = result["patterns"]["distribution"]
        assert "mean" in distribution
        assert "median" in distribution
        assert "std" in distribution
        assert "skewness" in distribution
        assert "kurtosis" in distribution
    
    @pytest.mark.asyncio
    async def test_predict_resource_usage(self):
        """Test resource usage prediction."""
        result = await predictive_analytics.predict_resource_usage(
            self.resource_data, 
            resource_type="cpu", 
            prediction_horizon=12
        )
        
        assert "error" not in result
        assert "predictions" in result
        assert len(result["predictions"]) == 12
        assert result["resource_type"] == "cpu"
        assert "usage_categories" in result
        assert "model_accuracy" in result
        
        # Check prediction structure
        prediction = result["predictions"][0]
        assert "timestamp" in prediction
        assert "predicted_usage" in prediction
        assert "resource_type" in prediction
        assert "confidence" in prediction

class TestAnomalyDetection:
    """Test cases for anomaly detection engine."""
    
    def setup_method(self):
        """Set up test data."""
        # Normal data with some outliers
        self.normal_data = [
            {"value": 100 + i + np.random.normal(0, 2)} for i in range(50)
        ]
        
        # Add some outliers
        self.anomaly_data = self.normal_data + [
            {"value": 200},  # Outlier
            {"value": 50},   # Outlier
            {"value": 300}   # Outlier
        ]
        
        self.security_data = [
            {"action": "login_success", "user": "user1", "src_ip": "192.168.1.1"},
            {"action": "login_failed", "user": "user2", "src_ip": "192.168.1.2"},
            {"action": "login_failed", "user": "user2", "src_ip": "192.168.1.2"},
            {"action": "login_failed", "user": "user2", "src_ip": "192.168.1.2"},
            {"action": "login_success", "user": "user3", "src_ip": "192.168.1.3"},
        ]
        
        self.performance_data = [
            {"cpu_usage": 45.5, "memory_usage": 60.2, "disk_usage": 70.1},
            {"cpu_usage": 50.2, "memory_usage": 65.8, "disk_usage": 71.5},
            {"cpu_usage": 48.8, "memory_usage": 62.3, "disk_usage": 69.8},
            {"cpu_usage": 92.1, "memory_usage": 89.5, "disk_usage": 95.2},  # Anomaly
            {"cpu_usage": 47.9, "memory_usage": 61.7, "disk_usage": 70.9},
        ]
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_statistical(self):
        """Test statistical anomaly detection."""
        result = await anomaly_detector.detect_anomalies(
            self.anomaly_data, 
            method="statistical", 
            sensitivity=0.95
        )
        
        assert "error" not in result
        assert "anomalies_detected" in result
        assert "detection_method" in result
        assert result["detection_method"] == "statistical"
        assert "anomaly_details" in result
        assert result["anomalies_detected"] > 0
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_isolation_forest(self):
        """Test isolation forest anomaly detection."""
        result = await anomaly_detector.detect_anomalies(
            self.anomaly_data, 
            method="isolation_forest", 
            sensitivity=0.9
        )
        
        assert "error" not in result
        assert result["detection_method"] == "isolation_forest"
        assert "anomaly_details" in result
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_auto_method(self):
        """Test automatic method selection."""
        result = await anomaly_detector.detect_anomalies(
            self.anomaly_data, 
            method="auto", 
            sensitivity=0.95
        )
        
        assert "error" not in result
        assert "detection_method" in result
        assert result["detection_method"] in ["statistical", "isolation_forest", "time_series"]
    
    @pytest.mark.asyncio
    async def test_real_time_anomaly_scoring(self):
        """Test real-time anomaly scoring."""
        current_data = {"value": 250}  # Anomalous value
        historical_data = [{"value": 100 + i} for i in range(20)]
        
        result = await anomaly_detector.real_time_anomaly_scoring(
            current_data, 
            historical_data, 
            field="value"
        )
        
        assert "error" not in result
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "confidence" in result
        assert "baseline_stats" in result
        assert "scoring_details" in result
        
        # Should detect the anomaly
        assert result["is_anomaly"] == True
        assert result["anomaly_score"] > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_security_anomalies(self):
        """Test security anomaly detection."""
        result = await anomaly_detector.detect_security_anomalies(self.security_data)
        
        assert "error" not in result
        assert "security_anomalies" in result
        assert "overall_risk_score" in result
        assert "recommendations" in result
        
        # Check for specific security anomaly types
        security_anomalies = result["security_anomalies"]
        assert "failed_login_spikes" in security_anomalies
        assert "unusual_user_behavior" in security_anomalies
        assert "suspicious_ip_activity" in security_anomalies
    
    @pytest.mark.asyncio
    async def test_detect_performance_anomalies(self):
        """Test performance anomaly detection."""
        result = await anomaly_detector.detect_performance_anomalies(self.performance_data)
        
        assert "error" not in result
        assert "performance_anomalies" in result
        assert "health_score" in result
        assert "recommendations" in result
        
        # Check for specific performance anomaly types
        performance_anomalies = result["performance_anomalies"]
        assert "cpu_anomalies" in performance_anomalies
        assert "memory_anomalies" in performance_anomalies
        assert "disk_anomalies" in performance_anomalies
        
        # Should detect high CPU usage
        assert performance_anomalies["cpu_anomalies"]["detected"] == True
    
    @pytest.mark.asyncio
    async def test_empty_data_error(self):
        """Test anomaly detection with empty data."""
        result = await anomaly_detector.detect_anomalies([], method="statistical")
        
        assert "error" in result
        assert result["error"] == "No data provided for anomaly detection"

class TestIntelligentSuggestions:
    """Test cases for intelligent suggestions engine."""
    
    def setup_method(self):
        """Set up test data."""
        self.user_context = {
            "user_id": "test_user",
            "roles": ["admin", "security_analyst"],
            "accessible_indexes": ["security", "performance"],
            "preferences": {
                "preferred_categories": ["security", "performance"]
            }
        }
        
        self.query_history = [
            {
                "query": "search failed login",
                "timestamp": "2024-01-01T10:00:00Z",
                "results_count": 50,
                "feedback": "good"
            },
            {
                "query": "stats count by host",
                "timestamp": "2024-01-01T11:00:00Z",
                "results_count": 25,
                "feedback": "excellent"
            }
        ]
        
        # Setup user patterns
        intelligent_suggestions.user_patterns["test_user"] = {
            "query_history": self.query_history,
            "preferences": {},
            "successful_patterns": ["search", "stats", "failed", "login"],
            "failed_patterns": []
        }
    
    @pytest.mark.asyncio
    async def test_generate_suggestions(self):
        """Test generating intelligent suggestions."""
        result = await intelligent_suggestions.generate_suggestions(
            self.user_context,
            current_query="search error",
            max_suggestions=5
        )
        
        assert "error" not in result
        assert "suggestions" in result
        assert "total_suggestions" in result
        assert "suggestion_categories" in result
        assert "confidence_distribution" in result
        
        # Check suggestion structure
        if result["suggestions"]:
            suggestion = result["suggestions"][0]
            assert "query" in suggestion
            assert "confidence" in suggestion
            assert "category" in suggestion
            assert "explanation" in suggestion
            assert "spl_query" in suggestion
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_with_completion(self):
        """Test generating suggestions with current query for completion."""
        result = await intelligent_suggestions.generate_suggestions(
            self.user_context,
            current_query="search err",
            max_suggestions=10
        )
        
        assert "error" not in result
        assert result["total_suggestions"] <= 10
        
        # Should include completion suggestions
        categories = result["suggestion_categories"]
        assert "completion" in categories or "related" in categories
    
    @pytest.mark.asyncio
    async def test_learn_from_query(self):
        """Test learning from user query patterns."""
        result = await intelligent_suggestions.learn_from_query(
            "test_user",
            "search security incidents",
            results_count=15,
            user_feedback="good"
        )
        
        assert "error" not in result
        assert "learning_updated" in result
        assert result["learning_updated"] == True
        assert "patterns_extracted" in result
        assert "user_query_count" in result
        
        # Check that patterns were updated
        user_patterns = intelligent_suggestions.user_patterns["test_user"]
        assert len(user_patterns["query_history"]) > len(self.query_history)
    
    @pytest.mark.asyncio
    async def test_suggest_improvements(self):
        """Test suggesting query improvements."""
        execution_stats = {
            "execution_time": 45.0,  # Slow query
            "results_count": 0       # No results
        }
        
        result = await intelligent_suggestions.suggest_improvements(
            "search *",
            execution_stats
        )
        
        assert "error" not in result
        assert "improvements" in result
        assert "total_suggestions" in result
        assert "original_query" in result
        assert "improvement_categories" in result
        
        # Should suggest performance improvements
        improvements = result["improvements"]
        assert len(improvements) > 0
        
        # Check for specific improvement types
        improvement_types = [imp["type"] for imp in improvements]
        assert "performance" in improvement_types or "accuracy" in improvement_types
    
    @pytest.mark.asyncio
    async def test_get_contextual_help(self):
        """Test contextual help generation."""
        result = await intelligent_suggestions.get_contextual_help(
            "search error | stats count by",
            cursor_position=25
        )
        
        assert "error" not in result
        assert "help_info" in result
        assert "current_context" in result
        assert "cursor_position" in result
        assert "query_fragment" in result
        
        help_info = result["help_info"]
        assert "syntax_help" in help_info
        assert "field_suggestions" in help_info
        assert "function_suggestions" in help_info
        assert "operator_suggestions" in help_info
        assert "example_queries" in help_info
    
    @pytest.mark.asyncio
    async def test_contextual_help_field_context(self):
        """Test contextual help in field context."""
        result = await intelligent_suggestions.get_contextual_help(
            "search error | stats count by ",
            cursor_position=30
        )
        
        assert "error" not in result
        assert result["current_context"] in ["field", "general"]
        
        # Should provide field suggestions
        help_info = result["help_info"]
        assert len(help_info["field_suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_query_pattern_extraction(self):
        """Test query pattern extraction."""
        patterns = intelligent_suggestions._extract_query_patterns(
            "search error | stats count by host | where count > 10"
        )
        
        assert "search" in patterns
        assert "stats" in patterns
        assert "where" in patterns
        assert "count" in patterns
        assert "host" in patterns
    
    @pytest.mark.asyncio
    async def test_suggestion_ranking(self):
        """Test suggestion ranking system."""
        suggestions = [
            intelligent_suggestions.QuerySuggestion(
                query="test1",
                confidence=0.9,
                category="history",
                explanation="test",
                spl_query="search test1",
                estimated_results=100,
                relevance_score=0.8,
                context_tags=["test"]
            ),
            intelligent_suggestions.QuerySuggestion(
                query="test2",
                confidence=0.7,
                category="popular",
                explanation="test",
                spl_query="search test2",
                estimated_results=50,
                relevance_score=0.6,
                context_tags=["test"]
            )
        ]
        
        ranked = intelligent_suggestions._rank_suggestions(suggestions, self.user_context)
        
        assert len(ranked) == 2
        # Higher confidence should rank higher
        assert ranked[0].confidence >= ranked[1].confidence
    
    @pytest.mark.asyncio
    async def test_diversity_filter(self):
        """Test diversity filter for suggestions."""
        suggestions = [
            intelligent_suggestions.QuerySuggestion(
                query="test1",
                confidence=0.9,
                category="history",
                explanation="test",
                spl_query="search test1",
                estimated_results=100,
                relevance_score=0.8,
                context_tags=["test"]
            ),
            intelligent_suggestions.QuerySuggestion(
                query="test1",  # Duplicate
                confidence=0.8,
                category="history",
                explanation="test",
                spl_query="search test1",
                estimated_results=100,
                relevance_score=0.8,
                context_tags=["test"]
            ),
            intelligent_suggestions.QuerySuggestion(
                query="test2",
                confidence=0.7,
                category="popular",
                explanation="test",
                spl_query="search test2",
                estimated_results=50,
                relevance_score=0.6,
                context_tags=["test"]
            )
        ]
        
        filtered = intelligent_suggestions._apply_diversity_filter(suggestions, 5)
        
        assert len(filtered) == 2  # Should remove duplicate
        assert filtered[0].query != filtered[1].query

class TestAIIntegration:
    """Integration tests for AI features."""
    
    @pytest.mark.asyncio
    async def test_predictive_anomaly_integration(self):
        """Test integration between predictive analytics and anomaly detection."""
        # Generate data with trend and anomalies
        base_data = [
            {"_time": f"2024-01-01T{i:02d}:00:00Z", "value": 100 + i * 2}
            for i in range(24)
        ]
        
        # Add anomalies
        anomaly_data = base_data + [
            {"_time": "2024-01-01T12:30:00Z", "value": 200},  # Outlier
            {"_time": "2024-01-01T18:45:00Z", "value": 50}    # Outlier
        ]
        
        # Test trend analysis
        trend_result = await predictive_analytics.analyze_trends(base_data)
        assert "error" not in trend_result
        assert trend_result["trend_type"] == "increasing"
        
        # Test anomaly detection on same data
        anomaly_result = await anomaly_detector.detect_anomalies(
            anomaly_data, 
            method="statistical"
        )
        assert "error" not in anomaly_result
        assert anomaly_result["anomalies_detected"] > 0
        
        # Results should be consistent
        assert trend_result["slope"] > 0  # Increasing trend
        assert anomaly_result["anomaly_rate"] > 0  # Anomalies detected
    
    @pytest.mark.asyncio
    async def test_suggestions_learning_integration(self):
        """Test integration between suggestions and learning."""
        user_context = {
            "user_id": "integration_test_user",
            "roles": ["analyst"],
            "accessible_indexes": ["test"],
            "preferences": {}
        }
        
        # Learn from a query
        learn_result = await intelligent_suggestions.learn_from_query(
            "integration_test_user",
            "search performance metrics",
            results_count=25,
            user_feedback="excellent"
        )
        
        assert "error" not in learn_result
        assert learn_result["learning_updated"] == True
        
        # Generate suggestions - should incorporate learned patterns
        suggestion_result = await intelligent_suggestions.generate_suggestions(
            user_context,
            current_query="search perf",
            max_suggestions=5
        )
        
        assert "error" not in suggestion_result
        assert suggestion_result["total_suggestions"] > 0
        
        # Should include history-based suggestions
        categories = suggestion_result["suggestion_categories"]
        assert "history" in categories or "related" in categories

@pytest.mark.asyncio
async def test_ai_endpoints_health():
    """Test AI endpoints health check."""
    # This would typically test the actual API endpoints
    # For now, just verify the engines are functional
    
    # Test predictive analytics
    simple_data = [{"value": i} for i in range(10)]
    result = await predictive_analytics.detect_patterns(simple_data)
    assert "error" not in result
    
    # Test anomaly detection
    result = await anomaly_detector.detect_anomalies(simple_data, method="statistical")
    assert "error" not in result
    
    # Test intelligent suggestions
    user_context = {"user_id": "test", "roles": [], "accessible_indexes": []}
    result = await intelligent_suggestions.generate_suggestions(user_context)
    assert "error" not in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])