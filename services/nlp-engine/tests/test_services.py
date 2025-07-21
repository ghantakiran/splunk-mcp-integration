#!/usr/bin/env python3
"""
Comprehensive service layer tests for NLP Engine Service.

This module tests core services including NLP processing, AI providers,
query optimization, and business logic components.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta


class TestNLPService:
    """Test NLP service core functionality."""
    
    def test_nlp_service_initialization(self, mock_settings):
        """Test NLP service initialization."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        assert service is not None
        assert hasattr(service, 'translate_query')
        assert hasattr(service, 'validate_spl')
        assert hasattr(service, 'optimize_query')
    
    @pytest.mark.asyncio
    async def test_translate_query_success(
        self, 
        mock_settings,
        mock_openai_client,
        sample_user_context
    ):
        """Test successful query translation."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_call_ai_provider') as mock_call:
            mock_call.return_value = {
                "spl": "search error earliest=-1h",
                "confidence": 0.95,
                "explanation": "Search for errors in the last hour"
            }
            
            result = await service.translate_query(
                "show me errors from the last hour",
                sample_user_context
            )
            
            assert result["spl"] == "search error earliest=-1h"
            assert result["confidence"] == 0.95
            assert "explanation" in result
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_translate_query_with_optimization(
        self, 
        mock_settings,
        mock_openai_client,
        mock_time_range_optimizer,
        sample_user_context
    ):
        """Test query translation with optimization enabled."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_call_ai_provider') as mock_call, \
             patch.object(service, '_apply_optimizations') as mock_optimize:
            
            mock_call.return_value = {
                "spl": "search error",
                "confidence": 0.85,
                "explanation": "Search for errors"
            }
            
            mock_optimize.return_value = {
                "spl": "search index=main error earliest=-1h",
                "confidence": 0.85,
                "explanation": "Optimized search for errors",
                "optimization": {
                    "time_range_optimized": True,
                    "indexes_optimized": True
                }
            }
            
            result = await service.translate_query(
                "show me errors",
                sample_user_context,
                optimize=True
            )
            
            assert "index=main" in result["spl"]
            assert "earliest=-1h" in result["spl"]
            assert result["optimization"]["time_range_optimized"] is True
    
    @pytest.mark.asyncio
    async def test_translate_query_provider_failure(
        self, 
        mock_settings,
        sample_user_context
    ):
        """Test handling of AI provider failures."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_call_ai_provider') as mock_call:
            mock_call.side_effect = Exception("AI provider unavailable")
            
            with pytest.raises(Exception) as exc_info:
                await service.translate_query(
                    "show me errors",
                    sample_user_context
                )
            
            assert "provider unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_spl_success(self, mock_settings):
        """Test successful SPL validation."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_validate_spl_syntax') as mock_syntax, \
             patch.object(service, '_validate_spl_security') as mock_security:
            
            mock_syntax.return_value = {
                "is_valid": True,
                "syntax_score": 1.0,
                "warnings": []
            }
            
            mock_security.return_value = {
                "has_violations": False,
                "risk_level": "low",
                "violations": []
            }
            
            result = await service.validate_spl(
                "search error earliest=-1h | stats count",
                {"user_id": "test"}
            )
            
            assert result["is_valid"] is True
            assert result["syntax_check"]["is_valid"] is True
            assert result["security_check"]["has_violations"] is False
    
    @pytest.mark.asyncio
    async def test_validate_spl_security_violation(self, mock_settings):
        """Test SPL validation with security violations."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_validate_spl_syntax') as mock_syntax, \
             patch.object(service, '_validate_spl_security') as mock_security:
            
            mock_syntax.return_value = {
                "is_valid": True,
                "syntax_score": 1.0,
                "warnings": []
            }
            
            mock_security.return_value = {
                "has_violations": True,
                "risk_level": "high",
                "violations": ["Dangerous delete command detected"]
            }
            
            result = await service.validate_spl(
                "search * | delete",
                {"user_id": "test"}
            )
            
            assert result["is_valid"] is False
            assert result["security_check"]["has_violations"] is True
            assert "delete" in str(result["security_check"]["violations"])


class TestAIProviders:
    """Test AI provider integrations."""
    
    @pytest.mark.asyncio
    async def test_openai_provider_success(self, mock_openai_client):
        """Test successful OpenAI provider call."""
        from app.ai.providers import OpenAIProvider
        
        provider = OpenAIProvider("test-api-key")
        
        result = await provider.translate_query(
            "show me errors from the last hour",
            {"user_id": "test"}
        )
        
        assert "spl" in result
        assert "confidence" in result
        mock_openai_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_anthropic_provider_success(self, mock_anthropic_client):
        """Test successful Anthropic provider call."""
        from app.ai.providers import AnthropicProvider
        
        provider = AnthropicProvider("test-api-key")
        
        result = await provider.translate_query(
            "show me errors from the last hour",
            {"user_id": "test"}
        )
        
        assert "spl" in result
        assert "confidence" in result
        mock_anthropic_client.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_provider_rate_limit_handling(self, mock_openai_client):
        """Test handling of provider rate limits."""
        from app.ai.providers import OpenAIProvider
        import openai
        
        provider = OpenAIProvider("test-api-key")
        
        # Mock rate limit error
        mock_openai_client.chat.completions.create.side_effect = openai.RateLimitError(
            "Rate limit exceeded",
            response=Mock(status_code=429),
            body=None
        )
        
        with pytest.raises(Exception) as exc_info:
            await provider.translate_query(
                "show me errors",
                {"user_id": "test"}
            )
        
        assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_provider_fallback_mechanism(self):
        """Test provider fallback mechanism."""
        from app.ai.providers import AIProviderManager
        
        manager = AIProviderManager()
        
        with patch.object(manager, '_openai_provider') as mock_openai, \
             patch.object(manager, '_anthropic_provider') as mock_anthropic:
            
            # OpenAI fails
            mock_openai.translate_query.side_effect = Exception("OpenAI unavailable")
            
            # Anthropic succeeds
            mock_anthropic.translate_query.return_value = {
                "spl": "search error earliest=-1h",
                "confidence": 0.92,
                "explanation": "Search for errors"
            }
            
            result = await manager.translate_query(
                "show me errors",
                {"user_id": "test"}
            )
            
            assert result["spl"] == "search error earliest=-1h"
            assert result["confidence"] == 0.92
            # Should have tried both providers
            mock_openai.translate_query.assert_called_once()
            mock_anthropic.translate_query.assert_called_once()


class TestQueryOptimization:
    """Test query optimization services."""
    
    @pytest.mark.asyncio
    async def test_time_range_optimization(self, mock_time_range_optimizer):
        """Test time range optimization service."""
        from app.ai.time_range_optimization import TimeRangeOptimizer
        
        optimizer = TimeRangeOptimizer()
        
        result = await optimizer.optimize_time_range(
            "search error",
            {"query_intent": "recent_analysis"}
        )
        
        assert "optimized_earliest" in result
        assert "optimization_strategy" in result
        assert "estimated_performance_gain" in result
        mock_time_range_optimizer.optimize_time_range.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_index_optimization(self, mock_index_optimization):
        """Test index selection optimization."""
        from app.ai.index_selection_optimization import IndexOptimizer
        
        optimizer = IndexOptimizer()
        
        result = await optimizer.optimize_indexes(
            "search failed_login",
            {"accessible_indexes": ["main", "security"]}
        )
        
        assert "recommended_indexes" in result
        assert "confidence" in result
        mock_index_optimization.optimize_indexes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_performance_analysis(self, mock_query_performance):
        """Test query performance analysis."""
        from app.ai.query_performance_analysis import QueryPerformanceAnalyzer
        
        analyzer = QueryPerformanceAnalyzer()
        
        result = await analyzer.analyze_performance(
            "search error earliest=-1h | stats count by source"
        )
        
        assert "estimated_time_seconds" in result
        assert "complexity_score" in result
        assert "optimization_suggestions" in result
        mock_query_performance.analyze_performance.assert_called_once()
    
    def test_spl_command_complexity_calculation(self):
        """Test SPL command complexity calculation."""
        from app.ai.query_performance_analysis import QueryPerformanceAnalyzer
        
        analyzer = QueryPerformanceAnalyzer()
        
        # Simple query
        simple_complexity = analyzer.calculate_complexity("search error")
        assert simple_complexity < 0.5
        
        # Complex query
        complex_query = "search error earliest=-7d | stats count by source | eventstats avg(count) as avg_count | where count > avg_count * 2"
        complex_complexity = analyzer.calculate_complexity(complex_query)
        assert complex_complexity > 0.5
        
        # Complex query should have higher complexity
        assert complex_complexity > simple_complexity


class TestAIFeatures:
    """Test advanced AI features."""
    
    @pytest.mark.asyncio
    async def test_predictive_analytics(self, sample_ai_features_data):
        """Test predictive analytics functionality."""
        from app.ai.predictive_analytics import PredictiveAnalyzer
        
        analyzer = PredictiveAnalyzer()
        
        with patch.object(analyzer, '_train_model') as mock_train, \
             patch.object(analyzer, '_generate_forecast') as mock_forecast:
            
            mock_train.return_value = Mock(accuracy=0.92)
            mock_forecast.return_value = [
                {
                    "_time": "2024-01-01T13:00:00",
                    "predicted_count": 185,
                    "confidence_interval": [170, 200]
                }
            ]
            
            result = await analyzer.forecast(
                sample_ai_features_data["predictive_analytics"]["time_series_data"],
                "24h",
                0.85
            )
            
            assert "forecast" in result
            assert "model_accuracy" in result
            assert len(result["forecast"]) > 0
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, sample_ai_features_data):
        """Test anomaly detection functionality."""
        from app.ai.anomaly_detection import AnomalyDetector
        
        detector = AnomalyDetector()
        
        with patch.object(detector, '_calculate_baseline_stats') as mock_baseline, \
             patch.object(detector, '_detect_statistical_anomaly') as mock_detect:
            
            mock_baseline.return_value = {
                "mean": 101.2,
                "std_dev": 2.8
            }
            
            mock_detect.return_value = {
                "is_anomaly": True,
                "score": 4.2,
                "severity": "high"
            }
            
            result = await detector.detect_anomaly(
                sample_ai_features_data["anomaly_detection"]["current_value"],
                sample_ai_features_data["anomaly_detection"]["baseline_data"],
                3.0
            )
            
            assert result["is_anomaly"] is True
            assert result["severity"] == "high"
            assert result["score"] == 4.2
    
    @pytest.mark.asyncio
    async def test_intelligent_suggestions(self, sample_ai_features_data):
        """Test intelligent query suggestions."""
        from app.ai.intelligent_suggestions import SuggestionEngine
        
        engine = SuggestionEngine()
        
        with patch.object(engine, '_analyze_query_patterns') as mock_analyze, \
             patch.object(engine, '_generate_context_suggestions') as mock_generate:
            
            mock_analyze.return_value = {
                "primary_intent": "error_investigation",
                "patterns": ["time_based_analysis", "source_breakdown"]
            }
            
            mock_generate.return_value = [
                {
                    "query": "search error earliest=-1h | stats count by source",
                    "confidence": 0.9,
                    "reasoning": "Based on your recent error analysis pattern"
                }
            ]
            
            result = await engine.generate_suggestions(
                sample_ai_features_data["intelligent_suggestions"]["query_history"],
                "security_analysis",
                5
            )
            
            assert "suggestions" in result
            assert len(result["suggestions"]) > 0
            assert result["suggestions"][0]["confidence"] > 0.8


class TestSpecializedServices:
    """Test specialized service components."""
    
    def test_spl_mapping_service(self):
        """Test SPL mapping service functionality."""
        from app.ai.spl_mapping import SPLMappingService
        
        service = SPLMappingService()
        
        # Test basic search mapping
        result = service.map_natural_language_to_spl(
            "show me errors",
            "search"
        )
        
        assert result["base_command"] == "search"
        assert "error" in result["search_terms"]
    
    def test_statistical_functions_mapping(self):
        """Test statistical functions mapping."""
        from app.ai.statistical_functions import StatisticalFunctionMapper
        
        mapper = StatisticalFunctionMapper()
        
        # Test aggregation mapping
        result = mapper.map_aggregation("count by source")
        
        assert result["function"] == "stats"
        assert result["aggregation"] == "count"
        assert result["groupby"] == "source"
    
    def test_regex_pattern_matching(self):
        """Test regex pattern matching service."""
        from app.ai.regex_pattern_matching import RegexPatternService
        
        service = RegexPatternService()
        
        # Test IP address detection
        result = service.detect_patterns("find IP addresses like 192.168.1.1")
        
        assert "ip_address" in result["detected_patterns"]
        assert len(result["regex_suggestions"]) > 0
    
    def test_lookup_table_integration(self):
        """Test lookup table integration service."""
        from app.ai.lookup_table_integration import LookupTableService
        
        service = LookupTableService()
        
        # Test lookup suggestion
        result = service.suggest_lookups(
            "search user_activity | lookup user_info user OUTPUT department"
        )
        
        assert "suggested_lookups" in result
        assert len(result["suggested_lookups"]) >= 0
    
    def test_advanced_aggregation_service(self):
        """Test advanced aggregation service."""
        from app.ai.advanced_aggregation import AdvancedAggregationService
        
        service = AdvancedAggregationService()
        
        # Test complex aggregation mapping
        result = service.build_aggregation(
            "calculate average response time by hour and server"
        )
        
        assert "function" in result
        assert "timechart" in result["function"] or "stats" in result["function"]


class TestServiceIntegration:
    """Test service integration and workflow."""
    
    @pytest.mark.asyncio
    async def test_full_translation_workflow(
        self, 
        mock_settings,
        mock_openai_client,
        mock_time_range_optimizer,
        sample_user_context
    ):
        """Test complete translation workflow."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.multiple(
            service,
            _call_ai_provider=AsyncMock(return_value={
                "spl": "search error",
                "confidence": 0.85,
                "explanation": "Basic error search"
            }),
            _apply_optimizations=AsyncMock(return_value={
                "spl": "search index=main error earliest=-1h",
                "confidence": 0.85,
                "explanation": "Optimized error search",
                "optimization": {"time_range_optimized": True}
            }),
            _validate_result=AsyncMock(return_value=True)
        ):
            
            result = await service.translate_query(
                "show me recent errors",
                sample_user_context,
                optimize=True,
                validate=True
            )
            
            assert "search" in result["spl"]
            assert "index=main" in result["spl"]
            assert "earliest=-1h" in result["spl"]
            assert result["optimization"]["time_range_optimized"] is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self, 
        mock_settings,
        sample_user_context
    ):
        """Test error recovery in service workflow."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        with patch.object(service, '_call_ai_provider') as mock_primary, \
             patch.object(service, '_fallback_translation') as mock_fallback:
            
            # Primary provider fails
            mock_primary.side_effect = Exception("Primary provider failed")
            
            # Fallback succeeds
            mock_fallback.return_value = {
                "spl": "search error",
                "confidence": 0.6,
                "explanation": "Fallback translation"
            }
            
            result = await service.translate_query(
                "show me errors",
                sample_user_context
            )
            
            assert result["spl"] == "search error"
            assert result["confidence"] == 0.6
            mock_primary.assert_called_once()
            mock_fallback.assert_called_once()


class TestCaching:
    """Test caching functionality."""
    
    @pytest.mark.asyncio
    async def test_query_result_caching(self, mock_redis):
        """Test query result caching."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        # Mock cache hit
        mock_redis.get.return_value = json.dumps({
            "spl": "search error earliest=-1h",
            "confidence": 0.95,
            "explanation": "Cached result"
        }).encode()
        
        with patch.object(service, '_call_ai_provider') as mock_ai:
            result = await service.translate_query(
                "show me errors from the last hour",
                {"user_id": "test"}
            )
            
            assert result["spl"] == "search error earliest=-1h"
            assert result["explanation"] == "Cached result"
            # AI provider should not be called for cache hit
            mock_ai.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss_workflow(self, mock_redis):
        """Test cache miss workflow."""
        from app.ai.nlp_service import NLPService
        
        service = NLPService()
        
        # Mock cache miss
        mock_redis.get.return_value = None
        
        with patch.object(service, '_call_ai_provider') as mock_ai:
            mock_ai.return_value = {
                "spl": "search error earliest=-1h",
                "confidence": 0.95,
                "explanation": "Fresh result"
            }
            
            result = await service.translate_query(
                "show me errors from the last hour",
                {"user_id": "test"}
            )
            
            assert result["spl"] == "search error earliest=-1h"
            # AI provider should be called for cache miss
            mock_ai.assert_called_once()
            # Result should be cached
            mock_redis.set.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])