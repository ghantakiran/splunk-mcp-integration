#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for NLP Engine Service.

This module tests all API endpoints including SPL translation, AI features,
authentication, error handling, and response validation.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
from fastapi import status

from .conftest import assert_spl_query_valid, assert_response_structure


class TestSPLTranslationEndpoints:
    """Test SPL translation API endpoints."""
    
    def test_translate_simple_query_success(
        self, 
        test_client, 
        auth_headers,
        sample_user_context,
        mock_openai_client
    ):
        """Test successful simple query translation."""
        request_data = {
            "query": "show me errors from the last hour",
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["spl", "confidence", "explanation"]
        assert assert_response_structure(data, required_fields)
        assert assert_spl_query_valid(data["spl"])
        assert 0.0 <= data["confidence"] <= 1.0
    
    def test_translate_complex_aggregation_query(
        self, 
        test_client, 
        auth_headers,
        sample_user_context,
        mock_openai_client
    ):
        """Test complex aggregation query translation."""
        request_data = {
            "query": "count events by source type in the last 24 hours and show as chart",
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert assert_spl_query_valid(data["spl"])
        assert "stats" in data["spl"].lower() or "chart" in data["spl"].lower()
        assert data["confidence"] > 0.7  # High confidence for structured queries
    
    def test_translate_with_time_optimization(
        self, 
        test_client, 
        auth_headers,
        sample_user_context,
        mock_openai_client,
        mock_time_range_optimizer
    ):
        """Test translation with time range optimization."""
        request_data = {
            "query": "find errors in the database logs",
            "context": sample_user_context,
            "optimize_time_range": True
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "optimization" in data
        assert data["optimization"]["time_range_optimized"]
        mock_time_range_optimizer.optimize_time_range.assert_called_once()
    
    def test_translate_invalid_query(
        self, 
        test_client, 
        auth_headers,
        sample_user_context
    ):
        """Test translation of invalid/unclear query."""
        request_data = {
            "query": "",  # Empty query
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_translate_missing_context(
        self, 
        test_client, 
        auth_headers
    ):
        """Test translation without user context."""
        request_data = {
            "query": "show me errors"
            # Missing context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_translate_unauthorized(self, test_client, sample_user_context):
        """Test translation without authentication."""
        request_data = {
            "query": "show me errors",
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            json=request_data
            # No auth headers
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSPLValidationEndpoints:
    """Test SPL validation API endpoints."""
    
    def test_validate_spl_success(
        self, 
        test_client, 
        auth_headers,
        sample_spl_queries
    ):
        """Test successful SPL validation."""
        valid_query = sample_spl_queries[0]
        request_data = {
            "spl": valid_query["spl"],
            "context": {"user_id": "test-user"}
        }
        
        response = test_client.post(
            "/api/v1/spl/validate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["is_valid", "syntax_check", "security_check"]
        assert assert_response_structure(data, required_fields)
        assert data["is_valid"] is True
    
    def test_validate_invalid_spl(
        self, 
        test_client, 
        auth_headers,
        sample_spl_queries
    ):
        """Test validation of invalid SPL."""
        invalid_query = sample_spl_queries[3]  # Invalid query from fixture
        request_data = {
            "spl": invalid_query["spl"],
            "context": {"user_id": "test-user"}
        }
        
        response = test_client.post(
            "/api/v1/spl/validate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_valid"] is False
        assert "errors" in data
        assert len(data["errors"]) > 0
    
    def test_validate_security_violation(
        self, 
        test_client, 
        auth_headers
    ):
        """Test validation with security violations."""
        request_data = {
            "spl": "search * | delete",  # Dangerous delete command
            "context": {"user_id": "test-user"}
        }
        
        response = test_client.post(
            "/api/v1/spl/validate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["security_check"]["has_violations"] is True
        assert "delete" in str(data["security_check"]["violations"]).lower()


class TestOptimizationEndpoints:
    """Test query optimization API endpoints."""
    
    def test_optimize_query_performance(
        self, 
        test_client, 
        auth_headers,
        mock_query_performance
    ):
        """Test query performance optimization."""
        request_data = {
            "spl": "search error earliest=-1h | stats count by source",
            "context": {"user_id": "test-user"},
            "optimization_level": "aggressive"
        }
        
        response = test_client.post(
            "/api/v1/spl/optimize",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["optimized_spl", "performance_analysis", "optimizations_applied"]
        assert assert_response_structure(data, required_fields)
        mock_query_performance.analyze_performance.assert_called_once()
    
    def test_optimize_index_selection(
        self, 
        test_client, 
        auth_headers,
        mock_index_optimization
    ):
        """Test index selection optimization."""
        request_data = {
            "spl": "search failed_login",
            "context": {"user_id": "test-user", "accessible_indexes": ["main", "security"]},
            "optimize_indexes": True
        }
        
        response = test_client.post(
            "/api/v1/spl/optimize",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "index_optimization" in data
        mock_index_optimization.optimize_indexes.assert_called_once()


class TestAIFeaturesEndpoints:
    """Test AI features API endpoints."""
    
    def test_predictive_analytics_forecast(
        self, 
        test_client, 
        auth_headers,
        sample_ai_features_data
    ):
        """Test predictive analytics forecast endpoint."""
        request_data = {
            "data": sample_ai_features_data["predictive_analytics"]["time_series_data"],
            "forecast_horizon": "24h",
            "confidence_level": 0.85
        }
        
        with patch('app.ai.predictive_analytics.PredictiveAnalyzer') as mock_analyzer:
            mock_analyzer.return_value.forecast.return_value = {
                "forecast": [
                    {"_time": "2024-01-01T13:00:00", "predicted_count": 185, "confidence_interval": [170, 200]}
                ],
                "confidence": 0.85,
                "model_accuracy": 0.92
            }
            
            response = test_client.post(
                "/api/v1/ai/predictive/forecast",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["forecast", "confidence", "model_accuracy"]
        assert assert_response_structure(data, required_fields)
    
    def test_anomaly_detection(
        self, 
        test_client, 
        auth_headers,
        sample_ai_features_data
    ):
        """Test anomaly detection endpoint."""
        request_data = {
            "current_value": sample_ai_features_data["anomaly_detection"]["current_value"],
            "baseline_data": sample_ai_features_data["anomaly_detection"]["baseline_data"],
            "threshold": 3.0
        }
        
        with patch('app.ai.anomaly_detection.AnomalyDetector') as mock_detector:
            mock_detector.return_value.detect_anomaly.return_value = {
                "is_anomaly": True,
                "severity": "high",
                "confidence": 0.95,
                "explanation": "Current value significantly exceeds baseline"
            }
            
            response = test_client.post(
                "/api/v1/ai/anomaly/detect",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["is_anomaly", "severity", "confidence"]
        assert assert_response_structure(data, required_fields)
    
    def test_intelligent_suggestions(
        self, 
        test_client, 
        auth_headers,
        sample_ai_features_data
    ):
        """Test intelligent query suggestions endpoint."""
        request_data = {
            "query_history": sample_ai_features_data["intelligent_suggestions"]["query_history"],
            "current_context": "security_analysis",
            "max_suggestions": 5
        }
        
        with patch('app.ai.intelligent_suggestions.SuggestionEngine') as mock_engine:
            mock_engine.return_value.generate_suggestions.return_value = {
                "suggestions": [
                    {
                        "query": "search error earliest=-1h | stats count by source",
                        "confidence": 0.9,
                        "reasoning": "Based on your recent error analysis pattern"
                    }
                ]
            }
            
            response = test_client.post(
                "/api/v1/ai/suggestions/generate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0


class TestAlertParsing:
    """Test alert parsing functionality."""
    
    def test_parse_alert_simple(
        self, 
        test_client, 
        auth_headers,
        sample_user_context
    ):
        """Test simple alert parsing."""
        request_data = {
            "query": "alert me when error count exceeds 10 in the last 5 minutes",
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/ai/parse-alert",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["search", "condition", "time_window"]
        assert assert_response_structure(data, required_fields)
        assert "error" in data["search"].lower()
        assert "10" in data["condition"]
    
    def test_parse_alert_complex(
        self, 
        test_client, 
        auth_headers,
        sample_user_context
    ):
        """Test complex alert parsing with multiple conditions."""
        request_data = {
            "query": "create alert for failed login attempts from same IP more than 5 times in 10 minutes",
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/ai/parse-alert",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "failed" in data["search"].lower() and "login" in data["search"].lower()
        assert "5" in data["condition"]
        assert "10" in data["time_window"]


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    def test_health_check(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        required_fields = ["status", "timestamp"]
        assert assert_response_structure(data, required_fields)
        assert data["status"] == "healthy"
    
    def test_ready_check(self, test_client):
        """Test readiness probe endpoint."""
        response = test_client.get("/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["ready"] is True
        assert "dependencies" in data
    
    def test_ai_providers_status(self, test_client, auth_headers):
        """Test AI providers status endpoint."""
        with patch('app.api.v1.endpoints.check_ai_providers') as mock_check:
            mock_check.return_value = {
                "openai": {"available": True, "latency_ms": 150},
                "anthropic": {"available": True, "latency_ms": 200}
            }
            
            response = test_client.get(
                "/api/v1/ai/providers/status",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "openai" in data
        assert "anthropic" in data


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_rate_limiting(self, test_client, auth_headers, sample_user_context):
        """Test rate limiting enforcement."""
        request_data = {
            "query": "test query",
            "context": sample_user_context
        }
        
        # Mock rate limiting
        with patch('app.utils.rate_limiter.check_rate_limit') as mock_limiter:
            mock_limiter.return_value = False  # Rate limit exceeded
            
            response = test_client.post(
                "/api/v1/spl/translate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_ai_provider_failure(
        self, 
        test_client, 
        auth_headers,
        sample_user_context
    ):
        """Test handling of AI provider failures."""
        request_data = {
            "query": "show me errors",
            "context": sample_user_context
        }
        
        # Mock AI provider failure
        with patch('app.ai.nlp_service.NLPService.translate_query') as mock_translate:
            mock_translate.side_effect = Exception("AI provider unavailable")
            
            response = test_client.post(
                "/api/v1/spl/translate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_invalid_json_request(self, test_client, auth_headers):
        """Test handling of invalid JSON requests."""
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            data="invalid json content"
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_large_query_handling(
        self, 
        test_client, 
        auth_headers,
        sample_user_context
    ):
        """Test handling of very large queries."""
        request_data = {
            "query": "show me errors " * 1000,  # Very long query
            "context": sample_user_context
        }
        
        response = test_client.post(
            "/api/v1/spl/translate",
            headers=auth_headers,
            json=request_data
        )
        
        # Should either handle gracefully or return appropriate error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]


class TestConcurrency:
    """Test concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_translations(
        self, 
        async_client, 
        auth_headers,
        sample_user_context,
        mock_openai_client
    ):
        """Test handling of concurrent translation requests."""
        import asyncio
        
        request_data = {
            "query": "show me errors",
            "context": sample_user_context
        }
        
        # Send multiple concurrent requests
        tasks = []
        for _ in range(5):
            task = async_client.post(
                "/api/v1/spl/translate",
                headers=auth_headers,
                json=request_data
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed or fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])