#!/usr/bin/env python3
"""
Comprehensive model tests for NLP Engine Service.

This module tests all Pydantic models including validation, serialization,
and data transformation logic for requests, responses, and internal models.
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pydantic import ValidationError
import json


class TestNLPRequestModels:
    """Test NLP request models and validation."""
    
    def test_spl_translation_request_valid(self):
        """Test valid SPL translation request model."""
        from app.models.requests import SPLTranslationRequest
        
        valid_data = {
            "query": "show me errors from the last hour",
            "context": {
                "user_id": "test-user-123",
                "roles": ["user"],
                "accessible_indexes": ["main", "security"]
            }
        }
        
        request = SPLTranslationRequest(**valid_data)
        
        assert request.query == valid_data["query"]
        assert request.context["user_id"] == valid_data["context"]["user_id"]
        assert isinstance(request.context["accessible_indexes"], list)
    
    def test_spl_translation_request_invalid_empty_query(self):
        """Test SPL translation request with empty query."""
        from app.models.requests import SPLTranslationRequest
        
        invalid_data = {
            "query": "",  # Empty query
            "context": {"user_id": "test-user-123"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            SPLTranslationRequest(**invalid_data)
        
        assert "query" in str(exc_info.value)
    
    def test_spl_translation_request_missing_context(self):
        """Test SPL translation request without context."""
        from app.models.requests import SPLTranslationRequest
        
        invalid_data = {
            "query": "show me errors"
            # Missing context
        }
        
        with pytest.raises(ValidationError) as exc_info:
            SPLTranslationRequest(**invalid_data)
        
        assert "context" in str(exc_info.value)
    
    def test_spl_translation_request_with_options(self):
        """Test SPL translation request with optional parameters."""
        from app.models.requests import SPLTranslationRequest
        
        data = {
            "query": "show me errors",
            "context": {"user_id": "test-user-123"},
            "optimize_time_range": True,
            "max_tokens": 2000,
            "temperature": 0.2,
            "provider": "openai"
        }
        
        request = SPLTranslationRequest(**data)
        
        assert request.optimize_time_range is True
        assert request.max_tokens == 2000
        assert request.temperature == 0.2
        assert request.provider == "openai"
    
    def test_spl_validation_request(self):
        """Test SPL validation request model."""
        from app.models.requests import SPLValidationRequest
        
        data = {
            "spl": "search error earliest=-1h | stats count",
            "context": {"user_id": "test-user-123"}
        }
        
        request = SPLValidationRequest(**data)
        
        assert request.spl == data["spl"]
        assert request.context["user_id"] == data["context"]["user_id"]
    
    def test_spl_optimization_request(self):
        """Test SPL optimization request model."""
        from app.models.requests import SPLOptimizationRequest
        
        data = {
            "spl": "search error earliest=-1h | stats count by source",
            "context": {"user_id": "test-user-123"},
            "optimization_level": "aggressive",
            "optimize_indexes": True,
            "target_performance": "speed"
        }
        
        request = SPLOptimizationRequest(**data)
        
        assert request.optimization_level == "aggressive"
        assert request.optimize_indexes is True
        assert request.target_performance == "speed"


class TestNLPResponseModels:
    """Test NLP response models and serialization."""
    
    def test_spl_translation_response(self):
        """Test SPL translation response model."""
        from app.models.responses import SPLTranslationResponse
        
        data = {
            "spl": "search error earliest=-1h",
            "confidence": 0.95,
            "explanation": "Search for errors in the last hour",
            "processing_time_ms": 150.5,
            "provider": "openai"
        }
        
        response = SPLTranslationResponse(**data)
        
        assert response.spl == data["spl"]
        assert response.confidence == data["confidence"]
        assert response.explanation == data["explanation"]
        assert response.processing_time_ms == data["processing_time_ms"]
        assert response.provider == data["provider"]
    
    def test_spl_translation_response_with_optimization(self):
        """Test SPL translation response with optimization data."""
        from app.models.responses import SPLTranslationResponse, OptimizationInfo
        
        optimization_data = {
            "time_range_optimized": True,
            "indexes_optimized": True,
            "performance_gain": 0.25,
            "suggestions": ["Added specific time range", "Selected optimal indexes"]
        }
        
        data = {
            "spl": "search index=main error earliest=-1h",
            "confidence": 0.92,
            "explanation": "Optimized search for errors",
            "optimization": OptimizationInfo(**optimization_data)
        }
        
        response = SPLTranslationResponse(**data)
        
        assert response.optimization.time_range_optimized is True
        assert response.optimization.performance_gain == 0.25
        assert len(response.optimization.suggestions) == 2
    
    def test_spl_validation_response_valid(self):
        """Test SPL validation response for valid query."""
        from app.models.responses import SPLValidationResponse, SyntaxCheck, SecurityCheck
        
        syntax_data = {
            "is_valid": True,
            "syntax_score": 1.0,
            "warnings": []
        }
        
        security_data = {
            "has_violations": False,
            "risk_level": "low",
            "violations": []
        }
        
        data = {
            "is_valid": True,
            "syntax_check": SyntaxCheck(**syntax_data),
            "security_check": SecurityCheck(**security_data),
            "estimated_performance": {
                "execution_time_seconds": 5.2,
                "complexity_score": 0.3
            }
        }
        
        response = SPLValidationResponse(**data)
        
        assert response.is_valid is True
        assert response.syntax_check.is_valid is True
        assert response.security_check.has_violations is False
    
    def test_spl_validation_response_invalid(self):
        """Test SPL validation response for invalid query."""
        from app.models.responses import SPLValidationResponse, SyntaxCheck, SecurityCheck
        
        syntax_data = {
            "is_valid": False,
            "syntax_score": 0.2,
            "warnings": [],
            "errors": ["Invalid command syntax"]
        }
        
        security_data = {
            "has_violations": True,
            "risk_level": "high",
            "violations": ["Potentially dangerous delete command"]
        }
        
        data = {
            "is_valid": False,
            "syntax_check": SyntaxCheck(**syntax_data),
            "security_check": SecurityCheck(**security_data),
            "errors": ["Query contains security violations"]
        }
        
        response = SPLValidationResponse(**data)
        
        assert response.is_valid is False
        assert len(response.syntax_check.errors) == 1
        assert response.security_check.has_violations is True
    
    def test_spl_optimization_response(self):
        """Test SPL optimization response model."""
        from app.models.responses import SPLOptimizationResponse, PerformanceAnalysis
        
        performance_data = {
            "original_complexity": 0.8,
            "optimized_complexity": 0.4,
            "estimated_speedup": 2.5,
            "resource_usage_reduction": 0.3
        }
        
        data = {
            "original_spl": "search error | stats count by source",
            "optimized_spl": "search index=main error earliest=-1h | stats count by source",
            "performance_analysis": PerformanceAnalysis(**performance_data),
            "optimizations_applied": ["Added time range", "Added index specification"],
            "confidence": 0.88
        }
        
        response = SPLOptimizationResponse(**data)
        
        assert response.original_spl != response.optimized_spl
        assert response.performance_analysis.estimated_speedup == 2.5
        assert len(response.optimizations_applied) == 2


class TestAIFeatureModels:
    """Test AI feature request/response models."""
    
    def test_predictive_analytics_request(self):
        """Test predictive analytics request model."""
        from app.models.ai_models import PredictiveAnalyticsRequest
        
        data = {
            "data": [
                {"_time": "2024-01-01T10:00:00", "count": 120},
                {"_time": "2024-01-01T11:00:00", "count": 150}
            ],
            "forecast_horizon": "24h",
            "confidence_level": 0.85,
            "model_type": "linear_regression"
        }
        
        request = PredictiveAnalyticsRequest(**data)
        
        assert len(request.data) == 2
        assert request.forecast_horizon == "24h"
        assert request.confidence_level == 0.85
        assert request.model_type == "linear_regression"
    
    def test_predictive_analytics_response(self):
        """Test predictive analytics response model."""
        from app.models.ai_models import PredictiveAnalyticsResponse, ForecastPoint
        
        forecast_data = [
            ForecastPoint(
                _time="2024-01-01T12:00:00",
                predicted_value=175.5,
                confidence_interval=[160.0, 190.0],
                trend="increasing"
            )
        ]
        
        data = {
            "forecast": forecast_data,
            "model_accuracy": 0.92,
            "confidence": 0.85,
            "insights": ["Upward trend detected", "Seasonal pattern identified"]
        }
        
        response = PredictiveAnalyticsResponse(**data)
        
        assert len(response.forecast) == 1
        assert response.model_accuracy == 0.92
        assert response.forecast[0].predicted_value == 175.5
    
    def test_anomaly_detection_request(self):
        """Test anomaly detection request model."""
        from app.models.ai_models import AnomalyDetectionRequest
        
        data = {
            "current_value": 250.0,
            "baseline_data": [100, 105, 98, 102, 99, 104, 101],
            "threshold": 3.0,
            "method": "statistical"
        }
        
        request = AnomalyDetectionRequest(**data)
        
        assert request.current_value == 250.0
        assert len(request.baseline_data) == 7
        assert request.threshold == 3.0
        assert request.method == "statistical"
    
    def test_anomaly_detection_response(self):
        """Test anomaly detection response model."""
        from app.models.ai_models import AnomalyDetectionResponse
        
        data = {
            "is_anomaly": True,
            "severity": "high",
            "confidence": 0.95,
            "score": 4.2,
            "explanation": "Current value significantly exceeds baseline",
            "threshold_used": 3.0,
            "baseline_stats": {
                "mean": 101.2,
                "std_dev": 2.8,
                "min": 98,
                "max": 105
            }
        }
        
        response = AnomalyDetectionResponse(**data)
        
        assert response.is_anomaly is True
        assert response.severity == "high"
        assert response.score == 4.2
        assert response.baseline_stats["mean"] == 101.2
    
    def test_intelligent_suggestions_request(self):
        """Test intelligent suggestions request model."""
        from app.models.ai_models import IntelligentSuggestionsRequest
        
        data = {
            "query_history": [
                "search error earliest=-1h",
                "search failed_login earliest=-4h"
            ],
            "current_context": "security_analysis",
            "max_suggestions": 5,
            "include_explanations": True
        }
        
        request = IntelligentSuggestionsRequest(**data)
        
        assert len(request.query_history) == 2
        assert request.current_context == "security_analysis"
        assert request.max_suggestions == 5
        assert request.include_explanations is True
    
    def test_intelligent_suggestions_response(self):
        """Test intelligent suggestions response model."""
        from app.models.ai_models import IntelligentSuggestionsResponse, QuerySuggestion
        
        suggestions_data = [
            QuerySuggestion(
                query="search error earliest=-1h | stats count by source",
                confidence=0.9,
                reasoning="Based on your recent error analysis pattern",
                category="analysis"
            )
        ]
        
        data = {
            "suggestions": suggestions_data,
            "context_analysis": {
                "primary_intent": "error_investigation",
                "confidence": 0.85
            }
        }
        
        response = IntelligentSuggestionsResponse(**data)
        
        assert len(response.suggestions) == 1
        assert response.suggestions[0].confidence == 0.9
        assert response.context_analysis["primary_intent"] == "error_investigation"


class TestAlertModels:
    """Test alert parsing models."""
    
    def test_alert_parsing_request(self):
        """Test alert parsing request model."""
        from app.models.alert_models import AlertParsingRequest
        
        data = {
            "query": "alert me when error count exceeds 10 in the last 5 minutes",
            "context": {"user_id": "test-user-123"}
        }
        
        request = AlertParsingRequest(**data)
        
        assert "error count exceeds 10" in request.query
        assert request.context["user_id"] == "test-user-123"
    
    def test_alert_parsing_response(self):
        """Test alert parsing response model."""
        from app.models.alert_models import AlertParsingResponse, AlertCondition, AlertSchedule
        
        condition_data = {
            "field": "count",
            "operator": "greater_than",
            "value": 10,
            "threshold_type": "absolute"
        }
        
        schedule_data = {
            "time_window": "5m",
            "check_frequency": "1m",
            "delay": "0s"
        }
        
        data = {
            "search": "search error | stats count",
            "condition": AlertCondition(**condition_data),
            "schedule": AlertSchedule(**schedule_data),
            "confidence": 0.92,
            "suggested_name": "High Error Count Alert"
        }
        
        response = AlertParsingResponse(**data)
        
        assert "error" in response.search
        assert response.condition.operator == "greater_than"
        assert response.schedule.time_window == "5m"
        assert response.confidence == 0.92


class TestUserContextModels:
    """Test user context and permission models."""
    
    def test_user_context_model(self):
        """Test user context model validation."""
        from app.models.context import UserContext
        
        data = {
            "user_id": "test-user-123",
            "username": "test_user",
            "roles": ["user", "analyst"],
            "permissions": ["splunk:search", "splunk:read"],
            "accessible_indexes": ["main", "security", "web"],
            "session_id": "session-456",
            "preferences": {
                "timezone": "UTC",
                "date_format": "%Y-%m-%d %H:%M:%S"
            }
        }
        
        context = UserContext(**data)
        
        assert context.user_id == "test-user-123"
        assert len(context.roles) == 2
        assert len(context.permissions) == 2
        assert len(context.accessible_indexes) == 3
        assert context.preferences["timezone"] == "UTC"
    
    def test_user_context_minimal(self):
        """Test user context with minimal required fields."""
        from app.models.context import UserContext
        
        data = {
            "user_id": "test-user-123",
            "roles": ["user"],
            "accessible_indexes": ["main"]
        }
        
        context = UserContext(**data)
        
        assert context.user_id == "test-user-123"
        assert context.username is None  # Optional field
        assert len(context.roles) == 1
    
    def test_query_context_model(self):
        """Test query context model."""
        from app.models.context import QueryContext
        
        data = {
            "conversation_id": "conv-123",
            "query_id": "query-456",
            "timestamp": datetime.utcnow(),
            "previous_queries": ["search error", "search info"],
            "session_duration_minutes": 15,
            "query_intent": "analysis"
        }
        
        context = QueryContext(**data)
        
        assert context.conversation_id == "conv-123"
        assert len(context.previous_queries) == 2
        assert context.session_duration_minutes == 15
        assert context.query_intent == "analysis"


class TestDataValidation:
    """Test data validation and edge cases."""
    
    def test_confidence_score_validation(self):
        """Test confidence score must be between 0 and 1."""
        from app.models.responses import SPLTranslationResponse
        
        # Valid confidence score
        valid_data = {
            "spl": "search error",
            "confidence": 0.85,
            "explanation": "Test"
        }
        response = SPLTranslationResponse(**valid_data)
        assert response.confidence == 0.85
        
        # Invalid confidence scores
        for invalid_confidence in [-0.1, 1.1, 2.0]:
            invalid_data = {
                "spl": "search error",
                "confidence": invalid_confidence,
                "explanation": "Test"
            }
            with pytest.raises(ValidationError):
                SPLTranslationResponse(**invalid_data)
    
    def test_time_range_validation(self):
        """Test time range format validation."""
        from app.models.requests import SPLTranslationRequest
        
        # Valid time ranges
        valid_contexts = [
            {"time_range": "-1h"},
            {"time_range": "-24h@h"},
            {"time_range": "earliest=-7d latest=now"},
            {"time_range": "@d-1h"}
        ]
        
        for context in valid_contexts:
            data = {
                "query": "test query",
                "context": {"user_id": "test", **context}
            }
            request = SPLTranslationRequest(**data)
            assert request.context.get("time_range") == context["time_range"]
    
    def test_spl_length_validation(self):
        """Test SPL query length validation."""
        from app.models.requests import SPLValidationRequest
        
        # Very long SPL should be handled appropriately
        long_spl = "search " + " OR ".join([f"field{i}=value{i}" for i in range(1000)])
        
        data = {
            "spl": long_spl,
            "context": {"user_id": "test"}
        }
        
        # Should either accept or reject gracefully
        try:
            request = SPLValidationRequest(**data)
            assert len(request.spl) == len(long_spl)
        except ValidationError as e:
            assert "length" in str(e).lower() or "too long" in str(e).lower()
    
    def test_array_field_validation(self):
        """Test array field validation."""
        from app.models.context import UserContext
        
        # Empty arrays should be valid
        data = {
            "user_id": "test",
            "roles": [],
            "accessible_indexes": []
        }
        
        context = UserContext(**data)
        assert context.roles == []
        assert context.accessible_indexes == []
    
    def test_optional_field_handling(self):
        """Test optional field handling."""
        from app.models.responses import SPLTranslationResponse
        
        # Minimal required fields only
        minimal_data = {
            "spl": "search error",
            "confidence": 0.85,
            "explanation": "Test"
        }
        
        response = SPLTranslationResponse(**minimal_data)
        
        assert response.processing_time_ms is None
        assert response.provider is None
        assert response.optimization is None


class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_json_serialization(self):
        """Test JSON serialization of models."""
        from app.models.responses import SPLTranslationResponse
        
        data = {
            "spl": "search error earliest=-1h",
            "confidence": 0.95,
            "explanation": "Search for errors in the last hour",
            "processing_time_ms": 150.5
        }
        
        response = SPLTranslationResponse(**data)
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["spl"] == data["spl"]
        assert parsed["confidence"] == data["confidence"]
        assert parsed["processing_time_ms"] == data["processing_time_ms"]
    
    def test_datetime_serialization(self):
        """Test datetime field serialization."""
        from app.models.context import QueryContext
        
        now = datetime.utcnow()
        data = {
            "conversation_id": "conv-123",
            "query_id": "query-456",
            "timestamp": now
        }
        
        context = QueryContext(**data)
        json_str = context.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "timestamp" in parsed
        # Should serialize to ISO format
        assert "T" in parsed["timestamp"]
    
    def test_model_validation_error_details(self):
        """Test validation error details are informative."""
        from app.models.requests import SPLTranslationRequest
        
        invalid_data = {
            "query": "",  # Empty query
            "context": {}  # Missing user_id
        }
        
        with pytest.raises(ValidationError) as exc_info:
            SPLTranslationRequest(**invalid_data)
        
        error_details = str(exc_info.value)
        assert "query" in error_details
        # Should provide clear error messages
        assert len(error_details) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])